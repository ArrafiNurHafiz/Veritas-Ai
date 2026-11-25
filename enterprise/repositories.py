"""Typed repository functions for the VERITAS AI enterprise data layer.

Rules enforced here:

* Every create/get/list function takes a mandatory, non-empty ``tenant_id`` and
  applies it as a SQL filter. There is no code path that reads a business row
  without a tenant scope.
* ``audit_events`` exposes create/get/list/verify only. No update or delete
  function exists, and the schema also rejects direct UPDATE/DELETE.
* Optimistic concurrency on ``approvals`` is checked against ``expected_version``
  inside a flushed UPDATE, so two concurrent decisions cannot both win.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .hashing import GENESIS_HASH, audit_hash, canonical_json, utc_now, utc_plus
from .models import (
    Anchor,
    Approval,
    AuditEvent,
    EgressDelivery,
    Event,
    Execution,
    Policy,
    Receipt,
    Session as UserSession,
    Tenant,
    ToolCall,
    ToolRegistryEntry,
    User,
    UserTenant,
)


class TenantRequired(ValueError):
    """Raised when a repository call omits the mandatory tenant scope."""


class NotFound(LookupError):
    """Raised when a required row does not exist inside the tenant scope."""


class VersionConflict(RuntimeError):
    """Raised when expected_version does not match the stored approval version."""


class IdempotencyConflict(RuntimeError):
    """Raised when an idempotency key is reused with different content."""


class InvalidTransition(RuntimeError):
    """Raised when a state transition is not allowed."""


class SeparationOfDuties(RuntimeError):
    """Raised when the requester tries to decide their own approval."""


class AppendOnlyViolation(RuntimeError):
    """Raised when someone attempts to mutate append-only audit data."""


def _require_tenant(tenant_id: str | None) -> str:
    if not isinstance(tenant_id, str) or not tenant_id.strip():
        raise TenantRequired("tenant_id is mandatory for every repository query")
    return tenant_id


def _limit(limit: int) -> int:
    return max(1, min(int(limit), 500))


# --------------------------------------------------------------------------- tenants / users


def create_tenant(
    session: Session,
    *,
    id: str,
    name: str,
    slug: str,
    status: str = "active",
) -> Tenant:
    row = Tenant(id=id, name=name, slug=slug, status=status)
    session.add(row)
    session.flush()
    return row


def get_tenant(session: Session, *, tenant_id: str) -> Tenant | None:
    return session.get(Tenant, _require_tenant(tenant_id))


def list_tenants(session: Session, *, limit: int = 50, offset: int = 0) -> list[Tenant]:
    return list(
        session.scalars(
            select(Tenant).order_by(Tenant.id).limit(_limit(limit)).offset(max(0, offset))
        )
    )


def create_user(
    session: Session,
    *,
    id: str,
    email: str,
    display_name: str | None = None,
    password_hash: str | None = None,
) -> User:
    row = User(
        id=id,
        email=email.strip().lower(),
        display_name=display_name,
        password_hash=password_hash,
    )
    session.add(row)
    session.flush()
    return row


def get_user(session: Session, *, user_id: str) -> User | None:
    return session.get(User, user_id)


def get_user_by_email(session: Session, *, email: str) -> User | None:
    clean = email.strip().lower()
    return session.scalar(select(User).where(User.email == clean))


def list_users(session: Session, *, limit: int = 50, offset: int = 0) -> list[User]:
    return list(
        session.scalars(select(User).order_by(User.id).limit(_limit(limit)).offset(max(0, offset)))
    )


def add_user_to_tenant(
    session: Session, *, tenant_id: str, user_id: str, role: str
) -> UserTenant:
    tenant_id = _require_tenant(tenant_id)
    row = UserTenant(tenant_id=tenant_id, user_id=user_id, role=role)
    session.add(row)
    session.flush()
    return row


def get_user_tenant(
    session: Session, *, tenant_id: str, user_id: str
) -> UserTenant | None:
    return session.get(UserTenant, (_require_tenant(tenant_id), user_id))


def list_user_memberships(session: Session, *, user_id: str) -> list[UserTenant]:
    return list(
        session.scalars(
            select(UserTenant)
            .where(UserTenant.user_id == user_id, UserTenant.status == "active")
            .order_by(UserTenant.tenant_id)
        )
    )


def list_user_tenants(
    session: Session, *, tenant_id: str, limit: int = 100, offset: int = 0
) -> list[UserTenant]:
    tenant_id = _require_tenant(tenant_id)
    return list(
        session.scalars(
            select(UserTenant)
            .where(UserTenant.tenant_id == tenant_id)
            .order_by(UserTenant.user_id)
            .limit(_limit(limit))
            .offset(max(0, offset))
        )
    )


def list_tenant_users_with_details(
    session: Session, *, tenant_id: str, limit: int = 100, offset: int = 0
) -> list[dict[str, Any]]:
    tenant_id = _require_tenant(tenant_id)
    stmt = (
        select(User, UserTenant)
        .join(UserTenant, User.id == UserTenant.user_id)
        .where(UserTenant.tenant_id == tenant_id)
        .order_by(User.email)
        .limit(_limit(limit))
        .offset(max(0, offset))
    )
    results: list[dict[str, Any]] = []
    for user, membership in session.execute(stmt).all():
        results.append(
            {
                "user_id": user.id,
                "email": user.email,
                "display_name": user.display_name or user.email.split("@")[0],
                "role": membership.role,
                "status": membership.status,
                "user_status": user.status,
                "tenant_id": membership.tenant_id,
                "has_password": bool(user.password_hash),
                "created_at": user.created_at,
            }
        )
    return results


def update_user_tenant_role(
    session: Session,
    *,
    tenant_id: str,
    user_id: str,
    role: str,
    status: str | None = None,
) -> UserTenant:
    tenant_id = _require_tenant(tenant_id)
    row = get_user_tenant(session, tenant_id=tenant_id, user_id=user_id)
    if row is None:
        raise NotFound(f"user {user_id} not in tenant {tenant_id}")
    row.role = role
    if status is not None:
        row.status = status
    session.flush()
    return row


# --------------------------------------------------------------------------- sessions


def create_user_session(
    session: Session,
    *,
    tenant_id: str,
    token_hash: str,
    user_id: str,
    role: str,
    csrf_hash: str,
    expires_at: str,
    email: str | None = None,
) -> UserSession:
    row = UserSession(
        tenant_id=_require_tenant(tenant_id),
        token_hash=token_hash,
        user_id=user_id,
        role=role,
        csrf_hash=csrf_hash,
        expires_at=expires_at,
        email=email,
    )
    session.add(row)
    session.flush()
    return row


def get_user_session(
    session: Session, *, tenant_id: str, token_hash: str
) -> UserSession | None:
    tenant_id = _require_tenant(tenant_id)
    return session.scalar(
        select(UserSession).where(
            UserSession.tenant_id == tenant_id,
            UserSession.token_hash == token_hash,
            UserSession.revoked_at.is_(None),
        )
    )


def revoke_user_session(session: Session, *, tenant_id: str, token_hash: str) -> bool:
    row = get_user_session(session, tenant_id=tenant_id, token_hash=token_hash)
    if row is None:
        return False
    row.revoked_at = utc_now()
    session.flush()
    return True


# --------------------------------------------------------------------------- policies


def create_policy(
    session: Session,
    *,
    tenant_id: str,
    id: str,
    version: int,
    source_json: str,
    digest: str,
    created_by: str | None = None,
) -> Policy:
    row = Policy(
        id=id,
        tenant_id=_require_tenant(tenant_id),
        version=version,
        source_json=source_json,
        digest=digest,
        created_by=created_by,
    )
    session.add(row)
    session.flush()
    return row


def get_policy(session: Session, *, tenant_id: str, policy_id: str) -> Policy | None:
    tenant_id = _require_tenant(tenant_id)
    return session.scalar(
        select(Policy).where(Policy.tenant_id == tenant_id, Policy.id == policy_id)
    )


def list_policies(
    session: Session, *, tenant_id: str, status: str | None = None, limit: int = 50, offset: int = 0
) -> list[Policy]:
    tenant_id = _require_tenant(tenant_id)
    stmt = select(Policy).where(Policy.tenant_id == tenant_id)
    if status is not None:
        stmt = stmt.where(Policy.status == status)
    return list(
        session.scalars(stmt.order_by(Policy.version.desc()).limit(_limit(limit)).offset(max(0, offset)))
    )


# --------------------------------------------------------------------------- executions


def create_execution(
    session: Session,
    *,
    tenant_id: str,
    id: str,
    idempotency_key: str,
    payload_json: str,
    payload_hash: str | None = None,
    status: str = "CREATED",
    decision: str | None = None,
    reason_code: str | None = None,
    proposal_json: str | None = None,
    args_hash: str | None = None,
    tool: str | None = None,
    tool_calls: int = 0,
    actor: str | None = None,
    project_id: str | None = None,
    agent_id: str | None = None,
    task_type: str | None = None,
    correlation_id: str | None = None,
) -> Execution:
    row = Execution(
        id=id,
        tenant_id=_require_tenant(tenant_id),
        idempotency_key=idempotency_key,
        payload_json=payload_json,
        payload_hash=payload_hash,
        status=status,
        decision=decision,
        reason_code=reason_code,
        proposal_json=proposal_json,
        args_hash=args_hash,
        tool=tool,
        tool_calls=tool_calls,
        actor=actor,
        project_id=project_id,
        agent_id=agent_id,
        task_type=task_type,
        correlation_id=correlation_id,
    )
    session.add(row)
    session.flush()
    return row


def get_execution(session: Session, *, tenant_id: str, execution_id: str) -> Execution | None:
    tenant_id = _require_tenant(tenant_id)
    return session.scalar(
        select(Execution).where(Execution.tenant_id == tenant_id, Execution.id == execution_id)
    )


def get_execution_by_idempotency_key(
    session: Session, *, tenant_id: str, idempotency_key: str
) -> Execution | None:
    tenant_id = _require_tenant(tenant_id)
    return session.scalar(
        select(Execution).where(
            Execution.tenant_id == tenant_id,
            Execution.idempotency_key == idempotency_key,
        )
    )


def list_executions(
    session: Session,
    *,
    tenant_id: str,
    status: str | None = None,
    decision: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[Execution]:
    tenant_id = _require_tenant(tenant_id)
    stmt = select(Execution).where(Execution.tenant_id == tenant_id)
    if status is not None:
        stmt = stmt.where(Execution.status == status)
    if decision is not None:
        stmt = stmt.where(Execution.decision == decision)
    return list(
        session.scalars(
            stmt.order_by(Execution.created_at.desc()).limit(_limit(limit)).offset(max(0, offset))
        )
    )


def set_execution_status(
    session: Session,
    *,
    tenant_id: str,
    execution_id: str,
    status: str,
    decision: str | None = None,
    reason_code: str | None = None,
    receipt_id: str | None = None,
    approval_id: str | None = None,
) -> Execution:
    row = get_execution(session, tenant_id=tenant_id, execution_id=execution_id)
    if row is None:
        raise NotFound("execution not found in tenant scope")
    row.status = status
    if decision is not None:
        row.decision = decision
    if reason_code is not None:
        row.reason_code = reason_code
    if receipt_id is not None:
        row.receipt_id = receipt_id
    if approval_id is not None:
        row.approval_id = approval_id
    session.flush()
    return row


def record_tool_call(
    session: Session, *, tenant_id: str, id: str, execution_id: str, tool: str, idempotency_key: str
) -> ToolCall:
    tenant_id = _require_tenant(tenant_id)
    execution = get_execution(session, tenant_id=tenant_id, execution_id=execution_id)
    if execution is None:
        raise NotFound("execution not found in tenant scope")
    row = ToolCall(
        id=id,
        tenant_id=tenant_id,
        execution_id=execution_id,
        tool=tool,
        idempotency_key=idempotency_key,
    )
    session.add(row)
    execution.tool_calls += 1
    session.flush()
    return row


def list_tool_calls(
    session: Session, *, tenant_id: str, execution_id: str, limit: int = 100
) -> list[ToolCall]:
    tenant_id = _require_tenant(tenant_id)
    return list(
        session.scalars(
            select(ToolCall)
            .where(ToolCall.tenant_id == tenant_id, ToolCall.execution_id == execution_id)
            .order_by(ToolCall.created_at)
            .limit(_limit(limit))
        )
    )


# --------------------------------------------------------------------------- execution events


def create_event(
    session: Session,
    *,
    tenant_id: str,
    execution_id: str,
    type: str,
    data: Mapping[str, Any],
    prev_hash: str,
    hash: str,
) -> Event:
    tenant_id = _require_tenant(tenant_id)
    row = Event(
        tenant_id=tenant_id,
        execution_id=execution_id,
        type=type,
        data_json=canonical_json(data),
        prev_hash=prev_hash,
        hash=hash,
    )
    session.add(row)
    session.flush()
    return row


def get_event(session: Session, *, tenant_id: str, seq: int) -> Event | None:
    tenant_id = _require_tenant(tenant_id)
    return session.scalar(select(Event).where(Event.tenant_id == tenant_id, Event.seq == seq))


def list_events(
    session: Session,
    *,
    tenant_id: str,
    execution_id: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Event]:
    tenant_id = _require_tenant(tenant_id)
    stmt = select(Event).where(Event.tenant_id == tenant_id)
    if execution_id is not None:
        stmt = stmt.where(Event.execution_id == execution_id)
    return list(
        session.scalars(stmt.order_by(Event.seq).limit(_limit(limit)).offset(max(0, offset)))
    )


# --------------------------------------------------------------------------- approvals


def create_approval(
    session: Session,
    *,
    tenant_id: str,
    id: str,
    execution_id: str,
    expires_at: str | None = None,
    args_hash: str | None = None,
    policy_version: int | None = None,
    requester: str | None = None,
) -> Approval:
    tenant_id = _require_tenant(tenant_id)
    row = Approval(
        id=id,
        tenant_id=tenant_id,
        execution_id=execution_id,
        status="pending",
        version=1,
        args_hash=args_hash,
        policy_version=policy_version,
        requester=requester,
        expires_at=expires_at or utc_plus(900),
    )
    session.add(row)
    session.flush()
    return row


def get_approval(session: Session, *, tenant_id: str, approval_id: str) -> Approval | None:
    tenant_id = _require_tenant(tenant_id)
    return session.scalar(
        select(Approval).where(Approval.tenant_id == tenant_id, Approval.id == approval_id)
    )


def list_approvals(
    session: Session,
    *,
    tenant_id: str,
    status: str | None = "pending",
    limit: int = 50,
    offset: int = 0,
) -> list[Approval]:
    tenant_id = _require_tenant(tenant_id)
    stmt = select(Approval).where(Approval.tenant_id == tenant_id)
    if status is not None:
        stmt = stmt.where(Approval.status == status)
    return list(
        session.scalars(stmt.order_by(Approval.created_at).limit(_limit(limit)).offset(max(0, offset)))
    )


def decide_approval(
    session: Session,
    *,
    tenant_id: str,
    approval_id: str,
    expected_version: int,
    decision: str,
    approver: str,
    reason: str | None = None,
    enforce_separation: bool = True,
) -> Approval:
    """Optimistically decide a pending approval and bump its version once.

    ``expected_version`` is mandatory: a stale caller gets ``VersionConflict``
    and no state change. Requester == approver is rejected by default.
    """
    if decision not in ("approve", "reject"):
        raise InvalidTransition("decision must be 'approve' or 'reject'")
    if not isinstance(expected_version, int) or isinstance(expected_version, bool):
        raise VersionConflict("expected_version must be an integer")
    tenant_id = _require_tenant(tenant_id)
    row = get_approval(session, tenant_id=tenant_id, approval_id=approval_id)
    if row is None:
        raise NotFound("approval not found in tenant scope")
    if enforce_separation and row.requester and row.requester == approver:
        raise SeparationOfDuties("requester cannot decide their own approval")
    # Stale optimistic-lock writers lose even if the row has since been decided.
    if row.version != expected_version:
        raise VersionConflict(
            f"expected_version {expected_version} does not match stored version {row.version}"
        )
    if row.status != "pending":
        raise InvalidTransition(f"approval is {row.status}, not pending")
    row.status = "approved" if decision == "approve" else "rejected"
    row.version = row.version + 1
    row.approver = approver
    row.reason = reason
    row.decided_at = utc_now()
    session.flush()
    return row


def expire_approval(
    session: Session, *, tenant_id: str, approval_id: str, expected_version: int
) -> Approval:
    tenant_id = _require_tenant(tenant_id)
    row = get_approval(session, tenant_id=tenant_id, approval_id=approval_id)
    if row is None:
        raise NotFound("approval not found in tenant scope")
    if row.status != "pending":
        raise InvalidTransition(f"approval is {row.status}, not pending")
    if row.version != expected_version:
        raise VersionConflict("stale approval version")
    row.status = "expired"
    row.version += 1
    row.decided_at = utc_now()
    session.flush()
    return row


# --------------------------------------------------------------------------- receipts / anchors


def create_receipt(
    session: Session,
    *,
    tenant_id: str,
    id: str,
    execution_id: str,
    body_json: str,
    digest: str,
    signature: str,
    key_id: str,
) -> Receipt:
    tenant_id = _require_tenant(tenant_id)
    row = Receipt(
        id=id,
        tenant_id=tenant_id,
        execution_id=execution_id,
        body_json=body_json,
        digest=digest,
        signature=signature,
        key_id=key_id,
    )
    session.add(row)
    session.flush()
    return row


def get_receipt(session: Session, *, tenant_id: str, receipt_id: str) -> Receipt | None:
    tenant_id = _require_tenant(tenant_id)
    return session.scalar(
        select(Receipt).where(Receipt.tenant_id == tenant_id, Receipt.id == receipt_id)
    )


def list_receipts(
    session: Session, *, tenant_id: str, execution_id: str | None = None, limit: int = 50, offset: int = 0
) -> list[Receipt]:
    tenant_id = _require_tenant(tenant_id)
    stmt = select(Receipt).where(Receipt.tenant_id == tenant_id)
    if execution_id is not None:
        stmt = stmt.where(Receipt.execution_id == execution_id)
    return list(
        session.scalars(stmt.order_by(Receipt.created_at.desc()).limit(_limit(limit)).offset(max(0, offset)))
    )


def create_anchor(
    session: Session,
    *,
    tenant_id: str,
    id: str,
    receipt_id: str,
    receipt_hash: str,
    status: str = "pending",
) -> Anchor:
    tenant_id = _require_tenant(tenant_id)
    if status not in ("pending", "confirmed", "failed"):
        raise InvalidTransition("anchor status must be pending/confirmed/failed")
    row = Anchor(
        id=id,
        tenant_id=tenant_id,
        receipt_id=receipt_id,
        receipt_hash=receipt_hash,
        status=status,
    )
    session.add(row)
    session.flush()
    return row


def get_anchor(session: Session, *, tenant_id: str, anchor_id: str) -> Anchor | None:
    tenant_id = _require_tenant(tenant_id)
    return session.scalar(
        select(Anchor).where(Anchor.tenant_id == tenant_id, Anchor.id == anchor_id)
    )


def list_anchors(
    session: Session, *, tenant_id: str, status: str | None = None, limit: int = 50, offset: int = 0
) -> list[Anchor]:
    tenant_id = _require_tenant(tenant_id)
    stmt = select(Anchor).where(Anchor.tenant_id == tenant_id)
    if status is not None:
        stmt = stmt.where(Anchor.status == status)
    return list(
        session.scalars(stmt.order_by(Anchor.created_at).limit(_limit(limit)).offset(max(0, offset)))
    )


def set_anchor_status(
    session: Session,
    *,
    tenant_id: str,
    anchor_id: str,
    status: str,
    tx_ref: str | None = None,
    last_error: str | None = None,
    increment_attempts: bool = False,
) -> Anchor:
    tenant_id = _require_tenant(tenant_id)
    if status not in ("pending", "confirmed", "failed"):
        raise InvalidTransition("anchor status must be pending/confirmed/failed")
    row = get_anchor(session, tenant_id=tenant_id, anchor_id=anchor_id)
    if row is None:
        raise NotFound("anchor not found in tenant scope")
    row.status = status
    if tx_ref is not None:
        row.tx_ref = tx_ref
    if last_error is not None:
        row.last_error = last_error
    if increment_attempts:
        row.attempts += 1
    session.flush()
    return row


# --------------------------------------------------------------------------- tool registry / egress


def register_tool(
    session: Session,
    *,
    tenant_id: str,
    id: str,
    tool_name: str,
    enabled: bool = True,
    config_json: str | None = None,
) -> ToolRegistryEntry:
    tenant_id = _require_tenant(tenant_id)
    row = ToolRegistryEntry(
        id=id,
        tenant_id=tenant_id,
        tool_name=tool_name,
        enabled=enabled,
        config_json=config_json,
    )
    session.add(row)
    session.flush()
    return row


def get_tool(
    session: Session, *, tenant_id: str, tool_name: str
) -> ToolRegistryEntry | None:
    tenant_id = _require_tenant(tenant_id)
    return session.scalar(
        select(ToolRegistryEntry).where(
            ToolRegistryEntry.tenant_id == tenant_id,
            ToolRegistryEntry.tool_name == tool_name,
        )
    )


def list_tools(
    session: Session, *, tenant_id: str, enabled_only: bool = False, limit: int = 100
) -> list[ToolRegistryEntry]:
    tenant_id = _require_tenant(tenant_id)
    stmt = select(ToolRegistryEntry).where(ToolRegistryEntry.tenant_id == tenant_id)
    if enabled_only:
        stmt = stmt.where(ToolRegistryEntry.enabled.is_(True))
    return list(session.scalars(stmt.order_by(ToolRegistryEntry.tool_name).limit(_limit(limit))))


def create_egress_delivery(
    session: Session,
    *,
    tenant_id: str,
    id: str,
    idempotency_key: str,
    destination: str,
    payload_digest: str,
    decision: str,
    reason_code: str | None = None,
    actor: str | None = None,
    sensitive_fields: str | None = None,
    delivery_status: str | None = None,
) -> EgressDelivery:
    tenant_id = _require_tenant(tenant_id)
    row = EgressDelivery(
        id=id,
        tenant_id=tenant_id,
        idempotency_key=idempotency_key,
        destination=destination,
        payload_digest=payload_digest,
        decision=decision,
        reason_code=reason_code,
        actor=actor,
        sensitive_fields=sensitive_fields,
        delivery_status=delivery_status,
    )
    session.add(row)
    session.flush()
    return row


def get_egress_delivery(
    session: Session, *, tenant_id: str, delivery_id: str
) -> EgressDelivery | None:
    tenant_id = _require_tenant(tenant_id)
    return session.scalar(
        select(EgressDelivery).where(
            EgressDelivery.tenant_id == tenant_id, EgressDelivery.id == delivery_id
        )
    )


def get_egress_by_idempotency_key(
    session: Session, *, tenant_id: str, idempotency_key: str
) -> EgressDelivery | None:
    tenant_id = _require_tenant(tenant_id)
    return session.scalar(
        select(EgressDelivery).where(
            EgressDelivery.tenant_id == tenant_id,
            EgressDelivery.idempotency_key == idempotency_key,
        )
    )


def list_egress_deliveries(
    session: Session, *, tenant_id: str, decision: str | None = None, limit: int = 50, offset: int = 0
) -> list[EgressDelivery]:
    tenant_id = _require_tenant(tenant_id)
    stmt = select(EgressDelivery).where(EgressDelivery.tenant_id == tenant_id)
    if decision is not None:
        stmt = stmt.where(EgressDelivery.decision == decision)
    return list(
        session.scalars(
            stmt.order_by(EgressDelivery.created_at.desc()).limit(_limit(limit)).offset(max(0, offset))
        )
    )


# --------------------------------------------------------------------------- audit (append-only)


def create_audit_event(
    session: Session,
    *,
    tenant_id: str,
    actor: str,
    action: str,
    target_type: str,
    target_id: str,
    payload: Mapping[str, Any],
) -> AuditEvent:
    """Append one event with a hash chained to the current global head.

    The chain is global (``seq`` is a single autoincrement sequence) so tampering
    cannot be hidden by rewriting a per-tenant head. ``tenant_id`` is still
    mandatory and stored on every event for scoped reads.
    """
    tenant_id = _require_tenant(tenant_id)
    prev_hash = session.scalar(select(AuditEvent.hash).order_by(AuditEvent.seq.desc()).limit(1))
    prev_hash = prev_hash or GENESIS_HASH
    payload_json = canonical_json(payload)
    row = AuditEvent(
        tenant_id=tenant_id,
        actor=actor,
        action=action,
        target_type=target_type,
        target_id=target_id,
        payload_json=payload_json,
        prev_hash=prev_hash,
        hash=audit_hash(prev_hash, payload_json),
        created_at=utc_now(),
    )
    session.add(row)
    session.flush()
    return row


def get_audit_event(session: Session, *, tenant_id: str, seq: int) -> AuditEvent | None:
    tenant_id = _require_tenant(tenant_id)
    return session.scalar(
        select(AuditEvent).where(AuditEvent.tenant_id == tenant_id, AuditEvent.seq == seq)
    )


def list_audit_events(
    session: Session,
    *,
    tenant_id: str,
    action: str | None = None,
    target_type: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[AuditEvent]:
    tenant_id = _require_tenant(tenant_id)
    stmt = select(AuditEvent).where(AuditEvent.tenant_id == tenant_id)
    if action is not None:
        stmt = stmt.where(AuditEvent.action == action)
    if target_type is not None:
        stmt = stmt.where(AuditEvent.target_type == target_type)
    return list(
        session.scalars(stmt.order_by(AuditEvent.seq).limit(_limit(limit)).offset(max(0, offset)))
    )


def verify_audit_chain(session: Session) -> dict[str, Any]:
    """Recompute every hash and predecessor link; return a verification report."""
    events: Sequence[AuditEvent] = list(session.scalars(select(AuditEvent).order_by(AuditEvent.seq)))
    errors: list[int] = []
    previous: AuditEvent | None = None
    for event in events:
        expected_prev = previous.hash if previous is not None else GENESIS_HASH
        if event.prev_hash != expected_prev:
            errors.append(int(event.seq))
        elif audit_hash(event.prev_hash, event.payload_json) != event.hash:
            errors.append(int(event.seq))
        previous = event
    return {"ok": not errors, "count": len(events), "errors": errors}
