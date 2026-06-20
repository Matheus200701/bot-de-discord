from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _to_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "sim", "on"}


def _to_int(value: str | None, default: int = 0) -> int:
    try:
        return int(value or default)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    discord_token: str | None = os.getenv("DISCORD_TOKEN")
    prefix: str = os.getenv("PREFIX", "!")
    database_path: str = os.getenv("DATABASE_PATH", "data/bot.db")
    owner_id: int = _to_int(os.getenv("OWNER_ID"), 0)
    message_content_intent: bool = _to_bool(os.getenv("MESSAGE_CONTENT_INTENT"), False)


settings = Settings()
