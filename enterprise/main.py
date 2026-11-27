"""VERITAS AI enterprise application.

This app is intentionally separate from the demo harness. It starts from an
empty database, derives tenant/role from the authenticated identity, and keeps
LLM output outside the authorization boundary.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
import json
import os
import re
import threading
import time
import uuid
from typing import Any, Mapping

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import Depends, FastAPI, Header, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse, RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text

from . import oidc, repositories as repo
from .agents import (
    PayloadValidationError,
    agent_allows_tool,
    evaluate_agent_policy,
    get_agent,
    list_agent_specs,
    validate_and_normalize_task_payload,
)
from .adapters import (
    AdapterDeliveryError,
    SsrfBlockedError,
    deliver_egress_webhook,
    execute_erp_tool,
    find_sensitive_fields,
    sync_erp_execution_status,
)
from .anchor_worker import (
    AnchorOutboxWorker,
    process_anchor,
    rpc_enabled,
    sweep_pending_anchors,
)
from .auth import (
    ApiError,
    Identity,
    current_identity,
    install_error_handler,
    issue_session,
    revoke_session,
)
from .config import get_engine, session_scope
from .hashing import GENESIS_HASH, canonical_json, sha256, utc_now
from .kms import get_signing_key
from .llm import propose
from .notifications import send_approval_email
from .passwords import hash_password, validate_password_strength, verify_password
from .rbac import ROLES, assert_approval_allowed, assert_role, require_role
from .session_store import InMemorySessionStore, configure_session_store
from .tools import DEFAULT_TOOLS, ToolRegistry

_OUTBOX_WORKER = AnchorOutboxWorker()


class ApprovalExpiryWorker:
    """Periodic background worker that marks overdue pending approvals as EXPIRED."""

    def __init__(self, poll_seconds: float | None = None) -> None:
        raw = os.environ.get("VERITAS_EXPIRY_SWEEP_SECONDS", "15").strip()
        self._poll = poll_seconds if poll_seconds is not None else float(raw or "15")
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None or self._poll <= 0:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="veritas-approval-expiry", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    def _run(self) -> None:
        while not self._stop.wait(self._poll):
            try:
                sweep_all_expired_approvals()
            except Exception:
                pass


_EXPIRY_WORKER = ApprovalExpiryWorker()


@asynccontextmanager
async def lifespan(_: FastAPI):
    bootstrap()
    _OUTBOX_WORKER.start()
    _EXPIRY_WORKER.start()
    try:
        yield
    finally:
        _EXPIRY_WORKER.stop()
        _OUTBOX_WORKER.stop()


app = FastAPI(title="VERITAS AI Enterprise", version="1.0.0", lifespan=lifespan)
install_error_handler(app)

_CORS_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("VERITAS_CORS_ORIGINS", "").split(",")
    if origin.strip() and origin.strip() != "*"
]
if _CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

if os.environ.get("VERITAS_SESSION_STORE", "").strip().lower() == "memory":
    configure_session_store(InMemorySessionStore())

_HTTP_REQUESTS: dict[tuple[str, str, int], int] = {}


@app.middleware("http")
async def observability_middleware(request: Request, call_next: Any) -> Response:
    cid = request.headers.get("X-Correlation-ID", "").strip() or uuid.uuid4().hex[:16]
    request.state.correlation_id = cid
    start = time.monotonic()
    response = await call_next(request)
    elapsed_ms = round((time.monotonic() - start) * 1000, 2)
    key = (request.method, request.url.path, response.status_code)
    _HTTP_REQUESTS[key] = _HTTP_REQUESTS.get(key, 0) + 1
    response.headers["X-Correlation-ID"] = cid
    if os.environ.get("VERITAS_LOG_JSON", "").strip() == "1":
        print(
            json.dumps(
                {
                    "ts": utc_now(),
                    "correlation_id": cid,
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": elapsed_ms,
                }
            ),
            flush=True,
        )
    return response


class TaskRequest(BaseModel):
    agent_id: str | None = None
    task_type: str | None = None
    payload: dict[str, Any]


class DecisionRequest(BaseModel):
    decision: str = Field(pattern="^(approve|reject)$")
    reason: str = ""
    expected_version: int = 1


class PolicyRequest(BaseModel):
    auto_approve_limit_idr: int
    hard_cap_idr: int | None = None
    vendors: list[str] | None = None


class LoginRequest(BaseModel):
    email: str
    password: str
    tenant_id: str | None = None


class UserCreateRequest(BaseModel):
    email: str
    display_name: str | None = None
    role: str
    password: str


class UserRoleUpdateRequest(BaseModel):
    role: str
    status: str | None = Field(default=None, pattern="^(active|disabled)$")


class ToolToggleRequest(BaseModel):
    enabled: bool


class AgentToggleRequest(BaseModel):
    enabled: bool


class TenantCreateRequest(BaseModel):
    id: str = Field(min_length=2, max_length=64)
    name: str = Field(min_length=2, max_length=255)
    slug: str | None = Field(default=None, max_length=128)


class EgressRequest(BaseModel):
    destination: str
    payload: dict[str, Any]


class VendorUpsertRequest(BaseModel):
    vendor_code: str
    name: str
    tax_id: str | None = None
    status: str = Field(default="active", pattern="^(active|blocked)$")


class VendorStatusRequest(BaseModel):
    status: str = Field(pattern="^(active|blocked)$")


_DEFAULT_FX_RATES: dict[str, float] = {
    "IDR": 1.0,
    "USD": 16000.0,
    "SGD": 11800.0,
    "EUR": 17200.0,
}


def _fx_rates() -> dict[str, float]:
    raw = os.environ.get("VERITAS_FX_RATES", "").strip()
    if not raw:
        return dict(_DEFAULT_FX_RATES)
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return {**{k.upper(): float(v) for k, v in parsed.items()}, "IDR": 1.0}
    except Exception:
        pass
    return dict(_DEFAULT_FX_RATES)


def _normalize_currency_payload(payload: dict[str, Any]) -> None:
    """Convert multi-currency amount + currency into integer amount_idr when needed."""
    currency = str(payload.get("currency") or "IDR").strip().upper()
    payload["currency"] = currency
    if "amount_idr" in payload and type(payload["amount_idr"]) is int:
        return
    raw_amount = payload.get("amount")
    if isinstance(raw_amount, (int, float)) and not isinstance(raw_amount, bool) and raw_amount > 0:
        rates = _fx_rates()
        if currency not in rates:
            raise ApiError(422, "UNSUPPORTED_CURRENCY", f"Unsupported currency '{currency}'.")
        payload["original_amount"] = raw_amount
        payload["amount_idr"] = int(round(float(raw_amount) * rates[currency]))


def _is_production() -> bool:
    return os.environ.get("VERITAS_ENV", "").strip().lower() == "production"


_LOGIN_WINDOW_SECONDS = 60
_LOGIN_MAX_FAILURES = 5
_LOGIN_FAILURES: dict[str, list[float]] = {}


def _login_blocked(key: str) -> bool:
    now = time.monotonic()
    recent = [ts for ts in _LOGIN_FAILURES.get(key, ()) if now - ts < _LOGIN_WINDOW_SECONDS]
    _LOGIN_FAILURES[key] = recent
    return len(recent) >= _LOGIN_MAX_FAILURES


def _record_login_failure(key: str) -> None:
    _LOGIN_FAILURES.setdefault(key, []).append(time.monotonic())


def _clear_login_failures(key: str) -> None:
    _LOGIN_FAILURES.pop(key, None)


# --------------------------------------------------------------------------- signing

def signer() -> tuple[Ed25519PrivateKey, str]:
    key = get_signing_key()
    return key.private_key, key.key_id


# --------------------------------------------------------------------------- policy

DEFAULT_POLICY_SOURCE = {
    "auto_approve_limit_idr": 5_000_000,
    "hard_cap_idr": 25_000_000,
    "vendors": ["V-ABC", "V-XYZ"],
}


def policy_from_row(row: Any) -> dict[str, Any]:
    return json.loads(row.source_json)


def evaluate_policy(source: Mapping[str, Any], tool: str, args: Mapping[str, Any]) -> tuple[str, str]:
    return evaluate_agent_policy(source, tool, args)


def active_policy(session: Any, tenant_id: str) -> Any:
    rows = repo.list_policies(session, tenant_id=tenant_id, status="active", limit=1)
    if not rows:
        raise ApiError(503, "POLICY_UNAVAILABLE", "No active policy for tenant.")
    return rows[0]


def registry_for(session: Any, tenant_id: str) -> ToolRegistry:
    registry = ToolRegistry()
    for row in repo.list_tools(session, tenant_id=tenant_id, enabled_only=True):
        try:
            registry.allow(tenant_id, row.tool_name)
        except ValueError:
            continue
    return registry


# --------------------------------------------------------------------------- bootstrap

def _seed_tenant_defaults(session: Any, *, tenant_id: str) -> None:
    """Ensure a tenant has baseline policy v1, registered tools, agent configs, and sample vendors."""
    if not repo.list_policies(session, tenant_id=tenant_id, limit=1):
        source = dict(DEFAULT_POLICY_SOURCE)
        repo.create_policy(
            session,
            tenant_id=tenant_id,
            id=f"pol_{uuid.uuid4().hex[:12]}",
            version=1,
            source_json=canonical_json(source),
            digest=sha256(canonical_json(source)),
        )
    for tool in DEFAULT_TOOLS:
        if repo.get_tool(session, tenant_id=tenant_id, tool_name=tool.name) is None:
            repo.register_tool(
                session,
                tenant_id=tenant_id,
                id=f"tool_{uuid.uuid4().hex[:12]}",
                tool_name=tool.name,
            )
    for spec in list_agent_specs():
        if repo.get_agent_config(session, tenant_id=tenant_id, agent_id=spec.agent_id) is None:
            repo.upsert_agent_config(
                session,
                tenant_id=tenant_id,
                id=f"agcfg_{uuid.uuid4().hex[:12]}",
                agent_id=spec.agent_id,
                enabled=True,
                updated_by="system:bootstrap",
            )
    for v_code, v_name in (("V-ABC", "PT Global Tech (ABC)"), ("V-XYZ", "PT Nusantara Cloud (XYZ)")):
        if repo.get_vendor_by_code(session, tenant_id=tenant_id, vendor_code=v_code) is None:
            repo.upsert_vendor(
                session,
                tenant_id=tenant_id,
                id=f"vnd_{uuid.uuid4().hex[:12]}",
                vendor_code=v_code,
                name=v_name,
                status="active",
            )


def bootstrap() -> None:
    tenant_id = os.environ.get("VERITAS_BOOTSTRAP_TENANT_ID", "default").strip() or "default"
    tenant_name = os.environ.get("VERITAS_BOOTSTRAP_TENANT_NAME", "Default Tenant")
    with session_scope() as session:
        if repo.get_tenant(session, tenant_id=tenant_id) is None:
            repo.create_tenant(
                session,
                id=tenant_id,
                name=tenant_name,
                slug=os.environ.get("VERITAS_BOOTSTRAP_TENANT_SLUG", "default"),
            )
        _seed_tenant_defaults(session, tenant_id=tenant_id)
        admin_email = os.environ.get("VERITAS_BOOTSTRAP_ADMIN_EMAIL", "").strip().lower()
        admin_password = os.environ.get("VERITAS_BOOTSTRAP_ADMIN_PASSWORD", "")
        if admin_email and admin_password:
            existing_user = repo.get_user_by_email(session, email=admin_email)
            if existing_user is None:
                validate_password_strength(admin_password)
                existing_user = repo.create_user(
                    session,
                    id=f"usr_{uuid.uuid4().hex[:12]}",
                    email=admin_email,
                    display_name=os.environ.get("VERITAS_BOOTSTRAP_ADMIN_NAME", "Tenant Admin"),
                    password_hash=hash_password(admin_password),
                )
            if repo.get_user_tenant(session, tenant_id=tenant_id, user_id=existing_user.id) is None:
                repo.add_user_to_tenant(session, tenant_id=tenant_id, user_id=existing_user.id, role="admin")


# --------------------------------------------------------------------------- helpers

def _not_found(kind: str) -> ApiError:
    return ApiError(404, "NOT_FOUND", f"{kind} not found in tenant scope.")


def _row_dict(row: Any) -> dict[str, Any]:
    return {column.name: getattr(row, column.name) for column in row.__table__.columns}


def _append_event(
    session: Any,
    *,
    tenant_id: str,
    execution_id: str,
    event_type: str,
    data: Mapping[str, Any],
) -> str:
    previous = repo.list_events(session, tenant_id=tenant_id, execution_id=execution_id, limit=1)
    prev_hash = previous[-1].hash if previous else GENESIS_HASH
    digest = sha256(prev_hash + canonical_json({"execution_id": execution_id, "type": event_type, "data": data}))
    repo.create_event(
        session,
        tenant_id=tenant_id,
        execution_id=execution_id,
        type=event_type,
        data=data,
        prev_hash=prev_hash,
        hash=digest,
    )
    return digest


def _issue_receipt(
    session: Any,
    *,
    tenant_id: str,
    execution_id: str,
    decision: str,
    outcome: str,
    tool: str,
    args: Mapping[str, Any],
    actor: str,
    policy_digest: str,
    reason_code: str | None = None,
    agent_id: str = "procurement-agent",
) -> str:
    private, key_id = signer()
    receipt_id = f"rcpt_{uuid.uuid4().hex[:16]}"
    previous = repo.list_events(session, tenant_id=tenant_id, execution_id=execution_id, limit=1)
    previous_hash = previous[-1].hash if previous else GENESIS_HASH
    body = {
        "receipt_id": receipt_id,
        "tenant_id": tenant_id,
        "execution_id": execution_id,
        "agent_id": agent_id,
        "decision": decision,
        "outcome": outcome,
        "tool": tool,
        "input_digest": sha256(canonical_json(args)),
        "policy_digest": policy_digest,
        "previous_event_hash": previous_hash,
        "actor": actor,
        "timestamp_utc": utc_now(),
    }
    canonical = canonical_json(body)
    digest = sha256(canonical)
    signature = private.sign(canonical.encode()).hex()
    repo.create_receipt(
        session,
        tenant_id=tenant_id,
        id=receipt_id,
        execution_id=execution_id,
        body_json=canonical,
        digest=digest,
        signature=signature,
        key_id=key_id,
    )
    anchor = repo.create_anchor(
        session,
        tenant_id=tenant_id,
        id=f"anc_{uuid.uuid4().hex[:16]}",
        receipt_id=receipt_id,
        receipt_hash=digest,
        status="pending",
    )
    if rpc_enabled():
        process_anchor(session, anchor, actor=actor)
    repo.set_execution_status(
        session, tenant_id=tenant_id, execution_id=execution_id,
        status="SUCCEEDED", decision="ALLOW" if decision == "ALLOW" else "APPROVAL_REQUIRED",
        reason_code=reason_code or "WITHIN_LIMIT", receipt_id=receipt_id,
    )
    return receipt_id


def _execute_tool(session: Any, *, tenant_id: str, execution: Any, args: Mapping[str, Any]) -> None:
    tool_name = execution.tool or "approve_invoice"
    try:
        outcome = execute_erp_tool(
            execution_id=execution.id,
            tenant_id=tenant_id,
            tool_name=tool_name,
            arguments=args,
        )
    except (SsrfBlockedError, AdapterDeliveryError) as exc:
        repo.set_execution_status(
            session,
            tenant_id=tenant_id,
            execution_id=execution.id,
            status="FAILED",
            decision=execution.decision or "ALLOW",
            reason_code="TOOL_ADAPTER_FAILED",
        )
        _append_event(
            session,
            tenant_id=tenant_id,
            execution_id=execution.id,
            event_type="FAILED",
            data={"tool": tool_name, "error": str(exc)},
        )
        raise ApiError(502, "TOOL_EXECUTION_FAILED", str(exc)) from exc

    repo.record_tool_call(
        session,
        tenant_id=tenant_id,
        id=f"call_{uuid.uuid4().hex[:16]}",
        execution_id=execution.id,
        tool=tool_name,
        idempotency_key=f"call-{execution.id}",
    )
    _append_event(
        session, tenant_id=tenant_id, execution_id=execution.id,
        event_type="EXECUTING", data={"tool": tool_name, "adapter": outcome.get("mode")},
    )


# --------------------------------------------------------------------------- health / auth

@app.get("/health/live")
def health_live() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
def health_ready() -> dict[str, str]:
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:
        raise ApiError(503, "DATABASE_UNAVAILABLE", "Database is not reachable.") from exc
    return {"status": "ok", "database": "ok"}


@app.get("/api/v1/me")
def me(identity: Identity = Depends(current_identity)) -> dict[str, Any]:
    return {
        "user": identity.user_id,
        "role": identity.roles[0] if identity.roles else "",
        "roles": list(identity.roles),
        "tenant_id": identity.tenant_id,
        "organization_id": identity.tenant_id,
        "project_id": "proj-procurement",
        "email": identity.email,
    }


@app.get("/api/v1/auth/start")
async def auth_start(response: Response) -> Any:
    try:
        url = await oidc.start_authorization(response)
    except ApiError:
        raise
    except Exception as exc:
        raise ApiError(503, "OIDC_UNAVAILABLE", "Identity provider is not configured.") from exc
    return RedirectResponse(url, status_code=302)


@app.get("/api/v1/auth/test-login")
def auth_test_login(
    response: Response,
    user_id: str | None = Query(default=None),
    tenant_id: str | None = Query(default=None),
    role: str | None = Query(default=None),
    email: str | None = Query(default=None),
) -> dict[str, Any]:
    """Issue a demo login session when VERITAS_AUTH_TEST_MODE or VERITAS_SSO_BYPASS is enabled."""
    bypass = os.environ.get("VERITAS_SSO_BYPASS", "").strip().lower() in {"1", "true", "yes", "on"}
    if _is_production() and not bypass:
        raise ApiError(404, "NOT_FOUND", "Test login is disabled.")
    mode = os.environ.get("VERITAS_AUTH_TEST_MODE", "").strip().lower()
    if not bypass and mode not in {"1", "true", "yes", "on"}:
        raise ApiError(404, "NOT_FOUND", "Test login is disabled.")
    raw = os.environ.get("VERITAS_TEST_IDENTITY_JSON", "").strip()
    try:
        data = json.loads(raw) if raw else {}
    except Exception as exc:
        raise ApiError(401, "TEST_IDENTITY_INVALID", "Test identity is malformed.") from exc
    if not isinstance(data, dict):
        raise ApiError(401, "TEST_IDENTITY_INVALID", "Test identity is malformed.")
    if role:
        data["roles"] = [role]
    elif not data.get("roles"):
        data["roles"] = ["admin"]
    effective_role = str(data["roles"][0])
    if user_id:
        data["user_id"] = user_id
    elif email:
        data["user_id"] = email.strip().lower()
    elif not data.get("user_id"):
        data["user_id"] = f"demo-{effective_role}"
    if tenant_id:
        data["tenant_id"] = tenant_id
    elif not data.get("tenant_id"):
        data["tenant_id"] = os.environ.get("VERITAS_BOOTSTRAP_TENANT_ID", "default").strip() or "default"
    try:
        identity = Identity.from_mapping(data)
    except Exception as exc:
        raise ApiError(401, "TEST_IDENTITY_INVALID", "Test identity is malformed.") from exc
    issue_session(response, identity)
    return {"user_id": identity.user_id, "tenant_id": identity.tenant_id, "roles": list(identity.roles)}


@app.get("/api/v1/auth/callback")
async def auth_callback(request: Request, response: Response) -> dict[str, Any]:
    identity = await oidc.complete_authorization(request, response)
    issue_session(response, identity)
    return {"user_id": identity.user_id, "tenant_id": identity.tenant_id, "roles": list(identity.roles)}


@app.post("/api/v1/auth/login")
def auth_password_login(body: LoginRequest, response: Response) -> dict[str, Any]:
    """Authenticate an enterprise user against scrypt password hashes in the database."""
    email = body.email.strip().lower()
    if not email or not body.password:
        raise ApiError(401, "INVALID_CREDENTIALS", "Email and password are required.")
    if _login_blocked(email):
        raise ApiError(429, "RATE_LIMITED", "Too many failed login attempts; retry later.")
    with session_scope() as session:
        user = repo.get_user_by_email(session, email=email)
        if user is None or user.status != "active" or not verify_password(body.password, user.password_hash):
            _record_login_failure(email)
            raise ApiError(401, "INVALID_CREDENTIALS", "Invalid email or password.")
        memberships = repo.list_user_memberships(session, user_id=user.id)
        if not memberships:
            _record_login_failure(email)
            raise ApiError(403, "NO_TENANT_ACCESS", "User has no active tenant membership.")
        requested_tenant = (body.tenant_id or "").strip()
        if requested_tenant:
            membership = next((m for m in memberships if m.tenant_id == requested_tenant), None)
            if membership is None:
                raise ApiError(403, "TENANT_FORBIDDEN", "User is not a member of the requested tenant.")
        else:
            membership = memberships[0]
        _clear_login_failures(email)
        identity = Identity(
            user_id=user.id,
            tenant_id=membership.tenant_id,
            roles=(membership.role,),
            email=user.email,
        )
        csrf_token = issue_session(response, identity)
        repo.create_audit_event(
            session,
            tenant_id=identity.tenant_id,
            actor=identity.user_id,
            action="auth.login",
            target_type="user",
            target_id=user.id,
            payload={"method": "password", "role": membership.role},
        )
        return {
            "user": user.id,
            "user_id": user.id,
            "email": user.email,
            "display_name": user.display_name or user.email.split("@")[0],
            "role": membership.role,
            "roles": [membership.role],
            "tenant_id": membership.tenant_id,
            "csrf_token": csrf_token,
        }


@app.post("/api/v1/auth/logout")
def auth_logout(request: Request, response: Response) -> dict[str, bool]:
    return {"revoked": revoke_session(request, response)}


# --------------------------------------------------------------------------- users & roles


@app.get("/api/v1/users")
def users_list(
    identity: Identity = Depends(require_role("admin")),
) -> dict[str, Any]:
    with session_scope() as session:
        users = repo.list_tenant_users_with_details(session, tenant_id=identity.tenant_id)
        return {"users": users, "total": len(users)}


@app.post("/api/v1/users", status_code=201)
def users_create(
    body: UserCreateRequest,
    identity: Identity = Depends(require_role("admin")),
) -> dict[str, Any]:
    email = body.email.strip().lower()
    role = body.role.strip().lower()
    if "@" not in email:
        raise ApiError(422, "INVALID_EMAIL", "A valid email address is required.")
    if role not in ROLES:
        raise ApiError(422, "INVALID_ROLE", f"Role must be one of: {', '.join(sorted(ROLES))}.")
    try:
        validate_password_strength(body.password)
    except ValueError as exc:
        raise ApiError(422, "WEAK_PASSWORD", str(exc)) from exc

    with session_scope() as session:
        existing = repo.get_user_by_email(session, email=email)
        if existing is not None:
            if repo.get_user_tenant(session, tenant_id=identity.tenant_id, user_id=existing.id) is not None:
                raise ApiError(409, "USER_EXISTS", "User already belongs to this tenant.")
            user = existing
        else:
            user = repo.create_user(
                session,
                id=f"usr_{uuid.uuid4().hex[:12]}",
                email=email,
                display_name=(body.display_name or "").strip() or email.split("@")[0],
                password_hash=hash_password(body.password),
            )
        repo.add_user_to_tenant(
            session,
            tenant_id=identity.tenant_id,
            user_id=user.id,
            role=role,
        )
        repo.create_audit_event(
            session,
            tenant_id=identity.tenant_id,
            actor=identity.user_id,
            action="user.created",
            target_type="user",
            target_id=user.id,
            payload={"email": user.email, "role": role},
        )
        return {
            "user_id": user.id,
            "email": user.email,
            "display_name": user.display_name or user.email.split("@")[0],
            "role": role,
            "tenant_id": identity.tenant_id,
            "status": "active",
        }


@app.patch("/api/v1/users/{user_id}/role")
def users_update_role(
    user_id: str,
    body: UserRoleUpdateRequest,
    identity: Identity = Depends(require_role("admin")),
) -> dict[str, Any]:
    role = body.role.strip().lower()
    if role not in ROLES:
        raise ApiError(422, "INVALID_ROLE", f"Role must be one of: {', '.join(sorted(ROLES))}.")
    with session_scope() as session:
        try:
            updated = repo.update_user_tenant_role(
                session,
                tenant_id=identity.tenant_id,
                user_id=user_id,
                role=role,
                status=body.status,
            )
        except repo.NotFound as exc:
            raise _not_found("user") from exc
        repo.create_audit_event(
            session,
            tenant_id=identity.tenant_id,
            actor=identity.user_id,
            action="user.role_updated",
            target_type="user",
            target_id=user_id,
            payload={"role": updated.role, "status": updated.status},
        )
        return {
            "user_id": updated.user_id,
            "tenant_id": updated.tenant_id,
            "role": updated.role,
            "status": updated.status,
        }


# --------------------------------------------------------------------------- tasks

@app.post("/api/v1/tasks", status_code=202)
def create_task(
    body: TaskRequest,
    identity: Identity = Depends(require_role("operator", "admin")),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict[str, Any]:
    key = idempotency_key or f"idem-{uuid.uuid4().hex}"
    payload = dict(body.payload)
    raw_agent_id = body.agent_id if body.agent_id is not None else payload.get("agent_id")
    agent_id = str(raw_agent_id or "procurement-agent").strip()
    agent_spec = get_agent(agent_id)
    if agent_spec is None:
        raise ApiError(422, "UNKNOWN_AGENT", f"Unknown agent_id '{agent_id}'.")
    task_type = str(body.task_type or agent_spec.default_task_type).strip()
    if task_type not in agent_spec.task_types:
        raise ApiError(
            422,
            "INVALID_TASK_TYPE",
            f"task_type '{task_type}' is not valid for agent '{agent_id}'.",
        )
    try:
        validate_and_normalize_task_payload(
            agent_spec=agent_spec,
            task_type=task_type,
            payload=payload,
            normalize_currency=_normalize_currency_payload,
        )
    except PayloadValidationError as exc:
        raise ApiError(422, "INVALID_PAYLOAD", str(exc)) from exc

    with session_scope() as session:
        existing = repo.get_execution_by_idempotency_key(
            session, tenant_id=identity.tenant_id, idempotency_key=key
        )
        if existing is not None:
            if (
                existing.payload_hash != sha256(canonical_json(payload))
                or (existing.agent_id or "procurement-agent") != agent_id
            ):
                raise ApiError(409, "IDEMPOTENCY_CONFLICT", "Key reused with a different payload.")
            return {**_row_dict(existing), "replayed": True}

        execution_id = f"exec_{uuid.uuid4().hex[:16]}"
        repo.create_execution(
            session,
            tenant_id=identity.tenant_id,
            id=execution_id,
            idempotency_key=key,
            payload_json=canonical_json(payload),
            payload_hash=sha256(canonical_json(payload)),
            status="CREATED",
            actor=identity.user_id,
            agent_id=agent_id,
            task_type=task_type,
            correlation_id=uuid.uuid4().hex,
        )
        _append_event(
            session, tenant_id=identity.tenant_id, execution_id=execution_id,
            event_type="TASK_CREATED", data={"actor": identity.user_id, "agent_id": agent_id},
        )

        agent_cfg = repo.get_agent_config(session, tenant_id=identity.tenant_id, agent_id=agent_id)
        if agent_cfg is not None and not agent_cfg.enabled:
            repo.set_execution_status(
                session, tenant_id=identity.tenant_id, execution_id=execution_id,
                status="DENIED", decision="DENY", reason_code="AGENT_DISABLED",
            )
            _append_event(
                session, tenant_id=identity.tenant_id, execution_id=execution_id,
                event_type="DENIED", data={"reason_code": "AGENT_DISABLED"},
            )
            repo.create_audit_event(
                session, tenant_id=identity.tenant_id, actor=identity.user_id,
                action="task.denied", target_type="execution", target_id=execution_id,
                payload={"reason_code": "AGENT_DISABLED", "agent_id": agent_id},
            )
            return _row_dict(repo.get_execution(session, tenant_id=identity.tenant_id, execution_id=execution_id))

        policy = active_policy(session, identity.tenant_id)
        source = policy_from_row(policy)
        proposal = propose(
            payload,
            tenant_id=identity.tenant_id,
            registry=registry_for(session, identity.tenant_id),
            agent_id=agent_id,
            task_type=task_type,
        )
        if (
            not proposal.valid
            or proposal.tool is None
            or proposal.arguments is None
            or not agent_allows_tool(agent_id, proposal.tool)
        ):
            decision, reason = "DENY", proposal.error or (
                "TOOL_NOT_ALLOWED_FOR_AGENT" if proposal.tool else "INVALID_PROPOSAL"
            )
            repo.set_execution_status(
                session, tenant_id=identity.tenant_id, execution_id=execution_id,
                status="DENIED", decision=decision, reason_code=reason,
            )
            _append_event(
                session, tenant_id=identity.tenant_id, execution_id=execution_id,
                event_type="DENIED", data={"reason_code": reason},
            )
            repo.create_audit_event(
                session, tenant_id=identity.tenant_id, actor=identity.user_id,
                action="task.denied", target_type="execution", target_id=execution_id,
                payload={"reason_code": reason, "planner": proposal.planner, "agent_id": agent_id},
            )
            return _row_dict(repo.get_execution(session, tenant_id=identity.tenant_id, execution_id=execution_id))

        args = proposal.arguments
        # Persist proposal/args without changing status via the ORM row directly.
        execution = repo.get_execution(session, tenant_id=identity.tenant_id, execution_id=execution_id)
        execution.proposal_json = canonical_json({"tool": proposal.tool, "arguments": args})
        execution.args_hash = sha256(canonical_json(args))
        execution.tool = proposal.tool
        session.flush()
        _append_event(
            session, tenant_id=identity.tenant_id, execution_id=execution_id,
            event_type="PROPOSAL", data={"tool": proposal.tool, "planner": proposal.planner, "agent_id": agent_id},
        )

        vendor_code = str(args.get("vendor_id") or "")
        effective_source = dict(source)
        if vendor_code:
            vendor_row = repo.get_vendor_by_code(session, tenant_id=identity.tenant_id, vendor_code=vendor_code)
            if vendor_row is not None:
                if vendor_row.status == "blocked":
                    decision, reason = "DENY", "VENDOR_BLOCKED"
                else:
                    effective_source["vendors"] = sorted(set(source.get("vendors", [])) | {vendor_code})
                    decision, reason = evaluate_policy(effective_source, proposal.tool, args)
            else:
                decision, reason = evaluate_policy(effective_source, proposal.tool, args)
        else:
            decision, reason = evaluate_policy(effective_source, proposal.tool, args)
        _append_event(
            session, tenant_id=identity.tenant_id, execution_id=execution_id,
            event_type="POLICY_CHECK", data={"decision": decision, "reason_code": reason},
        )
        if decision == "DENY":
            repo.set_execution_status(
                session, tenant_id=identity.tenant_id, execution_id=execution_id,
                status="DENIED", decision=decision, reason_code=reason,
            )
            _append_event(
                session, tenant_id=identity.tenant_id, execution_id=execution_id,
                event_type="DENIED", data={"reason_code": reason},
            )
            repo.create_audit_event(
                session, tenant_id=identity.tenant_id, actor=identity.user_id,
                action="task.denied", target_type="execution", target_id=execution_id,
                payload={"reason_code": reason, "decision": decision, "agent_id": agent_id},
            )
            return _row_dict(repo.get_execution(session, tenant_id=identity.tenant_id, execution_id=execution_id))

        if decision == "APPROVAL_REQUIRED":
            approval = repo.create_approval(
                session,
                tenant_id=identity.tenant_id,
                id=f"aprv_{uuid.uuid4().hex[:16]}",
                execution_id=execution_id,
                args_hash=sha256(canonical_json(args)),
                policy_version=policy.version,
                requester=identity.user_id,
            )
            repo.set_execution_status(
                session, tenant_id=identity.tenant_id, execution_id=execution_id,
                status="WAITING_APPROVAL", decision=decision, reason_code=reason,
                approval_id=approval.id,
            )
            _append_event(
                session, tenant_id=identity.tenant_id, execution_id=execution_id,
                event_type="APPROVAL_REQUIRED", data={"approval_id": approval.id, "reason_code": reason},
            )
            repo.create_audit_event(
                session, tenant_id=identity.tenant_id, actor=identity.user_id,
                action="task.held", target_type="execution", target_id=execution_id,
                payload={"approval_id": approval.id, "reason_code": reason, "agent_id": agent_id},
            )
            ref_label = str(
                payload.get("invoice_id")
                or payload.get("reference_id")
                or payload.get("employee_id")
                or payload.get("principal_id")
                or payload.get("account_id")
                or execution_id
            )
            target_label = str(
                args.get("vendor_id")
                or args.get("account_code")
                or args.get("department")
                or args.get("zone")
                or args.get("principal_id")
                or args.get("scope")
                or agent_id
            )
            amount_val = int(args.get("amount_idr") or payload.get("amount_idr") or 0)
            notify_result = send_approval_email(
                recipients=repo.list_approver_emails(session, tenant_id=identity.tenant_id),
                execution_id=execution_id,
                invoice_id=ref_label,
                vendor_id=target_label,
                amount_idr=amount_val,
                currency=str(payload.get("currency") or "IDR"),
                original_amount=payload.get("original_amount"),
                reason_code=reason,
            )
            repo.create_audit_event(
                session,
                tenant_id=identity.tenant_id,
                actor="system:notifier",
                action="notification.approval_email",
                target_type="approval",
                target_id=approval.id,
                payload=notify_result,
            )
            return _row_dict(repo.get_execution(session, tenant_id=identity.tenant_id, execution_id=execution_id))

        _execute_tool(
            session, tenant_id=identity.tenant_id,
            execution=repo.get_execution(session, tenant_id=identity.tenant_id, execution_id=execution_id),
            args=args,
        )
        receipt_id = _issue_receipt(
            session, tenant_id=identity.tenant_id, execution_id=execution_id,
            decision="ALLOW", outcome="SUCCEEDED", tool=proposal.tool,
            args=args, actor=identity.user_id, policy_digest=policy.digest,
            reason_code=reason, agent_id=agent_id,
        )
        _append_event(
            session, tenant_id=identity.tenant_id, execution_id=execution_id,
            event_type="SUCCEEDED", data={"receipt_id": receipt_id, "reason_code": reason},
        )
        repo.create_audit_event(
            session, tenant_id=identity.tenant_id, actor=identity.user_id,
            action="task.executed", target_type="execution", target_id=execution_id,
            payload={"receipt_id": receipt_id, "decision": "ALLOW", "agent_id": agent_id},
        )
        return _row_dict(repo.get_execution(session, tenant_id=identity.tenant_id, execution_id=execution_id))


# --------------------------------------------------------------------------- approvals

def _sweep_expired_approvals(session: Any, *, tenant_id: str) -> int:
    """Transition any overdue pending approvals in the tenant to EXPIRED without executing tools."""
    expired_count = 0
    for ap in repo.list_expired_pending_approvals(session, tenant_id=tenant_id):
        repo.expire_approval(
            session,
            tenant_id=tenant_id,
            approval_id=ap.id,
            expected_version=ap.version,
        )
        repo.set_execution_status(
            session,
            tenant_id=tenant_id,
            execution_id=ap.execution_id,
            status="EXPIRED",
            decision="DENY",
            reason_code="APPROVAL_EXPIRED",
        )
        _append_event(
            session,
            tenant_id=tenant_id,
            execution_id=ap.execution_id,
            event_type="APPROVAL_EXPIRED",
            data={"approval_id": ap.id},
        )
        repo.create_audit_event(
            session,
            tenant_id=tenant_id,
            actor="system:expiry-sweeper",
            action="approval.expired",
            target_type="approval",
            target_id=ap.id,
            payload={"execution_id": ap.execution_id},
        )
        expired_count += 1
    return expired_count


def sweep_all_expired_approvals() -> int:
    """Sweep overdue pending approvals across all tenants for background expiration."""
    with session_scope() as session:
        tenant_ids = sorted({row.tenant_id for row in repo.list_all_expired_pending_approvals(session)})
    total = 0
    for tid in tenant_ids:
        with session_scope() as tenant_session:
            total += _sweep_expired_approvals(tenant_session, tenant_id=tid)
    return total


def _revalidate_approval_for_resume(
    session: Any,
    *,
    tenant_id: str,
    approval: Any,
    execution: Any,
    policy: Any,
    args: Mapping[str, Any],
) -> str | None:
    """Re-check state, hash, policy version, tool enablement, and vendor status before executing."""
    if execution.status != "WAITING_APPROVAL":
        return "INVALID_EXECUTION_STATE"
    if approval.args_hash and approval.args_hash != sha256(canonical_json(args)):
        return "ARGS_HASH_MISMATCH"
    if approval.policy_version is not None and approval.policy_version != policy.version:
        return "POLICY_CHANGED"
    tool_name = execution.tool or ""
    agent_id = execution.agent_id or "procurement-agent"
    agent_cfg = repo.get_agent_config(session, tenant_id=tenant_id, agent_id=agent_id)
    if agent_cfg is not None and not agent_cfg.enabled:
        return "AGENT_DISABLED"
    if not agent_allows_tool(agent_id, tool_name):
        return "TOOL_NOT_ALLOWED_FOR_AGENT"
    if not registry_for(session, tenant_id).is_allowed(tenant_id, tool_name):
        return "TOOL_NOT_ALLOWED_FOR_TENANT"
    source = policy_from_row(policy)
    effective_source = dict(source)
    vendor_code = str(args.get("vendor_id") or "")
    if vendor_code:
        vendor_row = repo.get_vendor_by_code(session, tenant_id=tenant_id, vendor_code=vendor_code)
        if vendor_row is not None:
            if vendor_row.status == "blocked":
                return "VENDOR_BLOCKED"
            effective_source["vendors"] = sorted(set(source.get("vendors", [])) | {vendor_code})
    decision, reason = evaluate_policy(effective_source, tool_name, args)
    if decision == "DENY":
        return reason
    return None


@app.get("/api/v1/approvals")
def approvals_list(
    identity: Identity = Depends(require_role("approver", "admin", "auditor")),
) -> list[dict[str, Any]]:
    with session_scope() as session:
        _sweep_expired_approvals(session, tenant_id=identity.tenant_id)
        return [_row_dict(row) for row in repo.list_approvals(session, tenant_id=identity.tenant_id)]


@app.post("/api/v1/approvals/{approval_id}/decisions")
def decide(
    approval_id: str,
    body: DecisionRequest,
    identity: Identity = Depends(require_role("approver", "admin")),
) -> dict[str, Any]:
    # Commit overdue approval expirations before opening the decision transaction
    # so returning 409 APPROVAL_EXPIRED never rolls back the expiry audit trail.
    with session_scope() as sweep_session:
        _sweep_expired_approvals(sweep_session, tenant_id=identity.tenant_id)
    with session_scope() as session:
        approval = repo.get_approval(session, tenant_id=identity.tenant_id, approval_id=approval_id)
        if approval is None:
            raise _not_found("approval")
        if approval.status == "expired":
            raise ApiError(409, "APPROVAL_EXPIRED", "Approval has expired.")
        assert_approval_allowed(identity, approval.requester or "", identity.tenant_id)

        execution = repo.get_execution(
            session, tenant_id=identity.tenant_id, execution_id=approval.execution_id
        )
        if execution is None:
            raise _not_found("execution")

        policy = active_policy(session, identity.tenant_id)
        args = json.loads(execution.proposal_json or "{}").get("arguments", {})

        resume_failure: str | None = None
        if body.decision == "approve":
            resume_failure = _revalidate_approval_for_resume(
                session,
                tenant_id=identity.tenant_id,
                approval=approval,
                execution=execution,
                policy=policy,
                args=args,
            )

        effective_decision = "reject" if (body.decision == "reject" or resume_failure) else "approve"
        effective_reason = (
            f"revalidation:{resume_failure}" if resume_failure else (body.reason or None)
        )
        try:
            decided = repo.decide_approval(
                session,
                tenant_id=identity.tenant_id,
                approval_id=approval_id,
                expected_version=body.expected_version,
                decision=effective_decision,
                approver=identity.user_id,
                reason=effective_reason,
            )
        except repo.SeparationOfDuties as exc:
            raise ApiError(403, "SEPARATION_OF_DUTIES", str(exc)) from exc
        except repo.VersionConflict as exc:
            raise ApiError(409, "VERSION_CONFLICT", str(exc)) from exc
        except repo.InvalidTransition as exc:
            raise ApiError(409, "INVALID_TRANSITION", str(exc)) from exc

        if resume_failure:
            repo.set_execution_status(
                session, tenant_id=identity.tenant_id, execution_id=execution.id,
                status="DENIED", decision="DENY", reason_code=resume_failure,
            )
            _append_event(
                session, tenant_id=identity.tenant_id, execution_id=execution.id,
                event_type="DENIED_ON_RESUME",
                data={"approver": identity.user_id, "reason_code": resume_failure},
            )
            erp_sync = sync_erp_execution_status(
                execution_id=execution.id,
                tenant_id=identity.tenant_id,
                tool_name=execution.tool or "",
                status="DENIED",
                reason=resume_failure,
            )
            repo.create_audit_event(
                session, tenant_id=identity.tenant_id, actor=identity.user_id,
                action="approval.denied_on_resume", target_type="approval", target_id=approval_id,
                payload={"reason_code": resume_failure, "erp_sync": erp_sync},
            )
            return {"approval": _row_dict(decided), "execution": _row_dict(execution)}

        _append_event(
            session, tenant_id=identity.tenant_id, execution_id=execution.id,
            event_type=decided.status.upper(),
            data={"approver": identity.user_id, "reason": body.reason},
        )
        if body.decision == "reject":
            repo.set_execution_status(
                session, tenant_id=identity.tenant_id, execution_id=execution.id,
                status="REJECTED", decision="DENY", reason_code="HUMAN_REJECTED",
            )
            erp_sync = sync_erp_execution_status(
                execution_id=execution.id,
                tenant_id=identity.tenant_id,
                tool_name=execution.tool or "",
                status="REJECTED",
                reason=body.reason,
            )
            repo.create_audit_event(
                session, tenant_id=identity.tenant_id, actor=identity.user_id,
                action="approval.rejected", target_type="approval", target_id=approval_id,
                payload={"reason": body.reason, "erp_sync": erp_sync},
            )
            return {"approval": _row_dict(decided), "execution": _row_dict(execution)}

        _execute_tool(session, tenant_id=identity.tenant_id, execution=execution, args=args)
        receipt_id = _issue_receipt(
            session, tenant_id=identity.tenant_id, execution_id=execution.id,
            decision="APPROVAL_REQUIRED", outcome="SUCCEEDED",
            tool=execution.tool or "approve_invoice", args=args,
            actor=identity.user_id, policy_digest=policy.digest,
            reason_code="HUMAN_APPROVED",
            agent_id=execution.agent_id or "procurement-agent",
        )
        _append_event(
            session, tenant_id=identity.tenant_id, execution_id=execution.id,
            event_type="SUCCEEDED", data={"receipt_id": receipt_id},
        )
        repo.create_audit_event(
            session, tenant_id=identity.tenant_id, actor=identity.user_id,
            action="approval.approved", target_type="approval", target_id=approval_id,
            payload={"receipt_id": receipt_id, "reason": body.reason},
        )
        return {"approval": _row_dict(decided), "execution": _row_dict(execution)}


# --------------------------------------------------------------------------- reads

@app.get("/api/v1/executions")
def executions_list(
    status: str | None = None,
    limit: int = 20,
    identity: Identity = Depends(require_role("operator", "approver", "admin", "auditor")),
) -> dict[str, Any]:
    with session_scope() as session:
        _sweep_expired_approvals(session, tenant_id=identity.tenant_id)
        rows = repo.list_executions(session, tenant_id=identity.tenant_id, status=status, limit=limit)
        return {"executions": [_row_dict(row) for row in rows], "total": len(rows)}


@app.get("/api/v1/executions/{execution_id}")
def execution_get(
    execution_id: str,
    identity: Identity = Depends(require_role("operator", "approver", "admin", "auditor")),
) -> dict[str, Any]:
    with session_scope() as session:
        _sweep_expired_approvals(session, tenant_id=identity.tenant_id)
        row = repo.get_execution(session, tenant_id=identity.tenant_id, execution_id=execution_id)
        if row is None:
            raise _not_found("execution")
        events = repo.list_events(session, tenant_id=identity.tenant_id, execution_id=execution_id)
        return {**_row_dict(row), "events": [_row_dict(event) for event in events]}


@app.get("/api/v1/policies")
def policies_get(identity: Identity = Depends(require_role("operator", "approver", "admin", "auditor"))) -> dict[str, Any]:
    with session_scope() as session:
        policy = active_policy(session, identity.tenant_id)
        return {
            "id": policy.id,
            "version": policy.version,
            "source": policy_from_row(policy),
            "digest": policy.digest,
            "status": policy.status,
        }


@app.put("/api/v1/policies")
def policies_put(
    body: PolicyRequest,
    identity: Identity = Depends(require_role("admin")),
) -> dict[str, Any]:
    if body.auto_approve_limit_idr <= 0:
        raise ApiError(422, "INVALID_LIMIT", "auto_approve_limit_idr must be positive.")
    with session_scope() as session:
        current = active_policy(session, identity.tenant_id)
        source = policy_from_row(current)
        source["auto_approve_limit_idr"] = body.auto_approve_limit_idr
        if body.hard_cap_idr is not None:
            source["hard_cap_idr"] = body.hard_cap_idr
        if body.vendors is not None:
            source["vendors"] = sorted(set(body.vendors))
        if source["auto_approve_limit_idr"] > source["hard_cap_idr"]:
            raise ApiError(422, "INVALID_LIMIT", "auto limit cannot exceed hard cap.")
        canonical = canonical_json(source)
        created = repo.create_policy(
            session,
            tenant_id=identity.tenant_id,
            id=f"pol_{uuid.uuid4().hex[:12]}",
            version=current.version + 1,
            source_json=canonical,
            digest=sha256(canonical),
            created_by=identity.user_id,
        )
        current.status = "superseded"
        session.flush()
        repo.create_audit_event(
            session, tenant_id=identity.tenant_id, actor=identity.user_id,
            action="policy.published", target_type="policy", target_id=created.id,
            payload={"version": created.version, "digest": created.digest},
        )
        return {"id": created.id, "version": created.version, "source": source, "digest": created.digest}


@app.get("/api/v1/receipts/{receipt_id}")
def receipt_get(
    receipt_id: str,
    identity: Identity = Depends(require_role("auditor", "admin", "operator", "approver")),
) -> dict[str, Any]:
    with session_scope() as session:
        receipt = repo.get_receipt(session, tenant_id=identity.tenant_id, receipt_id=receipt_id)
        if receipt is None:
            raise _not_found("receipt")
        anchors = [
            _row_dict(row)
            for row in repo.list_anchors(session, tenant_id=identity.tenant_id)
            if row.receipt_id == receipt_id
        ]
        return {
            "receipt": json.loads(receipt.body_json),
            "digest": receipt.digest,
            "signature": receipt.signature,
            "key_id": receipt.key_id,
            "anchor": anchors[0] if anchors else None,
        }


def _verification(receipt: Any, anchor: Any | None) -> dict[str, Any]:
    digest_matches = sha256(receipt.body_json) == receipt.digest
    signature_valid = False
    trusted_key = False
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

        private, key_id = signer()
        raw = private.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )
        Ed25519PublicKey.from_public_bytes(raw).verify(
            bytes.fromhex(receipt.signature), receipt.body_json.encode()
        )
        signature_valid = True
        trusted_key = receipt.key_id == key_id
    except Exception:
        pass
    anchor_status = anchor.status if anchor else "unknown"
    anchor_matches = bool(anchor) and anchor.receipt_hash == receipt.digest
    verified = (
        digest_matches and signature_valid and trusted_key
        and anchor_status == "confirmed" and anchor_matches
    )
    return {
        "receipt_id": receipt.id,
        "hash_matches": digest_matches,
        "signature_valid": signature_valid,
        "trusted_key": trusted_key,
        "anchor_status": anchor_status,
        "anchor_matches": anchor_matches,
        "verified": verified,
    }


@app.post("/api/v1/receipts/{receipt_id}/verify")
def receipt_verify(
    receipt_id: str,
    identity: Identity = Depends(require_role("auditor", "admin", "operator", "approver")),
) -> dict[str, Any]:
    with session_scope() as session:
        receipt = repo.get_receipt(session, tenant_id=identity.tenant_id, receipt_id=receipt_id)
        if receipt is None:
            raise _not_found("receipt")
        anchors = [row for row in repo.list_anchors(session, tenant_id=identity.tenant_id) if row.receipt_id == receipt_id]
        return _verification(receipt, anchors[0] if anchors else None)


@app.post("/api/v1/anchors/sweep")
def anchors_sweep(
    identity: Identity = Depends(require_role("admin")),
) -> dict[str, int]:
    """Flush pending EVM anchors for the caller's tenant."""
    return sweep_pending_anchors(tenant_id=identity.tenant_id, actor=identity.user_id)


