from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Cookie, HTTPException
from sqlalchemy import func, select

from apps.api.auth import SESSION_COOKIE, tenant_context
from packages.auth.models import DashboardUser, TenantMembership
from packages.database.models import Order, Product

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


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


@router.get("/{tenant_id}/orders")
async def orders(tenant_id: str, session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE)) -> list[dict[str, object]]:
    session, _, _, tenant_uuid = await tenant_context(tenant_id, session_token, "VIEWER")
    try:
        rows = await session.scalars(select(Order).where(Order.tenant_id == tenant_uuid).order_by(Order.created_at.desc()).limit(200))
        return [{"id": str(o.id), "discord_user_id": o.discord_user_id, "status": o.status, "currency": o.currency, "total_minor": o.total_minor, "created_at": o.created_at.isoformat()} for o in rows]
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
