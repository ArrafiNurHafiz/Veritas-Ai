"""Standalone ERP Sandbox service (port 8003) with webhook receiver and transaction ledger UI."""
from __future__ import annotations

import hashlib
import hmac
import html
import json
import os
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse
import httpx
from pydantic import BaseModel, Field

from .db import (
    get_transaction,
    init_db,
    list_transactions,
    record_erp_submission,
    record_webhook_transaction,
    reverse_transaction,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="VERITAS ERP Sandbox",
    version="1.0.0",
    description="Standalone mock ERP ledger & webhook receiver before connecting a real company ERP.",
    lifespan=lifespan,
)


def _verify_bearer(auth_header: str | None) -> None:
    expected = os.environ.get("ERP_SANDBOX_API_KEY", "").strip()
    if not expected:
        return
    if auth_header != f"Bearer {expected}":
        raise HTTPException(status_code=401, detail="Invalid ERP bearer token.")


def _verify_hmac(raw_body: bytes, signature_header: str | None) -> bool:
    secret = os.environ.get("ERP_SANDBOX_HMAC_SECRET", "").strip()
    if not secret:
        return False
    if not signature_header or not signature_header.startswith("sha256="):
        raise HTTPException(status_code=401, detail="Missing or malformed X-Veritas-Signature.")
    expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    provided = signature_header.split("=", 1)[1].strip()
    if not hmac.compare_digest(expected, provided):
        raise HTTPException(status_code=401, detail="Invalid X-Veritas-Signature.")
    return True


@app.get("/health/live")
def health_live() -> dict[str, str]:
    return {"status": "ok", "service": "erp-sandbox"}


@app.post("/api/erp/webhook")
async def receive_erp_webhook(
    request: Request,
    authorization: str | None = Header(default=None),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    x_veritas_signature: str | None = Header(default=None, alias="X-Veritas-Signature"),
    x_veritas_erp_adapter: str | None = Header(default=None, alias="X-Veritas-ERP-Adapter"),
) -> dict[str, Any]:
    _verify_bearer(authorization)
    raw_body = await request.body()
    sig_ok = _verify_hmac(raw_body, x_veritas_signature)
    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON payload.") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Payload must be a JSON object.")

    idem = (idempotency_key or "").strip() or f"erp-idem-{uuid.uuid4().hex[:12]}"
    tx, is_replay = record_webhook_transaction(
        idempotency_key=idem,
        payload=payload,
        adapter_hint=(x_veritas_erp_adapter or "").strip().lower(),
        signature_verified=sig_ok,
    )
    return {
        "ok": True,
        "idempotent_replay": is_replay,
        "transaction_id": tx["id"],
        "journal_number": tx["journal_number"],
        "status": tx["status"],
        "amount_idr": tx["amount_idr"],
    }


@app.get("/api/erp/transactions")
def api_list_transactions() -> dict[str, Any]:
    rows = list_transactions()
    posted_total = sum(int(r["amount_idr"]) for r in rows if r["status"] == "POSTED")
    return {
        "transactions": rows,
        "total_count": len(rows),
        "total_posted_idr": posted_total,
    }


@app.get("/api/erp/transactions/{tx_id}")
def api_get_transaction(tx_id: str) -> dict[str, Any]:
    tx = get_transaction(tx_id)
    if tx is None:
        raise HTTPException(status_code=404, detail="ERP transaction not found.")
    return tx


@app.post("/api/erp/transactions/{tx_id}/reverse")
def api_reverse_transaction(tx_id: str) -> dict[str, Any]:
    tx = reverse_transaction(tx_id)
    if tx is None:
        raise HTTPException(status_code=404, detail="ERP transaction not found.")
    return tx


class ErpSubmitRequest(BaseModel):
    invoice_id: str = Field(..., min_length=1)
    vendor_code: str = Field(..., min_length=1)
    amount: float = Field(..., gt=0)
    currency: str = Field(default="IDR")
    description: str = Field(default="ERP invoice submission")