@app.post("/api/v1/anchors/{anchor_id}/confirm")
def anchor_confirm(
    anchor_id: str,
    identity: Identity = Depends(require_role("admin")),
) -> dict[str, Any]:
    """Confirm the local mock anchor. Disabled when an EVM RPC anchor URL is configured."""
    if rpc_enabled():
        raise ApiError(
            409,
            "ANCHOR_MODE",
            "Manual confirm is disabled while VERITAS_ANCHOR_RPC_URL is configured.",
        )
    with session_scope() as session:
        anchor = repo.get_anchor(session, tenant_id=identity.tenant_id, anchor_id=anchor_id)
        if anchor is None:
            raise _not_found("anchor")
        confirmed = repo.set_anchor_status(
            session,
            tenant_id=identity.tenant_id,
            anchor_id=anchor_id,
            status="confirmed",
            tx_ref=f"mock-{uuid.uuid4().hex[:16]}",
        )
        repo.create_audit_event(
            session, tenant_id=identity.tenant_id, actor=identity.user_id,
            action="anchor.confirmed", target_type="anchor", target_id=anchor_id,
            payload={"status": "confirmed", "anchor_is_mock": True},
        )
        return _row_dict(confirmed)


@app.get("/api/v1/agents")
def agents_list(
    identity: Identity = Depends(require_role("operator", "approver", "admin", "auditor")),
) -> dict[str, Any]:
    with session_scope() as session:
        policy = active_policy(session, identity.tenant_id)
        counts = repo.count_executions_by_agent(session, tenant_id=identity.tenant_id)
        tool_rows = repo.list_tools(session, tenant_id=identity.tenant_id)
        cfg_map = {
            row.agent_id: row.enabled
            for row in repo.list_agent_configs(session, tenant_id=identity.tenant_id)
        }
        if tool_rows:
            enabled_tools = {t.tool_name for t in tool_rows if t.enabled}
        else:
            enabled_tools = {t.name for t in DEFAULT_TOOLS}
        return {
            "agents": [
                {
                    "agent_id": spec.agent_id,
                    "name": spec.name,
                    "version": spec.version,
                    "description": spec.description,
                    "enabled": cfg_map.get(spec.agent_id, True),
                    "status": "OPERATIONAL" if cfg_map.get(spec.agent_id, True) else "DISABLED",
                    "default_task_type": spec.default_task_type,
                    "task_types": list(spec.task_types),
                    "allowed_tools": [t for t in spec.tools if t in enabled_tools],
                    "policy_version": policy.version,
                    "executions": counts.get(spec.agent_id, 0),
                }
                for spec in list_agent_specs()
            ]
        }


