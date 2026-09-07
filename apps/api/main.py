from __future__ import annotations

import os
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.webhooks import router as webhook_router
from packages.commerce.services import CommerceError, OutOfStock, add_to_cart, create_order_from_cart
from packages.database.models import Order, Product
from packages.database.session import SessionFactory
from packages.payments.mercadopago import MercadoPagoError, MercadoPagoPixProvider
from packages.payments.service import create_payment_intent

app = FastAPI(title="Discord Commerce API", version="0.3.0")
app.include_router(webhook_router)
DEFAULT_TENANT_ID = UUID(os.getenv("DEFAULT_TENANT_ID", "00000000-0000-0000-0000-000000000001"))


class ProductIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    sku: str = Field(min_length=1, max_length=80)
    price_minor: int = Field(ge=0)
    currency: str = Field(default="BRL", min_length=3, max_length=3)
    stock_quantity: int = Field(default=0, ge=0)
    description: str | None = Field(default=None, max_length=5000)


class ProductOut(ProductIn):
    id: UUID
    active: bool


class CartItemIn(BaseModel):
    product_id: UUID
    quantity: int = Field(gt=0, le=10000)


class CheckoutIn(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=128)


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
        result = await session.scalars(
            select(Product).where(Product.tenant_id == DEFAULT_TENANT_ID).order_by(Product.created_at.desc())
        )
        return list(result.all())
    finally:
        await session.close()


@app.post("/api/v1/products", response_model=ProductOut, status_code=201)
async def create_product(data: ProductIn, session: AsyncSession = Depends(db_session)) -> Product:
    try:
        product = Product(tenant_id=DEFAULT_TENANT_ID, **data.model_dump())
        session.add(product)
        await session.commit()
        await session.refresh(product)
        return product
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


@app.get("/api/v1/products/{product_id}", response_model=ProductOut)
async def get_product(product_id: UUID, session: AsyncSession = Depends(db_session)) -> Product:
    try:
        product = await session.scalar(
            select(Product).where(Product.id == product_id, Product.tenant_id == DEFAULT_TENANT_ID)
        )
        if product is None:
            raise HTTPException(404, "product_not_found")
        return product
    finally:
        await session.close()


@app.post("/api/v1/cart/items", status_code=204)
async def cart_add(
    data: CartItemIn,
    x_discord_user_id: int = Header(..., alias="X-Discord-User-ID"),
    session: AsyncSession = Depends(db_session),
) -> None:
    try:
        async with session.begin():
            await add_to_cart(session, DEFAULT_TENANT_ID, x_discord_user_id, data.product_id, data.quantity)
    except CommerceError as exc:
        await session.rollback()
        raise HTTPException(400, str(exc)) from exc
    finally:
        await session.close()


@app.post("/api/v1/checkout", status_code=201)
async def checkout(
    data: CheckoutIn,
    x_discord_user_id: int = Header(..., alias="X-Discord-User-ID"),
    session: AsyncSession = Depends(db_session),
) -> dict[str, object]:
    try:
        async with session.begin():
            order = await create_order_from_cart(session, DEFAULT_TENANT_ID, x_discord_user_id, data.idempotency_key)
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
async def create_pix_payment(
    data: PaymentIn,
    x_discord_user_id: int = Header(..., alias="X-Discord-User-ID"),
    session: AsyncSession = Depends(db_session),
) -> dict[str, object]:
    try:
        async with session.begin():
            order = await session.scalar(
                select(Order).where(
                    Order.id == data.order_id,
                    Order.tenant_id == DEFAULT_TENANT_ID,
                    Order.discord_user_id == x_discord_user_id,
                )
            )
            if order is None:
                raise HTTPException(404, "order_not_found")
            record = await create_payment_intent(
                session,
                MercadoPagoPixProvider(),
                DEFAULT_TENANT_ID,
                data.order_id,
                data.payer_email,
                data.idempotency_key,
            )
            return {
                "id": str(record.id),
                "provider": record.provider,
                "provider_payment_id": record.provider_payment_id,
                "status": record.status,
                "amount_minor": record.amount_minor,
                "currency": record.currency,
                "checkout_url": record.checkout_url,
                "qr_code": record.qr_code,
                "qr_code_text": record.qr_code_text,
            }
    except MercadoPagoError as exc:
        await session.rollback()
        raise HTTPException(502, str(exc)) from exc
    except CommerceError as exc:
        await session.rollback()
        raise HTTPException(400, str(exc)) from exc
    finally:
        await session.close()
