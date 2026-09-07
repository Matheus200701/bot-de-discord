from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, Boolean, Column, DateTime, Integer, MetaData, String, Table, func, select
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession

metadata = MetaData()


def _uuid_column(name: str, **kwargs):
    return Column(name, PGUUID(as_uuid=True), **kwargs)

coupons = Table("coupons", metadata, _uuid_column("id", primary_key=True), _uuid_column("tenant_id", nullable=False), Column("code", String(64), nullable=False), Column("discount_type", String(16), nullable=False), Column("discount_value", BigInteger, nullable=False), Column("currency", String(3)), Column("min_order_minor", BigInteger, nullable=False), Column("max_discount_minor", BigInteger), Column("usage_limit", Integer), Column("per_user_limit", Integer, nullable=False), Column("used_count", Integer, nullable=False), Column("starts_at", DateTime(timezone=True)), Column("ends_at", DateTime(timezone=True)), Column("active", Boolean, nullable=False))
coupon_usages = Table("coupon_usages", metadata, _uuid_column("id", primary_key=True), _uuid_column("tenant_id", nullable=False), _uuid_column("coupon_id", nullable=False), Column("discord_user_id", BigInteger, nullable=False), _uuid_column("order_id", nullable=False), Column("discount_minor", BigInteger, nullable=False), Column("created_at", DateTime(timezone=True), nullable=False))
wallets = Table("cashback_wallets", metadata, _uuid_column("id", primary_key=True), _uuid_column("tenant_id", nullable=False), Column("discord_user_id", BigInteger, nullable=False), Column("balance_minor", BigInteger, nullable=False), Column("currency", String(3), nullable=False), Column("updated_at", DateTime(timezone=True), nullable=False))
wallet_ledger = Table("cashback_ledger", metadata, _uuid_column("id", primary_key=True), _uuid_column("tenant_id", nullable=False), Column("discord_user_id", BigInteger, nullable=False), _uuid_column("order_id"), Column("type", String(24), nullable=False), Column("amount_minor", BigInteger, nullable=False), Column("idempotency_key", String(160), nullable=False), Column("created_at", DateTime(timezone=True), nullable=False))
affiliates = Table("affiliates", metadata, _uuid_column("id", primary_key=True), _uuid_column("tenant_id", nullable=False), Column("discord_user_id", BigInteger, nullable=False), Column("code", String(64), nullable=False), Column("commission_bps", Integer, nullable=False), Column("active", Boolean, nullable=False))
affiliate_attributions = Table("affiliate_attributions", metadata, _uuid_column("id", primary_key=True), _uuid_column("tenant_id", nullable=False), _uuid_column("affiliate_id", nullable=False), _uuid_column("order_id", nullable=False), Column("commission_minor", BigInteger, nullable=False), Column("created_at", DateTime(timezone=True), nullable=False))
vip_tiers = Table("vip_tiers", metadata, _uuid_column("id", primary_key=True), _uuid_column("tenant_id", nullable=False), Column("name", String(64), nullable=False), Column("min_spend_minor", BigInteger, nullable=False), Column("discount_bps", Integer, nullable=False), Column("cashback_bps", Integer, nullable=False))
vip_memberships = Table("vip_memberships", metadata, _uuid_column("id", primary_key=True), _uuid_column("tenant_id", nullable=False), Column("discord_user_id", BigInteger, nullable=False), _uuid_column("tier_id", nullable=False), Column("updated_at", DateTime(timezone=True), nullable=False))

class PromotionError(Exception):
    pass

def _now() -> datetime:
    return datetime.now(timezone.utc)

def _money_bps(amount: int, bps: int) -> int:
    return int((Decimal(amount) * Decimal(bps) / Decimal(10_000)).quantize(Decimal("1"), rounding=ROUND_DOWN))

async def price_checkout(session: AsyncSession, *, tenant_id: UUID, discord_user_id: int, subtotal_minor: int, currency: str, coupon_code: str | None = None, affiliate_code: str | None = None) -> tuple[int, int, str | None, str | None, int]:
    """Return total, discount, coupon id, normalized affiliate code and cashback bps."""
    discount = 0
    coupon_id = None
    normalized_affiliate = affiliate_code.strip().upper() if affiliate_code else None
    cashback_bps = 0
    now = _now()
    if coupon_code:
        code = coupon_code.strip().upper()
        row = (await session.execute(select(coupons).where(coupons.c.tenant_id == tenant_id, func.upper(coupons.c.code) == code, coupons.c.active.is_(True)).with_for_update())).mappings().first()
        if row is None or (row["starts_at"] and row["starts_at"] > now) or (row["ends_at"] and row["ends_at"] <= now): raise PromotionError("coupon_invalid_or_expired")
        if row["currency"] and row["currency"] != currency: raise PromotionError("coupon_currency_mismatch")
        if subtotal_minor < int(row["min_order_minor"] or 0): raise PromotionError("coupon_minimum_not_met")
        if row["usage_limit"] is not None and int(row["used_count"]) >= int(row["usage_limit"]): raise PromotionError("coupon_usage_exhausted")
        user_count = await session.scalar(select(func.count()).select_from(coupon_usages).where(coupon_usages.c.coupon_id == row["id"], coupon_usages.c.discord_user_id == discord_user_id))
        if int(user_count or 0) >= int(row["per_user_limit"]): raise PromotionError("coupon_user_limit_reached")
        if row["discount_type"] == "PERCENT": discount = _money_bps(subtotal_minor, int(row["discount_value"]))
        elif row["discount_type"] == "FIXED": discount = min(subtotal_minor, int(row["discount_value"]))
        else: raise PromotionError("coupon_discount_type_invalid")
        if row["max_discount_minor"] is not None: discount = min(discount, int(row["max_discount_minor"]))
        coupon_id = str(row["id"])
    if normalized_affiliate:
        affiliate = await session.scalar(select(affiliates.c.id).where(affiliates.c.tenant_id == tenant_id, affiliates.c.code == normalized_affiliate, affiliates.c.active.is_(True)))
        if affiliate is None: raise PromotionError("affiliate_invalid")
    tier = (await session.execute(select(vip_tiers.c.discount_bps, vip_tiers.c.cashback_bps).join(vip_memberships, vip_memberships.c.tier_id == vip_tiers.c.id).where(vip_memberships.c.tenant_id == tenant_id, vip_memberships.c.discord_user_id == discord_user_id))).first()
    if tier:
        discount = min(subtotal_minor, discount + _money_bps(subtotal_minor - discount, int(tier[0] or 0)))
        cashback_bps = int(tier[1] or 0)
    return max(0, subtotal_minor - discount), discount, coupon_id, normalized_affiliate, cashback_bps

