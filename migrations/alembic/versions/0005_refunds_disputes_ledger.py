"""add refunds disputes and ledger

Revision ID: 0005_refunds_disputes_ledger
Revises: 0004_payment_reliability_outbox
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005_refunds_disputes_ledger"
down_revision = "0004_payment_reliability_outbox"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "refunds",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payment_intent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("provider_refund_id", sa.String(200)),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="REQUESTED"),
        sa.Column("reason", sa.String(500)),
        sa.Column("last_error", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["payment_intent_id"], ["payment_intents.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", "idempotency_key", name="uq_refund_tenant_idempotency"),
        sa.UniqueConstraint("provider", "provider_refund_id", name="uq_refund_provider_external"),
        sa.CheckConstraint("amount_minor > 0", name="ck_refund_amount_positive"),
    )
    op.create_index("ix_refunds_tenant", "refunds", ["tenant_id"])
    op.create_index("ix_refunds_order", "refunds", ["order_id"])
    op.create_index("ix_refunds_payment", "refunds", ["payment_intent_id"])
    op.create_index("ix_refunds_provider", "refunds", ["provider"])
    op.create_index("ix_refunds_status", "refunds", ["status"])

    op.create_table(
        "disputes",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True)),
        sa.Column("order_id", postgresql.UUID(as_uuid=True)),
        sa.Column("payment_intent_id", postgresql.UUID(as_uuid=True)),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("provider_dispute_id", sa.String(200), nullable=False),
        sa.Column("provider_payment_id", sa.String(200)),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("amount_minor", sa.BigInteger()),
        sa.Column("currency", sa.String(3)),
        sa.Column("coverage_applied", sa.Boolean()),
        sa.Column("reason", sa.String(500)),
        sa.Column("payload", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["payment_intent_id"], ["payment_intents.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("provider", "provider_dispute_id", name="uq_dispute_provider_external"),
    )
    for name, column in (("ix_disputes_tenant", "tenant_id"), ("ix_disputes_order", "order_id"), ("ix_disputes_payment", "payment_intent_id"), ("ix_disputes_provider", "provider"), ("ix_disputes_status", "status"), ("ix_disputes_provider_payment", "provider_payment_id")):
        op.create_index(name, "disputes", [column])

    op.create_table(
        "ledger_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("idempotency_key", sa.String(200), nullable=False),
        sa.Column("reference_type", sa.String(64), nullable=False),
        sa.Column("reference_id", sa.String(128), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("tenant_id", "idempotency_key", name="uq_ledger_tenant_idempotency"),
    )
    op.create_index("ix_ledger_reference_type", "ledger_transactions", ["reference_type"])
    op.create_index("ix_ledger_reference_id", "ledger_transactions", ["reference_id"])
    op.create_table(
        "ledger_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("transaction_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account", sa.String(120), nullable=False),
        sa.Column("debit_minor", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("credit_minor", sa.BigInteger(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["transaction_id"], ["ledger_transactions.id"], ondelete="CASCADE"),
        sa.CheckConstraint("debit_minor >= 0", name="ck_ledger_debit_nonnegative"),
        sa.CheckConstraint("credit_minor >= 0", name="ck_ledger_credit_nonnegative"),
        sa.CheckConstraint("(debit_minor = 0) <> (credit_minor = 0)", name="ck_ledger_one_side_only"),
    )
    op.create_index("ix_ledger_entries_transaction", "ledger_entries", ["transaction_id"])
    op.create_index("ix_ledger_entries_account", "ledger_entries", ["account"])


def downgrade() -> None:
    op.drop_table("ledger_entries")
    op.drop_table("ledger_transactions")
    op.drop_table("disputes")
    op.drop_table("refunds")
