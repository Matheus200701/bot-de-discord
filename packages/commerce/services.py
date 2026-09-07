from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.database.models import Cart, CartItem, InventoryReservation, Order, OrderItem, Product
from packages.promotions.service import PromotionError, consume_coupon, price_checkout, save_order_promotion

class CommerceError(Exception): pass
class OutOfStock(CommerceError): pass
class InvalidOrderTransition(CommerceError): pass

@dataclass(frozen=True)
class CartLine:
    product_id: UUID
    quantity: int

ORDER_TRANSITIONS: dict[str, frozenset[str]] = {
    "PENDING": frozenset({"PAYMENT_PENDING", "CANCELLED"}), "PAYMENT_PENDING": frozenset({"PAID", "CANCELLED", "EXPIRED"}),
    "PAID": frozenset({"FULFILLING", "REFUND_PENDING"}), "FULFILLING": frozenset({"FULFILLED", "REFUND_PENDING"}), "FULFILLED": frozenset({"REFUND_PENDING"}),
    "REFUND_PENDING": frozenset({"REFUNDED", "REFUND_FAILED"}), "REFUNDED": frozenset(), "REFUND_FAILED": frozenset({"REFUND_PENDING"}),
    "CANCELLED": frozenset(), "EXPIRED": frozenset(),
}

async def get_or_create_cart(session: AsyncSession, tenant_id: UUID, discord_user_id: int) -> Cart:
    result = await session.execute(select(Cart).where(Cart.tenant_id == tenant_id, Cart.discord_user_id == discord_user_id))
    cart = result.scalar_one_or_none()
    if cart is None:
        cart = Cart(tenant_id=tenant_id, discord_user_id=discord_user_id); session.add(cart); await session.flush()
    return cart

async def add_to_cart(session: AsyncSession, tenant_id: UUID, discord_user_id: int, product_id: UUID, quantity: int) -> Cart:
    if quantity <= 0: raise CommerceError("quantity_must_be_positive")
    cart = await get_or_create_cart(session, tenant_id, discord_user_id)
    product = await session.scalar(select(Product).where(Product.id == product_id, Product.tenant_id == tenant_id, Product.active.is_(True)))
    if product is None: raise CommerceError("product_not_found")
    line = await session.scalar(select(CartItem).where(CartItem.cart_id == cart.id, CartItem.product_id == product_id))
    if line is None: session.add(CartItem(cart_id=cart.id, product_id=product.id, quantity=quantity, unit_price_minor=product.price_minor))
    else: line.quantity += quantity; line.unit_price_minor = product.price_minor
    await session.flush(); return cart

async def create_order_from_cart(session: AsyncSession, tenant_id: UUID, discord_user_id: int, idempotency_key: str, coupon_code: str | None = None, affiliate_code: str | None = None) -> Order:
    existing = await session.scalar(select(Order).where(Order.idempotency_key == idempotency_key))
    if existing is not None:
        if existing.tenant_id != tenant_id or existing.discord_user_id != discord_user_id: raise CommerceError("idempotency_key_conflict")
        return existing
    cart = await get_or_create_cart(session, tenant_id, discord_user_id)
    rows = (await session.execute(select(CartItem, Product).join(Product, Product.id == CartItem.product_id).where(CartItem.cart_id == cart.id, Product.tenant_id == tenant_id, Product.active.is_(True)).with_for_update(of=Product))).all()
    if not rows: raise CommerceError("cart_empty")
    total = 0
    order = Order(id=uuid4(), tenant_id=tenant_id, discord_user_id=discord_user_id, status="PENDING", currency=cart.currency, total_minor=0, idempotency_key=idempotency_key)
    session.add(order); await session.flush()
    for line, product in rows:
        if line.quantity <= 0: raise CommerceError("invalid_cart_quantity")
        if product.stock_quantity < line.quantity: raise OutOfStock(product.sku)
        product.stock_quantity -= line.quantity
        subtotal = product.price_minor * line.quantity
        order.items.append(OrderItem(product_id=product.id, sku=product.sku, name=product.name, quantity=line.quantity, unit_price_minor=product.price_minor, subtotal_minor=subtotal))
        session.add(InventoryReservation(tenant_id=tenant_id, order_id=order.id, product_id=product.id, quantity=line.quantity, status="RESERVED"))
        total += subtotal
    try:
        final_total, discount, coupon_id, normalized_affiliate, cashback_bps = await price_checkout(session, tenant_id=tenant_id, discord_user_id=discord_user_id, subtotal_minor=total, currency=cart.currency, coupon_code=coupon_code, affiliate_code=affiliate_code)
    except PromotionError as exc: raise CommerceError(str(exc)) from exc
    order.total_minor = final_total; order.status = "PAYMENT_PENDING"
    if coupon_id:
        try: await consume_coupon(session, tenant_id=tenant_id, coupon_id=coupon_id, discord_user_id=discord_user_id, order_id=order.id, discount_minor=discount)
        except PromotionError as exc: raise CommerceError(str(exc)) from exc
    await save_order_promotion(session, tenant_id=tenant_id, order_id=order.id, coupon_id=coupon_id, coupon_code=coupon_code.strip().upper() if coupon_code else None, discount_minor=discount, affiliate_code=normalized_affiliate, cashback_bps=cashback_bps)
    await session.execute(delete(CartItem).where(CartItem.cart_id == cart.id)); await session.flush(); return order

async def transition_order(session: AsyncSession, order_id: UUID, tenant_id: UUID, target: str) -> Order:
    order = await session.scalar(select(Order).where(Order.id == order_id, Order.tenant_id == tenant_id).with_for_update())
    if order is None: raise CommerceError("order_not_found")
    if target not in ORDER_TRANSITIONS.get(order.status, frozenset()): raise InvalidOrderTransition(f"{order.status}->{target}")
    order.status = target; await session.flush(); return order
