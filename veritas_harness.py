"""VERITAS AI — Harness MVP slice (single service, single SQLite file).

Control Before Action: an agent proposal never invokes a protected tool until the
Harness policy check — and any required human approval — passes. Receipts are
Ed25519-signed; the anchor is a local mock and pending until explicitly confirmed.

Run:  uvicorn veritas_harness:app --port 8002
Test: .venv/bin/python tests/test_demo.py

ponytail: one process, one connection, one demo org, in-process mock receiver.
Upgrade path: per-service Postgres schemas, mTLS identities, real Besu adapter.
"""
from __future__ import annotations

import hashlib
import hmac
import html
import json
import os
import secrets
import sqlite3
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import Depends, FastAPI, Header, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse
from pydantic import BaseModel

from anchor_chain import AnchorError, enabled as chain_enabled, read_digest, submit_digest
from llm_planner import propose

# --------------------------------------------------------------------------- policy

ORG_ID = "org-nexora"
PROJECT_ID = "proj-procurement"
AGENT_ID = "procurement-agent"
POLICY_VERSION = 1

AUTO_LIMIT_IDR = 5_000_000
HARD_CAP_IDR = 25_000_000
ALLOWED_VENDORS = {"V-ABC", "V-XYZ"}
ALLOWED_DESTINATIONS = {"mock://crm", "mock://ledger"}
SENSITIVE_FIELDS = {"customer_secret", "api_key", "card_number"}
APPROVAL_TTL_SECONDS = 900

POLICY_SRC = {
    "auto_approve_limit_idr": AUTO_LIMIT_IDR,
    "hard_cap_idr": HARD_CAP_IDR,
    "vendors": sorted(ALLOWED_VENDORS),
    "destinations": sorted(ALLOWED_DESTINATIONS),
}

TERMINAL = {"SUCCEEDED", "DENIED", "REJECTED", "FAILED", "EXPIRED"}

DEV_TOKENS = {
    "tok-operator": {"user": "rina.operator", "role": "operator", "org": ORG_ID, "project": PROJECT_ID},
    "tok-approver": {"user": "budi.approver", "role": "approver", "org": ORG_ID, "project": PROJECT_ID},
    "tok-admin": {"user": "sari.admin", "role": "admin", "org": ORG_ID, "project": PROJECT_ID},
    "tok-auditor": {"user": "dewi.auditor", "role": "auditor", "org": ORG_ID, "project": PROJECT_ID},
}
# ponytail: dev defaults so a clean checkout runs; inject VERITAS_TOKENS in any demo you show.
TOKENS: dict[str, dict[str, str]] = json.loads(os.environ.get("VERITAS_TOKENS", "")) if os.environ.get("VERITAS_TOKENS") else DEV_TOKENS
for _identity in TOKENS.values():
    _identity.setdefault("org", ORG_ID)
    _identity.setdefault("project", PROJECT_ID)
INTERNAL_TOKEN = os.environ.get("VERITAS_INTERNAL_TOKEN", "dev-internal")

SESSION_TTL_SECONDS = int(os.environ.get("VERITAS_SESSION_TTL_SECONDS", "43200"))
COOKIE_SECURE = os.environ.get("VERITAS_COOKIE_SECURE") == "1"
COOKIE_SAMESITE = os.environ.get("VERITAS_COOKIE_SAMESITE", "lax")
LOGIN_WINDOW_SECONDS = 60
LOGIN_MAX_FAILURES = 5

# ponytail: plaintext demo passwords in env, not a password database. Swap for a users
# table plus a real hash (argon2/scrypt) when accounts stop being synthetic.
DEMO_PASSWORD = os.environ.get("VERITAS_DEMO_PASSWORD") or "demo123456"
DEMO_ACCOUNTS = {
    "alexa.chen@nexora.internal": {"user": "alexa.chen", "role": "admin"},
    "sarah.jenkins@nexora.internal": {"user": "sarah.jenkins", "role": "approver"},
    "marcus.vance@nexora.internal": {"user": "marcus.vance", "role": "operator"},
    "dr.rachel.k@nexora.internal": {"user": "dr.rachel.k", "role": "auditor"},
}
ACCOUNTS: dict[str, dict[str, str]] = (
    json.loads(os.environ["VERITAS_ACCOUNTS"]) if os.environ.get("VERITAS_ACCOUNTS") else DEMO_ACCOUNTS
)
for _email, _account in ACCOUNTS.items():
    _account.setdefault("user", _email.split("@")[0])
    _account.setdefault("role", "auditor")
    _account.setdefault("org", ORG_ID)
    _account.setdefault("project", PROJECT_ID)
    _account.setdefault("password", DEMO_PASSWORD)
LOGIN_FAILURES: dict[str, list[float]] = {}

