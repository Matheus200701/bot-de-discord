"""add fulfillment records

Revision ID: 0006_fulfillment
Revises: 0005_refunds_disputes_ledger
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0006_fulfillment"
down_revision = "0005_refunds_disputes_ledger"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fulfillments",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("discord_user_id", sa.BigInteger(), nullable=False),
        sa.Column("delivery_type", sa.String(32), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="PENDING"),
        sa.Column("discord_guild_id", sa.BigInteger()),
        sa.Column("discord_role_id", sa.BigInteger()),
        sa.Column("delivery_url", sa.Text()),
        sa.Column("access_token_hash", sa.String(64)),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text()),
        sa.Column("delivered_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["order_item_id"], ["order_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", "order_id", "product_id", "delivery_type", name="uq_fulfillment_order_product_type"),
        sa.UniqueConstraint("access_token_hash", name="uq_fulfillment_access_token_hash"),
        sa.CheckConstraint("attempts >= 0", name="ck_fulfillment_attempts_nonnegative"),
        sa.CheckConstraint("delivery_type IN ('discord_role','digital_link')", name="ck_fulfillment_delivery_type"),
        sa.CheckConstraint("status IN ('PENDING','PROCESSING','DELIVERED','FAILED','REVOKED')", name="ck_fulfillment_status"),
    )
    for name, column in (
        ("ix_fulfillments_tenant", "tenant_id"),
        ("ix_fulfillments_order", "order_id"),
        ("ix_fulfillments_product", "product_id"),
        ("ix_fulfillments_user", "discord_user_id"),
        ("ix_fulfillments_status", "status"),
    ):
        op.create_index(name, "fulfillments", [column])


def downgrade() -> None:
    op.drop_table("fulfillments")
