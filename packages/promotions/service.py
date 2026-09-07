from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN
from uuid import UUID, uuid4

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from packages.database.models import Order


class PromotionError(Exception):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _money_bps(amount: int, bps: int) -> int:
    return int((Decimal(amount) * Decimal(bps) / Decimal(10_000)).quantize(Decimal("1"), rounding=ROUND_DOWN))


async def price_checkout(session: AsyncSession, *, tenant_id: UUID, discord_user_id: int, subtotal_minor: int, currency: str, coupon_code: str | None = None, affiliate_code: str | None = None) -> tuple[int, int, str | None, str | None, int]:
    discount = 0
    coupon_id = None
    affiliate = affiliate_code.strip().upper() if affiliate_code else None
    cashback_bps = 0
    if coupon_code:
        code = coupon_code.strip().upper()
        row = (await session.execute(text("SELECT * FROM coupons WHERE tenant_id=:tenant AND upper(code)=:code AND active=true FOR UPDATE").bindparams(tenant=tenant_id, code=code))).mappings().first()
        now = _now()
        if row is None or (row["starts_at"] and row["starts_at"] > now) or (row["ends_at"] and row["ends_at"] <= now): raise PromotionError("coupon_invalid_or_expired")
        if row["currency"] and row["currency"] != currency: raise PromotionError("coupon_currency_mismatch")
        if subtotal_minor < row["min_order_minor"]: raise PromotionError("coupon_minimum_not_met")
        if row["usage_limit"] is not None and row["used_count"] >= row["usage_limit"]: raise PromotionError("coupon_usage_exhausted")
        count = await session.scalar(text("SELECT count(*) FROM coupon_usages WHERE coupon_id=:coupon AND discord_user_id=:user").bindparams(coupon=row["id"], user=discord_user_id))
        if int(count or 0) >= row["per_user_limit"]: raise PromotionError("coupon_user_limit_reached")
        discount = _money_bps(subtotal_minor, row["discount_value"]) if row["discount_type"] == "PERCENT" else min(subtotal_minor, row["discount_value"])
        if row["discount_type"] not in {"PERCENT", "FIXED"}: raise PromotionError("coupon_discount_type_invalid")
        if row["max_discount_minor"] is not None: discount = min(discount, row["max_discount_minor"])
        coupon_id = str(row["id"])
    if affiliate and not await session.scalar(text("SELECT 1 FROM affiliates WHERE tenant_id=:tenant AND code=:code AND active=true").bindparams(tenant=tenant_id, code=affiliate)):
        raise PromotionError("affiliate_invalid")
    tier = (await session.execute(text("SELECT t.discount_bps,t.cashback_bps FROM vip_tiers t JOIN vip_memberships m ON m.tier_id=t.id WHERE m.tenant_id=:tenant AND m.discord_user_id=:user").bindparams(tenant=tenant_id, user=discord_user_id))).first()
    if tier:
        discount = min(subtotal_minor, discount + _money_bps(subtotal_minor - discount, tier[0]))
        cashback_bps = tier[1]
    return subtotal_minor - discount, discount, coupon_id, affiliate, cashback_bps


async def save_order_promotion(session: AsyncSession, *, tenant_id: UUID, order_id: UUID, coupon_id: str | None, coupon_code: str | None, discount_minor: int, affiliate_code: str | None, cashback_bps: int) -> None:
    affiliate_id = None
    if affiliate_code:
        affiliate_id = await session.scalar(text("SELECT id FROM affiliates WHERE tenant_id=:tenant AND code=:code").bindparams(tenant=tenant_id, code=affiliate_code))
    await session.execute(text("INSERT INTO order_promotions(id,tenant_id,order_id,coupon_id,coupon_code,discount_minor,affiliate_id,affiliate_code,cashback_bps) VALUES (:id,:tenant,:order,:coupon,:coupon_code,:discount,:affiliate,:affiliate_code,:cashback)").bindparams(id=uuid4(), tenant=tenant_id, order=order_id, coupon=UUID(coupon_id) if coupon_id else None, coupon_code=coupon_code, discount=discount_minor, affiliate=affiliate_id, affiliate_code=affiliate_code, cashback=cashback_bps))


