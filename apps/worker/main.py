from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select

from packages.database.models import OutboxEvent, PaymentIntentRecord
from packages.database.session import SessionFactory
from packages.payments.mercadopago import MercadoPagoPixProvider
from packages.payments.reliability import (
    MAX_OUTBOX_ATTEMPTS,
    OUTBOX_BASE_DELAY_SECONDS,
    OUTBOX_MAX_DELAY_SECONDS,
    OutboxDispatcher,
    exponential_backoff,
    reconcile_payment,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
LOGGER = logging.getLogger("commerce-worker")
POLL_SECONDS = 2
BATCH_SIZE = 50
STALE_LOCK_SECONDS = 300


async def _requeue_stale_outbox(session) -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=STALE_LOCK_SECONDS)
    result = await session.execute(
        select(OutboxEvent).where(
            OutboxEvent.status == "PROCESSING",
            OutboxEvent.locked_at < cutoff,
        ).with_for_update(skip_locked=True)
    )
    for event in result.scalars():
        event.status = "PENDING"
        event.locked_at = None


async def process_outbox(dispatcher: OutboxDispatcher) -> int:
    processed = 0
    async with SessionFactory() as session:
        async with session.begin():
            await _requeue_stale_outbox(session)
            result = await session.execute(
                select(OutboxEvent)
                .where(
                    OutboxEvent.status == "PENDING",
                    OutboxEvent.next_attempt_at <= datetime.now(timezone.utc),
                )
                .order_by(OutboxEvent.created_at)
                .limit(BATCH_SIZE)
                .with_for_update(skip_locked=True)
            )
            events = list(result.scalars())
            for event in events:
                event.status = "PROCESSING"
                event.locked_at = datetime.now(timezone.utc)

    for event_id in [event.id for event in events]:
        try:
            async with SessionFactory() as session:
                async with session.begin():
                    event = await session.scalar(select(OutboxEvent).where(OutboxEvent.id == event_id).with_for_update())
                    if event is None or event.status != "PROCESSING":
                        continue
                    await dispatcher.dispatch(session, event)
                    event.status = "PROCESSED"
                    event.processed_at = datetime.now(timezone.utc)
                    event.locked_at = None
                    event.last_error = None
                    processed += 1
        except Exception as exc:
            async with SessionFactory() as session:
                async with session.begin():
                    event = await session.scalar(select(OutboxEvent).where(OutboxEvent.id == event_id).with_for_update())
                    if event is None:
                        continue
                    event.attempts += 1
                    event.locked_at = None
                    event.last_error = str(exc)[:4000]
                    if event.attempts >= MAX_OUTBOX_ATTEMPTS:
                        event.status = "DEAD"
                        LOGGER.error("Outbox event %s moved to DEAD after %s attempts", event.id, event.attempts)
                    else:
                        event.status = "PENDING"
                        event.next_attempt_at = datetime.now(timezone.utc) + timedelta(
                            seconds=exponential_backoff(event.attempts, OUTBOX_BASE_DELAY_SECONDS, OUTBOX_MAX_DELAY_SECONDS)
                        )
    return processed


async def reconcile_due_payments(provider: MercadoPagoPixProvider) -> int:
    count = 0
    for _ in range(BATCH_SIZE):
        async with SessionFactory() as session:
            async with session.begin():
                result = await session.execute(
                    select(PaymentIntentRecord.id)
                    .where(
                        PaymentIntentRecord.provider == provider.name,
                        PaymentIntentRecord.status.not_in({"approved", "cancelled", "rejected", "expired"}),
                        or_(
                            PaymentIntentRecord.next_reconcile_at.is_(None),
                            PaymentIntentRecord.next_reconcile_at <= datetime.now(timezone.utc),
                        ),
                    )
                    .order_by(PaymentIntentRecord.updated_at)
                    .limit(1)
                    .with_for_update(skip_locked=True)
                )
                payment_id = result.scalar_one_or_none()
                if payment_id is None:
                    return count
                status = await reconcile_payment(session, provider, payment_id)
                count += 1
                LOGGER.info("Reconciled payment %s status=%s", payment_id, status)
    return count


async def main() -> None:
    provider = MercadoPagoPixProvider()
    dispatcher = OutboxDispatcher()

    async def log_payment_event(session, event: OutboxEvent) -> None:
        LOGGER.info("Outbox payment event %s type=%s aggregate=%s", event.id, event.event_type, event.aggregate_id)

    for event_type in (
        "payment.created",
        "payment.paid",
        "payment.status.action_required",
        "payment.status.waiting_payment",
        "payment.status.cancelled",
        "payment.status.rejected",
        "payment.status.expired",
        "payment.reconciliation_dead_lettered",
        "payment.unknown",
    ):
        dispatcher.register(event_type, log_payment_event)

    while True:
        try:
            outbox_count, reconcile_count = await asyncio.gather(
                process_outbox(dispatcher),
                reconcile_due_payments(provider),
            )
            if outbox_count or reconcile_count:
                LOGGER.info("worker cycle outbox=%s reconciled=%s", outbox_count, reconcile_count)
        except Exception:
            LOGGER.exception("worker cycle failed")
        await asyncio.sleep(POLL_SECONDS)


if __name__ == "__main__":
    asyncio.run(main())
