from __future__ import annotations

import asyncio

import discord
from discord.ext import commands

from utils.embeds import default_embed, success_embed


class FecharTicketView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(label="Fechar ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="ticket:fechar")
    async def fechar(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.guild is None or interaction.channel is None:
            return

        permissions = interaction.user.guild_permissions
        is_author = False
        bot = interaction.client
        row = None
        if hasattr(bot, "db"):
            row = await bot.db.fetchone("SELECT user_id FROM tickets WHERE channel_id = ?", (interaction.channel.id,))
            is_author = bool(row and row["user_id"] == interaction.user.id)

        if not permissions.manage_channels and not is_author:
            await interaction.response.send_message("❌ Apenas a equipe ou o autor do ticket pode fechar este ticket.", ephemeral=True)
            return

        await interaction.response.send_message("🔒 Ticket será fechado em 5 segundos.")
        if hasattr(bot, "db"):
            await bot.db.execute("UPDATE tickets SET status = 'closed' WHERE channel_id = ?", (interaction.channel.id,))
        await asyncio.sleep(5)
        await interaction.channel.delete(reason=f"Ticket fechado por {interaction.user}")


class TicketView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(label="Abrir ticket", style=discord.ButtonStyle.success, emoji="🎫", custom_id="ticket:abrir")
    async def abrir(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.guild is None:
            return

        bot = interaction.client
        guild = interaction.guild
        author = interaction.user

        existing = None
        if hasattr(bot, "db"):
            existing = await bot.db.fetchone(
                "SELECT channel_id FROM tickets WHERE guild_id = ? AND user_id = ? AND status = 'open'",
                (guild.id, author.id),
            )
        if existing:
            channel = guild.get_channel(existing["channel_id"])
            if channel:
                await interaction.response.send_message(f"❌ Você já tem um ticket aberto: {channel.mention}", ephemeral=True)
                return

        category = discord.utils.get(guild.categories, name="Tickets")
        if category is None:
            category = await guild.create_category("Tickets", reason="Sistema de tickets")

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            author: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True),
        }

        channel = await guild.create_text_channel(
            name=f"ticket-{author.name}"[:90],
            category=category,
            overwrites=overwrites,
            reason=f"Ticket aberto por {author}",
        )

        if hasattr(bot, "db"):
            await bot.db.execute(
                "INSERT OR REPLACE INTO tickets (channel_id, guild_id, user_id, status) VALUES (?, ?, ?, 'open')",
                (channel.id, guild.id, author.id),
            )

        embed = default_embed(
            "🎫 Ticket aberto",
            f"Olá {author.mention}. Explique seu problema com detalhes.\n\nA equipe responderá quando possível.",
        )
        await channel.send(content=author.mention, embed=embed, view=FecharTicketView())
        await interaction.response.send_message(f"✅ Ticket criado: {channel.mention}", ephemeral=True)


class Tickets(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        bot.add_view(TicketView())
        bot.add_view(FecharTicketView())

    @commands.hybrid_command(name="ticketpainel", description="Cria o painel de tickets no canal atual.")
    @commands.guild_only()
    @commands.has_guild_permissions(manage_guild=True)
    @commands.bot_has_guild_permissions(manage_channels=True, send_messages=True)
    async def ticketpainel(self, ctx: commands.Context) -> None:
        embed = default_embed(
            "🎫 Suporte",
            "Clique no botão abaixo para abrir um ticket privado com a equipe do servidor.",
        )
        await ctx.send(embed=embed, view=TicketView())


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Tickets(bot))
