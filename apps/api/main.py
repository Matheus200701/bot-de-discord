from __future__ import annotations

import os
import secrets
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.auth import router as auth_router
from apps.api.dashboard import router as dashboard_router
from apps.api.promotions import router as promotions_router
from apps.api.security import SecurityMiddleware
from apps.api.webhooks import router as webhook_router
from packages.commerce.services import CommerceError, OutOfStock, add_to_cart, create_order_from_cart
from packages.database.models import FulfillmentRecord, Order, Product
from packages.database.session import SessionFactory
from packages.payments.mercadopago import MercadoPagoError, MercadoPagoPixProvider
from packages.payments.service import create_payment_intent
from packages.security.secrets import TenantSecretResolver

app = FastAPI(title="Discord Commerce API", version="0.17.0")
app.add_middleware(SecurityMiddleware)
app.include_router(webhook_router)
app.include_router(promotions_router)
app.include_router(auth_router)
app.include_router(dashboard_router)
secret_resolver = TenantSecretResolver()

class ProductIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    sku: str = Field(min_length=1, max_length=80)
    price_minor: int = Field(ge=0)
    currency: str = Field(default="BRL", min_length=3, max_length=3)
    stock_quantity: int = Field(default=0, ge=0)
    description: str | None = Field(default=None, max_length=5000)
    metadata_json: dict = Field(default_factory=dict)

class ProductOut(ProductIn):
    id: UUID
    active: bool

class CartItemIn(BaseModel):
    product_id: UUID
    quantity: int = Field(gt=0, le=10000)

class CheckoutIn(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=128)
    coupon_code: str | None = Field(default=None, min_length=2, max_length=64)
    affiliate_code: str | None = Field(default=None, min_length=2, max_length=64)

class PaymentIn(BaseModel):
    order_id: UUID
    payer_email: str = Field(min_length=5, max_length=320)
    idempotency_key: str = Field(min_length=8, max_length=128)

async def db_session() -> AsyncSession:
    return SessionFactory()

@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}

@app.get("/ready")
async def ready(session: AsyncSession = Depends(db_session)) -> dict[str, str]:
    try:
        await session.execute(select(1))
    except Exception as exc:
        await session.close()
        raise HTTPException(503, "database_unavailable") from exc
    await session.close()
    return {"status": "ready"}

@app.get("/api/v1/products", response_model=list[ProductOut])
async def products(session: AsyncSession = Depends(db_session)) -> list[Product]:
    try:
        result = await session.scalars(select(Product).where(Product.active.is_(True)).order_by(Product.created_at.desc()))
        return list(result.all())
    finally:
        await session.close()

@app.get("/api/v1/products/{product_id}", response_model=ProductOut)
async def get_product(product_id: UUID, session: AsyncSession = Depends(db_session)) -> Product:
    try:
        product = await session.scalar(select(Product).where(Product.id == product_id, Product.active.is_(True)))
        if product is None:
            raise HTTPException(404, "product_not_found")
        return product
    finally:
        await session.close()

@app.post("/api/v1/cart/items", status_code=204)
async def cart_add(data: CartItemIn, x_discord_user_id: int = Header(..., alias="X-Discord-User-ID"), session: AsyncSession = Depends(db_session)) -> None:
    try:
        tenant_id = data.product_id
        async with session.begin():
            product = await session.scalar(select(Product).where(Product.id == tenant_id, Product.active.is_(True)))
            if product is None:
                raise HTTPException(404, "product_not_found")
            await add_to_cart(session, product.tenant_id, x_discord_user_id, data.product_id, data.quantity)
    except CommerceError as exc:
        await session.rollback()
        raise HTTPException(400, str(exc)) from exc
    finally:
        await session.close()

@app.post("/api/v1/checkout", status_code=201)
async def checkout(data: CheckoutIn, x_discord_user_id: int = Header(..., alias="X-Discord-User-ID"), tenant_id: UUID, session: AsyncSession = Depends(db_session)) -> dict[str, object]:
    try:
        async with session.begin():
            order = await create_order_from_cart(session, tenant_id, x_discord_user_id, data.idempotency_key, data.coupon_code, data.affiliate_code)
            return {"id": str(order.id), "status": order.status, "currency": order.currency, "total_minor": order.total_minor}
    except OutOfStock as exc:
        await session.rollback()
        raise HTTPException(409, {"code": "out_of_stock", "sku": str(exc)}) from exc
    except CommerceError as exc:
        await session.rollback()
        raise HTTPException(400, str(exc)) from exc
    finally:
        await session.close()

@app.post("/api/v1/payments/mercadopago/pix", status_code=201)
async def create_pix_payment(data: PaymentIn, x_discord_user_id: int = Header(..., alias="X-Discord-User-ID"), tenant_id: UUID, session: AsyncSession = Depends(db_session)) -> dict[str, object]:
    try:
        async with session.begin():
            order = await session.scalar(select(Order).where(Order.id == data.order_id, Order.tenant_id == tenant_id, Order.discord_user_id == x_discord_user_id))
            if order is None:
                raise HTTPException(404, "order_not_found")
            provider = MercadoPagoPixProvider(access_token=secret_resolver.mercadopago_access_token(tenant_id), webhook_secret=secret_resolver.mercadopago_webhook_secret(tenant_id))
            record = await create_payment_intent(session, provider, tenant_id, data.order_id, data.payer_email, data.idempotency_key)
            return {"id": str(record.id), "provider": record.provider, "provider_payment_id": record.provider_payment_id, "status": record.status, "amount_minor": record.amount_minor, "currency": record.currency, "checkout_url": record.checkout_url, "qr_code": record.qr_code, "qr_code_text": record.qr_code_text}
    except MercadoPagoError as exc:
        await session.rollback()
        raise HTTPException(502, str(exc)) from exc
    except CommerceError as exc:
        await session.rollback()
        raise HTTPException(400, str(exc)) from exc
    finally:
        await session.close()

@app.get("/api/v1/orders/{order_id}/deliveries")
async def order_deliveries(order_id: UUID, x_discord_user_id: int = Header(..., alias="X-Discord-User-ID"), tenant_id: UUID, session: AsyncSession = Depends(db_session)) -> list[dict[str, object | None]]:
    try:
        order = await session.scalar(select(Order).where(Order.id == order_id, Order.tenant_id == tenant_id, Order.discord_user_id == x_discord_user_id))
        if order is None:
            raise HTTPException(404, "order_not_found")
        records = await session.scalars(select(FulfillmentRecord).where(FulfillmentRecord.order_id == order_id, FulfillmentRecord.tenant_id == tenant_id).order_by(FulfillmentRecord.created_at))
        return [{"id": str(r.id), "product_id": str(r.product_id), "type": r.delivery_type, "status": r.status, "delivery_url": r.delivery_url if r.delivery_type == "digital_link" and r.status == "DELIVERED" else None, "guild_id": r.discord_guild_id, "role_id": r.discord_role_id, "delivered_at": r.delivered_at.isoformat() if r.delivered_at else None} for r in records]
    finally:
        await session.close()
