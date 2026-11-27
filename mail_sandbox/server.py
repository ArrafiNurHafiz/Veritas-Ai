"""Minimal RFC-compliant SMTP catcher (:1025) + FastAPI Web Inbox UI (:8025)."""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timezone
from email import policy
from email.parser import BytesParser
import html
import os
from pathlib import Path
import sqlite3
from typing import Any, Iterator
import uuid

from fastapi import FastAPI
from fastapi.responses import HTMLResponse


def default_db_path() -> str:
    return os.environ.get("MAIL_SANDBOX_DB", "").strip() or str(
        Path(__file__).resolve().parent / "mail_sandbox.db"
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
            CREATE TABLE IF NOT EXISTS captured_emails (
                id TEXT PRIMARY KEY,
                mail_from TEXT NOT NULL,
                rcpt_to TEXT NOT NULL,
                subject TEXT NOT NULL,
                text_body TEXT NOT NULL,
                html_body TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )


def save_captured_email(
    *,
    mail_from: str,
    rcpt_to: list[str],
    raw_bytes: bytes,
    db_path: str | None = None,
) -> dict[str, Any]:
    parsed = BytesParser(policy=policy.default).parsebytes(raw_bytes)
    subject = str(parsed.get("Subject") or "(no subject)")
    text_body = ""
    html_body = ""
    if parsed.is_multipart():
        for part in parsed.walk():
            ctype = part.get_content_type()
            if ctype == "text/plain" and not text_body:
                text_body = part.get_content()
            elif ctype == "text/html" and not html_body:
                html_body = part.get_content()
    else:
        content = parsed.get_content()
        if parsed.get_content_type() == "text/html":
            html_body = str(content)
        else:
            text_body = str(content)

    msg_id = f"mail_{uuid.uuid4().hex[:12]}"
    now = _utc_now()
    with db_conn(db_path) as conn:
        conn.execute(
            """
            INSERT INTO captured_emails (id, mail_from, rcpt_to, subject, text_body, html_body, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (msg_id, mail_from, ", ".join(rcpt_to), subject, str(text_body), str(html_body), now),
        )
        row = conn.execute("SELECT * FROM captured_emails WHERE id = ?", (msg_id,)).fetchone()
        return dict(row)


def list_captured_emails(db_path: str | None = None) -> list[dict[str, Any]]:
    with db_conn(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM captured_emails ORDER BY created_at DESC, id DESC LIMIT 100"
        ).fetchall()
        return [dict(r) for r in rows]


async def _handle_smtp_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    writer.write(b"220 veritas-mail-sandbox ESMTP\r\n")
    await writer.drain()
    mail_from = ""
    rcpt_to: list[str] = []
    in_data = False
    data_lines: list[bytes] = []

    try:
        while True:
            raw_line = await reader.readline()
            if not raw_line:
                break
            if in_data:
                stripped = raw_line.rstrip(b"\r\n")
                if stripped == b".":
                    in_data = False
                    raw_msg = b"\r\n".join(
                        line[1:] if line.startswith(b"..") else line for line in data_lines
                    )
                    save_captured_email(mail_from=mail_from, rcpt_to=rcpt_to, raw_bytes=raw_msg)
                    data_lines = []
                    writer.write(b"250 2.0.0 Ok: queued in mail_sandbox\r\n")
                    await writer.drain()
                else:
                    data_lines.append(stripped)
                continue

            cmd = raw_line.decode("utf-8", errors="replace").strip()
            upper = cmd.upper()
            if upper.startswith("EHLO") or upper.startswith("HELO"):
                writer.write(b"250-veritas-mail-sandbox\r\n250 SIZE 10485760\r\n")
            elif upper.startswith("MAIL FROM:"):
                mail_from = cmd.split(":", 1)[1].strip().strip("<>")
                rcpt_to = []
                writer.write(b"250 2.1.0 Ok\r\n")
            elif upper.startswith("RCPT TO:"):
                rcpt_to.append(cmd.split(":", 1)[1].strip().strip("<>"))
                writer.write(b"250 2.1.5 Ok\r\n")
            elif upper == "DATA":
                in_data = True
                data_lines = []
                writer.write(b"354 End data with <CR><LF>.<CR><LF>\r\n")
            elif upper == "RSET":
                mail_from = ""
                rcpt_to = []
                writer.write(b"250 2.0.0 Ok\r\n")
            elif upper == "NOOP":
                writer.write(b"250 2.0.0 Ok\r\n")
            elif upper == "QUIT":
                writer.write(b"221 2.0.0 Bye\r\n")
                await writer.drain()
                break
            else:
                writer.write(b"250 Ok\r\n")
            await writer.drain()
    finally:
        writer.close()
        await writer.wait_closed()


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    smtp_host = os.environ.get("MAIL_SANDBOX_SMTP_HOST", "127.0.0.1")
    smtp_port = int(os.environ.get("MAIL_SANDBOX_SMTP_PORT", "1025"))
    smtp_server = await asyncio.start_server(_handle_smtp_client, smtp_host, smtp_port)
    try:
        yield
    finally:
        smtp_server.close()
        await smtp_server.wait_closed()


app = FastAPI(
    title="VERITAS Mail Sandbox",
    version="1.0.0",
    description="Local SMTP catcher (:1025) and approval email inbox viewer (:8025).",
    lifespan=lifespan,
)


@app.get("/health/live")
def health_live() -> dict[str, str]:
    return {"status": "ok", "service": "mail-sandbox"}


@app.get("/api/messages")
def api_list_messages() -> dict[str, Any]:
    items = list_captured_emails()
    return {"messages": items, "total_count": len(items)}


@app.get("/", response_class=HTMLResponse)
def inbox_ui() -> str:
    items = list_captured_emails()
    cards = []
    for item in items:
        body_preview = html.escape(item["text_body"] or "(empty)").replace("\n", "<br/>")
        cards.append(
            f"""
            <div class="card">
              <div style="display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;">
                <strong style="font-size:16px;">{html.escape(item['subject'])}</strong>
                <span style="font-family:monospace;font-size:12px;color:#64748b;">{html.escape(item['created_at'])}</span>
              </div>
              <div style="margin:6px 0 12px;font-size:12px;color:#475569;">
                <strong>From:</strong> {html.escape(item['mail_from'])} &nbsp;|&nbsp;
                <strong>To:</strong> {html.escape(item['rcpt_to'])}
              </div>
              <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:12px;font-size:13px;line-height:1.5;">
                {body_preview}
              </div>
            </div>
            """
        )
    cards_html = "\n".join(cards) if cards else '<div class="card">Belum ada email approval yang masuk. Buat task invoice di atas batas auto-approve (&gt; Rp 5.000.000) untuk memicu email.</div>'
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>VERITAS Mail Sandbox — Approval Inbox</title>
  <style>
    body {{ font-family: system-ui, -apple-system, sans-serif; background:#f8fafc; color:#0f172a; margin:0; padding:32px; }}
    .wrap {{ max-width:960px; margin:0 auto; }}
    .card {{ background:#fff; border:1px solid #e2e8f0; border-radius:14px; padding:18px; margin-bottom:16px; }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card" style="display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap;">
      <div>
        <div style="font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:#64748b;font-weight:600;">Local SMTP Catcher (:1025) &amp; Inbox (:8025)</div>
        <h1 style="margin:4px 0 6px;font-size:24px;">VERITAS Approval Email Inbox</h1>
        <div style="font-size:13px;color:#475569;">Menangkap email approval yang dikirim via SMTP sebelum memakai SMTP perusahaan asli.</div>
      </div>
      <div style="text-align:right;">
        <div style="font-size:22px;font-weight:700;font-family:monospace;">{len(items)} emails</div>
        <button onclick="location.reload()" style="margin-top:6px;padding:6px 12px;border:1px solid #cbd5e1;border-radius:8px;background:#fff;cursor:pointer;">Refresh</button>
      </div>
    </div>
    {cards_html}
  </div>
</body>
</html>"""