# --------------------------------------------------------------------------- storage

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS executions(
  id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, project_id TEXT, agent_id TEXT,
  task_type TEXT, payload_json TEXT NOT NULL, payload_hash TEXT NOT NULL,
  tool TEXT, args_json TEXT, args_hash TEXT, decision TEXT, reason_code TEXT,
  status TEXT NOT NULL, idempotency_key TEXT UNIQUE, actor TEXT, correlation_id TEXT,
  receipt_id TEXT, approval_id TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS approvals(
  id TEXT PRIMARY KEY, execution_id TEXT NOT NULL, status TEXT NOT NULL, version INTEGER NOT NULL,
  args_hash TEXT NOT NULL, policy_version INTEGER NOT NULL, approver TEXT, reason TEXT,
  expires_at TEXT NOT NULL, decided_at TEXT, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS tool_calls(
  id TEXT PRIMARY KEY, execution_id TEXT NOT NULL, tool TEXT NOT NULL,
  idempotency_key TEXT UNIQUE, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS invoices(invoice_id TEXT PRIMARY KEY, amount_idr INTEGER NOT NULL, status TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS receipts(
  id TEXT PRIMARY KEY, execution_id TEXT NOT NULL, body_json TEXT NOT NULL, digest TEXT NOT NULL,
  signature TEXT NOT NULL, key_id TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS anchors(
  id TEXT PRIMARY KEY, receipt_id TEXT NOT NULL, receipt_hash TEXT NOT NULL, status TEXT NOT NULL,
  tx_ref TEXT, attempts INTEGER NOT NULL DEFAULT 0, last_error TEXT, created_at TEXT NOT NULL, updated_at TEXT);
CREATE TABLE IF NOT EXISTS events(
  seq INTEGER PRIMARY KEY AUTOINCREMENT, execution_id TEXT NOT NULL, type TEXT NOT NULL,
  data_json TEXT NOT NULL, prev_hash TEXT NOT NULL, hash TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS egress_deliveries(
  id TEXT PRIMARY KEY, idempotency_key TEXT UNIQUE NOT NULL, destination TEXT NOT NULL,
  payload_digest TEXT NOT NULL, sensitive_fields TEXT, decision TEXT NOT NULL,
  reason_code TEXT, actor TEXT, organization_id TEXT, created_at TEXT NOT NULL,
  delivery_status TEXT, delivery_attempts INTEGER NOT NULL DEFAULT 0, last_error TEXT);
CREATE TABLE IF NOT EXISTS mock_inbox(
  seq INTEGER PRIMARY KEY AUTOINCREMENT, destination TEXT NOT NULL, payload_json TEXT NOT NULL,
  received_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sessions(
  token_hash TEXT PRIMARY KEY, user TEXT NOT NULL, role TEXT NOT NULL,
  org TEXT NOT NULL, project TEXT, email TEXT, csrf_hash TEXT NOT NULL,
  created_at TEXT NOT NULL, last_seen_at TEXT NOT NULL, expires_at TEXT NOT NULL, revoked_at TEXT);
CREATE TABLE IF NOT EXISTS schema_migrations(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL);
"""

DB_PATH = os.environ.get("VERITAS_DB", os.path.join(os.path.dirname(os.path.abspath(__file__)), "veritas.db"))
_LOCK = threading.RLock()
_CONN = sqlite3.connect(DB_PATH, check_same_thread=False)
_CONN.row_factory = sqlite3.Row
_CONN.executescript(SCHEMA)
_CONN.commit()


def one(sql: str, args: tuple = ()) -> sqlite3.Row | None:
    return _CONN.execute(sql, args).fetchone()


def rows(sql: str, args: tuple = ()) -> list[sqlite3.Row]:
    return _CONN.execute(sql, args).fetchall()


def run(sql: str, args: tuple = ()) -> sqlite3.Cursor:
    cur = _CONN.execute(sql, args)
    _CONN.commit()
    return cur


def ensure_columns() -> None:
    """Idempotent column adds so an older veritas.db keeps working."""
    for table, columns in (
        ("anchors", (("attempts", "INTEGER NOT NULL DEFAULT 0"), ("last_error", "TEXT"), ("updated_at", "TEXT"))),
        ("egress_deliveries", (
            ("organization_id", "TEXT"),
            ("delivery_status", "TEXT"),
            ("delivery_attempts", "INTEGER NOT NULL DEFAULT 0"),
            ("last_error", "TEXT"),
        )),
    ):
        existing = {row["name"] for row in rows(f"PRAGMA table_info({table})")}
        for name, ddl in columns:
            if name not in existing:
                run(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")


# --------------------------------------------------------------------------- evidence

def canonical(obj: Any) -> bytes:
    """Precisely documented JCS equivalent: sorted keys, UTF-8, no whitespace, JSON numbers."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode()
    return hashlib.sha256(data).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def utc_plus(seconds: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")

def backfill_egress_delivery() -> None:
    run("UPDATE egress_deliveries SET delivery_status = CASE WHEN decision='ALLOW' THEN 'DELIVERED' ELSE 'SKIPPED' END,"
        " delivery_attempts = CASE WHEN decision='ALLOW' AND delivery_attempts=0 THEN 1 ELSE delivery_attempts END"
        " WHERE delivery_status IS NULL")
    run("UPDATE egress_deliveries SET organization_id=? WHERE organization_id IS NULL", (ORG_ID,))

MIGRATIONS = (
    (1, ensure_columns),
    (2, backfill_egress_delivery),
)

def migrate() -> list[int]:
    """Apply unapplied migrations in order. Safe to call on every start."""
    applied = {row["version"] for row in rows("SELECT version FROM schema_migrations")}
    newly = []
    for version, step in MIGRATIONS:
        if version in applied:
            continue
        with _LOCK:
            step()
            run("INSERT INTO schema_migrations(version, applied_at) VALUES(?, ?)", (version, utc_now()))
        newly.append(version)
    return newly

migrate()

def _login_key(value: str) -> str:
    return value.strip().lower()

def login_blocked(key: str) -> bool:
    cutoff = time.monotonic() - LOGIN_WINDOW_SECONDS
    attempts = [seen for seen in LOGIN_FAILURES.get(key, []) if seen > cutoff]
    LOGIN_FAILURES[key] = attempts
    return len(attempts) >= LOGIN_MAX_FAILURES

def record_login_failure(key: str) -> None:
    cutoff = time.monotonic() - LOGIN_WINDOW_SECONDS
    LOGIN_FAILURES[key] = [seen for seen in LOGIN_FAILURES.get(key, []) if seen > cutoff] + [time.monotonic()]

def clear_login_failures(key: str) -> None:
    LOGIN_FAILURES.pop(key, None)

def sweep_sessions() -> None:
    run("DELETE FROM sessions WHERE expires_at <= ? OR (revoked_at IS NOT NULL AND revoked_at <= ?)",
        (utc_now(), utc_plus(-86400)))

def create_session(identity: dict, email: str | None = None) -> tuple[str, str]:
    """Opaque token + CSRF; only their hashes are stored."""
    sweep_sessions()
    token, csrf, now = secrets.token_urlsafe(32), secrets.token_hex(16), utc_now()
    run(
        "INSERT INTO sessions(token_hash,user,role,org,project,email,csrf_hash,created_at,last_seen_at,expires_at)"
        " VALUES(?,?,?,?,?,?,?,?,?,?)",
        (sha(token), identity["user"], identity["role"], identity.get("org", ORG_ID),
         identity.get("project", PROJECT_ID), email, sha(csrf), now, now, utc_plus(SESSION_TTL_SECONDS)),
    )
    return token, csrf

def session_identity(token: str | None) -> dict | None:
    if not token:
        return None
    row = one("SELECT * FROM sessions WHERE token_hash=? AND revoked_at IS NULL AND expires_at > ?",
              (sha(token), utc_now()))
    if not row:
        return None
    run("UPDATE sessions SET last_seen_at=? WHERE token_hash=?", (utc_now(), row["token_hash"]))
    identity = {"user": row["user"], "role": row["role"], "org": row["org"], "project": row["project"]}
    if row["email"]:
        identity["email"] = row["email"]
    return identity

def revoke_session(token: str | None) -> None:
    if token:
        run("UPDATE sessions SET revoked_at=? WHERE token_hash=? AND revoked_at IS NULL", (utc_now(), sha(token)))

def session_csrf_ok(request: Request, supplied: str) -> bool:
    expected = request.cookies.get("vt_csrf", "")
    if not expected or not supplied or not hmac.compare_digest(expected, supplied):
        return False
    token = request.cookies.get("vt_session", "")
    row = one("SELECT csrf_hash FROM sessions WHERE token_hash=? AND revoked_at IS NULL AND expires_at > ?",
              (sha(token), utc_now())) if token else None
    return bool(row) and hmac.compare_digest(row["csrf_hash"], sha(supplied))


def _load_signing_key() -> Ed25519PrivateKey:
    injected = os.environ.get("VERITAS_SIGNING_SEED", "").strip()
    if injected:
        seed = bytes.fromhex(injected)
        if len(seed) != 32:
            raise SystemExit("VERITAS_SIGNING_SEED must be 64 hex characters (32 bytes).")
        return Ed25519PrivateKey.from_private_bytes(seed)
    row = one("SELECT v FROM meta WHERE k='signing_seed'")
    if row:
        return Ed25519PrivateKey.from_private_bytes(bytes.fromhex(row["v"]))
    seed = Ed25519PrivateKey.generate().private_bytes(
        serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption()
    )
    run("INSERT INTO meta(k,v) VALUES('signing_seed',?)", (seed.hex(),))
    return Ed25519PrivateKey.from_private_bytes(seed)


SIGNING_KEY = _load_signing_key()
PUBLIC_KEY = SIGNING_KEY.public_key()
PUBLIC_BYTES = PUBLIC_KEY.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
KEY_ID = sha(PUBLIC_BYTES)[:16]
POLICY_DIGEST = sha(canonical(POLICY_SRC))


def add_event(execution_id: str, etype: str, data: dict) -> str:
    prev = one("SELECT hash FROM events WHERE execution_id=? ORDER BY seq DESC LIMIT 1", (execution_id,))
    prev_hash = prev["hash"] if prev else "genesis"
    digest = sha(prev_hash.encode() + canonical({"execution_id": execution_id, "type": etype, "data": data}))
    run(
        "INSERT INTO events(execution_id,type,data_json,prev_hash,hash,created_at) VALUES(?,?,?,?,?,?)",
        (execution_id, etype, canonical(data).decode(), prev_hash, digest, utc_now()),
    )
    return digest


def latest_event_hash(execution_id: str) -> str:
    row = one("SELECT hash FROM events WHERE execution_id=? ORDER BY seq DESC LIMIT 1", (execution_id,))
    return row["hash"] if row else "genesis"


def issue_receipt(ex: sqlite3.Row, actor: str, outcome: str) -> str:
    receipt_id = f"rcpt_{uuid.uuid4().hex[:16]}"
    body = {
        "version": 1,
        "receipt_id": receipt_id,
        "execution_id": ex["id"],
        "organization_id": ex["organization_id"],
        "project_id": ex["project_id"],
        "agent_id": ex["agent_id"],
        "tool": ex["tool"],
        "input_digest": ex["args_hash"],
        "policy_version": POLICY_VERSION,
        "policy_digest": POLICY_DIGEST,
        "decision": ex["decision"],
        "actor": actor,
        "outcome": outcome,
        "created_at": utc_now(),
        "correlation_id": ex["correlation_id"],
        "previous_event_hash": latest_event_hash(ex["id"]),
        "nonce": secrets.token_hex(16),
    }
    canon = canonical(body)
    digest = sha(canon)
    signature = SIGNING_KEY.sign(canon).hex()
    run(
        "INSERT INTO receipts(id,execution_id,body_json,digest,signature,key_id,created_at) VALUES(?,?,?,?,?,?,?)",
        (receipt_id, ex["id"], canon.decode(), digest, signature, KEY_ID, utc_now()),
    )
    anchor_id = f"anc_{uuid.uuid4().hex[:16]}"
    run(
        "INSERT INTO anchors(id,receipt_id,receipt_hash,status,created_at,updated_at) VALUES(?,?,?,?,?,?)",
        (anchor_id, receipt_id, digest, "pending", utc_now(), utc_now()),
    )
    if chain_enabled():
        submit_anchor(anchor_id, digest)
    return receipt_id


def submit_anchor(anchor_id: str, receipt_hash: str) -> None:
    """One attempt; failures stay pending with last_error so the receipt is never lost."""
    run("UPDATE anchors SET attempts=attempts+1, updated_at=? WHERE id=?", (utc_now(), anchor_id))
    try:
        tx_ref = submit_digest(receipt_hash)
    except AnchorError as exc:
        run("UPDATE anchors SET last_error=? WHERE id=?", (str(exc)[:200], anchor_id))
        return
    run("UPDATE anchors SET status='submitted',tx_ref=?,last_error=NULL,updated_at=? WHERE id=? AND status='pending'",
        (tx_ref, utc_now(), anchor_id))


def sweep_anchors() -> dict:
    """Submit pending anchors, then confirm submitted ones whose calldata read-back matches."""
    summary = {"enabled": chain_enabled(), "submitted": 0, "confirmed": 0, "failed": 0, "waiting": 0}
    if not summary["enabled"]:
        return summary
    for anchor in rows("SELECT * FROM anchors WHERE status='pending' ORDER BY created_at LIMIT 50"):
        before = anchor["status"]
        submit_anchor(anchor["id"], anchor["receipt_hash"])
        fresh = one("SELECT status FROM anchors WHERE id=?", (anchor["id"],))
        if fresh["status"] != before:
            summary["submitted"] += 1
    for anchor in rows("SELECT * FROM anchors WHERE status='submitted' ORDER BY created_at LIMIT 50"):
        try:
            seen = read_digest(anchor["tx_ref"])
        except AnchorError as exc:
            run("UPDATE anchors SET last_error=?,updated_at=? WHERE id=?", (str(exc)[:200], utc_now(), anchor["id"]))
            summary["waiting"] += 1
            continue
        if seen is None:
            summary["waiting"] += 1
        elif seen == anchor["receipt_hash"]:
            run("UPDATE anchors SET status='confirmed',last_error=NULL,updated_at=? WHERE id=? AND status='submitted'",
                (utc_now(), anchor["id"]))
            summary["confirmed"] += 1
        else:
            run("UPDATE anchors SET status='failed',last_error='DIGEST_MISMATCH',updated_at=? WHERE id=? AND status='submitted'",
                (utc_now(), anchor["id"]))
            summary["failed"] += 1
    return summary


# --------------------------------------------------------------------------- auth and errors

class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, details: dict | None = None):
        self.status, self.code, self.message, self.details = status, code, message, details


def require_role(*roles: str):
    def dependency(request: Request):
        identity, source = request_identity(request)
        if not identity:
            raise ApiError(401, "UNAUTHENTICATED", "Valid bearer token or session cookie required.")
        if roles and identity["role"] not in roles:
            raise ApiError(403, "FORBIDDEN", "Role not permitted for this action.")
        if source == "cookie" and request.method not in ("GET", "HEAD", "OPTIONS"):
            supplied = request.headers.get("X-CSRF-Token", "")
            if not session_csrf_ok(request, supplied):
                raise ApiError(403, "CSRF_REQUIRED", "X-CSRF-Token must match the csrf cookie and the active session.")
        request.state.identity = identity
        return identity

    return dependency


def request_identity(request: Request) -> tuple[dict | None, str | None]:
    scheme, _, token = request.headers.get("Authorization", "").partition(" ")
    if scheme.lower() == "bearer" and token in TOKENS:
        return TOKENS[token], "bearer"
    identity = session_identity(request.cookies.get("vt_session"))
    if identity:
        return identity, "cookie"
    return None, None


def scope_of(identity: dict) -> tuple[str, str]:
    return identity.get("org", ORG_ID), identity.get("project", PROJECT_ID)


def require_execution_scope(ex: sqlite3.Row, identity: dict) -> None:
    """Cross-org reads answer 404, not 403: do not confirm that an ID exists elsewhere."""
    org, project = scope_of(identity)
    if ex["organization_id"] != org or (project and ex["project_id"] != project):
        raise ApiError(404, "NOT_FOUND", "Execution not found.")


def require_internal(x_internal_token: str = Header(default="")):
    if x_internal_token != INTERNAL_TOKEN:
        raise ApiError(401, "INTERNAL_UNAUTHENTICATED", "Internal service token required.")


app = FastAPI(title="VERITAS AI Harness", version="0.1.0")

HTTP_COUNTERS: dict[tuple[str, str], int] = {}
LOG_JSON = os.environ.get("VERITAS_LOG_JSON") == "1"

CORS_ORIGINS = [origin.strip() for origin in os.environ.get("VERITAS_CORS_ORIGINS", "").split(",") if origin.strip()]
if CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Correlation-ID"],
    )


@app.middleware("http")
async def observability(request: Request, call_next):
    """Correlation ID, JSON access log, and request counters in one pass."""
    request.state.correlation_id = request.headers.get("X-Correlation-ID") or uuid.uuid4().hex
    started = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
    key = (request.method, f"{response.status_code // 100}xx")
    HTTP_COUNTERS[key] = HTTP_COUNTERS.get(key, 0) + 1
    response.headers["X-Correlation-ID"] = request.state.correlation_id
    if LOG_JSON:
        print(json.dumps({
            "ts": utc_now(), "level": "info", "msg": "request",
            "method": request.method, "path": request.url.path,
            "status": response.status_code, "duration_ms": elapsed_ms,
            "correlation_id": request.state.correlation_id,
        }), flush=True)
    return response


@app.exception_handler(ApiError)
async def api_error_handler(request: Request, exc: ApiError):
    cid = getattr(request.state, "correlation_id", "")
    return JSONResponse(
        status_code=exc.status,
        content={"error": {"code": exc.code, "message": exc.message, "details": exc.details or {}}, "correlation_id": cid},
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    cid = getattr(request.state, "correlation_id", "")
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "INVALID_REQUEST", "message": "Request failed validation.", "details": {"errors": str(exc.errors())}}, "correlation_id": cid},
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    cid = getattr(request.state, "correlation_id", "")
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "INTERNAL_ERROR", "message": "Internal error.", "details": {}}, "correlation_id": cid},
    )


# --------------------------------------------------------------------------- API session auth (separate frontend)

def set_session_cookies(response, token: str, csrf: str) -> None:
    response.set_cookie("vt_session", token, httponly=True, samesite=COOKIE_SAMESITE, secure=COOKIE_SECURE)
    response.set_cookie("vt_csrf", csrf, samesite=COOKIE_SAMESITE, secure=COOKIE_SECURE)


class LoginRequest(BaseModel):
    email: str | None = None
    password: str | None = None
    token: str | None = None


@app.post("/api/v1/auth/login")
def api_login(body: LoginRequest):
    email = body.email or ""
    email = email.strip().lower()
    token = body.token
    key = _login_key(email) if email else _login_key(f"token:{token}")
    if login_blocked(key):
        raise ApiError(429, "RATE_LIMITED", "Too many failed attempts; retry later.")
    identity, session_email = None, None
    if email:
        account = ACCOUNTS.get(email)
        password = body.password
        if account and isinstance(password, str) and hmac.compare_digest(password, account["password"]):
            identity = {"user": account["user"], "role": account["role"],
                        "org": account["org"], "project": account["project"]}
            session_email = email
    elif isinstance(token, str) and token in TOKENS:
        identity = TOKENS[token]
    if not identity:
        record_login_failure(key)
        raise ApiError(401, "INVALID_CREDENTIALS", "Unknown credentials.")
    clear_login_failures(key)
    session_token, csrf = create_session(identity, session_email)
    payload = {"user": identity["user"], "role": identity["role"], "csrf_token": csrf,
               "expires_in": SESSION_TTL_SECONDS}
    if session_email:
        payload["email"] = session_email
    response = JSONResponse(payload)
    set_session_cookies(response, session_token, csrf)
    return response


@app.post("/api/v1/auth/logout")
def api_logout(request: Request, identity: dict = Depends(require_role())):
    revoke_session(request.cookies.get("vt_session"))
    response = JSONResponse({"status": "logged_out"})
    response.delete_cookie("vt_session")
    response.delete_cookie("vt_csrf")
    return response


@app.get("/api/v1/me")
def api_me(identity: dict = Depends(require_role())):
    org, project = scope_of(identity)
    payload = {"user": identity["user"], "role": identity["role"],
               "organization_id": org, "project_id": project}
    if identity.get("email"):
        payload["email"] = identity["email"]
    return payload


# --------------------------------------------------------------------------- policy engine

def evaluate(tool: str, args: dict) -> tuple[str, str]:
    if tool != "approve_invoice":
        return "DENY", "UNKNOWN_TOOL"
    vendor, amount = args.get("vendor_id"), args.get("amount_idr")
    if vendor not in ALLOWED_VENDORS:
        return "DENY", "VENDOR_NOT_ALLOWED"
    if type(amount) is not int or amount <= 0:
        return "DENY", "INVALID_AMOUNT"
    if amount > HARD_CAP_IDR:
        return "DENY", "AMOUNT_HARD_CAP"
    if amount <= AUTO_LIMIT_IDR:
        return "ALLOW", "WITHIN_LIMIT"
    return "APPROVAL_REQUIRED", "AMOUNT_LIMIT"


def revalidate_for_resume(ex: sqlite3.Row) -> tuple[str, str]:
    """Approval covers the amount limit only; other constraints must still hold."""
    if ex["args_hash"] != sha(canonical(json.loads(ex["args_json"]))):
        return "DENY", "ARGUMENTS_CHANGED"
    args = json.loads(ex["args_json"])
    if args.get("vendor_id") not in ALLOWED_VENDORS:
        return "DENY", "VENDOR_NOT_ALLOWED"
    if type(args.get("amount_idr")) is not int or not 0 < args["amount_idr"] <= HARD_CAP_IDR:
        return "DENY", "INVALID_AMOUNT"
    return "ALLOW", "APPROVED"


def plan_task(payload: Any) -> dict:
    if not isinstance(payload, dict):
        raise ApiError(422, "INVALID_PROPOSAL", "Task payload must be an object.")
    invoice_id, amount, vendor = payload.get("invoice_id"), payload.get("amount_idr"), payload.get("vendor")
    if not isinstance(invoice_id, str) or not invoice_id:
        raise ApiError(422, "INVALID_PROPOSAL", "invoice_id is required.")
    if type(amount) is not int or amount <= 0:
        raise ApiError(422, "INVALID_PROPOSAL", "amount_idr must be a positive integer.")
    if not isinstance(vendor, str) or not vendor:
        raise ApiError(422, "INVALID_PROPOSAL", "vendor is required.")
    vendor_id = vendor if vendor.startswith("V-") else f"V-{vendor}"
    return {"tool": "approve_invoice", "arguments": {"invoice_id": invoice_id, "amount_idr": amount, "vendor_id": vendor_id}}


# --------------------------------------------------------------------------- execution

def sweep_expired() -> int:
    """Expire overdue approvals so pending never lingers past its deadline."""
    now = utc_now()
    with _LOCK:
        expired = rows("SELECT * FROM approvals WHERE status='pending' AND expires_at < ?", (now,))
        for approval in expired:
            run("UPDATE approvals SET status='expired',decided_at=? WHERE id=? AND status='pending'", (now, approval["id"]))
            run("UPDATE executions SET status='EXPIRED',updated_at=? WHERE id=? AND status='WAITING_APPROVAL'",
                (now, approval["execution_id"]))
            add_event(approval["execution_id"], "APPROVAL_EXPIRED", {"approval_id": approval["id"]})
        return len(expired)


def proposal_error(proposal: Any) -> str | None:
    """Model output is untrusted data; shape failures deny instead of crashing."""
    if not isinstance(proposal, dict):
        return "INVALID_PROPOSAL"
    tool, arguments = proposal.get("tool"), proposal.get("arguments")
    if not isinstance(tool, str) or not isinstance(arguments, dict):
        return "INVALID_PROPOSAL"
    if not isinstance(arguments.get("invoice_id"), str) or not arguments["invoice_id"]:
        return "INVALID_PROPOSAL"
    if type(arguments.get("amount_idr")) is not int:
        return "INVALID_PROPOSAL"
    if not isinstance(arguments.get("vendor_id"), str) or not arguments["vendor_id"]:
        return "INVALID_PROPOSAL"
    return None


def execute_protected(ex: sqlite3.Row, actor: str) -> None:
    """Claim EXECUTING exactly once, invoke the simulated tool, issue receipt."""
    claimed = run(
        "UPDATE executions SET status='EXECUTING', updated_at=? WHERE id=? AND status IN ('ALLOWED')",
        (utc_now(), ex["id"]),
    )
    if claimed.rowcount != 1:
        return
    add_event(ex["id"], "EXECUTING", {})
    run(
        "INSERT OR IGNORE INTO tool_calls(id,execution_id,tool,idempotency_key,created_at) VALUES(?,?,?,?,?)",
        (f"call_{uuid.uuid4().hex[:16]}", ex["id"], ex["tool"], ex["id"], utc_now()),
    )
    args = json.loads(ex["args_json"])
    run("INSERT OR IGNORE INTO invoices(invoice_id,amount_idr,status) VALUES(?,?,'received')", (args["invoice_id"], args["amount_idr"]))
    run("UPDATE invoices SET status='paid_simulated' WHERE invoice_id=? AND status<>'paid_simulated'", (args["invoice_id"],))
    ex = one("SELECT * FROM executions WHERE id=?", (ex["id"],))
    receipt_id = issue_receipt(ex, actor, "SUCCEEDED")
    run(
        "UPDATE executions SET status='SUCCEEDED', receipt_id=?, actor=?, updated_at=? WHERE id=?",
        (receipt_id, actor, utc_now(), ex["id"]),
    )
    add_event(ex["id"], "SUCCEEDED", {"receipt_id": receipt_id, "invoice_id": args["invoice_id"]})


def execution_view(execution_id: str, identity: dict | None = None) -> dict:
    sweep_expired()
    ex = one("SELECT * FROM executions WHERE id=?", (execution_id,))
    if not ex:
        raise ApiError(404, "NOT_FOUND", "Execution not found.")
    if identity:
        require_execution_scope(ex, identity)
    view = {
        "execution_id": ex["id"],
        "status": ex["status"],
        "organization_id": ex["organization_id"],
        "project_id": ex["project_id"],
        "agent_id": ex["agent_id"],
        "task_type": ex["task_type"],
        "proposal": {"tool": ex["tool"], "arguments": json.loads(ex["args_json"])} if ex["args_json"] else None,
        "decision": ex["decision"],
        "reason_code": ex["reason_code"],
        "tool_calls": one("SELECT COUNT(*) AS n FROM tool_calls WHERE execution_id=?", (ex["id"],))["n"],
        "receipt_id": ex["receipt_id"],
        "approval_id": ex["approval_id"],
        "idempotency_key": ex["idempotency_key"],
        "actor": ex["actor"],
        "created_at": ex["created_at"],
        "updated_at": ex["updated_at"],
    }
    if ex["receipt_id"]:
        anchor = one("SELECT status,tx_ref,attempts,last_error FROM anchors WHERE receipt_id=?", (ex["receipt_id"],))
        view["anchor"] = ({"status": anchor["status"], "tx_ref": anchor["tx_ref"],
                           "attempts": anchor["attempts"], "last_error": anchor["last_error"]}
                          if anchor else {"status": "unknown", "tx_ref": None, "attempts": 0, "last_error": None})
    return view


# --------------------------------------------------------------------------- routes: task, execution, approval

@app.post("/api/v1/tasks", status_code=202)
def create_task(
    body: dict,
    request: Request,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    identity: dict = Depends(require_role("operator", "admin")),
):
    return submit_task(body.get("payload", body), idempotency_key, identity, request.state.correlation_id, body.get("task_type", "invoice_review"))


def submit_task(payload: Any, idempotency_key: str, identity: dict, cid: str, task_type: str = "invoice_review") -> dict:
    with _LOCK:
        existing = one("SELECT * FROM executions WHERE idempotency_key=?", (idempotency_key,))
        if existing:
            if existing["payload_hash"] != sha(canonical(payload)):
                raise ApiError(409, "IDEMPOTENCY_CONFLICT", "Idempotency key reused with a different payload.")
            require_execution_scope(existing, identity)
            view = execution_view(existing["id"], identity)
            view["replayed"] = True
            return view

        execution_id = f"exec_{uuid.uuid4().hex[:16]}"
        org, project = scope_of(identity)
        run(
            "INSERT INTO executions(id,organization_id,project_id,agent_id,task_type,payload_json,payload_hash,"
            "status,idempotency_key,actor,correlation_id,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (execution_id, org, project, AGENT_ID, task_type, canonical(payload).decode(),
             sha(canonical(payload)), "CREATED", idempotency_key, identity["user"], cid, utc_now(), utc_now()),
        )
        add_event(execution_id, "TASK_CREATED", {"actor": identity["user"]})
        add_event(execution_id, "PLANNING", {})
        suggested, planner = propose(payload)
        if suggested is None:
            proposal = plan_task(payload)
            plan_error = None
        else:
            proposal = suggested
            plan_error = proposal_error(proposal)
        tool = proposal.get("tool") if isinstance(proposal, dict) else None
        args = proposal.get("arguments") if isinstance(proposal, dict) else None
        args_ok = isinstance(args, dict)
        add_event(execution_id, "PROPOSAL", {
            "planner": planner,
            "tool": tool if isinstance(tool, str) else None,
            "arguments": args if args_ok else None,
            "valid": plan_error is None,
        })
        if plan_error:
            decision, reason = "DENY", plan_error
        else:
            decision, reason = evaluate(tool, args)
        run(
            "UPDATE executions SET tool=?,args_json=?,args_hash=?,decision=?,reason_code=?,status='POLICY_CHECK',updated_at=? WHERE id=?",
            (tool if isinstance(tool, str) else None,
             canonical(args).decode() if args_ok else None,
             sha(canonical(args)) if args_ok else None,
             decision, reason, utc_now(), execution_id),
        )
        add_event(execution_id, "POLICY_CHECK", {"decision": decision, "reason_code": reason, "policy_version": POLICY_VERSION, "policy_digest": POLICY_DIGEST})

        if decision == "DENY":
            run("UPDATE executions SET status='DENIED',updated_at=? WHERE id=?", (utc_now(), execution_id))
            add_event(execution_id, "DENIED", {"reason_code": reason})
        elif decision == "APPROVAL_REQUIRED":
            approval_id = f"aprv_{uuid.uuid4().hex[:16]}"
            run(
                "INSERT INTO approvals(id,execution_id,status,version,args_hash,policy_version,expires_at,created_at) VALUES(?,?,?,?,?,?,?,?)",
                (approval_id, execution_id, "pending", 1, sha(canonical(args)), POLICY_VERSION, utc_plus(APPROVAL_TTL_SECONDS), utc_now()),
            )
            run("UPDATE executions SET status='WAITING_APPROVAL',approval_id=?,updated_at=? WHERE id=?", (approval_id, utc_now(), execution_id))
            add_event(execution_id, "APPROVAL_REQUIRED", {"approval_id": approval_id, "reason_code": reason})
        else:
            run("UPDATE executions SET status='ALLOWED',updated_at=? WHERE id=?", (utc_now(), execution_id))
            add_event(execution_id, "ALLOWED", {"reason_code": reason})
            execute_protected(one("SELECT * FROM executions WHERE id=?", (execution_id,)), identity["user"])

        return execution_view(execution_id)


@app.get("/api/v1/executions")
def list_executions(status: str = "", limit: int = 20, offset: int = 0,
                    identity: dict = Depends(require_role())):
    sweep_expired()
    org, project = scope_of(identity)
    limit, offset = max(1, min(limit, 100)), max(0, offset)
    clause, args = "organization_id=? AND project_id=?", [org, project]
    if status:
        clause += " AND status=?"
        args.append(status)
    total = one(f"SELECT COUNT(*) AS n FROM executions WHERE {clause}", tuple(args))["n"]
    items = [
        execution_view(row["id"], identity)
        for row in rows(f"SELECT id FROM executions WHERE {clause} ORDER BY created_at DESC LIMIT ? OFFSET ?",
                        (*args, limit, offset))
    ]
    return {"executions": items, "total": total, "limit": limit, "offset": offset}

@app.get("/api/v1/dashboard/summary")
def dashboard_summary(identity: dict = Depends(require_role())):
    sweep_expired()
    org, project = scope_of(identity)
    by_status = {row["status"]: row["n"] for row in rows(
        "SELECT status, COUNT(*) AS n FROM executions WHERE organization_id=? AND project_id=? GROUP BY status",
        (org, project))}
    pending = one(
        "SELECT COUNT(*) AS n FROM approvals a JOIN executions e ON e.id=a.execution_id "
        "WHERE a.status='pending' AND e.organization_id=? AND e.project_id=?", (org, project))["n"]
    anchors = {row["status"]: row["n"] for row in rows(
        "SELECT an.status, COUNT(*) AS n FROM anchors an JOIN receipts r ON r.id=an.receipt_id "
        "JOIN executions e ON e.id=r.execution_id WHERE e.organization_id=? AND e.project_id=? GROUP BY an.status",
        (org, project))}
    return {
        "organization_id": org, "project_id": project,
        "executions": {"total": sum(by_status.values()), "by_status": by_status},
        "approvals_pending": pending,
        "receipts": sum(1 for row in rows(
            "SELECT receipt_id FROM executions WHERE organization_id=? AND project_id=? AND receipt_id IS NOT NULL",
            (org, project))),
        "anchors": anchors,
        "policy_version": POLICY_VERSION,
    }

@app.get("/api/v1/policies")
def list_policies(identity: dict = Depends(require_role())):
    return {"policy_version": POLICY_VERSION, "digest": POLICY_DIGEST, "source": POLICY_SRC,
            "approval_ttl_seconds": APPROVAL_TTL_SECONDS, "sensitive_fields": sorted(SENSITIVE_FIELDS),
            "tool": {"name": "approve_invoice", "simulated": True}}

@app.get("/api/v1/agents")
def list_agents(identity: dict = Depends(require_role())):
    org, project = scope_of(identity)
    runs = one("SELECT COUNT(*) AS n FROM executions WHERE organization_id=? AND project_id=? AND agent_id=?",
               (org, project, AGENT_ID))["n"]
    return {"agents": [{
        "agent_id": AGENT_ID, "name": "Procurement Agent", "status": "OPERATIONAL",
        "allowed_tools": ["approve_invoice"], "policy_version": POLICY_VERSION,
        "executions": runs,
    }]}

@app.get("/api/v1/executions/{execution_id}")
def get_execution(execution_id: str, identity: dict = Depends(require_role())):
    return execution_view(execution_id, identity)


@app.get("/api/v1/executions/{execution_id}/events")
def get_events(execution_id: str, identity: dict = Depends(require_role())):
    ex = one("SELECT * FROM executions WHERE id=?", (execution_id,))
    if not ex:
        raise ApiError(404, "NOT_FOUND", "Execution not found.")
    require_execution_scope(ex, identity)
    items = []
    for event in rows("SELECT * FROM events WHERE execution_id=? ORDER BY seq", (execution_id,)):
        items.append({"seq": event["seq"], "type": event["type"], "data": json.loads(event["data_json"]),
                      "prev_hash": event["prev_hash"], "hash": event["hash"], "created_at": event["created_at"]})
    return {"execution_id": execution_id, "events": items}


@app.get("/api/v1/approvals")
def list_approvals(identity: dict = Depends(require_role("approver", "admin", "auditor"))):
    sweep_expired()
    org, project = scope_of(identity)
    pending = rows(
        "SELECT a.*, e.status AS execution_status, e.args_json, e.actor, e.created_at AS execution_created_at "
        "FROM approvals a JOIN executions e ON e.id=a.execution_id "
        "WHERE a.status='pending' AND e.organization_id=? AND e.project_id=? ORDER BY a.created_at",
        (org, project),
    )
    items = []
    for approval in pending:
        item = dict(approval)
        item.pop("args_json", None)
        item.pop("execution_status", None)
        item.pop("execution_created_at", None)
        item.pop("actor", None)
        item["execution"] = {
            "status": approval["execution_status"],
            "proposal": {"tool": "approve_invoice", "arguments": json.loads(approval["args_json"])},
            "actor": approval["actor"],
            "created_at": approval["execution_created_at"],
        }
        items.append(item)
    return {"approvals": items}


@app.post("/api/v1/approvals/{approval_id}/decisions")
def decide_approval(
    approval_id: str,
    body: dict,
    identity: dict = Depends(require_role("approver", "admin")),
):
    return decide_core(approval_id, body.get("decision"), body.get("reason"), body.get("expected_version"), identity)


def deny_on_resume(approval: sqlite3.Row, ex: sqlite3.Row, identity: dict, reason: str) -> dict:
    """Revalidation failed: reject the approval, deny the execution, never call the tool."""
    run(
        "UPDATE approvals SET status='rejected',version=?,approver=?,reason=?,decided_at=? WHERE id=?",
        (approval["version"] + 1, identity["user"], f"revalidation:{reason}", utc_now(), approval["id"]),
    )
    run("UPDATE executions SET status='DENIED',decision='DENY',reason_code=?,updated_at=? WHERE id=?",
        (reason, utc_now(), ex["id"]))
    add_event(ex["id"], "DENIED_ON_RESUME", {"reason_code": reason})
    return {"approval_id": approval["id"], "status": "rejected", "execution": execution_view(ex["id"])}


def decide_core(approval_id: str, decision: Any, reason: Any, expected_version: Any, identity: dict) -> dict:
    if decision not in ("approve", "reject"):
        raise ApiError(422, "INVALID_DECISION", "decision must be approve or reject.")
    with _LOCK:
        sweep_expired()
        approval = one("SELECT * FROM approvals WHERE id=?", (approval_id,))
        if not approval:
            raise ApiError(404, "NOT_FOUND", "Approval not found.")
        if approval["status"] == "expired":
            raise ApiError(409, "APPROVAL_EXPIRED", "Approval has expired.")
        if approval["status"] != "pending":
            raise ApiError(409, "APPROVAL_NOT_PENDING", "Approval already decided or expired.")
        if expected_version is not None and expected_version != approval["version"]:
            raise ApiError(409, "VERSION_CONFLICT", "Approval changed since you loaded it.")
        ex = one("SELECT * FROM executions WHERE id=?", (approval["execution_id"],))
        if not ex:
            raise ApiError(404, "NOT_FOUND", "Execution not found.")
        require_execution_scope(ex, identity)
        if ex["actor"] == identity["user"]:
            raise ApiError(403, "SEPARATION_OF_DUTIES", "Requester cannot decide their own approval.")
        if utc_now() > approval["expires_at"]:
            run("UPDATE approvals SET status='expired',decided_at=? WHERE id=?", (utc_now(), approval_id))
            run("UPDATE executions SET status='EXPIRED',updated_at=? WHERE id=?", (utc_now(), ex["id"]))
            add_event(ex["id"], "APPROVAL_EXPIRED", {})
            raise ApiError(409, "APPROVAL_EXPIRED", "Approval has expired.")

        new_version = approval["version"] + 1
        if decision == "reject":
            run("UPDATE approvals SET status='rejected',version=?,approver=?,reason=?,decided_at=? WHERE id=?",
                (new_version, identity["user"], reason, utc_now(), approval_id))
            run("UPDATE executions SET status='REJECTED',updated_at=? WHERE id=?", (utc_now(), ex["id"]))
            add_event(ex["id"], "REJECTED", {"approver": identity["user"], "reason": reason})
            return {"approval_id": approval_id, "status": "rejected", "execution": execution_view(ex["id"])}

        if approval["policy_version"] != POLICY_VERSION:
            return deny_on_resume(approval, ex, identity, "POLICY_CHANGED")

        verdict, why = revalidate_for_resume(ex)
        if verdict != "ALLOW":
            return deny_on_resume(approval, ex, identity, why)

        run("UPDATE approvals SET status='approved',version=?,approver=?,reason=?,decided_at=? WHERE id=?",
            (new_version, identity["user"], reason, utc_now(), approval_id))
        run("UPDATE executions SET status='ALLOWED',decision='ALLOWED',reason_code='HUMAN_APPROVED',updated_at=? WHERE id=?",
            (utc_now(), ex["id"]))
        add_event(ex["id"], "APPROVED", {"approver": identity["user"], "reason": reason})
        execute_protected(one("SELECT * FROM executions WHERE id=?", (ex["id"],)), identity["user"])
        return {"approval_id": approval_id, "status": "approved", "execution": execution_view(ex["id"])}


# --------------------------------------------------------------------------- routes: receipts and anchors

def verify_receipt(body: dict, stored_digest: str | None = None) -> dict:
    body = dict(body)
    signature = body.pop("signature", None)
    key_id = body.pop("key_id", None)
    canon = canonical(body)
    digest = sha(canon)
    trusted = key_id == KEY_ID
    try:
        PUBLIC_KEY.verify(bytes.fromhex(signature or ""), canon)
        signature_valid = True
    except Exception:
        signature_valid = False
    receipt_id = body.get("receipt_id")
    anchor = one("SELECT status,receipt_hash FROM anchors WHERE receipt_id=?", (receipt_id,)) if receipt_id else None
    anchor_status = anchor["status"] if anchor else "unknown"
    anchor_matches = bool(anchor) and anchor["receipt_hash"] == digest
    hash_matches = stored_digest is None or digest == stored_digest
    verified = signature_valid and trusted and hash_matches and anchor_status == "confirmed" and anchor_matches
    return {"receipt_id": receipt_id, "signature_valid": signature_valid, "trusted_key": trusted,
            "hash_matches": hash_matches, "anchor_status": anchor_status,
            "anchor_matches": anchor_matches, "verified": verified}


@app.get("/api/v1/receipts/{receipt_id}")
def get_receipt(receipt_id: str, identity: dict = Depends(require_role())):
    receipt = one("SELECT * FROM receipts WHERE id=?", (receipt_id,))
    if not receipt:
        raise ApiError(404, "NOT_FOUND", "Receipt not found.")
    ex = one("SELECT * FROM executions WHERE id=?", (receipt["execution_id"],))
    if not ex:
        raise ApiError(404, "NOT_FOUND", "Receipt not found.")
    require_execution_scope(ex, identity)
    anchor = one("SELECT * FROM anchors WHERE receipt_id=?", (receipt_id,))
    return {"receipt": json.loads(receipt["body_json"]), "signature": receipt["signature"],
            "key_id": receipt["key_id"], "digest": receipt["digest"],
            "anchor": {"id": anchor["id"], "status": anchor["status"], "tx_ref": anchor["tx_ref"]} if anchor else None}


@app.post("/api/v1/receipts/{receipt_id}/verify")
def verify_stored(receipt_id: str, identity: dict = Depends(require_role())):
    return verify_stored_receipt(receipt_id, identity)


def verify_stored_receipt(receipt_id: str, identity: dict | None = None) -> dict:
    receipt = one("SELECT * FROM receipts WHERE id=?", (receipt_id,))
    if not receipt:
        raise ApiError(404, "NOT_FOUND", "Receipt not found.")
    if identity:
        ex = one("SELECT * FROM executions WHERE id=?", (receipt["execution_id"],))
        if not ex:
            raise ApiError(404, "NOT_FOUND", "Receipt not found.")
        require_execution_scope(ex, identity)
    body = json.loads(receipt["body_json"])
    body.update({"signature": receipt["signature"], "key_id": receipt["key_id"]})
    return verify_receipt(body, stored_digest=receipt["digest"])


@app.post("/api/v1/verify")
def verify_supplied(body: dict, identity: dict = Depends(require_role())):
    return verify_receipt(body)


@app.post("/internal/v1/anchors/{anchor_id}/confirm", dependencies=[Depends(require_internal)])
def confirm_anchor(anchor_id: str):
    return confirm_anchor_core(anchor_id)


def confirm_anchor_core(anchor_id: str) -> dict:
    if chain_enabled():
        raise ApiError(409, "ANCHOR_MODE", "Manual confirm is disabled while an RPC anchor adapter is configured.")
    anchor = one("SELECT * FROM anchors WHERE id=?", (anchor_id,))
    if not anchor:
        raise ApiError(404, "NOT_FOUND", "Anchor not found.")
    tx_ref = "0x" + uuid.uuid4().hex
    run("UPDATE anchors SET status='confirmed',tx_ref=? WHERE id=? AND status='pending'", (tx_ref, anchor_id))
    return {"anchor_id": anchor_id, "status": "confirmed", "tx_ref": tx_ref}


@app.post("/api/v1/anchors/{anchor_id}/confirm")
def api_confirm_anchor(anchor_id: str, identity: dict = Depends(require_role("admin"))):
    anchor = one("SELECT receipt_id FROM anchors WHERE id=?", (anchor_id,))
    if not anchor:
        raise ApiError(404, "NOT_FOUND", "Anchor not found.")
    receipt = one("SELECT execution_id FROM receipts WHERE id=?", (anchor["receipt_id"],))
    execution = one("SELECT * FROM executions WHERE id=?", (receipt["execution_id"],)) if receipt else None
    if not execution:
        raise ApiError(404, "NOT_FOUND", "Anchor not found.")
    require_execution_scope(execution, identity)
    result = confirm_anchor_core(anchor_id)
    return {**result, "execution_id": receipt["execution_id"]}


@app.post("/internal/v1/anchors/sweep", dependencies=[Depends(require_internal)])
def internal_sweep_anchors():
    return sweep_anchors()


@app.get("/internal/v1/latest-anchor/{receipt_id}", dependencies=[Depends(require_internal)])
def latest_anchor(receipt_id: str):
    anchor = one("SELECT * FROM anchors WHERE receipt_id=?", (receipt_id,))
    if not anchor:
        raise ApiError(404, "NOT_FOUND", "Anchor not found.")
    return {"anchor_id": anchor["id"], "status": anchor["status"], "tx_ref": anchor["tx_ref"],
            "attempts": anchor["attempts"], "last_error": anchor["last_error"]}


# --------------------------------------------------------------------------- routes: outbound data

def find_sensitive(value: Any, found: set[str] | None = None) -> set[str]:
    found = found if found is not None else set()
    if isinstance(value, dict):
        for key, inner in value.items():
            if key.casefold() in SENSITIVE_FIELDS:
                found.add(key.casefold())
            find_sensitive(inner, found)
    elif isinstance(value, list):
        for inner in value:
            find_sensitive(inner, found)
    return found


RECEIVER_FAILURES = {"remaining": 0}

def deliver_to_mock(destination: str, payload: Any) -> str | None:
    """One delivery attempt. Returns an error code, or None when accepted."""
    if RECEIVER_FAILURES["remaining"] > 0:
        RECEIVER_FAILURES["remaining"] -= 1
        return "RECEIVER_UNAVAILABLE"
    run("INSERT INTO mock_inbox(destination,payload_json,received_at) VALUES(?,?,?)",
        (destination, canonical(payload).decode(), utc_now()))
    return None

def attempt_delivery(delivery_id: str, destination: str, payload: Any) -> int:
    error = deliver_to_mock(destination, payload)
    run("UPDATE egress_deliveries SET delivery_attempts=delivery_attempts+1, delivery_status=?, last_error=? WHERE id=?",
        ("FAILED" if error else "DELIVERED", error, delivery_id))
    return 0 if error else 1

def egress_view(row: sqlite3.Row, replayed: bool = False, mock_calls: int = 0) -> dict:
    return {"delivery_id": row["id"], "decision": row["decision"], "reason_code": row["reason_code"],
            "delivery_status": row["delivery_status"], "delivery_attempts": row["delivery_attempts"],
            "last_error": row["last_error"], "delivered": row["delivery_status"] == "DELIVERED",
            "mock_calls": mock_calls, "replayed": replayed}

@app.post("/internal/mock/receiver/failures", dependencies=[Depends(require_internal)])
def mock_receiver_failures(body: dict):
    remaining = body.get("remaining", 0)
    if type(remaining) is not int or remaining < 0:
        raise ApiError(422, "INVALID_PAYLOAD", "remaining must be a non-negative integer.")
    RECEIVER_FAILURES["remaining"] = remaining
    return {"remaining": remaining}


@app.post("/api/v1/egress/send", status_code=202)
def egress_send(
    body: dict,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    identity: dict = Depends(require_role("operator", "admin")),
):
    return send_egress(body.get("destination"), body.get("payload"), idempotency_key, identity)


def send_egress(destination: Any, payload: Any, idempotency_key: str, identity: dict) -> dict:
    if not isinstance(destination, str) or not isinstance(payload, (dict, list)):
        raise ApiError(422, "INVALID_PAYLOAD", "destination (string) and payload (object) are required.")
    payload_digest = sha(canonical(payload))
    org = scope_of(identity)[0]
    with _LOCK:
        existing = one("SELECT * FROM egress_deliveries WHERE idempotency_key=?", (idempotency_key,))
        if existing:
            if (existing["payload_digest"], existing["destination"], existing["organization_id"]) != (
                    payload_digest, destination, org):
                raise ApiError(409, "IDEMPOTENCY_CONFLICT", "Idempotency key reused with different content.")
            mock_calls = 0
            if existing["decision"] == "ALLOW" and existing["delivery_status"] != "DELIVERED":
                mock_calls = attempt_delivery(existing["id"], destination, payload)
                existing = one("SELECT * FROM egress_deliveries WHERE id=?", (existing["id"],))
            return egress_view(existing, replayed=True, mock_calls=mock_calls)

        sensitive = find_sensitive(payload)
        if destination not in ALLOWED_DESTINATIONS:
            decision, reason_code = "DENY", "DESTINATION_NOT_ALLOWED"
        elif sensitive:
            decision, reason_code = "DENY", "SENSITIVE_FIELD"
        else:
            decision, reason_code = "ALLOW", "ALLOWLISTED"
        delivery_id = f"dlv_{uuid.uuid4().hex[:16]}"
        run(
            "INSERT INTO egress_deliveries(id,idempotency_key,destination,payload_digest,sensitive_fields,decision,"
            "reason_code,actor,organization_id,created_at,delivery_status) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (delivery_id, idempotency_key, destination, payload_digest, ",".join(sorted(sensitive)) or None,
             decision, reason_code, identity["user"], org, utc_now(), "SKIPPED" if decision == "DENY" else None),
        )
        mock_calls = 1 if decision == "ALLOW" and attempt_delivery(delivery_id, destination, payload) else 0
        return egress_view(one("SELECT * FROM egress_deliveries WHERE id=?", (delivery_id,)), mock_calls=mock_calls)