@app.patch("/api/v1/agents/{agent_id}")
def agents_toggle(
    agent_id: str,
    body: AgentToggleRequest,
    identity: Identity = Depends(require_role("admin")),
) -> dict[str, Any]:
    spec = get_agent(agent_id)
    if spec is None:
        raise _not_found("agent")
    with session_scope() as session:
        cfg = repo.upsert_agent_config(
            session,
            tenant_id=identity.tenant_id,
            id=f"agcfg_{uuid.uuid4().hex[:12]}",
            agent_id=spec.agent_id,
            enabled=body.enabled,
            updated_by=identity.user_id,
        )
        repo.create_audit_event(
            session,
            tenant_id=identity.tenant_id,
            actor=identity.user_id,
            action="agent.toggled",
            target_type="agent",
            target_id=spec.agent_id,
            payload={"enabled": bool(cfg.enabled)},
        )
        return {
            "agent_id": spec.agent_id,
            "enabled": bool(cfg.enabled),
            "status": "OPERATIONAL" if cfg.enabled else "DISABLED",
        }


@app.post("/api/v1/tenants", status_code=201)
def tenants_onboard(
    body: TenantCreateRequest,
    identity: Identity = Depends(require_role("admin")),
) -> dict[str, Any]:
    clean_id = body.id.strip().lower()
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,62}", clean_id):
        raise ApiError(
            422,
            "INVALID_TENANT_ID",
            "Tenant id must contain lowercase letters, digits, or hyphens (2-63 chars).",
        )
    clean_slug = (body.slug or clean_id).strip().lower()
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,126}", clean_slug):
        raise ApiError(
            422,
            "INVALID_TENANT_SLUG",
            "Tenant slug must contain lowercase letters, digits, or hyphens.",
        )
    with session_scope() as session:
        if repo.get_tenant(session, tenant_id=clean_id) is not None or (
            repo.get_tenant_by_slug(session, slug=clean_slug) is not None
        ):
            raise ApiError(409, "TENANT_EXISTS", f"Tenant '{clean_id}' already exists.")
        tenant = repo.create_tenant(
            session,
            id=clean_id,
            name=body.name.strip(),
            slug=clean_slug,
        )
        _seed_tenant_defaults(session, tenant_id=clean_id)
        if repo.get_user(session, user_id=identity.user_id) is not None:
            if repo.get_user_tenant(session, tenant_id=clean_id, user_id=identity.user_id) is None:
                repo.add_user_to_tenant(
                    session, tenant_id=clean_id, user_id=identity.user_id, role="admin"
                )
        repo.create_audit_event(
            session,
            tenant_id=clean_id,
            actor=identity.user_id,
            action="tenant.created",
            target_type="tenant",
            target_id=clean_id,
            payload={"name": tenant.name, "slug": tenant.slug, "created_by_tenant": identity.tenant_id},
        )
        return {**_row_dict(tenant), "seeded": True}


