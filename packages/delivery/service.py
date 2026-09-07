from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.commerce.services import CommerceError, transition_order
from packages.database.models import FulfillmentRecord, Order, OrderItem, Product
from packages.payments.reliability import enqueue_outbox


async def prepare_order_fulfillment(session: AsyncSession, order_id: UUID, tenant_id: UUID) -> list[FulfillmentRecord]:
    order = await session.scalar(
        select(Order).where(Order.id == order_id, Order.tenant_id == tenant_id).with_for_update()
    )
    if order is None:
        raise CommerceError("order_not_found")
    if order.status not in {"PAID", "FULFILLING", "FULFILLED"}:
        return []

    items = list(
        (
            await session.execute(
                select(OrderItem, Product)
                .join(Product, Product.id == OrderItem.product_id)
                .where(OrderItem.order_id == order.id, Product.tenant_id == tenant_id)
            )
        ).all()
    )
    created: list[FulfillmentRecord] = []
    for item, product in items:
        metadata = product.metadata_json or {}
        delivery = metadata.get("delivery") if isinstance(metadata, dict) else None
        if not isinstance(delivery, dict):
            continue
        delivery_type = str(delivery.get("type", ""))
        if delivery_type not in {"discord_role", "digital_link"}:
            continue
        existing = await session.scalar(
            select(FulfillmentRecord).where(
                FulfillmentRecord.tenant_id == tenant_id,
                FulfillmentRecord.order_id == order.id,
                FulfillmentRecord.product_id == product.id,
                FulfillmentRecord.delivery_type == delivery_type,
            )
        )
        if existing is not None:
            continue
        if delivery_type == "discord_role" and (
            _int_or_none(delivery.get("guild_id")) is None or _int_or_none(delivery.get("role_id")) is None
        ):
            raise CommerceError("discord_role_delivery_configuration_invalid")
        if delivery_type == "digital_link" and _string_or_none(delivery.get("url")) is None:
            raise CommerceError("digital_link_delivery_configuration_invalid")
        record = FulfillmentRecord(
            tenant_id=tenant_id,
            order_id=order.id,
            order_item_id=item.id,
            product_id=product.id,
            discord_user_id=order.discord_user_id,
            delivery_type=delivery_type,
            status="PENDING",
            discord_guild_id=_int_or_none(delivery.get("guild_id")),
            discord_role_id=_int_or_none(delivery.get("role_id")),
            delivery_url=_string_or_none(delivery.get("url")),
        )
        session.add(record)
        await session.flush()
        created.append(record)
        enqueue_outbox(
            session,
            tenant_id=tenant_id,
            aggregate_type="fulfillment",
            aggregate_id=str(record.id),
            event_type="fulfillment.execute",
            payload={"fulfillment_id": str(record.id)},
        )

    if created and order.status == "PAID":
        await transition_order(session, order.id, tenant_id, "FULFILLING")
    elif not created and order.status == "FULFILLING":
        await transition_order(session, order.id, tenant_id, "FULFILLED")
    return created


def _int_or_none(value: object) -> int | None:
    if value is None:
        return None
    try:
        parsed = int(str(value))
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _string_or_none(value: object) -> str | None:
    if value is None:
        return None
    value = str(value).strip()
    return value or None


async def mark_fulfillment_delivered(session: AsyncSession, fulfillment_id: UUID) -> None:
    record = await session.scalar(
        select(FulfillmentRecord).where(FulfillmentRecord.id == fulfillment_id).with_for_update()
    )
    if record is None:
        raise CommerceError("fulfillment_not_found")
    if record.status == "DELIVERED":
        return
    record.status = "DELIVERED"
    record.delivered_at = datetime.now(timezone.utc)
    record.last_error = None

    pending = await session.scalar(
        select(FulfillmentRecord.id)
        .where(
            FulfillmentRecord.order_id == record.order_id,
            FulfillmentRecord.status.in_(["PENDING", "PROCESSING"]),
        )
        .limit(1)
    )
    if pending is None:
        order = await session.scalar(
            select(Order).where(Order.id == record.order_id, Order.tenant_id == record.tenant_id).with_for_update()
        )
        if order is not None and order.status == "FULFILLING":
            await transition_order(session, order.id, record.tenant_id, "FULFILLED")


async def mark_fulfillment_failed(session: AsyncSession, fulfillment_id: UUID, error: str) -> None:
    record = await session.scalar(
        select(FulfillmentRecord).where(FulfillmentRecord.id == fulfillment_id).with_for_update()
    )
    if record is None:
        raise CommerceError("fulfillment_not_found")
    record.status = "FAILED"
    record.attempts += 1
    record.last_error = error[:4000]


async def revoke_fulfillment(session: AsyncSession, fulfillment_id: UUID) -> None:
    record = await session.scalar(
        select(FulfillmentRecord).where(FulfillmentRecord.id == fulfillment_id).with_for_update()
    )
    if record is None:
        raise CommerceError("fulfillment_not_found")
    if record.status == "REVOKED":
        return
    record.status = "REVOKED"
    record.revoked_at = datetime.now(timezone.utc)