@app.get("/internal/mock/receiver/calls", dependencies=[Depends(require_internal)])
def mock_receiver_calls(destination: str | None = None):
    if destination:
        items = rows("SELECT * FROM mock_inbox WHERE destination=? ORDER BY seq", (destination,))
    else:
        items = rows("SELECT * FROM mock_inbox ORDER BY seq")
    return {"count": len(items), "calls": [
        {"destination": i["destination"], "payload": json.loads(i["payload_json"]), "received_at": i["received_at"]} for i in items
    ]}


# --------------------------------------------------------------------------- health

@app.get("/health/live")
def health_live():
    return {"status": "ok"}


@app.get("/health/ready")
def health_ready():
    one("SELECT 1")
    return {"status": "ok", "database": "ok"}


@app.get("/metrics", response_class=PlainTextResponse, dependencies=[Depends(require_internal)])
def metrics():
    """Prometheus text: request counters in-process, business gauges from the database."""
    lines = ["# HELP veritas_http_requests_total HTTP requests by method and status class.",
             "# TYPE veritas_http_requests_total counter"]
    lines += [f'veritas_http_requests_total{{method="{method}",status="{status}"}} {count}'
              for (method, status), count in sorted(HTTP_COUNTERS.items())]
    gauges = [
        ("veritas_executions_total", "Executions created.", "SELECT COUNT(*) AS n FROM executions"),
        ("veritas_denied_total", "Executions denied by policy.", "SELECT COUNT(*) AS n FROM executions WHERE decision='DENY'"),
        ("veritas_succeeded_total", "Executions that reached SUCCEEDED.", "SELECT COUNT(*) AS n FROM executions WHERE status='SUCCEEDED'"),
        ("veritas_tool_calls_total", "Protected tool calls actually made.", "SELECT COUNT(*) AS n FROM tool_calls"),
        ("veritas_receipts_total", "Signed receipts issued.", "SELECT COUNT(*) AS n FROM receipts"),
        ("veritas_anchors_pending", "Anchors still pending confirmation.", "SELECT COUNT(*) AS n FROM anchors WHERE status='pending'"),
        ("veritas_approvals_pending", "Approvals awaiting a decision.", "SELECT COUNT(*) AS n FROM approvals WHERE status='pending'"),
        ("veritas_egress_blocked_total", "Outbound deliveries denied.", "SELECT COUNT(*) AS n FROM egress_deliveries WHERE decision='DENY'"),
    ]
    for name, help_text, sql in gauges:
        lines += [f"# HELP {name} {help_text}", f"# TYPE {name} gauge", f"{name} {one(sql)['n']}"]
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- demo UI