@app.get("/api/v1/tools")
def tools_list(
    identity: Identity = Depends(require_role("operator", "approver", "admin", "auditor")),
) -> dict[str, Any]:
    with session_scope() as session:
        rows = repo.list_tools(session, tenant_id=identity.tenant_id)
        return {"tools": [_row_dict(row) for row in rows]}


@app.patch("/api/v1/tools/{tool_name}")
def tools_toggle(
    tool_name: str,
    body: ToolToggleRequest,
    identity: Identity = Depends(require_role("admin")),
) -> dict[str, Any]:
    with session_scope() as session:
        try:
            updated = repo.set_tool_enabled(
                session,
                tenant_id=identity.tenant_id,
                tool_name=tool_name,
                enabled=body.enabled,
            )
        except repo.NotFound as exc:
            raise _not_found("tool") from exc
        repo.create_audit_event(
            session,
            tenant_id=identity.tenant_id,
            actor=identity.user_id,
            action="tool.toggled",
            target_type="tool",
            target_id=updated.id,
            payload={"tool_name": updated.tool_name, "enabled": updated.enabled},
        )
        return _row_dict(updated)


@app.post("/api/v1/verify")
def verify_supplied_receipt(
    body: dict[str, Any],
    identity: Identity = Depends(require_role("auditor", "admin", "operator", "approver")),
) -> dict[str, Any]:
    """Verify a caller-supplied receipt JSON + Ed25519 signature."""
    payload = dict(body.get("receipt")) if isinstance(body.get("receipt"), dict) else dict(body)
    signature = str(body.get("signature") or payload.pop("signature", "") or "")
    key_id = str(body.get("key_id") or payload.pop("key_id", "") or "")
    payload.pop("signature", None)
    payload.pop("key_id", None)
    canonical_body = canonical_json(payload)
    computed_digest = sha256(canonical_body)
    receipt_id = payload.get("receipt_id") if isinstance(payload.get("receipt_id"), str) else None

    signature_valid = False
    trusted_key = False
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

        private, active_key_id = signer()
        raw = private.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )
        Ed25519PublicKey.from_public_bytes(raw).verify(
            bytes.fromhex(signature), canonical_body.encode()
        )
        signature_valid = True
        trusted_key = key_id == active_key_id
    except Exception:
        pass

    hash_matches = signature_valid
    anchor_status = "unknown"
    anchor_matches = False
    if receipt_id:
        with session_scope() as session:
            stored = repo.get_receipt(session, tenant_id=identity.tenant_id, receipt_id=receipt_id)
            if stored is not None:
                hash_matches = computed_digest == stored.digest
                anchors = [
                    row for row in repo.list_anchors(session, tenant_id=identity.tenant_id)
                    if row.receipt_id == receipt_id
                ]
                if anchors:
                    anchor_status = anchors[0].status
                    anchor_matches = hash_matches and anchors[0].receipt_hash == computed_digest

    verified = (
        hash_matches and signature_valid and trusted_key
        and anchor_status == "confirmed" and anchor_matches
    )
    return {
        "receipt_id": receipt_id,
        "hash_matches": hash_matches,
        "signature_valid": signature_valid,
        "trusted_key": trusted_key,
        "anchor_status": anchor_status,
        "anchor_matches": anchor_matches,
        "verified": verified,
    }


