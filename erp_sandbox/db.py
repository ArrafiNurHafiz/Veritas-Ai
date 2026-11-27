"""SQLite persistence for the standalone ERP Sandbox ledger and transactions."""
from __future__ import annotations

import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


def default_db_path() -> str:
    return os.environ.get("ERP_SANDBOX_DB", "").strip() or str(
        Path(__file__).resolve().parent / "erp_sandbox.db"
    )


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@contextmanager
def db_conn(db_path: str | None = None) -> Iterator[sqlite3.Connection]:
    path = db_path or default_db_path()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: str | None = None) -> None:
    with db_conn(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS erp_transactions (
                id TEXT PRIMARY KEY,
                journal_number TEXT NOT NULL UNIQUE,
                idempotency_key TEXT NOT NULL UNIQUE,
                execution_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                adapter_format TEXT NOT NULL,
                tool_name TEXT NOT NULL,
                invoice_id TEXT NOT NULL,
                vendor_code TEXT NOT NULL,
                amount_idr INTEGER NOT NULL,
                currency TEXT NOT NULL,
                status TEXT NOT NULL,
                description TEXT NOT NULL,
                signature_verified INTEGER NOT NULL DEFAULT 0,
                raw_payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
    seed_initial_transactions(db_path)


def seed_initial_transactions(db_path: str | None = None) -> None:
    """Populate baseline ERP transactions once so the ledger is immediately usable."""
    with db_conn(db_path) as conn:
        existing = conn.execute("SELECT COUNT(*) FROM erp_transactions").fetchone()[0]
        if existing > 0:
            return
        now = _utc_now()
        seeds = [
            (
                "erp_tx_seed_001",
                "ERP-JRN-2026-0001",
                "seed-erp-0001",
                "exec_seed_0001",
                "tenant-a",
                "webhook",
                "approve_invoice",
                "INV-2026-0891",
                "V-ABC",
                2_450_000,
                "IDR",
                "POSTED",
                "Monthly cloud compute & managed database cluster",
                1,
                json.dumps({"source": "erp_seed", "invoice_id": "INV-2026-0891", "vendor_code": "V-ABC"}),
                now,
                now,
            ),
            (
                "erp_tx_seed_002",
                "ERP-JRN-2026-0002",
                "seed-erp-0002",
                "exec_seed_0002",
                "tenant-a",
                "odoo",
                "approve_invoice",
                "INV-2026-0892",
                "V-XYZ",
                4_800_000,
                "IDR",
                "POSTED",
                "Warehouse logistics & freight settlement",
                1,
                json.dumps({"source": "erp_seed", "invoice_id": "INV-2026-0892", "vendor_code": "V-XYZ"}),
                now,
                now,
            ),
            (
                "erp_tx_seed_003",
                "ERP-JRN-2026-0003",
                "seed-erp-0003",
                "exec_seed_0003",
                "tenant-a",
                "sap",
                "approve_invoice",
                "INV-2026-0893",
                "V-ABC",
                16_000_000,
                "USD",
                "POSTED",
                "Annual enterprise security & SOC2 audit retainer (USD 1,000)",
                1,
                json.dumps({"source": "erp_seed", "invoice_id": "INV-2026-0893", "vendor_code": "V-ABC"}),
                now,
                now,
            ),
        ]
        conn.executemany(
            """
            INSERT INTO erp_transactions (
                id, journal_number, idempotency_key, execution_id, tenant_id,
                adapter_format, tool_name, invoice_id, vendor_code, amount_idr,
                currency, status, description, signature_verified, raw_payload_json,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            seeds,
        )


def _next_journal_number(conn: sqlite3.Connection) -> str:
    count = conn.execute("SELECT COUNT(*) FROM erp_transactions").fetchone()[0]
    return f"ERP-JRN-2026-{count + 1:04d}"


def extract_erp_fields(payload: dict[str, Any], adapter_hint: str = "") -> dict[str, Any]:
    """Normalize webhook, Odoo JSON-RPC, or SAP OData payloads into ledger fields."""
    if "params" in payload and isinstance(payload["params"], dict):
        params = payload["params"]
        vals = params.get("vals") if isinstance(params.get("vals"), dict) else {}
        return {
            "adapter_format": adapter_hint or "odoo",
            "execution_id": str(params.get("veritas_execution_id") or ""),
            "tenant_id": str(params.get("tenant_id") or "tenant-a"),
            "tool_name": str(params.get("tool") or "approve_invoice"),
            "status": str(payload.get("status") or params.get("status") or "POSTED").upper(),
            "invoice_id": str(vals.get("ref") or ""),
            "vendor_code": str(vals.get("partner_code") or "UNKNOWN"),
            "amount_idr": int(vals.get("amount_total") or 0),
            "currency": str(vals.get("currency") or "IDR"),
            "description": str(vals.get("narration") or "Odoo journal posting"),
        }

    if "DocumentType" in payload and "ReferenceDocument" in payload:
        return {
            "adapter_format": adapter_hint or "sap",
            "execution_id": str(payload.get("VeritasExecutionId") or ""),
            "tenant_id": str(payload.get("CompanyCode") or "tenant-a"),
            "tool_name": str(payload.get("Tool") or "approve_invoice"),
            "status": str(payload.get("status") or "POSTED").upper(),
            "invoice_id": str(payload.get("ReferenceDocument") or ""),
            "vendor_code": str(payload.get("VendorAccount") or "UNKNOWN"),
            "amount_idr": int(payload.get("AmountInTransactionCurrency") or 0),
            "currency": str(payload.get("Currency") or "IDR"),
            "description": str(
                (payload.get("RawArguments") or {}).get("description") or "SAP FI document posting"
            ),
        }

    args = payload.get("arguments") if isinstance(payload.get("arguments"), dict) else {}
    return {
        "adapter_format": adapter_hint or "webhook",
        "execution_id": str(payload.get("execution_id") or ""),
        "tenant_id": str(payload.get("tenant_id") or "tenant-a"),
        "tool_name": str(payload.get("tool") or "approve_invoice"),
        "status": str(payload.get("status") or "POSTED").upper(),
        "invoice_id": str(args.get("invoice_id") or args.get("reference_id") or ""),
        "vendor_code": str(
            args.get("vendor_id")
            or args.get("vendor_code")
            or args.get("vendor")
            or args.get("account_code")
            or "UNKNOWN"
        ),
        "amount_idr": int(args.get("amount_idr") or 0),
        "currency": str(args.get("currency") or "IDR"),
        "description": str(
            args.get("description") or args.get("reason") or "VERITAS approved ERP posting"
        ),
    }


def record_webhook_transaction(
    *,
    idempotency_key: str,
    payload: dict[str, Any],
    adapter_hint: str = "",
    signature_verified: bool = False,
    db_path: str | None = None,
) -> tuple[dict[str, Any], bool]:
    """Insert a posted ERP transaction idempotently. Returns (row_dict, is_replay)."""
    with db_conn(db_path) as conn:
        existing = conn.execute(
            "SELECT * FROM erp_transactions WHERE idempotency_key = ?",
            (idempotency_key,),
        ).fetchone()
        if existing is not None:
            return dict(existing), True

        fields = extract_erp_fields(payload, adapter_hint=adapter_hint)
        raw_status = str(fields.get("status") or payload.get("status") or "POSTED").upper()
        target_status = raw_status if raw_status in {"POSTED", "REJECTED", "DENIED", "REVERSED"} else "POSTED"
        now = _utc_now()
        if fields["execution_id"]:
            by_exec = conn.execute(
                "SELECT * FROM erp_transactions WHERE execution_id = ?",
                (fields["execution_id"],),
            ).fetchone()
            if by_exec is not None:
                conn.execute(
                    """
                    UPDATE erp_transactions
                    SET status = ?,
                        idempotency_key = ?,
                        adapter_format = ?,
                        signature_verified = ?,
                        raw_payload_json = ?,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        target_status,
                        idempotency_key,
                        fields["adapter_format"],
                        1 if signature_verified else 0,
                        json.dumps(payload, sort_keys=True),
                        now,
                        by_exec["id"],
                    ),
                )
                updated = conn.execute(
                    "SELECT * FROM erp_transactions WHERE id = ?",
                    (by_exec["id"],),
                ).fetchone()
                return dict(updated), False

        tx_id = f"erp_tx_{uuid.uuid4().hex[:12]}"
        journal_number = _next_journal_number(conn)
        conn.execute(
            """
            INSERT INTO erp_transactions (
                id, journal_number, idempotency_key, execution_id, tenant_id,
                adapter_format, tool_name, invoice_id, vendor_code, amount_idr,
                currency, status, description, signature_verified, raw_payload_json,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tx_id,
                journal_number,
                idempotency_key,
                fields["execution_id"],
                fields["tenant_id"],
                fields["adapter_format"],
                fields["tool_name"],
                fields["invoice_id"] or f"INV-{tx_id[-6:].upper()}",
                fields["vendor_code"],
                fields["amount_idr"],
                fields["currency"],
                "POSTED",
                fields["description"],
                1 if signature_verified else 0,
                json.dumps(payload, sort_keys=True),
                now,
                now,
            ),
        )
        row = conn.execute("SELECT * FROM erp_transactions WHERE id = ?", (tx_id,)).fetchone()
        return dict(row), False


def record_erp_submission(
    *,
    execution_id: str,
    tenant_id: str,
    invoice_id: str,
    vendor_code: str,
    amount_idr: int,
    currency: str,
    status: str,
    description: str,
    raw_payload: dict[str, Any],
    db_path: str | None = None,
) -> dict[str, Any]:
    """Record or update an ERP-initiated transaction submitted to VERITAS AI."""
    with db_conn(db_path) as conn:
        now = _utc_now()
        if execution_id:
            existing = conn.execute(
                "SELECT * FROM erp_transactions WHERE execution_id = ?",
                (execution_id,),
            ).fetchone()
            if existing is not None:
                # Preserve POSTED if the VERITAS webhook already arrived first.
                next_status = "POSTED" if existing["status"] == "POSTED" else status
                conn.execute(
                    "UPDATE erp_transactions SET status = ?, updated_at = ? WHERE id = ?",
                    (next_status, now, existing["id"]),
                )
                row = conn.execute(
                    "SELECT * FROM erp_transactions WHERE id = ?", (existing["id"],)
                ).fetchone()
                return dict(row)

        tx_id = f"erp_tx_{uuid.uuid4().hex[:12]}"
        journal_number = _next_journal_number(conn)
        conn.execute(
            """
            INSERT INTO erp_transactions (
                id, journal_number, idempotency_key, execution_id, tenant_id,
                adapter_format, tool_name, invoice_id, vendor_code, amount_idr,
                currency, status, description, signature_verified, raw_payload_json,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tx_id,
                journal_number,
                f"erp-origin-{tx_id}",
                execution_id,
                tenant_id,
                "erp_origin",
                "approve_invoice",
                invoice_id,
                vendor_code,
                amount_idr,
                currency,
                status,
                description,
                1,
                json.dumps(raw_payload, sort_keys=True),
                now,
                now,
            ),
        )
        row = conn.execute("SELECT * FROM erp_transactions WHERE id = ?", (tx_id,)).fetchone()
        return dict(row)


def list_transactions(db_path: str | None = None) -> list[dict[str, Any]]:
    with db_conn(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM erp_transactions ORDER BY created_at DESC, journal_number DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def get_transaction(tx_id: str, db_path: str | None = None) -> dict[str, Any] | None:
    with db_conn(db_path) as conn:
        row = conn.execute("SELECT * FROM erp_transactions WHERE id = ?", (tx_id,)).fetchone()
        return dict(row) if row is not None else None


def reverse_transaction(tx_id: str, db_path: str | None = None) -> dict[str, Any] | None:
    with db_conn(db_path) as conn:
        row = conn.execute("SELECT * FROM erp_transactions WHERE id = ?", (tx_id,)).fetchone()
        if row is None:
            return None
        now = _utc_now()
        conn.execute(
            "UPDATE erp_transactions SET status = 'REVERSED', updated_at = ? WHERE id = ?",
            (now, tx_id),
        )
        updated = conn.execute("SELECT * FROM erp_transactions WHERE id = ?", (tx_id,)).fetchone()
        return dict(updated)
