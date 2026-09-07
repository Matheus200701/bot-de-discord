"""create core commerce tables

Revision ID: 0001_core
Revises: None
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_core"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.create_table(
        "products",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sku", sa.String(80), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("price_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("stock_quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("tenant_id", "sku", name="uq_product_tenant_sku"),
        sa.CheckConstraint("price_minor >= 0", name="ck_products_price_nonnegative"),
        sa.CheckConstraint("stock_quantity >= 0", name="ck_products_stock_nonnegative"),
    )
    op.create_index("ix_products_tenant", "products", ["tenant_id"])
    op.create_index("ix_products_tenant_active", "products", ["tenant_id", "active"])

    op.create_table(
        "orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("discord_user_id", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="PENDING"),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("total_minor", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("idempotency_key", sa.String(128), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("total_minor >= 0", name="ck_orders_total_nonnegative"),
    )
    op.create_index("ix_orders_tenant", "orders", ["tenant_id"])
    op.create_index("ix_orders_tenant_user", "orders", ["tenant_id", "discord_user_id"])
    op.create_index("ix_orders_status", "orders", ["status"])

    op.create_table(
        "payment_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("provider_event_id", sa.String(200), nullable=False, unique=True),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("payment_events")
    op.drop_table("orders")
    op.drop_table("products")