CSS = """
:root{color-scheme:dark}
*{box-sizing:border-box}
body{margin:0;background:#0e1116;color:#e6e9ef;font:15px/1.5 ui-sans-serif,system-ui,sans-serif}
header{display:flex;gap:18px;align-items:center;padding:14px 24px;background:#151a21;border-bottom:1px solid #232a33;flex-wrap:wrap}
header a{color:#9aa4b2;text-decoration:none}
header b{color:#fff;letter-spacing:.4px}
main{max-width:1080px;margin:0 auto;padding:24px}
h1{font-size:22px;margin:0 0 16px}
h2{font-size:16px;margin:26px 0 8px;color:#c8d0da}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{text-align:left;padding:8px 10px;border-bottom:1px solid #232a33;vertical-align:top}
th{color:#8792a2;font-weight:500}
form.inline{display:inline}
input,select,textarea,button{font:inherit;background:#0e1116;color:#e6e9ef;border:1px solid #2b3542;border-radius:6px;padding:6px 8px}
button{background:#1f6feb;border-color:#1f6feb;cursor:pointer;margin-top:8px}
button.ghost{background:transparent;border-color:#2b3542;color:#9aa4b2;margin:0}
button.danger{background:#b62324;border-color:#b62324}
.card{background:#151a21;border:1px solid #232a33;border-radius:10px;padding:16px;margin:12px 0}
.muted{color:#8792a2}
.badge{display:inline-block;padding:2px 8px;border-radius:999px;font-size:12px;border:1px solid #2b3542}
.SUCCEEDED,.confirmed,.ALLOW,.ALLOWED{color:#3fb950;border-color:#2ea043}
.DENIED,.REJECTED,.FAILED,.EXPIRED,.SENSITIVE_FIELD{color:#f85149;border-color:#b62324}
.WAITING_APPROVAL,.APPROVAL_REQUIRED,.pending{color:#d29922;border-color:#9e6a03}
label{display:block;font-size:12px;color:#8792a2;margin:8px 0 2px}
code{font-size:12px;color:#c8d0da;word-break:break-all}
pre{background:#0e1116;border:1px solid #232a33;border-radius:8px;padding:10px;overflow:auto;font-size:12px;white-space:pre-wrap;word-break:break-all}
.flash{background:#1c2530;border:1px solid #2b3542;border-radius:8px;padding:10px 12px;margin-bottom:12px}
"""

