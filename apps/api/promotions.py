from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Cookie, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text

from apps.api.auth import CSRF_COOKIE, SESSION_COOKIE, require_csrf, tenant_context

router = APIRouter(prefix="/api/v1/promotions", tags=["promotions"])


class CouponIn(BaseModel):
    code: str = Field(min_length=2, max_length=64)
    discount_type: str
    discount_value: int = Field(gt=0)
    currency: str | None = Field(default="BRL", min_length=3, max_length=3)
    min_order_minor: int = Field(default=0, ge=0)
    max_discount_minor: int | None = Field(default=None, ge=0)
    usage_limit: int | None = Field(default=None, gt=0)
    per_user_limit: int = Field(default=1, gt=0)
    starts_at: datetime | None = None
    ends_at: datetime | None = None


class AffiliateIn(BaseModel):
    discord_user_id: int
    code: str = Field(min_length=2, max_length=64)
    commission_bps: int = Field(default=500, ge=0, le=10000)


class VipTierIn(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    min_spend_minor: int = Field(ge=0)
    discount_bps: int = Field(default=0, ge=0, le=10000)
    cashback_bps: int = Field(default=0, ge=0, le=10000)


async def _admin_session(tenant_id: UUID, session_token: str | None, csrf_cookie: str | None, csrf_header: str | None):
    require_csrf(csrf_cookie, csrf_header)
    return await tenant_context(str(tenant_id), session_token, "ADMIN")


@router.post("/{tenant_id}/coupons", status_code=201)
async def create_coupon(
    tenant_id: UUID,
    data: CouponIn,
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE),
    csrf_cookie: str | None = Cookie(default=None, alias=CSRF_COOKIE),
    x_csrf_token: str | None = Header(default=None, alias="X-CSRF-Token"),
) -> dict[str, object]:
    session, _, _, tenant_uuid = await _admin_session(tenant_id, session_token, csrf_cookie, x_csrf_token)
    try:
        if data.discount_type not in {"PERCENT", "FIXED"}:
            raise HTTPException(400, "discount_type_invalid")
        if data.discount_type == "PERCENT" and data.discount_value > 10000:
            raise HTTPException(400, "percent_must_be_bps")
        if data.starts_at and data.ends_at and data.starts_at >= data.ends_at:
            raise HTTPException(400, "invalid_coupon_window")
        async with session.begin():
            await session.execute(
                text(
                    "INSERT INTO coupons(id,tenant_id,code,discount_type,discount_value,currency,min_order_minor,max_discount_minor,usage_limit,per_user_limit,starts_at,ends_at) "
                    "VALUES (:id,:tenant,:code,:type,:value,:currency,:min,:max,:limit,:per_user,:starts,:ends)"
                ).bindparams(
                    id=uuid4(), tenant=tenant_uuid, code=data.code.strip().upper(), type=data.discount_type,
                    value=data.discount_value, currency=data.currency, min=data.min_order_minor,
                    max=data.max_discount_minor, limit=data.usage_limit, per_user=data.per_user_limit,
                    starts=data.starts_at, ends=data.ends_at,
                )
            )
        return {"status": "created", "code": data.code.strip().upper(), "tenant_id": str(tenant_uuid)}
    finally:
        await session.close()


@router.post("/{tenant_id}/affiliates", status_code=201)
async def create_affiliate(
    tenant_id: UUID,
    data: AffiliateIn,
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE),
    csrf_cookie: str | None = Cookie(default=None, alias=CSRF_COOKIE),
    x_csrf_token: str | None = Header(default=None, alias="X-CSRF-Token"),
) -> dict[str, object]:
    session, _, _, tenant_uuid = await _admin_session(tenant_id, session_token, csrf_cookie, x_csrf_token)
    try:
        async with session.begin():
            await session.execute(
                text("INSERT INTO affiliates(id,tenant_id,discord_user_id,code,commission_bps) VALUES (:id,:tenant,:user,:code,:bps)")
                .bindparams(id=uuid4(), tenant=tenant_uuid, user=data.discord_user_id, code=data.code.strip().upper(), bps=data.commission_bps)
            )
        return {"status": "created", "code": data.code.strip().upper(), "tenant_id": str(tenant_uuid)}
    finally:
        await session.close()


@router.post("/{tenant_id}/vip/tiers", status_code=201)
async def create_vip_tier(
    tenant_id: UUID,
    data: VipTierIn,
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE),
    csrf_cookie: str | None = Cookie(default=None, alias=CSRF_COOKIE),
    x_csrf_token: str | None = Header(default=None, alias="X-CSRF-Token"),
) -> dict[str, object]:
    session, _, _, tenant_uuid = await _admin_session(tenant_id, session_token, csrf_cookie, x_csrf_token)
    try:
        async with session.begin():
            await session.execute(
                text("INSERT INTO vip_tiers(id,tenant_id,name,min_spend_minor,discount_bps,cashback_bps) VALUES (:id,:tenant,:name,:spend,:discount,:cashback)")
                .bindparams(id=uuid4(), tenant=tenant_uuid, name=data.name, spend=data.min_spend_minor, discount=data.discount_bps, cashback=data.cashback_bps)
            )
        return {"status": "created", "name": data.name, "tenant_id": str(tenant_uuid)}
    finally:
        await session.close()


@router.get("/{tenant_id}/cashback/{discord_user_id}")
async def cashback_balance(
    tenant_id: UUID,
    discord_user_id: int,
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE),
) -> dict[str, object]:
    session, _, _, tenant_uuid = await tenant_context(str(tenant_id), session_token, "ADMIN")
    try:
        row = (
            await session.execute(
                text("SELECT balance_minor,currency FROM cashback_wallets WHERE tenant_id=:tenant AND discord_user_id=:user")
                .bindparams(tenant=tenant_uuid, user=discord_user_id)
            )
        ).mappings().first()
        return {"discord_user_id": discord_user_id, "balance_minor": int(row["balance_minor"]) if row else 0, "currency": row["currency"] if row else "BRL", "tenant_id": str(tenant_uuid)}
    finally:
        await session.close()
