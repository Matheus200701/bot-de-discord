from __future__ import annotations

import asyncio
import random
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Awaitable, Callable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.commerce.services import CommerceError, transition_order
from packages.database.models import Order, OutboxEvent, PaymentIntentRecord
from packages.payments.base import PaymentProvider
from packages.payments.finance import post_ledger_transaction

MAX_OUTBOX_ATTEMPTS = 12
OUTBOX_BASE_DELAY_SECONDS = 2
OUTBOX_MAX_DELAY_SECONDS = 15 * 60
RECONCILE_BASE_DELAY_SECONDS = 30
RECONCILE_MAX_DELAY_SECONDS = 60 * 60


def exponential_backoff(attempt: int, base: int, cap: int) -> float:
    exponent = max(0, attempt - 1)
    return min(cap, base * (2**exponent)) + random.uniform(0, min(1.0, base))


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_seconds: int = 30) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_seconds = recovery_seconds
        self.failures: dict[str, int] = defaultdict(int)
        self.opened_at: dict[str, datetime] = {}

    def allow(self, key: str) -> bool:
        opened = self.opened_at.get(key)
        if opened is None:
            return True
        if datetime.now(timezone.utc) - opened >= timedelta(seconds=self.recovery_seconds):
            self.opened_at.pop(key, None)
            self.failures[key] = 0
            return True
        return False

    def success(self, key: str) -> None:
        self.failures[key] = 0
        self.opened_at.pop(key, None)

    def failure(self, key: str) -> None:
        self.failures[key] += 1
        if self.failures[key] >= self.failure_threshold:
            self.opened_at[key] = datetime.now(timezone.utc)


PSP_BREAKERS = CircuitBreaker()


def enqueue_outbox(session: AsyncSession, *, tenant_id: UUID | None, aggregate_type: str, aggregate_id: str, event_type: str, payload: dict) -> OutboxEvent:
    event = OutboxEvent(tenant_id=tenant_id, aggregate_type=aggregate_type, aggregate_id=aggregate_id, event_type=event_type, payload=payload)
    session.add(event)
    return event


async def reconcile_payment(session: AsyncSession, provider: PaymentProvider, payment_id: UUID, *, timeout_seconds: float = 10.0) -> str:
    payment = await session.scalar(select(PaymentIntentRecord).where(PaymentIntentRecord.id == payment_id).with_for_update())
    if payment is None:
        raise CommerceError("payment_not_found")
    if payment.status in {"approved", "cancelled", "rejected", "expired"}:
        return payment.status

    breaker_key = provider.name
    if not PSP_BREAKERS.allow(breaker_key):
        payment.next_reconcile_at = datetime.now(timezone.utc) + timedelta(seconds=RECONCILE_BASE_DELAY_SECONDS)
        return "circuit_open"

    try:
        remote = await asyncio.wait_for(provider.get_payment(payment.provider_payment_id), timeout=timeout_seconds)
        if remote.amount_minor != payment.amount_minor or remote.currency != payment.currency:
            raise CommerceError("payment_amount_mismatch")
        PSP_BREAKERS.success(breaker_key)
        previous_status = payment.status
        payment.status = remote.status
        payment.reconcile_attempts = 0
        payment.last_reconcile_error = None
        payment.next_reconcile_at = next_reconcile_time(remote.status)

        if remote.status == "approved":
            await post_ledger_transaction(
                session,
                tenant_id=payment.tenant_id,
                idempotency_key=f"payment-approved:{payment.id}",
                reference_type="payment",
                reference_id=str(payment.id),
                currency=payment.currency,
                debit_account=f"cash:{payment.provider}",
                credit_account="revenue:sales",
                amount_minor=payment.amount_minor,
            )
            order = await session.scalar(select(Order).where(Order.id == payment.order_id, Order.tenant_id == payment.tenant_id).with_for_update())
            if order is not None and order.status == "PAYMENT_PENDING":
                await transition_order(session, payment.order_id, payment.tenant_id, "PAID")
            if previous_status != "approved":
                enqueue_outbox(session, tenant_id=payment.tenant_id, aggregate_type="payment", aggregate_id=str(payment.id), event_type="payment.paid", payload={"order_id": str(payment.order_id), "provider": payment.provider})
        elif remote.status in {"cancelled", "rejected", "expired"}:
            order = await session.scalar(select(Order).where(Order.id == payment.order_id, Order.tenant_id == payment.tenant_id).with_for_update())
            if order is not None and order.status == "PAYMENT_PENDING":
                target = "EXPIRED" if remote.status == "expired" else "CANCELLED"
                await transition_order(session, payment.order_id, payment.tenant_id, target)
        return remote.status
    except Exception as exc:
        PSP_BREAKERS.failure(breaker_key)
        payment.reconcile_attempts += 1
        payment.last_reconcile_error = str(exc)[:2000]
        if payment.reconcile_attempts >= MAX_OUTBOX_ATTEMPTS:
            payment.next_reconcile_at = None
            enqueue_outbox(session, tenant_id=payment.tenant_id, aggregate_type="payment", aggregate_id=str(payment.id), event_type="payment.reconciliation_dead_lettered", payload={"order_id": str(payment.order_id), "error": str(exc)[:2000]})
            return "dead_lettered"
        payment.next_reconcile_at = datetime.now(timezone.utc) + timedelta(seconds=exponential_backoff(payment.reconcile_attempts, RECONCILE_BASE_DELAY_SECONDS, RECONCILE_MAX_DELAY_SECONDS))
        return "retry_scheduled"


def next_reconcile_time(status: str) -> datetime | None:
    if status in {"approved", "cancelled", "rejected", "expired"}:
        return None
    return datetime.now(timezone.utc) + timedelta(seconds=60)


OutboxHandler = Callable[[AsyncSession, OutboxEvent], Awaitable[None]]


class OutboxDispatcher:
    def __init__(self) -> None:
        self.handlers: dict[str, OutboxHandler] = {}

    def register(self, event_type: str, handler: OutboxHandler) -> None:
        self.handlers[event_type] = handler

    async def dispatch(self, session: AsyncSession, event: OutboxEvent) -> None:
        handler = self.handlers.get(event.event_type)
        if handler is not None:
            await handler(session, event)