LOGIN_BODY = """<h1>Masuk demo</h1><div class="card"><form method="post" action="/ui/login">
<label>Token demo</label><input name="token" placeholder="tok-operator" autofocus>
<p class="muted" style="font-size:12px">operator tok-operator · approver tok-approver · auditor tok-auditor · admin tok-admin</p>
<button>Masuk</button></form></div>"""


def esc(value: Any) -> str:
    return html.escape(str(value))


def money(amount: int) -> str:
    return f"IDR {amount:,}"


def badge(value: Any) -> str:
    return f'<span class="badge {esc(value)}">{esc(value)}</span>'


def identity_from_request(request: Request) -> dict | None:
    scheme, _, token = request.headers.get("Authorization", "").partition(" ")
    if scheme.lower() == "bearer" and token in TOKENS:
        return TOKENS[token]
    return session_identity(request.cookies.get("vt_session"))


def csrf_ok(request: Request, form: Any) -> bool:
    return session_csrf_ok(request, str(form.get("csrf", "")))


def shell(identity: dict | None, csrf: str, title: str, body: str, flash: str = "") -> str:
    nav = '<a href="/ui/dashboard">Dashboard</a><a href="/trust">Trust Explorer</a><a href="/docs">API docs</a>'
    who = ""
    if identity:
        who = (
            f'<span class="muted">{esc(identity["user"])} · {esc(identity["role"])}</span>'
            f'<form class="inline" method="post" action="/ui/logout"><input type="hidden" name="csrf" value="{esc(csrf)}">'
            '<button class="ghost">keluar</button></form>'
        )
    flash_html = f'<div class="flash">{flash}</div>' if flash else ""
    return (
        '<!doctype html><html lang="id"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{esc(title)} · VERITAS AI</title><style>{CSS}</style></head><body>"
        f"<header><b>VERITAS AI</b>{nav}<span style=\"margin-left:auto\"></span>{who}</header>"
        f"<main>{flash_html}{body}</main></body></html>"
    )


