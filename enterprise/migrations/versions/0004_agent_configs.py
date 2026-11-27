"""Add agent_configs table for per-tenant AI agent governance.

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-26 06:40:00+00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_configs",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("agent_id", sa.String(length=64), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("updated_by", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "agent_id", name="uq_agent_configs_tenant_agent"),
    )
    op.create_index("ix_agent_configs_tenant_enabled", "agent_configs", ["tenant_id", "enabled"])


def downgrade() -> None:
    op.drop_index("ix_agent_configs_tenant_enabled", table_name="agent_configs")
    op.drop_table("agent_configs")
