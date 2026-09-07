from __future__ import annotations

import os
import secrets
from datetime import datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from packages.database.session import SessionFactory

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


def _check_admin(key: str | None) -> None:
    configured = os.getenv("COMMERCE_ADMIN_KEY")
    if not configured: raise HTTPException(503, "promotion_admin_auth_not_configured")
    if not key or not secrets.compare_digest(key, configured): raise HTTPException(403, "forbidden")

@router.post("/coupons", status_code=201)
async def create_coupon(data: CouponIn, x_admin_key: str | None = Header(default=None, alias="X-Commerce-Admin-Key")) -> dict[str, object]:
    _check_admin(x_admin_key)
    if data.discount_type not in {"PERCENT", "FIXED"}: raise HTTPException(400, "discount_type_invalid")
    if data.discount_type == "PERCENT" and data.discount_value > 10000: raise HTTPException(400, "percent_must_be_bps")
    async with SessionFactory() as session:
        async with session.begin():
            await session.execute(text("INSERT INTO coupons(id,tenant_id,code,discount_type,discount_value,currency,min_order_minor,max_discount_minor,usage_limit,per_user_limit) VALUES (:id,:tenant,:code,:type,:value,:currency,:min,:max,:limit,:per_user)").bindparams(id=uuid4(), tenant=_tenant(), code=data.code.strip().upper(), type=data.discount_type, value=data.discount_value, currency=data.currency, min=data.min_order_minor, max=data.max_discount_minor, limit=data.usage_limit, per_user=data.per_user_limit))
    return {"status":"created","code":data.code.strip().upper()}

@router.post("/affiliates", status_code=201)
async def create_affiliate(data: AffiliateIn, x_admin_key: str | None = Header(default=None, alias="X-Commerce-Admin-Key")) -> dict[str, object]:
    _check_admin(x_admin_key)
    async with SessionFactory() as session:
        async with session.begin(): await session.execute(text("INSERT INTO affiliates(id,tenant_id,discord_user_id,code,commission_bps) VALUES (:id,:tenant,:user,:code,:bps)").bindparams(id=uuid4(), tenant=_tenant(), user=data.discord_user_id, code=data.code.strip().upper(), bps=data.commission_bps))
    return {"status":"created","code":data.code.strip().upper()}

@router.post("/vip/tiers", status_code=201)
async def create_vip_tier(data: VipTierIn, x_admin_key: str | None = Header(default=None, alias="X-Commerce-Admin-Key")) -> dict[str, object]:
    _check_admin(x_admin_key)
    async with SessionFactory() as session:
        async with session.begin(): await session.execute(text("INSERT INTO vip_tiers(id,tenant_id,name,min_spend_minor,discount_bps,cashback_bps) VALUES (:id,:tenant,:name,:spend,:discount,:cashback)").bindparams(id=uuid4(), tenant=_tenant(), name=data.name, spend=data.min_spend_minor, discount=data.discount_bps, cashback=data.cashback_bps))
    return {"status":"created","name":data.name}

@router.get("/cashback/{discord_user_id}")
async def cashback_balance(discord_user_id: int, x_admin_key: str | None = Header(default=None, alias="X-Commerce-Admin-Key")) -> dict[str, object]:
    _check_admin(x_admin_key)
    async with SessionFactory() as session:
        row = (await session.execute(text("SELECT balance_minor,currency FROM cashback_wallets WHERE tenant_id=:tenant AND discord_user_id=:user").bindparams(tenant=_tenant(), user=discord_user_id))).mappings().first()
    return {"discord_user_id": discord_user_id, "balance_minor": int(row["balance_minor"]) if row else 0, "currency": row["currency"] if row else "BRL"}

def _tenant() -> UUID:
    return UUID(os.getenv("DEFAULT_TENANT_ID", "00000000-0000-0000-0000-000000000001"))
