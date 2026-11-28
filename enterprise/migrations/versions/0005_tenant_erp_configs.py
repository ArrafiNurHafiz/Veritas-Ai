"""Add tenant_erp_configs table for per-tenant custom ERP connectors.

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-28 03:45:00+00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenant_erp_configs",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("adapter", sa.String(length=32), nullable=False, server_default="webhook"),
        sa.Column("endpoint_url", sa.Text(), nullable=True),
        sa.Column("auth_type", sa.String(length=32), nullable=False, server_default="none"),
        sa.Column("auth_header", sa.String(length=64), nullable=False, server_default="Authorization"),
        sa.Column("credentials_encrypted", sa.Text(), nullable=True),
        sa.Column("field_mapping", sa.JSON(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("updated_by", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", name="uq_tenant_erp_configs_tenant"),
    )


def downgrade() -> None:
    op.drop_table("tenant_erp_configs")