def ui_error(message: str, status: int = 400, identity: dict | None = None) -> HTMLResponse:
    csrf = "" if not identity else ""
    return HTMLResponse(shell(identity, csrf, "Error", f'<h1>Error</h1><div class="card">{esc(message)}</div>'), status_code=status)


@app.get("/ui", response_class=HTMLResponse)
def ui_home(request: Request):
    if identity_from_request(request):
        return RedirectResponse("/ui/dashboard", status_code=303)
    response = HTMLResponse(shell(None, "", "Masuk", LOGIN_BODY))
    if not request.cookies.get("vt_csrf"):
        response.set_cookie("vt_csrf", secrets.token_hex(16), samesite="strict")
    return response


@app.post("/ui/login")
async def ui_login(request: Request):
    form = await request.form()
    token = str(form.get("token", "")).strip()
    if token not in TOKENS:
        return HTMLResponse(shell(None, "", "Masuk", LOGIN_BODY + '<div class="flash">Token tidak dikenal.</div>'), status_code=401)
    session_token, csrf = create_session(TOKENS[token])
    response = RedirectResponse("/ui/dashboard", status_code=303)
    set_session_cookies(response, session_token, csrf)
    return response


@app.post("/ui/logout")
async def ui_logout(request: Request):
    form = await request.form()
    if not csrf_ok(request, form):
        return ui_error("CSRF token tidak valid.", 403)
    revoke_session(request.cookies.get("vt_session"))
    response = RedirectResponse("/ui", status_code=303)
    response.delete_cookie("vt_session")
    response.delete_cookie("vt_csrf")
    return response


