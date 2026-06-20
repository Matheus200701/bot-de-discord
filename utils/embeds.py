from __future__ import annotations

import discord

DEFAULT_COLOR = 0x2B2D31
SUCCESS_COLOR = 0x57F287
ERROR_COLOR = 0xED4245
WARNING_COLOR = 0xFEE75C


def default_embed(title: str, description: str | None = None) -> discord.Embed:
    return discord.Embed(title=title, description=description, color=DEFAULT_COLOR)


def success_embed(description: str) -> discord.Embed:
    return discord.Embed(title="✅ Sucesso", description=description, color=SUCCESS_COLOR)


def error_embed(description: str) -> discord.Embed:
    return discord.Embed(title="❌ Erro", description=description, color=ERROR_COLOR)


def warning_embed(description: str) -> discord.Embed:
    return discord.Embed(title="⚠️ Atenção", description=description, color=WARNING_COLOR)
