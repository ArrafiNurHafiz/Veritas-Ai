"""Add vendors master table.

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-25 17:15:00+00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "vendors",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("vendor_code", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("tax_id", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "vendor_code", name="uq_vendors_tenant_code"),
    )
    op.create_index("ix_vendors_tenant_status", "vendors", ["tenant_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_vendors_tenant_status", table_name="vendors")
    op.drop_table("vendors")