@app.get("/ui/dashboard", response_class=HTMLResponse)
def ui_dashboard(request: Request, msg: str = ""):
    identity = identity_from_request(request)
    if not identity:
        return RedirectResponse("/ui", status_code=303)
    csrf = request.cookies.get("vt_csrf", "")
    org, project = scope_of(identity)
    can_submit = identity["role"] in ("operator", "admin")
    can_approve = identity["role"] in ("approver", "admin")

    if can_submit:
        task_form = """<div class="card"><form method="post" action="/ui/tasks">
<label>Invoice ID</label><input name="invoice_id" value="INV-2036-010" required>
<label>Nominal</label><input name="amount_idr" type="number" min="1" value="8500000" required>
<label>Vendor</label><select name="vendor"><option>ABC</option><option>XYZ</option><option>EVIL</option></select>
<button>Ajukan tugas</button></form></div>"""
    else:
        task_form = '<p class="muted">Peran ini tidak dapat mengajukan tugas.</p>'

    execution_rows = "".join(
        f'<tr><td><a href="/ui/executions/{esc(ex["id"])}">{esc(ex["id"][:13])}</a></td><td>{badge(ex["status"])}</td>'
        f'<td>{esc(ex["decision"] or "-")}</td><td>{esc(ex["reason_code"] or "-")}</td>'
        f'<td>{money(json.loads(ex["args_json"])["amount_idr"]) if ex["args_json"] else "-"}</td>'
        f'<td>{esc(ex["created_at"])}</td></tr>'
        for ex in rows("SELECT * FROM executions WHERE organization_id=? AND project_id=? "
                       "ORDER BY created_at DESC LIMIT 15", (org, project))
    ) or '<tr><td colspan="6" class="muted">Belum ada eksekusi.</td></tr>'

    if can_approve:
        approval_rows = "".join(
            f'<tr><td>{esc(a["id"][:16])}</td><td><a href="/ui/executions/{esc(a["execution_id"])}">{esc(a["execution_id"][:13])}</a></td>'
            f'<td>{money(json.loads(a["args_json"])["amount_idr"])}</td><td>{esc(a["expires_at"])}</td><td>'
            f'<form class="inline" method="post" action="/ui/approvals/{esc(a["id"])}/decisions">'
            f'<input type="hidden" name="csrf" value="{esc(csrf)}"><input type="hidden" name="decision" value="approve">'
            '<input type="hidden" name="reason" value="Reviewed via dashboard"><button>Setujui</button></form> '
            f'<form class="inline" method="post" action="/ui/approvals/{esc(a["id"])}/decisions">'
            f'<input type="hidden" name="csrf" value="{esc(csrf)}"><input type="hidden" name="decision" value="reject">'
            '<input type="hidden" name="reason" value="Ditolak via dashboard"><button class="danger">Tolak</button></form>'
            "</td></tr>"
            for a in rows("SELECT a.*, e.args_json FROM approvals a JOIN executions e ON e.id=a.execution_id "
                          "WHERE a.status='pending' AND e.organization_id=? AND e.project_id=? ORDER BY a.created_at",
                          (org, project))
        ) or '<tr><td colspan="5" class="muted">Tidak ada approval menunggu.</td></tr>'
    else:
        approval_rows = '<tr><td colspan="5" class="muted">Hanya approver/admin yang dapat memutuskan.</td></tr>'

    delivery_rows = "".join(
        f'<tr><td>{esc(d["id"][:13])}</td><td>{esc(d["destination"])}</td><td>{badge(d["decision"])}</td>'
        f'<td>{esc(d["reason_code"] or "-")}</td><td>{esc(d["sensitive_fields"] or "-")}</td><td>{esc(d["created_at"])}</td></tr>'
        for d in rows("SELECT * FROM egress_deliveries ORDER BY created_at DESC LIMIT 10")
    ) or '<tr><td colspan="6" class="muted">Belum ada pengiriman.</td></tr>'

    egress_form = """<div class="card"><form method="post" action="/ui/egress">
<label>Tujuan</label><select name="destination"><option>mock://crm</option><option>mock://ledger</option><option>https://evil.example</option></select>
<label>Payload (JSON)</label><textarea name="payload" rows="3">{"name": "Nexora", "amount_idr": 8500000}</textarea>
<button>Kirim lewat Harness</button>
<p class="muted" style="font-size:12px">Ubah payload ke {"api_key": "sk-live-secret"} untuk melihat blokir. Pemeriksaan hanya untuk jalur yang dimediasi Harness.</p>
</form></div>"""

    body = f"""
<h1>Dashboard</h1>
<div class="grid" style="grid-template-columns:repeat(auto-fit,minmax(300px,1fr))">
<div><h2>Ajukan invoice</h2>{task_form}</div>
<div><h2>Kirim data keluar</h2>{egress_form}</div>
</div>
<h2>Approval menunggu</h2>
<table><tr><th>Approval</th><th>Eksekusi</th><th>Nominal</th><th>Kedaluwarsa</th><th>Aksi</th></tr>{approval_rows}</table>
<h2>Eksekusi</h2>
<table><tr><th>ID</th><th>Status</th><th>Keputusan</th><th>Alasan</th><th>Nominal</th><th>Dibuat</th></tr>{execution_rows}</table>
<h2>Pengiriman data keluar</h2>
<table><tr><th>ID</th><th>Tujuan</th><th>Keputusan</th><th>Alasan</th><th>Field sensitif</th><th>Waktu</th></tr>{delivery_rows}</table>
"""
    return HTMLResponse(shell(identity, csrf, "Dashboard", body, esc(msg) if msg else ""))


@app.post("/ui/tasks")
async def ui_create_task(request: Request):
    identity = identity_from_request(request)
    if not identity:
        return RedirectResponse("/ui", status_code=303)
    form = await request.form()
    if not csrf_ok(request, form):
        return ui_error("CSRF token tidak valid.", 403, identity)
    if identity["role"] not in ("operator", "admin"):
        return ui_error("Peran tidak berhak mengajukan tugas.", 403, identity)
    try:
        payload = {
            "invoice_id": str(form.get("invoice_id", "")).strip(),
            "amount_idr": int(str(form.get("amount_idr", ""))),
            "vendor": str(form.get("vendor", "")).strip(),
        }
        view = submit_task(payload, f"ui-{uuid.uuid4().hex[:12]}", identity, uuid.uuid4().hex)
    except (ValueError, ApiError) as exc:
        message = exc.message if isinstance(exc, ApiError) else "Nominal harus bilangan bulat."
        return ui_dashboard(request, msg=message)
    return RedirectResponse(f"/ui/executions/{view['execution_id']}", status_code=303)


