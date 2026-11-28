"""SQLAlchemy 2.0 ORM schema for the VERITAS AI enterprise data layer.

Every business table carries an indexed ``tenant_id`` foreign key to ``tenants``.
``tenants``, ``users``, ``user_tenants`` and ``sessions`` are identity/tenancy
structures and are intentionally exempt from that business-table rule.
``audit_events`` is append-only: the repository exposes no update/delete and a
database trigger rejects any direct mutation.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    event,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from .hashing import utc_now

_BIGINT = BigInteger().with_variant(Integer, "sqlite")


class Base(DeclarativeBase):
    """Declarative base shared by ORM models and Alembic metadata."""


class TimestampMixin:
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=utc_now)
    updated_at: Mapped[str] = mapped_column(
        Text, nullable=False, default=utc_now, onupdate=utc_now
    )


def _tenant_key() -> Mapped[str]:
    return mapped_column(
        String(64),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )


# --------------------------------------------------------------------------- tenancy / identity


class Tenant(Base, TimestampMixin):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    display_name: Mapped[str | None] = mapped_column(String(255))
    password_hash: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")


class UserTenant(Base, TimestampMixin):
    __tablename__ = "user_tenants"

    tenant_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")

    __table_args__ = (Index("ix_user_tenants_tenant_role", "tenant_id", "role"),)


class Session(Base):
    __tablename__ = "sessions"

    token_hash: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = _tenant_key()
    user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    email: Mapped[str | None] = mapped_column(String(320))
    csrf_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=utc_now)
    last_seen_at: Mapped[str] = mapped_column(Text, nullable=False, default=utc_now)
    expires_at: Mapped[str] = mapped_column(Text, nullable=False)
    revoked_at: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (Index("ix_sessions_tenant_expires", "tenant_id", "expires_at"),)


# --------------------------------------------------------------------------- business tables


class Policy(Base, TimestampMixin):
    __tablename__ = "policies"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = _tenant_key()
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    source_json: Mapped[str] = mapped_column(Text, nullable=False)
    digest: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    created_by: Mapped[str | None] = mapped_column(String(128))

    __table_args__ = (
        UniqueConstraint("tenant_id", "version", name="uq_policies_tenant_version"),
        Index("ix_policies_tenant_status", "tenant_id", "status"),
    )


class Execution(Base, TimestampMixin):
    __tablename__ = "executions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = _tenant_key()
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="CREATED")
    decision: Mapped[str | None] = mapped_column(String(32))
    reason_code: Mapped[str | None] = mapped_column(String(64))
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    payload_hash: Mapped[str | None] = mapped_column(String(64))
    proposal_json: Mapped[str | None] = mapped_column(Text)
    args_hash: Mapped[str | None] = mapped_column(String(64))
    tool: Mapped[str | None] = mapped_column(String(128))
    tool_calls: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    actor: Mapped[str | None] = mapped_column(String(128))
    project_id: Mapped[str | None] = mapped_column(String(64))
    agent_id: Mapped[str | None] = mapped_column(String(64))
    task_type: Mapped[str | None] = mapped_column(String(64))
    correlation_id: Mapped[str | None] = mapped_column(String(128))
    receipt_id: Mapped[str | None] = mapped_column(String(64))
    approval_id: Mapped[str | None] = mapped_column(String(64))

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "idempotency_key", name="uq_executions_tenant_idempotency"
        ),
        Index("ix_executions_tenant_status_created", "tenant_id", "status", "created_at"),
    )


class Event(Base):
    __tablename__ = "events"

    seq: Mapped[int] = mapped_column(_BIGINT, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = _tenant_key()
    execution_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("executions.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    data_json: Mapped[str] = mapped_column(Text, nullable=False)
    prev_hash: Mapped[str] = mapped_column(Text, nullable=False)
    hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=utc_now)

    __table_args__ = (
        Index("ix_events_tenant_execution_seq", "tenant_id", "execution_id", "seq"),
    )


class Approval(Base, TimestampMixin):
    __tablename__ = "approvals"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = _tenant_key()
    execution_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("executions.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    args_hash: Mapped[str | None] = mapped_column(String(64))
    policy_version: Mapped[int | None] = mapped_column(Integer)
    requester: Mapped[str | None] = mapped_column(String(128))
    approver: Mapped[str | None] = mapped_column(String(128))
    reason: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[str] = mapped_column(Text, nullable=False)
    decided_at: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','approved','rejected','expired')",
            name="ck_approvals_status",
        ),
        Index("ix_approvals_tenant_status", "tenant_id", "status", "created_at"),
    )


class Receipt(Base):
    __tablename__ = "receipts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = _tenant_key()
    execution_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("executions.id", ondelete="CASCADE"), nullable=False
    )
    body_json: Mapped[str] = mapped_column(Text, nullable=False)
    digest: Mapped[str] = mapped_column(String(64), nullable=False)
    signature: Mapped[str] = mapped_column(Text, nullable=False)
    key_id: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=utc_now)

    __table_args__ = (Index("ix_receipts_tenant_created", "tenant_id", "created_at"),)


class Anchor(Base, TimestampMixin):
    __tablename__ = "anchors"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = _tenant_key()
    receipt_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("receipts.id", ondelete="CASCADE"), nullable=False
    )
    receipt_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    tx_ref: Mapped[str | None] = mapped_column(String(128))
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','confirmed','failed')", name="ck_anchors_status"
        ),
        Index("ix_anchors_tenant_status", "tenant_id", "status"),
    )


class AuditEvent(Base):
    __tablename__ = "audit_events"

    seq: Mapped[int] = mapped_column(_BIGINT, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = _tenant_key()
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    prev_hash: Mapped[str] = mapped_column(Text, nullable=False)
    hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=utc_now)

    __table_args__ = (Index("ix_audit_events_tenant_seq", "tenant_id", "seq"),)


class ToolRegistryEntry(Base, TimestampMixin):
    __tablename__ = "tool_registry"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = _tenant_key()
    tool_name: Mapped[str] = mapped_column(String(128), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    config_json: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        UniqueConstraint("tenant_id", "tool_name", name="uq_tool_registry_tenant_tool"),
    )


class EgressDelivery(Base, TimestampMixin):
    __tablename__ = "egress_deliveries"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = _tenant_key()
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    destination: Mapped[str] = mapped_column(String(255), nullable=False)
    payload_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    sensitive_fields: Mapped[str | None] = mapped_column(Text)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    reason_code: Mapped[str | None] = mapped_column(String(64))
    actor: Mapped[str | None] = mapped_column(String(128))
    delivery_status: Mapped[str | None] = mapped_column(String(32))
    delivery_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "idempotency_key", name="uq_egress_tenant_idempotency"
        ),
        Index("ix_egress_tenant_created", "tenant_id", "created_at"),
    )


class ToolCall(Base):
    __tablename__ = "tool_calls"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = _tenant_key()
    execution_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("executions.id", ondelete="CASCADE"), nullable=False
    )
    tool: Mapped[str] = mapped_column(String(128), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=utc_now)

    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_tool_calls_tenant_idempotency"),
        Index("ix_tool_calls_tenant_execution", "tenant_id", "execution_id"),
    )


class Vendor(Base, TimestampMixin):
    __tablename__ = "vendors"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = _tenant_key()
    vendor_code: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    tax_id: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")

    __table_args__ = (
        UniqueConstraint("tenant_id", "vendor_code", name="uq_vendors_tenant_code"),
        Index("ix_vendors_tenant_status", "tenant_id", "status"),
    )


class AgentConfig(Base, TimestampMixin):
    __tablename__ = "agent_configs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = _tenant_key()
    agent_id: Mapped[str] = mapped_column(String(64), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_by: Mapped[str | None] = mapped_column(String(128))

    __table_args__ = (
        UniqueConstraint("tenant_id", "agent_id", name="uq_agent_configs_tenant_agent"),
        Index("ix_agent_configs_tenant_enabled", "tenant_id", "enabled"),
    )


class TenantErpConfig(Base, TimestampMixin):
    __tablename__ = "tenant_erp_configs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = _tenant_key()
    adapter: Mapped[str] = mapped_column(String(32), nullable=False, default="webhook")
    endpoint_url: Mapped[str | None] = mapped_column(Text)
    auth_type: Mapped[str] = mapped_column(String(32), nullable=False, default="none")
    auth_header: Mapped[str] = mapped_column(String(64), nullable=False, default="Authorization")
    credentials_encrypted: Mapped[str | None] = mapped_column(Text)
    field_mapping: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_by: Mapped[str | None] = mapped_column(String(128))

    __table_args__ = (
        UniqueConstraint("tenant_id", name="uq_tenant_erp_configs_tenant"),
    )


# --------------------------------------------------------------------------- append-only guard


_SQLITE_AUDIT_TRIGGERS = (
    """CREATE TRIGGER IF NOT EXISTS trg_audit_events_no_update
       BEFORE UPDATE ON audit_events BEGIN
         SELECT RAISE(ABORT, 'audit_events is append-only');
       END""",
    """CREATE TRIGGER IF NOT EXISTS trg_audit_events_no_delete
       BEFORE DELETE ON audit_events BEGIN
         SELECT RAISE(ABORT, 'audit_events is append-only');
       END""",
)

_POSTGRES_AUDIT_TRIGGERS = (
    """CREATE OR REPLACE FUNCTION vt_reject_audit_mutation()
       RETURNS trigger AS $$
       BEGIN
         RAISE EXCEPTION 'audit_events is append-only';
       END;
       $$ LANGUAGE plpgsql""",
    """CREATE TRIGGER trg_audit_events_no_update
       BEFORE UPDATE ON audit_events
       FOR EACH ROW EXECUTE FUNCTION vt_reject_audit_mutation()""",
    """CREATE TRIGGER trg_audit_events_no_delete
       BEFORE DELETE ON audit_events
       FOR EACH ROW EXECUTE FUNCTION vt_reject_audit_mutation()""",
)


@event.listens_for(Base.metadata, "after_create")
def _install_append_only_guard(target, connection, **kwargs) -> None:  # noqa: ANN001, ARG001
    """Mirror the Alembic triggers when tables are created from metadata (tests)."""
    dialect = connection.dialect.name
    statements = (
        _SQLITE_AUDIT_TRIGGERS
        if dialect == "sqlite"
        else _POSTGRES_AUDIT_TRIGGERS
        if dialect == "postgresql"
        else ()
    )
    for statement in statements:
        connection.exec_driver_sql(statement)


ALL_MODELS = (
    Tenant,
    User,
    UserTenant,
    Session,
    Policy,
    Execution,
    Event,
    Approval,
    Receipt,
    Anchor,
    AuditEvent,
    ToolRegistryEntry,
    EgressDelivery,
    ToolCall,
    Vendor,
    AgentConfig,
    TenantErpConfig,
)
