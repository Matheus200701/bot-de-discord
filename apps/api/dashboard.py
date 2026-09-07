from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Cookie, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from apps.api.auth import CSRF_COOKIE, SESSION_COOKIE, require_csrf, tenant_context
from packages.auth.models import DashboardUser, TenantMembership
from packages.database.models import Order, Product
from packages.payments.finance import request_refund

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])

class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    sku: str = Field(min_length=1, max_length=80)
    price_minor: int = Field(ge=0)
    currency: str = Field(default="BRL", min_length=3, max_length=3)
    stock_quantity: int = Field(default=0, ge=0)
    description: str | None = Field(default=None, max_length=5000)
    metadata_json: dict = Field(default_factory=dict)

class RefundCreate(BaseModel):
    amount_minor: int | None = Field(default=None, gt=0)
    idempotency_key: str = Field(min_length=8, max_length=128)
    reason: str | None = Field(default=None, max_length=500)

@router.get("/{tenant_id}/overview")
async def overview(tenant_id: str, session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE)) -> dict[str, object]:
    session, _, membership, tenant_uuid = await tenant_context(tenant_id, session_token, "VIEWER")
    try:
        orders = await session.scalar(select(func.count()).select_from(Order).where(Order.tenant_id == tenant_uuid))
        revenue = await session.scalar(select(func.coalesce(func.sum(Order.total_minor), 0)).where(Order.tenant_id == tenant_uuid, Order.status.in_(["PAID", "FULFILLING", "FULFILLED"])))
        products = await session.scalar(select(func.count()).select_from(Product).where(Product.tenant_id == tenant_uuid, Product.active.is_(True)))
        return {"role": membership.role, "orders": int(orders or 0), "revenue_minor": int(revenue or 0), "active_products": int(products or 0)}
    finally:
        await session.close()

@router.get("/{tenant_id}/products")
async def products(tenant_id: str, session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE)) -> list[dict[str, object]]:
    session, _, _, tenant_uuid = await tenant_context(tenant_id, session_token, "OPERATOR")
    try:
        rows = await session.scalars(select(Product).where(Product.tenant_id == tenant_uuid).order_by(Product.created_at.desc()).limit(200))
        return [{"id": str(p.id), "sku": p.sku, "name": p.name, "price_minor": p.price_minor, "currency": p.currency, "stock_quantity": p.stock_quantity, "active": p.active, "metadata": p.metadata_json} for p in rows]
    finally:
        await session.close()

@router.post("/{tenant_id}/products", status_code=201)
async def create_product(tenant_id: str, data: ProductCreate, session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE), csrf_cookie: str | None = Cookie(default=None, alias=CSRF_COOKIE), x_csrf_token: str | None = Header(default=None, alias="X-CSRF-Token")) -> dict[str, object]:
    require_csrf(csrf_cookie, x_csrf_token)
    session, _, _, tenant_uuid = await tenant_context(tenant_id, session_token, "OPERATOR")
    try:
        product = Product(tenant_id=tenant_uuid, **data.model_dump())
        session.add(product)
        await session.commit()
        await session.refresh(product)
        return {"id": str(product.id), "sku": product.sku, "name": product.name, "price_minor": product.price_minor, "currency": product.currency, "stock_quantity": product.stock_quantity, "active": product.active}
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()

@router.get("/{tenant_id}/orders")
async def orders(tenant_id: str, session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE)) -> list[dict[str, object]]:
    session, _, _, tenant_uuid = await tenant_context(tenant_id, session_token, "VIEWER")
    try:
        rows = await session.scalars(select(Order).where(Order.tenant_id == tenant_uuid).order_by(Order.created_at.desc()).limit(200))
        return [{"id": str(o.id), "discord_user_id": o.discord_user_id, "status": o.status, "currency": o.currency, "total_minor": o.total_minor, "created_at": o.created_at.isoformat()} for o in rows]
    finally:
        await session.close()

@router.post("/{tenant_id}/orders/{order_id}/refund", status_code=202)
async def refund(tenant_id: str, order_id: UUID, data: RefundCreate, session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE), csrf_cookie: str | None = Cookie(default=None, alias=CSRF_COOKIE), x_csrf_token: str | None = Header(default=None, alias="X-CSRF-Token")) -> dict[str, object]:
    require_csrf(csrf_cookie, x_csrf_token)
    session, _, _, tenant_uuid = await tenant_context(tenant_id, session_token, "ADMIN")
    try:
        order = await session.scalar(select(Order).where(Order.id == order_id, Order.tenant_id == tenant_uuid))
        if order is None:
            raise HTTPException(404, "order_not_found")
        refund_record = await request_refund(session, tenant_id=tenant_uuid, order_id=order_id, amount_minor=data.amount_minor, idempotency_key=data.idempotency_key, reason=data.reason)
        await session.commit()
        return {"id": str(refund_record.id), "status": refund_record.status, "amount_minor": refund_record.amount_minor, "currency": refund_record.currency}
    except HTTPException:
        await session.rollback()
        raise
    except Exception as exc:
        await session.rollback()
        raise HTTPException(400, str(exc)) from exc
    finally:
        await session.close()

@router.get("/{tenant_id}/members")
async def members(tenant_id: str, session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE)) -> list[dict[str, object]]:
    session, _, _, tenant_uuid = await tenant_context(tenant_id, session_token, "ADMIN")
    try:
        rows = await session.execute(select(DashboardUser.discord_user_id, DashboardUser.username, DashboardUser.global_name, TenantMembership.role).join(TenantMembership, TenantMembership.user_id == DashboardUser.id).where(TenantMembership.tenant_id == tenant_uuid, TenantMembership.active.is_(True)).order_by(DashboardUser.username))
        return [{"discord_user_id": r.discord_user_id, "username": r.username, "global_name": r.global_name, "role": r.role} for r in rows]
    finally:
        await session.close()