@app.get("/api/v1/egress")
def egress_list(
    identity: Identity = Depends(require_role("operator", "approver", "admin", "auditor")),
) -> dict[str, Any]:
    with session_scope() as session:
        rows = repo.list_egress_deliveries(session, tenant_id=identity.tenant_id)
        return {"deliveries": [_row_dict(row) for row in rows], "total": len(rows)}


@app.post("/api/v1/egress/send")
def egress_send(
    body: EgressRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    identity: Identity = Depends(require_role("operator", "admin")),
) -> JSONResponse:
    destination = body.destination.strip()
    if not destination:
        raise ApiError(422, "INVALID_DESTINATION", "destination is required.")
    payload_digest = sha256(canonical_json({"destination": destination, "payload": body.payload}))

    with session_scope() as session:
        existing = repo.get_egress_by_idempotency_key(
            session, tenant_id=identity.tenant_id, idempotency_key=idempotency_key
        )
        if existing is not None:
            if existing.payload_digest != payload_digest:
                raise ApiError(409, "IDEMPOTENCY_CONFLICT", "Idempotency-Key already used with different payload.")
            if existing.delivery_status != "FAILED":
                status_code = 200 if existing.decision == "ALLOW" else 403
                return JSONResponse(status_code=status_code, content={**_row_dict(existing), "replayed": True})

        policy = active_policy(session, identity.tenant_id)
        policy_src = policy_from_row(policy)
        env_dests = {
            d.strip()
            for d in os.environ.get("VERITAS_EGRESS_DESTINATIONS", "mock://crm,mock://ledger").split(",")
            if d.strip()
        }
        allowed_dests = set(policy_src.get("destinations") or []) | env_dests

        sensitive = find_sensitive_fields(body.payload)
        if sensitive:
            row = repo.create_egress_delivery(
                session,
                tenant_id=identity.tenant_id,
                id=f"dlv_{uuid.uuid4().hex[:16]}",
                idempotency_key=idempotency_key,
                destination=destination,
                payload_digest=payload_digest,
                decision="DENY",
                reason_code="SENSITIVE_FIELD",
                actor=identity.user_id,
                sensitive_fields=",".join(sensitive),
                delivery_status="SKIPPED",
            )
            repo.create_audit_event(
                session, tenant_id=identity.tenant_id, actor=identity.user_id,
                action="egress.denied", target_type="egress", target_id=row.id,
                payload={"reason": "SENSITIVE_FIELD", "fields": sensitive},
            )
            return JSONResponse(status_code=403, content=_row_dict(row))

        if destination not in allowed_dests:
            row = repo.create_egress_delivery(
                session,
                tenant_id=identity.tenant_id,
                id=f"dlv_{uuid.uuid4().hex[:16]}",
                idempotency_key=idempotency_key,
                destination=destination,
                payload_digest=payload_digest,
                decision="DENY",
                reason_code="DESTINATION_NOT_ALLOWED",
                actor=identity.user_id,
                delivery_status="SKIPPED",
            )
            repo.create_audit_event(
                session, tenant_id=identity.tenant_id, actor=identity.user_id,
                action="egress.denied", target_type="egress", target_id=row.id,
                payload={"reason": "DESTINATION_NOT_ALLOWED", "destination": destination},
            )
            return JSONResponse(status_code=403, content=_row_dict(row))

        try:
            outcome = deliver_egress_webhook(
                destination=destination,
                idempotency_key=idempotency_key,
                tenant_id=identity.tenant_id,
                payload=body.payload,
            )
            delivery_status = "DELIVERED"
            last_error = None
            http_status = 200
        except SsrfBlockedError as exc:
            delivery_status = "SKIPPED"
            last_error = str(exc)
            row = repo.create_egress_delivery(
                session,
                tenant_id=identity.tenant_id,
                id=f"dlv_{uuid.uuid4().hex[:16]}",
                idempotency_key=idempotency_key,
                destination=destination,
                payload_digest=payload_digest,
                decision="DENY",
                reason_code="SSRF_BLOCKED",
                actor=identity.user_id,
                delivery_status=delivery_status,
            )
            row.last_error = last_error
            session.flush()
            return JSONResponse(status_code=403, content=_row_dict(row))
        except AdapterDeliveryError as exc:
            delivery_status = "FAILED"
            last_error = str(exc)
            outcome = {"mode": "https_webhook"}
            http_status = 502

        if existing is not None and existing.delivery_status == "FAILED":
            existing.delivery_status = delivery_status
            existing.delivery_attempts = (existing.delivery_attempts or 0) + 1
            existing.last_error = last_error
            session.flush()
            row = existing
        else:
            row = repo.create_egress_delivery(
                session,
                tenant_id=identity.tenant_id,
                id=f"dlv_{uuid.uuid4().hex[:16]}",
                idempotency_key=idempotency_key,
                destination=destination,
                payload_digest=payload_digest,
                decision="ALLOW",
                reason_code="ALLOWLISTED",
                actor=identity.user_id,
                delivery_status=delivery_status,
            )
            row.delivery_attempts = 1
            row.last_error = last_error
            session.flush()

        repo.create_audit_event(
            session, tenant_id=identity.tenant_id, actor=identity.user_id,
            action="egress.delivered" if delivery_status == "DELIVERED" else "egress.failed",
            target_type="egress", target_id=row.id,
            payload={"destination": destination, "status": delivery_status, "mode": outcome.get("mode")},
        )
        return JSONResponse(status_code=http_status, content=_row_dict(row))