async def consume_coupon(session: AsyncSession, *, tenant_id: UUID, coupon_id: str, discord_user_id: int, order_id: UUID, discount_minor: int) -> None:
    result = await session.execute(text("UPDATE coupons SET used_count=used_count+1 WHERE id=:id AND tenant_id=:tenant AND (usage_limit IS NULL OR used_count<usage_limit)").bindparams(id=UUID(coupon_id), tenant=tenant_id))
    if result.rowcount != 1: raise PromotionError("coupon_usage_exhausted")
    await session.execute(text("INSERT INTO coupon_usages(id,tenant_id,coupon_id,discord_user_id,order_id,discount_minor) VALUES (:id,:tenant,:coupon,:user,:order,:discount)").bindparams(id=uuid4(), tenant=tenant_id, coupon=UUID(coupon_id), user=discord_user_id, order=order_id, discount=discount_minor))


async def credit_cashback(session: AsyncSession, *, tenant_id: UUID, discord_user_id: int, order_id: UUID, amount_minor: int, currency: str, idempotency_key: str) -> None:
    if amount_minor <= 0: return
    exists = await session.scalar(text("SELECT 1 FROM cashback_ledger WHERE tenant_id=:tenant AND idempotency_key=:key").bindparams(tenant=tenant_id, key=idempotency_key))
    if exists: return
    await session.execute(text("INSERT INTO cashback_wallets(id,tenant_id,discord_user_id,balance_minor,currency) VALUES (:id,:tenant,:user,:amount,:currency) ON CONFLICT (tenant_id,discord_user_id) DO UPDATE SET balance_minor=cashback_wallets.balance_minor+EXCLUDED.balance_minor,updated_at=now()").bindparams(id=uuid4(), tenant=tenant_id, user=discord_user_id, amount=amount_minor, currency=currency))
    await session.execute(text("INSERT INTO cashback_ledger(id,tenant_id,discord_user_id,order_id,type,amount_minor,idempotency_key) VALUES (:id,:tenant,:user,:order,'EARN',:amount,:key)").bindparams(id=uuid4(), tenant=tenant_id, user=discord_user_id, order=order_id, amount=amount_minor, key=idempotency_key))


async def attribute_affiliate(session: AsyncSession, *, tenant_id: UUID, affiliate_code: str, order_id: UUID, commission_base_minor: int) -> None:
    existing = await session.scalar(text("SELECT 1 FROM affiliate_attributions WHERE tenant_id=:tenant AND order_id=:order").bindparams(tenant=tenant_id, order=order_id))
    if existing: return
    row = (await session.execute(text("SELECT id,commission_bps FROM affiliates WHERE tenant_id=:tenant AND code=:code AND active=true FOR UPDATE").bindparams(tenant=tenant_id, code=affiliate_code))).mappings().first()
    if row is None: raise PromotionError("affiliate_invalid")
    commission = _money_bps(commission_base_minor, row["commission_bps"])
    await session.execute(text("INSERT INTO affiliate_attributions(id,tenant_id,affiliate_id,order_id,commission_minor) VALUES (:id,:tenant,:affiliate,:order,:commission)").bindparams(id=uuid4(), tenant=tenant_id, affiliate=row["id"], order=order_id, commission=commission))


async def refresh_vip(session: AsyncSession, *, tenant_id: UUID, discord_user_id: int) -> None:
    paid = await session.scalar(select(func.coalesce(func.sum(Order.total_minor), 0)).where(Order.tenant_id == tenant_id, Order.discord_user_id == discord_user_id, Order.status.in_(["PAID", "FULFILLING", "FULFILLED"])))
    tier = await session.scalar(text("SELECT id FROM vip_tiers WHERE tenant_id=:tenant AND min_spend_minor<=:spend ORDER BY min_spend_minor DESC LIMIT 1").bindparams(tenant=tenant_id, spend=int(paid or 0)))
    if tier is None: return
    await session.execute(text("INSERT INTO vip_memberships(id,tenant_id,discord_user_id,tier_id) VALUES (:id,:tenant,:user,:tier) ON CONFLICT (tenant_id,discord_user_id) DO UPDATE SET tier_id=EXCLUDED.tier_id,updated_at=now()").bindparams(id=uuid4(), tenant=tenant_id, user=discord_user_id, tier=tier))
