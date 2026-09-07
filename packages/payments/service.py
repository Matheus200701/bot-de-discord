from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.commerce.services import CommerceError, transition_order
from packages.database.models import Order, PaymentIntentRecord
from packages.payments.base import PaymentProvider


async def create_payment_intent(
    session: AsyncSession,
    provider: PaymentProvider,
    tenant_id: UUID,
    order_id: UUID,
    payer_email: str,
    idempotency_key: str,
) -> PaymentIntentRecord:
    order = await session.scalar(
        select(Order).where(Order.id == order_id, Order.tenant_id == tenant_id).with_for_update()
    )
    if order is None:
        raise CommerceError("order_not_found")
    if order.status != "PAYMENT_PENDING":
        raise CommerceError("order_not_payment_pending")

    existing = await session.scalar(
        select(PaymentIntentRecord).where(
            PaymentIntentRecord.order_id == order_id,
            PaymentIntentRecord.provider == provider.name,
        )
    )
    if existing is not None:
        return existing

    intent = await provider.create_payment(
        order_id=str(order.id),
        amount_minor=order.total_minor,
        currency=order.currency,
        metadata={
            "payer_email": payer_email,
            "idempotency_key": idempotency_key,
            "description": f"Pedido {order.id}",
        },
    )
    record = PaymentIntentRecord(
        tenant_id=tenant_id,
        order_id=order.id,
        provider=provider.name,
        provider_payment_id=intent.provider_payment_id,
        status=intent.status,
        amount_minor=intent.amount_minor,
        currency=intent.currency,
        checkout_url=intent.checkout_url,
        qr_code=intent.qr_code,
        qr_code_text=intent.qr_code_text,
    )
    session.add(record)
    await session.flush()
    return record


async def mark_payment_paid(
    session: AsyncSession,
    tenant_id: UUID,
    payment: PaymentIntentRecord,
) -> None:
    if payment.tenant_id != tenant_id:
        raise CommerceError("payment_tenant_mismatch")
    if payment.status == "approved":
        return
    payment.status = "approved"
    await transition_order(session, payment.order_id, tenant_id, "PAID")