@app.get("/api/v1/vendors")
def vendors_list(
    identity: Identity = Depends(require_role("operator", "approver", "admin", "auditor")),
) -> dict[str, Any]:
    with session_scope() as session:
        rows = repo.list_vendors(session, tenant_id=identity.tenant_id)
        return {"vendors": [_row_dict(row) for row in rows]}


@app.post("/api/v1/vendors", status_code=201)
def vendors_upsert(
    body: VendorUpsertRequest,
    identity: Identity = Depends(require_role("admin")),
) -> dict[str, Any]:
    code = body.vendor_code.strip()
    if not code or not body.name.strip():
        raise ApiError(422, "INVALID_VENDOR", "vendor_code and name are required.")
    with session_scope() as session:
        row = repo.upsert_vendor(
            session,
            tenant_id=identity.tenant_id,
            id=f"vnd_{uuid.uuid4().hex[:12]}",
            vendor_code=code,
            name=body.name.strip(),
            tax_id=body.tax_id,
            status=body.status,
        )
        repo.create_audit_event(
            session,
            tenant_id=identity.tenant_id,
            actor=identity.user_id,
            action="vendor.synced",
            target_type="vendor",
            target_id=row.id,
            payload={"vendor_code": row.vendor_code, "status": row.status},
        )
        return _row_dict(row)