async def consume_coupon(session: AsyncSession, *, tenant_id: UUID, coupon_id: str, discord_user_id: int, order_id: UUID, discount_minor: int) -> None:
    result = await session.execute(coupons.update().where(coupons.c.id == UUID(coupon_id), coupons.c.tenant_id == tenant_id, (coupons.c.usage_limit.is_(None) | (coupons.c.used_count < coupons.c.usage_limit))).values(used_count=coupons.c.used_count + 1))
    if result.rowcount != 1: raise PromotionError("coupon_usage_exhausted")
    await session.execute(coupon_usages.insert().values(id=uuid4(), tenant_id=tenant_id, coupon_id=UUID(coupon_id), discord_user_id=discord_user_id, order_id=order_id, discount_minor=discount_minor, created_at=_now()))

async def credit_cashback(session: AsyncSession, *, tenant_id: UUID, discord_user_id: int, order_id: UUID, amount_minor: int, currency: str, idempotency_key: str) -> None:
    if amount_minor <= 0: return
    if await session.scalar(select(wallet_ledger.c.id).where(wallet_ledger.c.tenant_id == tenant_id, wallet_ledger.c.idempotency_key == idempotency_key)): return
    wallet = (await session.execute(select(wallets).where(wallets.c.tenant_id == tenant_id, wallets.c.discord_user_id == discord_user_id).with_for_update())).mappings().first()
    if wallet is None: await session.execute(wallets.insert().values(id=uuid4(), tenant_id=tenant_id, discord_user_id=discord_user_id, balance_minor=amount_minor, currency=currency, updated_at=_now()))
    else: await session.execute(wallets.update().where(wallets.c.id == wallet["id"]).values(balance_minor=wallet["balance_minor"] + amount_minor, updated_at=_now()))
    await session.execute(wallet_ledger.insert().values(id=uuid4(), tenant_id=tenant_id, discord_user_id=discord_user_id, order_id=order_id, type="EARN", amount_minor=amount_minor, idempotency_key=idempotency_key, created_at=_now()))

async def attribute_affiliate(session: AsyncSession, *, tenant_id: UUID, affiliate_code: str, order_id: UUID, commission_base_minor: int) -> None:
    affiliate = (await session.execute(select(affiliates).where(affiliates.c.tenant_id == tenant_id, affiliates.c.code == affiliate_code.strip().upper(), affiliates.c.active.is_(True)).with_for_update())).mappings().first()
    if affiliate is None: raise PromotionError("affiliate_invalid")
    commission = _money_bps(commission_base_minor, int(affiliate["commission_bps"]))
    await session.execute(affiliate_attributions.insert().values(id=uuid4(), tenant_id=tenant_id, affiliate_id=affiliate["id"], order_id=order_id, commission_minor=commission, created_at=_now()))

async def refresh_vip(session: AsyncSession, *, tenant_id: UUID, discord_user_id: int) -> None:
    from packages.database.models import Order
    paid = await session.scalar(select(func.coalesce(func.sum(Order.total_minor), 0)).where(Order.tenant_id == tenant_id, Order.discord_user_id == discord_user_id, Order.status.in_(["PAID", "FULFILLING", "FULFILLED"])))
    tier = (await session.execute(select(vip_tiers.c.id).where(vip_tiers.c.tenant_id == tenant_id, vip_tiers.c.min_spend_minor <= int(paid or 0)).order_by(vip_tiers.c.min_spend_minor.desc()).limit(1))).scalar_one_or_none()
    if tier is None: return
    existing = await session.scalar(select(vip_memberships.c.id).where(vip_memberships.c.tenant_id == tenant_id, vip_memberships.c.discord_user_id == discord_user_id))
    if existing: await session.execute(vip_memberships.update().where(vip_memberships.c.id == existing).values(tier_id=tier, updated_at=_now()))
    else: await session.execute(vip_memberships.insert().values(id=uuid4(), tenant_id=tenant_id, discord_user_id=discord_user_id, tier_id=tier, updated_at=_now()))
