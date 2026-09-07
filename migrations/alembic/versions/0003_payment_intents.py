"""add payment intents

Revision ID: 0003_payment_intents
Revises: 0002_cart_checkout
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003_payment_intents"
down_revision = "0002_cart_checkout"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "payment_intents",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("provider_payment_id", sa.String(200), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("checkout_url", sa.Text()),
        sa.Column("qr_code", sa.Text()),
        sa.Column("qr_code_text", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("provider", "provider_payment_id", name="uq_payment_provider_external"),
        sa.CheckConstraint("amount_minor >= 0", name="ck_payment_amount_nonnegative"),
    )
    op.create_index("ix_payment_intents_tenant", "payment_intents", ["tenant_id"])
    op.create_index("ix_payment_intents_order", "payment_intents", ["order_id"])
    op.create_index("ix_payment_intents_provider", "payment_intents", ["provider"])
    op.create_index("ix_payment_intents_status", "payment_intents", ["status"])


def downgrade() -> None:
    op.drop_table("payment_intents")