@app.post("/ui/approvals/{approval_id}/decisions")
async def ui_decide(request: Request, approval_id: str):
    identity = identity_from_request(request)
    if not identity:
        return RedirectResponse("/ui", status_code=303)
    form = await request.form()
    if not csrf_ok(request, form):
        return ui_error("CSRF token tidak valid.", 403, identity)
    try:
        result = decide_core(approval_id, str(form.get("decision", "")), str(form.get("reason", "")),
                             int(str(form.get("expected_version", 1))), identity)
    except (ValueError, ApiError) as exc:
        message = exc.message if isinstance(exc, ApiError) else "Permintaan tidak valid."
        return ui_dashboard(request, msg=message)
    execution = result["execution"]
    return RedirectResponse(
        f"/ui/executions/{execution['execution_id']}?msg={esc('Approval: ' + result['status'])}", status_code=303
    )


@app.post("/ui/egress")
async def ui_egress(request: Request):
    identity = identity_from_request(request)
    if not identity:
        return RedirectResponse("/ui", status_code=303)
    form = await request.form()
    if not csrf_ok(request, form):
        return ui_error("CSRF token tidak valid.", 403, identity)
    try:
        payload = json.loads(str(form.get("payload", "")))
        result = send_egress(str(form.get("destination", "")), payload, f"ui-{uuid.uuid4().hex[:12]}", identity)
    except json.JSONDecodeError:
        return ui_dashboard(request, msg="Payload harus JSON valid.")
    except (ApiError, TypeError) as exc:
        message = exc.message if isinstance(exc, ApiError) else "Payload harus objek JSON."
        return ui_dashboard(request, msg=message)
    return ui_dashboard(
        request,
        msg=f"Egress {result['decision']} ({result['reason_code']}); panggilan mock receiver: {result['mock_calls']}.",
    )


@app.post("/ui/receipts/{receipt_id}/verify")
async def ui_verify(request: Request, receipt_id: str):
    identity = identity_from_request(request)
    if not identity:
        return RedirectResponse("/ui", status_code=303)
    form = await request.form()
    if not csrf_ok(request, form):
        return ui_error("CSRF token tidak valid.", 403, identity)
    try:
        result = verify_stored_receipt(receipt_id, identity)
    except ApiError as exc:
        return ui_error(exc.message, exc.status, identity)
    receipt = one("SELECT execution_id FROM receipts WHERE id=?", (receipt_id,))
    message = (
        f"verified={str(result['verified']).lower()} · signature={str(result['signature_valid']).lower()} · "
        f"hash={str(result['hash_matches']).lower()} · anchor={result['anchor_status']}"
    )
    return RedirectResponse(f"/ui/executions/{receipt['execution_id']}?msg={esc(message)}", status_code=303)


@app.post("/ui/anchors/{anchor_id}/confirm")
async def ui_confirm_anchor(request: Request, anchor_id: str):
    identity = identity_from_request(request)
    if not identity:
        return RedirectResponse("/ui", status_code=303)
    form = await request.form()
    if not csrf_ok(request, form):
        return ui_error("CSRF token tidak valid.", 403, identity)
    if identity["role"] != "admin":
        return ui_error("Hanya admin yang dapat mengonfirmasi anchor.", 403, identity)
    anchor = one("SELECT receipt_id FROM anchors WHERE id=?", (anchor_id,))
    if not anchor:
        return ui_error("Anchor tidak ditemukan.", 404, identity)
    receipt = one("SELECT execution_id FROM receipts WHERE id=?", (anchor["receipt_id"],))
    execution = one("SELECT * FROM executions WHERE id=?", (receipt["execution_id"],)) if receipt else None
    if not execution:
        return ui_error("Anchor tidak ditemukan.", 404, identity)
    require_execution_scope(execution, identity)
    confirm_anchor_core(anchor_id)
    return RedirectResponse(f"/ui/executions/{receipt['execution_id']}?msg=Anchor dikonfirmasi.", status_code=303)


@app.get("/ui/executions/{execution_id}", response_class=HTMLResponse)
def ui_execution(request: Request, execution_id: str, msg: str = ""):
    identity = identity_from_request(request)
    if not identity:
        return RedirectResponse("/ui", status_code=303)
    csrf = request.cookies.get("vt_csrf", "")
    try:
        view = execution_view(execution_id, identity)
    except ApiError as exc:
        return ui_error(exc.message, exc.status, identity)

    events_html = "".join(
        f'<tr><td>{ev["seq"]}</td><td>{esc(ev["type"])}</td><td><code>{esc(json.dumps(ev["data"]))}</code></td>'
        f'<td><code>{esc(ev["hash"][:12])}</code></td></tr>'
        for ev in (dict(r) | {"data": json.loads(r["data_json"])} for r in rows(
            "SELECT * FROM events WHERE execution_id=? ORDER BY seq", (execution_id,)))
    )

    receipt_html = '<p class="muted">Belum ada receipt.</p>'
    if view["receipt_id"]:
        receipt = one("SELECT * FROM receipts WHERE id=?", (view["receipt_id"],))
        anchor_row = one("SELECT * FROM anchors WHERE receipt_id=?", (view["receipt_id"],))
        confirm_btn = ""
        if anchor_row["status"] == "pending" and identity["role"] == "admin" and not chain_enabled():
            confirm_btn = (
                f'<form method="post" action="/ui/anchors/{esc(anchor_row["id"])}/confirm">'
                f'<input type="hidden" name="csrf" value="{esc(csrf)}"><button>Konfirmasi anchor (mock)</button></form>'
            )
        receipt_html = f"""
<div class="card">
<p>Receipt <code>{esc(receipt["id"])}</code> · digest <code>{esc(receipt["digest"])}</code></p>
<p>Anchor {badge(anchor_row["status"])} {('· tx ' + esc(anchor_row["tx_ref"])) if anchor_row["tx_ref"] else ''}</p>
<form method="post" action="/ui/receipts/{esc(receipt["id"])}/verify"><input type="hidden" name="csrf" value="{esc(csrf)}">
<button>Verifikasi receipt</button></form>{confirm_btn}
<details><summary class="muted">Canonical receipt</summary><pre>{esc(receipt["body_json"])}</pre></details>
</div>"""

    body = f"""
<h1>Eksekusi <code>{esc(view["execution_id"])}</code></h1>
<div class="card">
<p>Status {badge(view["status"])} · keputusan {esc(view["decision"] or "-")} · alasan {esc(view["reason_code"] or "-")}</p>
<p>Tool calls: <b>{view["tool_calls"]}</b> · receipt <code>{esc(view["receipt_id"] or "-")}</code></p>
<pre>{esc(json.dumps(view["proposal"], indent=2)) if view["proposal"] else "Tidak ada proposal"}</pre>
</div>
<h2>Receipt dan verifikasi</h2>{receipt_html}
<h2>Timeline</h2>
<table><tr><th>#</th><th>Event</th><th>Data</th><th>Hash</th></tr>{events_html}</table>
"""
    return HTMLResponse(shell(identity, csrf, "Eksekusi", body, esc(msg) if msg else ""))

# --------------------------------------------------------------------------- public trust explorer

def render_verification(result: dict) -> str:
    checks = [
        ("Signature valid", result["signature_valid"]),
        ("Trusted key", result["trusted_key"]),
        ("Hash matches", result["hash_matches"]),
        ("Anchor confirmed", result["anchor_status"] == "confirmed"),
        ("Anchor matches", result["anchor_matches"]),
    ]
    checks_html = "".join(
        f'<tr><td>{esc(name)}</td><td>{badge("PASS" if ok else "FAIL")}</td></tr>' for name, ok in checks
    )
    verdict = badge("VERIFIED" if result["verified"] else "NOT VERIFIED")
    return (
        f'<div class="card"><p>Verdict {verdict}</p>'
        f'<p class="muted">Receipt <code>{esc(result["receipt_id"] or "-")}</code> · anchor {badge(result["anchor_status"])}</p>'
        f"<table>{checks_html}</table>"
        '<p class="muted" style="font-size:12px">Verified hanya jika signature, key tepercaya, hash, dan anchor confirmed '
        "semuanya cocok. Anchor pending tidak pernah dianggap verified. Verifikasi membuktikan integritas catatan, "
        "bukan kebenaran keputusan AI atau data sumber.</p></div>"
    )


TRUST_BODY = """<h1>Trust Explorer</h1>
<p class="muted">Verifikasi publik tanpa login. Receipt ID berlaku sebagai kapabilitas; jangan bagikan di luar demo.</p>
<div class="card"><form method="get" action="/trust"><label>Receipt ID</label>
<input name="receipt_id" placeholder="rcpt_..." style="width:min(420px,100%)"><button>Verifikasi</button></form></div>"""


@app.get("/trust", response_class=HTMLResponse)
def trust_page(receipt_id: str = "", msg: str = ""):
    result_html = ""
    if receipt_id.strip():
        try:
            result_html = render_verification(verify_stored_receipt(receipt_id.strip()))
        except ApiError as exc:
            result_html = f'<div class="flash">{esc(exc.message)}</div>'
    body = (
        TRUST_BODY
        + result_html
        + """<div class="card"><h2>Verifikasi receipt ekspor</h2>
<form method="post" action="/trust/verify"><label>Tempel JSON receipt (termasuk signature dan key_id)</label>
<textarea name="receipt_json" rows="6" style="width:100%"></textarea><button>Verifikasi JSON</button>
<p class="muted" style="font-size:12px">Ubah satu field lalu kirim ulang: signature atau hash harus gagal.</p></form></div>"""
    )
    return HTMLResponse(shell(None, "", "Trust Explorer", body, esc(msg) if msg else ""))


@app.post("/trust/verify", response_class=HTMLResponse)
async def trust_verify(request: Request):
    form = await request.form()
    try:
        parsed = json.loads(str(form.get("receipt_json", "")).strip())
        if not isinstance(parsed, dict):
            raise ValueError
    except ValueError:
        return HTMLResponse(shell(None, "", "Trust Explorer", TRUST_BODY + '<div class="flash">JSON tidak valid.</div>'), status_code=422)
    return HTMLResponse(shell(None, "", "Trust Explorer", TRUST_BODY + render_verification(verify_receipt(parsed))))
