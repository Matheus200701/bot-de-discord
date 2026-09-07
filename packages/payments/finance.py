from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.commerce.services import CommerceError, transition_order
from packages.database.models import (
    LedgerEntry,
    LedgerTransaction,
    Order,
    OutboxEvent,
    PaymentIntentRecord,
    RefundRecord,
)


async def request_refund(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    order_id: UUID,
    amount_minor: int | None,
    idempotency_key: str,
    reason: str | None,
) -> RefundRecord:
    existing = await session.scalar(
        select(RefundRecord).where(
            RefundRecord.tenant_id == tenant_id,
            RefundRecord.idempotency_key == idempotency_key,
        )
    )
    if existing is not None:
        return existing

    payment = await session.scalar(
        select(PaymentIntentRecord).where(
            PaymentIntentRecord.tenant_id == tenant_id,
            PaymentIntentRecord.order_id == order_id,
        ).with_for_update()
    )
    if payment is None or payment.status != "approved":
        raise CommerceError("payment_not_refundable")
    if amount_minor is None:
        amount_minor = payment.amount_minor
    if amount_minor <= 0 or amount_minor > payment.amount_minor:
        raise CommerceError("invalid_refund_amount")

    refunded = await session.scalar(
        select(func.coalesce(func.sum(RefundRecord.amount_minor), 0)).where(
            RefundRecord.payment_intent_id == payment.id,
            RefundRecord.status.in_(["REQUESTED", "PROCESSING", "APPROVED"]),
        )
    )
    if int(refunded or 0) + amount_minor > payment.amount_minor:
        raise CommerceError("refund_exceeds_paid_amount")

    order = await session.scalar(
        select(Order).where(Order.id == order_id, Order.tenant_id == tenant_id).with_for_update()
    )
    if order is None:
        raise CommerceError("order_not_found")
    if order.status not in {"PAID", "FULFILLING", "FULFILLED", "REFUND_FAILED", "REFUND_PENDING"}:
        raise CommerceError("order_not_refundable")

    refund = RefundRecord(
        tenant_id=tenant_id,
        order_id=order_id,
        payment_intent_id=payment.id,
        provider=payment.provider,
        idempotency_key=idempotency_key,
        amount_minor=amount_minor,
        currency=payment.currency,
        status="REQUESTED",
        reason=reason,
    )
    session.add(refund)
    await session.flush()
    if order.status != "REFUND_PENDING":
        await transition_order(session, order_id, tenant_id, "REFUND_PENDING")
    session.add(OutboxEvent(
        tenant_id=tenant_id,
        aggregate_type="refund",
        aggregate_id=str(refund.id),
        event_type="refund.execute",
        payload={"refund_id": str(refund.id)},
    ))
    return refund


async def post_ledger_transaction(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    idempotency_key: str,
    reference_type: str,
    reference_id: str,
    currency: str,
    debit_account: str,
    credit_account: str,
    amount_minor: int,
) -> LedgerTransaction:
    if amount_minor <= 0:
        raise CommerceError("ledger_amount_must_be_positive")
    existing = await session.scalar(
        select(LedgerTransaction).where(
            LedgerTransaction.tenant_id == tenant_id,
            LedgerTransaction.idempotency_key == idempotency_key,
        )
    )
    if existing is not None:
        return existing
    transaction = LedgerTransaction(
        tenant_id=tenant_id,
        idempotency_key=idempotency_key,
        reference_type=reference_type,
        reference_id=reference_id,
        currency=currency,
    )
    transaction.entries.extend([
        LedgerEntry(account=debit_account, debit_minor=amount_minor, credit_minor=0),
        LedgerEntry(account=credit_account, debit_minor=0, credit_minor=amount_minor),
    ])
    session.add(transaction)
    await session.flush()
    return transaction
