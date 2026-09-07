from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.database.models import InventoryReservation, Product


DEFAULT_RESERVATION_TTL_SECONDS = 15 * 60


async def expire_reservations(
    session: AsyncSession,
    *,
    now: datetime | None = None,
    limit: int = 100,
) -> int:
    """Release expired reservations and restore stock atomically.

    PostgreSQL row locks make the operation safe against a concurrent payment
    transition. A reservation is released exactly once by changing its status
    from RESERVED to RELEASED under a lock before restoring inventory.
    """
    now = now or datetime.now(timezone.utc)
    result = await session.execute(
        select(InventoryReservation)
        .where(
            InventoryReservation.status == "RESERVED",
            InventoryReservation.expires_at.is_not(None),
            InventoryReservation.expires_at <= now,
        )
        .order_by(InventoryReservation.expires_at)
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    reservations = list(result.scalars())
    released = 0
    for reservation in reservations:
        product = await session.scalar(
            select(Product)
            .where(
                Product.id == reservation.product_id,
                Product.tenant_id == reservation.tenant_id,
            )
            .with_for_update()
        )
        if product is None:
            continue
        reservation.status = "RELEASED"
        product.stock_quantity += reservation.quantity
        released += 1
    await session.flush()
    return released


def reservation_expiry(ttl_seconds: int = DEFAULT_RESERVATION_TTL_SECONDS) -> datetime:
    if ttl_seconds <= 0:
        raise ValueError("ttl_seconds_must_be_positive")
    return datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
