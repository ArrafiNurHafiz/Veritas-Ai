"""Initial VERITAS AI enterprise schema.

Revision ID: 0001
Revises:
Create Date: 2026-11-25
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

_BIGINT = sa.BigInteger().with_variant(sa.Integer, "sqlite")


def _tenant_col() -> sa.Column:
    """Indexed tenant scope key on every business table."""
    return sa.Column(
        "tenant_id",
        sa.String(64),
        sa.ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(128), nullable=False, unique=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        *_timestamps(),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("display_name", sa.String(255), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        *_timestamps(),
    )

    op.create_table(
        "user_tenants",
        sa.Column(
            "tenant_id",
            sa.String(64),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            sa.String(64),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        *_timestamps(),
    )
    op.create_index("ix_user_tenants_tenant_role", "user_tenants", ["tenant_id", "role"])

    op.create_table(
        "sessions",
        sa.Column("token_hash", sa.String(128), primary_key=True),
        _tenant_col(),
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("email", sa.String(320), nullable=True),
        sa.Column("csrf_hash", sa.String(128), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("last_seen_at", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.Text(), nullable=False),
        sa.Column("revoked_at", sa.Text(), nullable=True),
    )
    op.create_index("ix_sessions_tenant_expires", "sessions", ["tenant_id", "expires_at"])

    op.create_table(
        "policies",
        sa.Column("id", sa.String(64), primary_key=True),
        _tenant_col(),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("source_json", sa.Text(), nullable=False),
        sa.Column("digest", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("created_by", sa.String(128), nullable=True),
        *_timestamps(),
        sa.UniqueConstraint("tenant_id", "version", name="uq_policies_tenant_version"),
    )
    op.create_index("ix_policies_tenant_status", "policies", ["tenant_id", "status"])

    op.create_table(
        "executions",
        sa.Column("id", sa.String(64), primary_key=True),
        _tenant_col(),
        sa.Column("status", sa.String(32), nullable=False, server_default="CREATED"),
        sa.Column("decision", sa.String(32), nullable=True),
        sa.Column("reason_code", sa.String(64), nullable=True),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=True),
        sa.Column("proposal_json", sa.Text(), nullable=True),
        sa.Column("args_hash", sa.String(64), nullable=True),
        sa.Column("tool", sa.String(128), nullable=True),
        sa.Column("tool_calls", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("actor", sa.String(128), nullable=True),
        sa.Column("project_id", sa.String(64), nullable=True),
        sa.Column("agent_id", sa.String(64), nullable=True),
        sa.Column("task_type", sa.String(64), nullable=True),
        sa.Column("correlation_id", sa.String(128), nullable=True),
        sa.Column("receipt_id", sa.String(64), nullable=True),
        sa.Column("approval_id", sa.String(64), nullable=True),
        *_timestamps(),
        sa.UniqueConstraint(
            "tenant_id", "idempotency_key", name="uq_executions_tenant_idempotency"
        ),
    )
    op.create_index(
        "ix_executions_tenant_status_created", "executions", ["tenant_id", "status", "created_at"]
    )

    op.create_table(
        "events",
        sa.Column("seq", _BIGINT, primary_key=True, autoincrement=True),
        _tenant_col(),
        sa.Column(
            "execution_id",
            sa.String(64),
            sa.ForeignKey("executions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("type", sa.String(64), nullable=False),
        sa.Column("data_json", sa.Text(), nullable=False),
        sa.Column("prev_hash", sa.Text(), nullable=False),
        sa.Column("hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
    )
    op.create_index("ix_events_tenant_execution_seq", "events", ["tenant_id", "execution_id", "seq"])

    op.create_table(
        "approvals",
        sa.Column("id", sa.String(64), primary_key=True),
        _tenant_col(),
        sa.Column(
            "execution_id",
            sa.String(64),
            sa.ForeignKey("executions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("args_hash", sa.String(64), nullable=True),
        sa.Column("policy_version", sa.Integer(), nullable=True),
        sa.Column("requester", sa.String(128), nullable=True),
        sa.Column("approver", sa.String(128), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.Text(), nullable=False),
        sa.Column("decided_at", sa.Text(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('pending','approved','rejected','expired')", name="ck_approvals_status"
        ),
    )
    op.create_index("ix_approvals_tenant_status", "approvals", ["tenant_id", "status", "created_at"])

    op.create_table(
        "receipts",
        sa.Column("id", sa.String(64), primary_key=True),
        _tenant_col(),
        sa.Column(
            "execution_id",
            sa.String(64),
            sa.ForeignKey("executions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("body_json", sa.Text(), nullable=False),
        sa.Column("digest", sa.String(64), nullable=False),
        sa.Column("signature", sa.Text(), nullable=False),
        sa.Column("key_id", sa.String(64), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
    )
    op.create_index("ix_receipts_tenant_created", "receipts", ["tenant_id", "created_at"])

    op.create_table(
        "anchors",
        sa.Column("id", sa.String(64), primary_key=True),
        _tenant_col(),
        sa.Column(
            "receipt_id",
            sa.String(64),
            sa.ForeignKey("receipts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("receipt_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("tx_ref", sa.String(128), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint("status IN ('pending','confirmed','failed')", name="ck_anchors_status"),
    )
    op.create_index("ix_anchors_tenant_status", "anchors", ["tenant_id", "status"])

    op.create_table(
        "audit_events",
        sa.Column("seq", _BIGINT, primary_key=True, autoincrement=True),
        _tenant_col(),
        sa.Column("actor", sa.String(128), nullable=False),
        sa.Column("action", sa.String(128), nullable=False),
        sa.Column("target_type", sa.String(64), nullable=False),
        sa.Column("target_id", sa.String(64), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("prev_hash", sa.Text(), nullable=False),
        sa.Column("hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
    )
    op.create_index("ix_audit_events_tenant_seq", "audit_events", ["tenant_id", "seq"])

    op.create_table(
        "tool_registry",
        sa.Column("id", sa.String(64), primary_key=True),
        _tenant_col(),
        sa.Column("tool_name", sa.String(128), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("config_json", sa.Text(), nullable=True),
        *_timestamps(),
        sa.UniqueConstraint("tenant_id", "tool_name", name="uq_tool_registry_tenant_tool"),
    )

    op.create_table(
        "egress_deliveries",
        sa.Column("id", sa.String(64), primary_key=True),
        _tenant_col(),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("destination", sa.String(255), nullable=False),
        sa.Column("payload_digest", sa.String(64), nullable=False),
        sa.Column("sensitive_fields", sa.Text(), nullable=True),
        sa.Column("decision", sa.String(32), nullable=False),
        sa.Column("reason_code", sa.String(64), nullable=True),
        sa.Column("actor", sa.String(128), nullable=True),
        sa.Column("delivery_status", sa.String(32), nullable=True),
        sa.Column("delivery_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        *_timestamps(),
        sa.UniqueConstraint(
            "tenant_id", "idempotency_key", name="uq_egress_tenant_idempotency"
        ),
    )
    op.create_index("ix_egress_tenant_created", "egress_deliveries", ["tenant_id", "created_at"])

    op.create_table(
        "tool_calls",
        sa.Column("id", sa.String(64), primary_key=True),
        _tenant_col(),
        sa.Column(
            "execution_id",
            sa.String(64),
            sa.ForeignKey("executions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tool", sa.String(128), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.UniqueConstraint(
            "tenant_id", "idempotency_key", name="uq_tool_calls_tenant_idempotency"
        ),
    )
    op.create_index("ix_tool_calls_tenant_execution", "tool_calls", ["tenant_id", "execution_id"])

    _install_audit_guard()


def _install_audit_guard() -> None:
    """Reject UPDATE/DELETE on audit_events at the database level."""
    dialect = op.get_bind().dialect.name
    if dialect == "sqlite":
        op.execute(
            """CREATE TRIGGER IF NOT EXISTS trg_audit_events_no_update
               BEFORE UPDATE ON audit_events BEGIN
                 SELECT RAISE(ABORT, 'audit_events is append-only');
               END"""
        )
        op.execute(
            """CREATE TRIGGER IF NOT EXISTS trg_audit_events_no_delete
               BEFORE DELETE ON audit_events BEGIN
                 SELECT RAISE(ABORT, 'audit_events is append-only');
               END"""
        )
    elif dialect == "postgresql":
        op.execute(
            """CREATE OR REPLACE FUNCTION vt_reject_audit_mutation()
               RETURNS trigger AS $$
               BEGIN
                 RAISE EXCEPTION 'audit_events is append-only';
               END;
               $$ LANGUAGE plpgsql"""
        )
        op.execute(
            """CREATE TRIGGER trg_audit_events_no_update
               BEFORE UPDATE ON audit_events
               FOR EACH ROW EXECUTE FUNCTION vt_reject_audit_mutation()"""
        )
        op.execute(
            """CREATE TRIGGER trg_audit_events_no_delete
               BEFORE DELETE ON audit_events
               FOR EACH ROW EXECUTE FUNCTION vt_reject_audit_mutation()"""
        )


def downgrade() -> None:
    dialect = op.get_bind().dialect.name
    if dialect == "sqlite":
        op.execute("DROP TRIGGER IF EXISTS trg_audit_events_no_update")
        op.execute("DROP TRIGGER IF EXISTS trg_audit_events_no_delete")
    elif dialect == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS trg_audit_events_no_update ON audit_events")
        op.execute("DROP TRIGGER IF EXISTS trg_audit_events_no_delete ON audit_events")
        op.execute("DROP FUNCTION IF EXISTS vt_reject_audit_mutation()")

    op.drop_table("tool_calls")
    op.drop_table("egress_deliveries")
    op.drop_table("tool_registry")
    op.drop_table("audit_events")
    op.drop_table("anchors")
    op.drop_table("receipts")
    op.drop_table("approvals")
    op.drop_table("events")
    op.drop_table("executions")
    op.drop_table("policies")
    op.drop_table("sessions")
    op.drop_table("user_tenants")
    op.drop_table("users")
    op.drop_table("tenants")
