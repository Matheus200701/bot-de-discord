from __future__ import annotations

from uuid import UUID

from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.database.models import Order
from packages.promotions.service import attribute_affiliate, credit_cashback, refresh_vip


async def handle_payment_paid(session: AsyncSession, event) -> None:
    tenant_id = UUID(str(event.tenant_id))
    order_id = UUID(str(event.payload["order_id"]))
    order = await session.scalar(select(Order).where(Order.id == order_id, Order.tenant_id == tenant_id).with_for_update())
    if order is None or order.status not in {"PAID", "FULFILLING", "FULFILLED"}: return
    promotion = (await session.execute(text("SELECT affiliate_code,cashback_bps FROM order_promotions WHERE tenant_id=:tenant AND order_id=:order").bindparams(tenant=tenant_id, order=order_id))).mappings().first()
    if promotion:
        if promotion["cashback_bps"] > 0:
            amount = (order.total_minor * promotion["cashback_bps"]) // 10_000
            await credit_cashback(session, tenant_id=tenant_id, discord_user_id=order.discord_user_id, order_id=order_id, amount_minor=amount, currency=order.currency, idempotency_key=f"cashback:order:{order_id}")
        if promotion["affiliate_code"]:
            await attribute_affiliate(session, tenant_id=tenant_id, affiliate_code=promotion["affiliate_code"], order_id=order_id, commission_base_minor=order.total_minor)
    await refresh_vip(session, tenant_id=tenant_id, discord_user_id=order.discord_user_id)
