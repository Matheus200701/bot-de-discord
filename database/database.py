from __future__ import annotations

from pathlib import Path
from typing import Any

import aiosqlite


class Database:
    def __init__(self, path: str) -> None:
        self.path = path
        self.connection: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.connection = await aiosqlite.connect(self.path)
        self.connection.row_factory = aiosqlite.Row

    async def setup(self) -> None:
        await self.execute(
            """
            CREATE TABLE IF NOT EXISTS warnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                moderator_id INTEGER NOT NULL,
                reason TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        await self.execute(
            """
            CREATE TABLE IF NOT EXISTS tickets (
                channel_id INTEGER PRIMARY KEY,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'open',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

    async def execute(self, query: str, parameters: tuple[Any, ...] = ()) -> None:
        if self.connection is None:
            raise RuntimeError("Banco de dados não conectado.")
        await self.connection.execute(query, parameters)
        await self.connection.commit()

    async def fetchone(self, query: str, parameters: tuple[Any, ...] = ()) -> aiosqlite.Row | None:
        if self.connection is None:
            raise RuntimeError("Banco de dados não conectado.")
        cursor = await self.connection.execute(query, parameters)
        row = await cursor.fetchone()
        await cursor.close()
        return row

    async def fetchall(self, query: str, parameters: tuple[Any, ...] = ()) -> list[aiosqlite.Row]:
        if self.connection is None:
            raise RuntimeError("Banco de dados não conectado.")
        cursor = await self.connection.execute(query, parameters)
        rows = await cursor.fetchall()
        await cursor.close()
        return list(rows)

    async def close(self) -> None:
        if self.connection is not None:
            await self.connection.close()
            self.connection = None
