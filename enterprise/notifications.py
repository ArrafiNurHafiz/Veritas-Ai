"""SMTP email notifications for human-in-the-loop approval gates."""
from __future__ import annotations

from email.message import EmailMessage
import html
import os
import smtplib
from typing import Iterable


def smtp_configured() -> bool:
    return bool(os.environ.get("SMTP_HOST", "").strip())


def send_approval_email(
    *,
    recipients: Iterable[str],
    execution_id: str,
    invoice_id: str,
    vendor_id: str,
    amount_idr: int,
    currency: str = "IDR",
    original_amount: int | None = None,
    reason_code: str = "AMOUNT_LIMIT",
) -> dict[str, object]:
    """Send an approval alert email via SMTP. Non-blocking on misconfiguration/outage."""
    clean_recipients = sorted({r.strip().lower() for r in recipients if r and "@" in r})
    extra = os.environ.get("VERITAS_APPROVAL_NOTIFY_EMAILS", "")
    for item in extra.split(","):
        if item.strip() and "@" in item:
            clean_recipients.append(item.strip().lower())
    clean_recipients = sorted(set(clean_recipients))

    if not clean_recipients:
        return {"sent": False, "reason": "no_recipients", "recipients": []}

    host = os.environ.get("SMTP_HOST", "").strip()
    if not host:
        return {"sent": False, "reason": "smtp_not_configured", "recipients": clean_recipients}

    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("SMTP_USER", "").strip()
    password = os.environ.get("SMTP_PASSWORD", "")
    sender = os.environ.get("SMTP_FROM", "").strip() or user or "noreply@veritas.internal"
    use_tls = os.environ.get("SMTP_USE_TLS", "1").strip().lower() in {"1", "true", "yes"}
    public_url = os.environ.get("VERITAS_PUBLIC_URL", "http://localhost:3000").rstrip("/")

    display_amt = (
        "Non-monetary gate"
        if amount_idr <= 0
        else (
            f"{currency} {original_amount:,} (≈ IDR {amount_idr:,})"
            if currency != "IDR" and original_amount is not None
            else f"IDR {amount_idr:,}"
        )
    )

    msg = EmailMessage()
    msg["Subject"] = f"[VERITAS AI] Approval Required: {invoice_id} ({display_amt})"
    msg["From"] = sender
    msg["To"] = ", ".join(clean_recipients)
    msg.set_content(
        "VERITAS AI Policy Gate held an agent action for human approval.\n\n"
        f"Execution ID : {execution_id}\n"
        f"Invoice ID   : {invoice_id}\n"
        f"Vendor       : {vendor_id}\n"
        f"Amount       : {display_amt}\n"
        f"Gate Reason  : {reason_code}\n\n"
        f"Review & Sign Off: {public_url}/dashboard/approvals\n"
    )
    msg.add_alternative(
        f"""<!doctype html>
<html>
  <body style="font-family:system-ui,-apple-system,sans-serif;background:#f8fafc;padding:24px;color:#0f172a;">
    <div style="max-width:560px;margin:0 auto;background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:24px;">
      <div style="font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:#64748b;font-weight:600;">VERITAS AI · Approval Gate</div>
      <h2 style="margin:6px 0 12px;font-size:20px;">Human Approval Required</h2>
      <p style="font-size:14px;color:#475569;margin:0 0 16px;">An autonomous agent action was held by deterministic policy and requires sign-off.</p>
      <table style="width:100%;border-collapse:collapse;font-size:13px;margin-bottom:20px;">
        <tr><td style="padding:6px 0;color:#64748b;">Execution ID</td><td style="padding:6px 0;font-family:monospace;">{html.escape(execution_id)}</td></tr>
        <tr><td style="padding:6px 0;color:#64748b;">Invoice ID</td><td style="padding:6px 0;font-weight:600;">{html.escape(invoice_id)}</td></tr>
        <tr><td style="padding:6px 0;color:#64748b;">Vendor</td><td style="padding:6px 0;font-family:monospace;">{html.escape(vendor_id)}</td></tr>
        <tr><td style="padding:6px 0;color:#64748b;">Amount</td><td style="padding:6px 0;font-weight:600;">{html.escape(display_amt)}</td></tr>
        <tr><td style="padding:6px 0;color:#64748b;">Gate Reason</td><td style="padding:6px 0;font-family:monospace;">{html.escape(reason_code)}</td></tr>
      </table>
      <a href="{html.escape(public_url)}/dashboard/approvals" style="display:inline-block;background:#121317;color:#a8ff53;text-decoration:none;padding:10px 18px;border-radius:8px;font-size:13px;font-weight:600;">Review &amp; Approve in VERITAS</a>
    </div>
  </body>
</html>""",
        subtype="html",
    )

    try:
        with smtplib.SMTP(host, port, timeout=5) as server:
            if use_tls:
                server.starttls()
            if user and password:
                server.login(user, password)
            server.send_message(msg)
        return {"sent": True, "recipients": clean_recipients}
    except Exception as exc:
        return {"sent": False, "reason": str(exc), "recipients": clean_recipients}