@app.post("/api/erp/submit-to-veritas")
def api_submit_to_veritas(body: ErpSubmitRequest) -> dict[str, Any]:
    """Create a transaction in ERP Sandbox and submit it directly to VERITAS AI."""
    harness_url = os.environ.get("VERITAS_HARNESS_URL", "http://127.0.0.1:8002").rstrip("/")
    idem_key = f"erp-submit-{uuid.uuid4().hex[:16]}"
    try:
        with httpx.Client(base_url=harness_url, timeout=15.0) as client:
            auth_res = client.get(
                "/api/v1/auth/test-login",
                params={"role": "operator", "email": "erp-sync@veritas.local"},
            )
            if auth_res.status_code >= 400:
                raise HTTPException(
                    status_code=502,
                    detail=f"VERITAS auth failed ({auth_res.status_code}): {auth_res.text}",
                )
            csrf_token = ""
            for name, val in client.cookies.items():
                if "csrf" in name.lower():
                    csrf_token = val
                    break
            headers = {"Idempotency-Key": idem_key}
            if csrf_token:
                headers["X-CSRF-Token"] = csrf_token
            task_res = client.post(
                "/api/v1/tasks",
                headers=headers,
                json={
                    "task_type": "invoice_review",
                    "payload": {
                        "invoice_id": body.invoice_id.strip(),
                        "vendor": body.vendor_code.strip(),
                        "amount": body.amount,
                        "currency": body.currency.strip().upper(),
                        "description": body.description.strip(),
                    },
                },
            )
            if task_res.status_code >= 400:
                raise HTTPException(
                    status_code=502,
                    detail=f"VERITAS task error ({task_res.status_code}): {task_res.text}",
                )
            veritas_data = task_res.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Failed to reach VERITAS AI: {exc}") from exc

    veritas_status = str(veritas_data.get("status") or "PENDING")
    erp_status = "POSTED" if veritas_status == "SUCCEEDED" else veritas_status
    payload_obj: dict[str, Any] = {}
    try:
        payload_obj = json.loads(veritas_data.get("payload_json") or "{}")
    except Exception:
        payload_obj = {}
    amount_idr = int(payload_obj.get("amount_idr") or round(body.amount))

    tx = record_erp_submission(
        execution_id=str(veritas_data.get("id") or ""),
        tenant_id=str(veritas_data.get("tenant_id") or "default"),
        invoice_id=body.invoice_id.strip(),
        vendor_code=body.vendor_code.strip(),
        amount_idr=amount_idr,
        currency=body.currency.strip().upper(),
        status=erp_status,
        description=body.description.strip(),
        raw_payload=veritas_data,
    )
    return {
        "ok": True,
        "transaction": tx,
        "veritas": {
            "execution_id": veritas_data.get("id"),
            "status": veritas_status,
            "decision": veritas_data.get("decision"),
            "reason_code": veritas_data.get("reason_code"),
            "approval_id": veritas_data.get("approval_id"),
            "receipt_id": veritas_data.get("receipt_id"),
        },
    }