@app.patch("/api/v1/vendors/{vendor_code}")
def vendors_update_status(
    vendor_code: str,
    body: VendorStatusRequest,
    identity: Identity = Depends(require_role("admin")),
) -> dict[str, Any]:
    with session_scope() as session:
        existing = repo.get_vendor_by_code(session, tenant_id=identity.tenant_id, vendor_code=vendor_code)
        if existing is None:
            raise _not_found("vendor")
        updated = repo.upsert_vendor(
            session,
            tenant_id=identity.tenant_id,
            id=existing.id,
            vendor_code=existing.vendor_code,
            name=existing.name,
            tax_id=existing.tax_id,
            status=body.status,
        )
        repo.create_audit_event(
            session,
            tenant_id=identity.tenant_id,
            actor=identity.user_id,
            action="vendor.status_updated",
            target_type="vendor",
            target_id=updated.id,
            payload={"vendor_code": updated.vendor_code, "status": updated.status},
        )
        return _row_dict(updated)


@app.get("/metrics", response_class=PlainTextResponse)
def prometheus_metrics(x_internal_token: str = Header(default="")) -> str:
    expected = os.environ.get("VERITAS_INTERNAL_TOKEN", "dev-internal").strip()
    if not expected or x_internal_token != expected:
        raise ApiError(401, "INTERNAL_AUTH_REQUIRED", "Valid X-Internal-Token is required.")

    from .models import Anchor, Approval, Execution

    with session_scope() as session:
        exec_total = session.scalar(select(func.count()).select_from(Execution)) or 0
        approvals_pending = (
            session.scalar(
                select(func.count()).select_from(Approval).where(Approval.status == "pending")
            )
            or 0
        )
        anchors_pending = (
            session.scalar(
                select(func.count()).select_from(Anchor).where(Anchor.status == "pending")
            )
            or 0
        )

    lines = [
        "# HELP veritas_executions_total Total executions across tenants",
        "# TYPE veritas_executions_total gauge",
        f"veritas_executions_total {exec_total}",
        "# HELP veritas_approvals_pending Pending human approvals",
        "# TYPE veritas_approvals_pending gauge",
        f"veritas_approvals_pending {approvals_pending}",
        "# HELP veritas_anchors_pending Pending cryptographic anchors",
        "# TYPE veritas_anchors_pending gauge",
        f"veritas_anchors_pending {anchors_pending}",
        "# HELP veritas_http_requests_total HTTP requests handled by status",
        "# TYPE veritas_http_requests_total counter",
    ]
    for (method, path, status_code), count in sorted(_HTTP_REQUESTS.items()):
        safe_path = path.replace('"', '\\"')
        lines.append(
            f'veritas_http_requests_total{{method="{method}",path="{safe_path}",status="{status_code}"}} {count}'
        )
    return "\n".join(lines) + "\n"


@app.get("/api/v1/audit-events")
def audit_events(
    verify: bool = Query(default=False),
    identity: Identity = Depends(require_role("auditor", "admin")),
) -> dict[str, Any]:
    with session_scope() as session:
        rows = repo.list_audit_events(session, tenant_id=identity.tenant_id)
        result: dict[str, Any] = {"events": [_row_dict(row) for row in rows]}
        if verify:
            result["chain"] = repo.verify_audit_chain(session)
        return result
