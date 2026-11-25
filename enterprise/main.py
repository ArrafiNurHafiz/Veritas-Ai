"""VERITAS AI enterprise application.

This app is intentionally separate from the demo harness. It starts from an
empty database, derives tenant/role from the authenticated identity, and keeps
LLM output outside the authorization boundary.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
import json
import os
import time
import uuid
from typing import Any, Mapping

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import Depends, FastAPI, Header, Query, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, text

from . import oidc, repositories as repo
from .adapters import (
    AdapterDeliveryError,
    SsrfBlockedError,
    deliver_egress_webhook,
    execute_erp_tool,
    find_sensitive_fields,
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
from .passwords import hash_password, validate_password_strength, verify_password
from .rbac import ROLES, assert_approval_allowed, assert_role, require_role
from .session_store import InMemorySessionStore, configure_session_store
from .tools import ToolRegistry

_OUTBOX_WORKER = AnchorOutboxWorker()


@asynccontextmanager
async def lifespan(_: FastAPI):
    bootstrap()
    _OUTBOX_WORKER.start()
    try:
        yield
    finally:
        _OUTBOX_WORKER.stop()


app = FastAPI(title="VERITAS AI Enterprise", version="1.0.0", lifespan=lifespan)
install_error_handler(app)

if os.environ.get("VERITAS_SESSION_STORE", "").strip().lower() == "memory":
    configure_session_store(InMemorySessionStore())


class TaskRequest(BaseModel):
    task_type: str = "invoice_review"
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


class EgressRequest(BaseModel):
    destination: str
    payload: dict[str, Any]


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
    if tool != "approve_invoice":
        return "DENY", "UNKNOWN_TOOL"
    amount = args.get("amount_idr")
    if type(amount) is not int or amount <= 0:
        return "DENY", "INVALID_AMOUNT"
    vendor = args.get("vendor_id")
    if not isinstance(vendor, str) or not vendor.strip():
        return "DENY", "INVALID_VENDOR"
    if vendor not in set(source.get("vendors", [])):
        return "DENY", "VENDOR_NOT_ALLOWED"
    hard_cap = int(source.get("hard_cap_idr", 25_000_000))
    if amount > hard_cap:
        return "DENY", "AMOUNT_HARD_CAP"
    limit = int(source.get("auto_approve_limit_idr", 5_000_000))
    if amount > limit:
        return "APPROVAL_REQUIRED", "AMOUNT_LIMIT"
    return "ALLOW", "WITHIN_LIMIT"


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
        for tool in ("approve_invoice", "check_vendor_status"):
            if repo.get_tool(session, tenant_id=tenant_id, tool_name=tool) is None:
                repo.register_tool(
                    session,
                    tenant_id=tenant_id,
                    id=f"tool_{uuid.uuid4().hex[:12]}",
                    tool_name=tool,
                )
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
) -> str:
    private, key_id = signer()
    receipt_id = f"rcpt_{uuid.uuid4().hex[:16]}"
    previous = repo.list_events(session, tenant_id=tenant_id, execution_id=execution_id, limit=1)
    previous_hash = previous[-1].hash if previous else GENESIS_HASH
    body = {
        "receipt_id": receipt_id,
        "tenant_id": tenant_id,
        "execution_id": execution_id,
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
) -> dict[str, Any]:
    """Issue a local test session. Disabled in production or without explicit dev flag."""
    if _is_production():
        raise ApiError(404, "NOT_FOUND", "Test login is disabled.")
    mode = os.environ.get("VERITAS_AUTH_TEST_MODE", "").strip().lower()
    if mode not in {"1", "true", "yes", "on"}:
        raise ApiError(404, "NOT_FOUND", "Test login is disabled.")
    raw = os.environ.get("VERITAS_TEST_IDENTITY_JSON", "").strip()
    try:
        data = json.loads(raw) if raw else {}
    except Exception as exc:
        raise ApiError(401, "TEST_IDENTITY_INVALID", "Test identity is malformed.") from exc
    if not isinstance(data, dict):
        raise ApiError(401, "TEST_IDENTITY_INVALID", "Test identity is malformed.")
    if user_id:
        data["user_id"] = user_id
    if tenant_id:
        data["tenant_id"] = tenant_id
    if role:
        data["roles"] = [role]
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
    if not isinstance(payload.get("invoice_id"), str) or not payload["invoice_id"].strip():
        raise ApiError(422, "INVALID_PAYLOAD", "invoice_id is required.")
    amount = payload.get("amount_idr")
    if type(amount) is not int or amount <= 0:
        raise ApiError(422, "INVALID_PAYLOAD", "amount_idr must be a positive integer.")
    vendor = payload.get("vendor_id") or payload.get("vendor")
    if not isinstance(vendor, str) or not vendor.strip():
        raise ApiError(422, "INVALID_PAYLOAD", "vendor is required.")
    payload["vendor"] = vendor

    with session_scope() as session:
        existing = repo.get_execution_by_idempotency_key(
            session, tenant_id=identity.tenant_id, idempotency_key=key
        )
        if existing is not None:
            if existing.payload_hash != sha256(canonical_json(payload)):
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
            agent_id=payload.get("agent_id", "procurement-agent"),
            task_type=body.task_type,
            correlation_id=uuid.uuid4().hex,
        )
        _append_event(
            session, tenant_id=identity.tenant_id, execution_id=execution_id,
            event_type="TASK_CREATED", data={"actor": identity.user_id},
        )

        policy = active_policy(session, identity.tenant_id)
        source = policy_from_row(policy)
        proposal = propose(
            payload,
            tenant_id=identity.tenant_id,
            registry=registry_for(session, identity.tenant_id),
        )
        if not proposal.valid or proposal.tool is None or proposal.arguments is None:
            decision, reason = "DENY", proposal.error or "INVALID_PROPOSAL"
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
                payload={"reason_code": reason, "planner": proposal.planner},
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
            event_type="PROPOSAL", data={"tool": proposal.tool, "planner": proposal.planner},
        )

        decision, reason = evaluate_policy(source, proposal.tool, args)
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
                payload={"reason_code": reason, "decision": decision},
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
                payload={"approval_id": approval.id, "reason_code": reason},
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
            reason_code=reason,
        )
        _append_event(
            session, tenant_id=identity.tenant_id, execution_id=execution_id,
            event_type="SUCCEEDED", data={"receipt_id": receipt_id, "reason_code": reason},
        )
        repo.create_audit_event(
            session, tenant_id=identity.tenant_id, actor=identity.user_id,
            action="task.executed", target_type="execution", target_id=execution_id,
            payload={"receipt_id": receipt_id, "decision": "ALLOW"},
        )
        return _row_dict(repo.get_execution(session, tenant_id=identity.tenant_id, execution_id=execution_id))


# --------------------------------------------------------------------------- approvals

@app.get("/api/v1/approvals")
def approvals_list(
    identity: Identity = Depends(require_role("approver", "admin", "auditor")),
) -> list[dict[str, Any]]:
    with session_scope() as session:
        return [_row_dict(row) for row in repo.list_approvals(session, tenant_id=identity.tenant_id)]


@app.post("/api/v1/approvals/{approval_id}/decisions")
def decide(
    approval_id: str,
    body: DecisionRequest,
    identity: Identity = Depends(require_role("approver", "admin")),
) -> dict[str, Any]:
    with session_scope() as session:
        approval = repo.get_approval(session, tenant_id=identity.tenant_id, approval_id=approval_id)
        if approval is None:
            raise _not_found("approval")
        assert_approval_allowed(identity, approval.requester or "", identity.tenant_id)
        try:
            decided = repo.decide_approval(
                session,
                tenant_id=identity.tenant_id,
                approval_id=approval_id,
                expected_version=body.expected_version,
                decision=body.decision,
                approver=identity.user_id,
                reason=body.reason or None,
            )
        except repo.SeparationOfDuties as exc:
            raise ApiError(403, "SEPARATION_OF_DUTIES", str(exc)) from exc
        except repo.VersionConflict as exc:
            raise ApiError(409, "VERSION_CONFLICT", str(exc)) from exc
        except repo.InvalidTransition as exc:
            raise ApiError(409, "INVALID_TRANSITION", str(exc)) from exc

        execution = repo.get_execution(
            session, tenant_id=identity.tenant_id, execution_id=decided.execution_id
        )
        if execution is None:
            raise _not_found("execution")
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
            repo.create_audit_event(
                session, tenant_id=identity.tenant_id, actor=identity.user_id,
                action="approval.rejected", target_type="approval", target_id=approval_id,
                payload={"reason": body.reason},
            )
            return {"approval": _row_dict(decided), "execution": _row_dict(execution)}

        policy = active_policy(session, identity.tenant_id)
        args = json.loads(execution.proposal_json or "{}").get("arguments", {})
        _execute_tool(session, tenant_id=identity.tenant_id, execution=execution, args=args)
        receipt_id = _issue_receipt(
            session, tenant_id=identity.tenant_id, execution_id=execution.id,
            decision="APPROVAL_REQUIRED", outcome="SUCCEEDED",
            tool=execution.tool or "approve_invoice", args=args,
            actor=identity.user_id, policy_digest=policy.digest,
            reason_code="HUMAN_APPROVED",
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
        rows = repo.list_executions(session, tenant_id=identity.tenant_id, status=status, limit=limit)
        return {"executions": [_row_dict(row) for row in rows], "total": len(rows)}


@app.get("/api/v1/executions/{execution_id}")
def execution_get(
    execution_id: str,
    identity: Identity = Depends(require_role("operator", "approver", "admin", "auditor")),
) -> dict[str, Any]:
    with session_scope() as session:
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
        runs = len(repo.list_executions(session, tenant_id=identity.tenant_id, limit=1000))
        enabled_tools = [
            t.tool_name
            for t in repo.list_tools(session, tenant_id=identity.tenant_id, enabled_only=True)
        ]
        return {
            "agents": [
                {
                    "agent_id": "procurement-agent",
                    "name": "Procurement Agent",
                    "status": "OPERATIONAL",
                    "allowed_tools": enabled_tools,
                    "policy_version": policy.version,
                    "executions": runs,
                }
            ]
        }


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