@app.get("/", response_class=HTMLResponse)
def erp_console() -> str:
    rows = list_transactions()
    posted_total = sum(int(r["amount_idr"]) for r in rows if r["status"] == "POSTED")
    row_html = []
    for r in rows:
        status = str(r["status"])
        if status == "POSTED":
            badge_bg, badge_fg = "#dcfce7", "#166534"
        elif status == "WAITING_APPROVAL":
            badge_bg, badge_fg = "#fef3c7", "#92400e"
        else:
            badge_bg, badge_fg = "#fee2e2", "#991b1b"
        action_btn = (
            f'<button onclick="reverseTx(\'{html.escape(r["id"])}\')" '
            'style="padding:4px 10px;border:1px solid #d4d4d8;border-radius:6px;background:#fff;cursor:pointer;">Reverse</button>'
            if status == "POSTED"
            else f'<span style="color:#71717a;font-size:12px;">{html.escape(status)}</span>'
        )
        row_html.append(
            f"<tr>"
            f"<td style='font-family:monospace;font-weight:600'>{html.escape(r['journal_number'])}</td>"
            f"<td>{html.escape(r['invoice_id'])}</td>"
            f"<td style='font-family:monospace'>{html.escape(r['vendor_code'])}</td>"
            f"<td style='text-align:right;font-family:monospace'>Rp {int(r['amount_idr']):,}</td>"
            f"<td>{html.escape(r['currency'])}</td>"
            f"<td><span style='padding:2px 8px;border-radius:999px;font-size:11px;font-weight:600;background:{badge_bg};color:{badge_fg}'>{html.escape(status)}</span></td>"
            f"<td style='font-family:monospace;font-size:12px'>{html.escape(r['adapter_format'])}</td>"
            f"<td style='font-size:12px;color:#52525b'>{html.escape(r['description'])}</td>"
            f"<td style='font-family:monospace;font-size:11px;color:#71717a'>{html.escape(r['created_at'])}</td>"
            f"<td>{action_btn}</td>"
            f"</tr>"
        )
    table_body = "\n".join(row_html)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>VERITAS ERP Sandbox — General Ledger</title>
  <style>
    body {{ font-family: system-ui, -apple-system, sans-serif; background:#f8fafc; color:#0f172a; margin:0; padding:32px; }}
    .wrap {{ max-width:1180px; margin:0 auto; }}
    .card {{ background:#fff; border:1px solid #e2e8f0; border-radius:14px; padding:20px; margin-bottom:20px; }}
    .grid {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap:12px; }}
    label {{ display:block; font-size:11px; text-transform:uppercase; letter-spacing:.05em; color:#64748b; margin-bottom:4px; font-weight:600; }}
    input, select {{ width:100%; box-sizing:border-box; padding:8px 10px; border:1px solid #cbd5e1; border-radius:8px; font-size:13px; }}
    .btn-primary {{ background:#0f172a; color:#a8ff53; border:none; border-radius:8px; padding:10px 16px; font-weight:600; cursor:pointer; font-size:13px; }}
    table {{ width:100%; border-collapse:collapse; font-size:13px; }}
    th, td {{ padding:10px 12px; border-bottom:1px solid #f1f5f9; text-align:left; }}
    th {{ font-size:11px; text-transform:uppercase; letter-spacing:.06em; color:#64748b; background:#f8fafc; }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card" style="display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap;">
      <div>
        <div style="font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:#64748b;font-weight:600;">Standalone ERP Sandbox (:8003)</div>
        <h1 style="margin:4px 0 6px;font-size:24px;">ERP General Ledger &amp; VERITAS Sync</h1>
        <div style="font-size:13px;color:#475569;">Webhook target: <code>POST http://127.0.0.1:8003/api/erp/webhook</code> &nbsp;|&nbsp; VERITAS Console: <a href="http://localhost:3000/dashboard" target="_blank">http://localhost:3000/dashboard</a></div>
      </div>
      <div style="text-align:right;">
        <div style="font-size:11px;text-transform:uppercase;color:#64748b;">Total Posted Ledger</div>
        <div style="font-size:24px;font-weight:700;font-family:monospace;">Rp {posted_total:,}</div>
        <div style="font-size:12px;color:#64748b;">{len(rows)} transactions recorded</div>
      </div>
    </div>

    <div class="card">
      <h2 style="margin:0 0 12px;font-size:16px;">Tambah Transaksi di ERP &amp; Kirim ke VERITAS AI</h2>
      <form id="erpForm" onsubmit="submitToVeritas(event)">
        <div class="grid">
          <div>
            <label>Invoice ID</label>
            <input id="invoice_id" required value="INV-ERP-{len(rows) + 101}" />
          </div>
          <div>
            <label>Vendor</label>
            <input id="vendor_code" required value="ABC" placeholder="ABC / XYZ / V-NEW" />
          </div>
          <div>
            <label>Amount</label>
            <input id="amount" type="number" step="any" min="1" required value="1200000" />
          </div>
          <div>
            <label>Currency</label>
            <select id="currency">
              <option value="IDR">IDR</option>
              <option value="USD">USD</option>
              <option value="SGD">SGD</option>
              <option value="EUR">EUR</option>
            </select>
          </div>
          <div>
            <label>Description</label>
            <input id="description" value="Procurement invoice from ERP" />
          </div>
        </div>
        <div style="margin-top:14px;display:flex;align-items:center;gap:12px;flex-wrap:wrap;">
          <button id="submitBtn" class="btn-primary" type="submit">Tambah Transaksi &amp; Kirim ke VERITAS</button>
          <span id="formStatus" style="font-size:13px;color:#475569;"></span>
        </div>
      </form>
    </div>

    <div class="card" style="overflow-x:auto;">
      <table>
        <thead>
          <tr>
            <th>Journal #</th>
            <th>Invoice</th>
            <th>Vendor</th>
            <th style="text-align:right;">Amount (IDR)</th>
            <th>CCY</th>
            <th>Status</th>
            <th>Source</th>
            <th>Description</th>
            <th>Created</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          {table_body}
        </tbody>
      </table>
    </div>
  </div>
  <script>
    async function submitToVeritas(e) {{
      e.preventDefault();
      const btn = document.getElementById('submitBtn');
      const status = document.getElementById('formStatus');
      btn.disabled = true;
      status.textContent = 'Mengirim ke VERITAS AI...';
      try {{
        const res = await fetch('/api/erp/submit-to-veritas', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{
            invoice_id: document.getElementById('invoice_id').value,
            vendor_code: document.getElementById('vendor_code').value,
            amount: Number(document.getElementById('amount').value),
            currency: document.getElementById('currency').value,
            description: document.getElementById('description').value,
          }}),
        }});
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Gagal mengirim ke VERITAS');
        status.textContent = 'Hasil VERITAS: ' + data.veritas.status + ' (' + (data.veritas.reason_code || 'OK') + ')';
        setTimeout(() => location.reload(), 600);
      }} catch (err) {{
        status.textContent = 'Error: ' + err.message;
        btn.disabled = false;
      }}
    }}
    async function reverseTx(id) {{
      await fetch('/api/erp/transactions/' + encodeURIComponent(id) + '/reverse', {{ method: 'POST' }});
      location.reload();
    }}
  </script>
</body>
</html>"""
