from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import discord
from discord.ext import commands

from config import settings
from database.database import Database

EXTENSIONS = (
    "cogs.utilidade",
    "cogs.moderacao",
    "cogs.tickets",
)


class CommunityBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.guilds = True
        intents.members = True
        intents.message_content = settings.message_content_intent

        super().__init__(
            command_prefix=settings.prefix,
            intents=intents,
            help_command=None,
            case_insensitive=True,
        )
        self.db = Database(settings.database_path)

    async def setup_hook(self) -> None:
        Path("data").mkdir(exist_ok=True)
        await self.db.connect()
        await self.db.setup()

        for extension in EXTENSIONS:
            try:
                await self.load_extension(extension)
                logging.info("Cog carregada: %s", extension)
            except Exception:
                logging.exception("Erro ao carregar a cog: %s", extension)

        synced = await self.tree.sync()
        logging.info("Comandos slash sincronizados: %s", len(synced))

    async def close(self) -> None:
        await self.db.close()
        await super().close()

    async def on_ready(self) -> None:
        if self.user is None:
            return
        activity = discord.Game(name="/ajuda | comunidade segura")
        await self.change_presence(status=discord.Status.online, activity=activity)
        logging.info("Bot online como %s", self.user)

    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        if isinstance(error, commands.CommandNotFound):
            return
        if isinstance(error, commands.MissingPermissions):
            await ctx.reply("❌ Você não tem permissão para usar esse comando.", mention_author=False)
            return
        if isinstance(error, commands.BotMissingPermissions):
            await ctx.reply("❌ Eu não tenho as permissões necessárias para executar isso.", mention_author=False)
            return
        logging.exception("Erro em comando", exc_info=error)
        await ctx.reply("❌ Ocorreu um erro ao executar o comando.", mention_author=False)


async def main() -> None:
    if not settings.discord_token or settings.discord_token == "COLOQUE_SEU_TOKEN_AQUI":
        raise RuntimeError("Configure DISCORD_TOKEN no arquivo .env antes de iniciar o bot.")

    bot = CommunityBot()
    async with bot:
        await bot.start(settings.discord_token)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    asyncio.run(main())
