from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (UniqueConstraint("tenant_id", "sku", name="uq_product_tenant_sku"),)
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    sku: Mapped[str] = mapped_column(String(80))
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text())
    price_minor: Mapped[int] = mapped_column(BigInteger())
    currency: Mapped[str] = mapped_column(String(3), default="BRL")
    stock_quantity: Mapped[int] = mapped_column(Integer(), default=0)
    active: Mapped[bool] = mapped_column(Boolean(), default=True, index=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Cart(Base):
    __tablename__ = "carts"
    __table_args__ = (UniqueConstraint("tenant_id", "discord_user_id", name="uq_cart_tenant_user"),)
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    discord_user_id: Mapped[int] = mapped_column(BigInteger(), index=True)
    currency: Mapped[str] = mapped_column(String(3), default="BRL")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    items: Mapped[list[CartItem]] = relationship(back_populates="cart", cascade="all, delete-orphan")


class CartItem(Base):
    __tablename__ = "cart_items"
    __table_args__ = (UniqueConstraint("cart_id", "product_id", name="uq_cart_item_product"),)
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    cart_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("carts.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("products.id"), index=True)
    quantity: Mapped[int] = mapped_column(Integer())
    unit_price_minor: Mapped[int] = mapped_column(BigInteger())
    cart: Mapped[Cart] = relationship(back_populates="items")


class Order(Base):
    __tablename__ = "orders"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    discord_user_id: Mapped[int] = mapped_column(BigInteger(), index=True)
    status: Mapped[str] = mapped_column(String(32), default="PENDING", index=True)
    currency: Mapped[str] = mapped_column(String(3), default="BRL")
    total_minor: Mapped[int] = mapped_column(BigInteger(), default=0)
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    items: Mapped[list[OrderItem]] = relationship(back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    order_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("products.id"), index=True)
    sku: Mapped[str] = mapped_column(String(80))
    name: Mapped[str] = mapped_column(String(200))
    quantity: Mapped[int] = mapped_column(Integer())
    unit_price_minor: Mapped[int] = mapped_column(BigInteger())
    subtotal_minor: Mapped[int] = mapped_column(BigInteger())
    order: Mapped[Order] = relationship(back_populates="items")


class InventoryReservation(Base):
    __tablename__ = "inventory_reservations"
    __table_args__ = (UniqueConstraint("order_id", "product_id", name="uq_reservation_order_product"),)
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    order_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("products.id"), index=True)
    quantity: Mapped[int] = mapped_column(Integer())
    status: Mapped[str] = mapped_column(String(16), default="RESERVED", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PaymentIntentRecord(Base):
    __tablename__ = "payment_intents"
    __table_args__ = (
        UniqueConstraint("provider", "provider_payment_id", name="uq_payment_provider_external"),
        UniqueConstraint("tenant_id", "order_id", "provider", name="uq_payment_order_provider"),
        UniqueConstraint("provider", "idempotency_key", name="uq_payment_provider_idempotency"),
    )
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    order_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(40), index=True)
    provider_payment_id: Mapped[str] = mapped_column(String(200))
    idempotency_key: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32), index=True)
    amount_minor: Mapped[int] = mapped_column(BigInteger())
    currency: Mapped[str] = mapped_column(String(3))
    checkout_url: Mapped[str | None] = mapped_column(Text())
    qr_code: Mapped[str | None] = mapped_column(Text())
    qr_code_text: Mapped[str | None] = mapped_column(Text())
    reconcile_attempts: Mapped[int] = mapped_column(Integer(), default=0)
    next_reconcile_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    last_reconcile_error: Mapped[str | None] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class PaymentEvent(Base):
    __tablename__ = "payment_events"
    __table_args__ = (UniqueConstraint("provider", "provider_event_id", name="uq_payment_event_provider_id"),)
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    provider: Mapped[str] = mapped_column(String(40))
    provider_event_id: Mapped[str] = mapped_column(String(200))
    event_type: Mapped[str] = mapped_column(String(100))
    payload: Mapped[dict] = mapped_column(JSON)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class OutboxEvent(Base):
    __tablename__ = "outbox_events"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), index=True)
    aggregate_type: Mapped[str] = mapped_column(String(64), index=True)
    aggregate_id: Mapped[str] = mapped_column(String(128), index=True)
    event_type: Mapped[str] = mapped_column(String(120), index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(16), default="PENDING", index=True)
    attempts: Mapped[int] = mapped_column(Integer(), default=0)
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RefundRecord(Base):
    __tablename__ = "refunds"
    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_refund_tenant_idempotency"),
        UniqueConstraint("provider", "provider_refund_id", name="uq_refund_provider_external"),
    )
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    order_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    payment_intent_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("payment_intents.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(40), index=True)
    provider_refund_id: Mapped[str | None] = mapped_column(String(200))
    idempotency_key: Mapped[str] = mapped_column(String(128))
    amount_minor: Mapped[int] = mapped_column(BigInteger())
    currency: Mapped[str] = mapped_column(String(3))
    status: Mapped[str] = mapped_column(String(24), default="REQUESTED", index=True)
    reason: Mapped[str | None] = mapped_column(String(500))
    last_error: Mapped[str | None] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class DisputeRecord(Base):
    __tablename__ = "disputes"
    __table_args__ = (UniqueConstraint("provider", "provider_dispute_id", name="uq_dispute_provider_external"),)
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), index=True)
    order_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("orders.id", ondelete="SET NULL"), index=True)
    payment_intent_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("payment_intents.id", ondelete="SET NULL"), index=True)
    provider: Mapped[str] = mapped_column(String(40), index=True)
    provider_dispute_id: Mapped[str] = mapped_column(String(200))
    provider_payment_id: Mapped[str | None] = mapped_column(String(200), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    amount_minor: Mapped[int | None] = mapped_column(BigInteger())
    currency: Mapped[str | None] = mapped_column(String(3))
    coverage_applied: Mapped[bool | None] = mapped_column(Boolean())
    reason: Mapped[str | None] = mapped_column(String(500))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class LedgerTransaction(Base):
    __tablename__ = "ledger_transactions"
    __table_args__ = (UniqueConstraint("tenant_id", "idempotency_key", name="uq_ledger_tenant_idempotency"),)
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(200))
    reference_type: Mapped[str] = mapped_column(String(64), index=True)
    reference_id: Mapped[str] = mapped_column(String(128), index=True)
    currency: Mapped[str] = mapped_column(String(3))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    entries: Mapped[list[LedgerEntry]] = relationship(back_populates="transaction", cascade="all, delete-orphan")


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    transaction_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("ledger_transactions.id", ondelete="CASCADE"), index=True)
    account: Mapped[str] = mapped_column(String(120), index=True)
    debit_minor: Mapped[int] = mapped_column(BigInteger(), default=0)
    credit_minor: Mapped[int] = mapped_column(BigInteger(), default=0)
    transaction: Mapped[LedgerTransaction] = relationship(back_populates="entries")


class FulfillmentRecord(Base):
    __tablename__ = "fulfillments"
    __table_args__ = (UniqueConstraint("tenant_id", "order_id", "product_id", "delivery_type", name="uq_fulfillment_order_product_type"),)
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    order_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    order_item_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("order_items.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), index=True)
    discord_user_id: Mapped[int] = mapped_column(BigInteger(), index=True)
    delivery_type: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(24), default="PENDING", index=True)
    discord_guild_id: Mapped[int | None] = mapped_column(BigInteger())
    discord_role_id: Mapped[int | None] = mapped_column(BigInteger())
    delivery_url: Mapped[str | None] = mapped_column(Text())
    access_token_hash: Mapped[str | None] = mapped_column(String(64), unique=True)
    attempts: Mapped[int] = mapped_column(Integer(), default=0)
    last_error: Mapped[str | None] = mapped_column(Text())
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
