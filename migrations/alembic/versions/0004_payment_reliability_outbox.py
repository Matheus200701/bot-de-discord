"""add payment reliability fields and transactional outbox

Revision ID: 0004_payment_reliability_outbox
Revises: 0003_payment_intents
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004_payment_reliability_outbox"
down_revision = "0003_payment_intents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("payment_intents", sa.Column("idempotency_key", sa.String(128), nullable=False, server_default="legacy-migration"))
    op.add_column("payment_intents", sa.Column("reconcile_attempts", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("payment_intents", sa.Column("next_reconcile_at", sa.DateTime(timezone=True)))
    op.add_column("payment_intents", sa.Column("last_reconcile_error", sa.Text()))
    op.create_unique_constraint("uq_payment_order_provider", "payment_intents", ["tenant_id", "order_id", "provider"])
    op.create_unique_constraint("uq_payment_provider_idempotency", "payment_intents", ["provider", "idempotency_key"])
    op.create_index("ix_payment_intents_reconcile_due", "payment_intents", ["next_reconcile_at"])
    op.alter_column("payment_intents", "idempotency_key", server_default=None)

    op.create_table(
        "outbox_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True)),
        sa.Column("aggregate_type", sa.String(64), nullable=False),
        sa.Column("aggregate_id", sa.String(128), nullable=False),
        sa.Column("event_type", sa.String(120), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="PENDING"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("locked_at", sa.DateTime(timezone=True)),
        sa.Column("processed_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("attempts >= 0", name="ck_outbox_attempts_nonnegative"),
    )
    for name, column in (
        ("ix_outbox_tenant", "tenant_id"),
        ("ix_outbox_aggregate", "aggregate_type"),
        ("ix_outbox_aggregate_id", "aggregate_id"),
        ("ix_outbox_event_type", "event_type"),
        ("ix_outbox_status", "status"),
        ("ix_outbox_next_attempt", "next_attempt_at"),
    ):
        op.create_index(name, "outbox_events", [column])


def downgrade() -> None:
    op.drop_table("outbox_events")
    op.drop_index("ix_payment_intents_reconcile_due", table_name="payment_intents")
    op.drop_constraint("uq_payment_provider_idempotency", "payment_intents", type_="unique")
    op.drop_constraint("uq_payment_order_provider", "payment_intents", type_="unique")
    op.drop_column("payment_intents", "last_reconcile_error")
    op.drop_column("payment_intents", "next_reconcile_at")
    op.drop_column("payment_intents", "reconcile_attempts")
    op.drop_column("payment_intents", "idempotency_key")
