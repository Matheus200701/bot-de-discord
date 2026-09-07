from __future__ import annotations

import asyncio
import os

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from packages.commerce.reservations import expire_reservations


DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is required")

engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def run_once() -> int:
    async with session_factory() as session:
        released = await expire_reservations(session)
        await session.commit()
        return released


async def main() -> None:
    interval = max(5, int(os.environ.get("RESERVATION_SWEEP_INTERVAL_SECONDS", "30")))
    while True:
        try:
            await run_once()
        except Exception as exc:  # noqa: BLE001
            print(f"reservation_sweeper_error={exc!r}", flush=True)
        await asyncio.sleep(interval)


if __name__ == "__main__":
    asyncio.run(main())
