from __future__ import annotations

from datetime import timedelta

import discord
from discord.ext import commands

from utils.embeds import default_embed, success_embed


class Moderacao(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.hybrid_command(name="banir", description="Bane um membro do servidor.")
    @commands.guild_only()
    @commands.has_guild_permissions(ban_members=True)
    @commands.bot_has_guild_permissions(ban_members=True)
    async def banir(self, ctx: commands.Context, membro: discord.Member, *, motivo: str = "Sem motivo informado") -> None:
        if membro.top_role >= ctx.author.top_role and ctx.guild.owner_id != ctx.author.id:
            await ctx.send("❌ Você não pode banir alguém com cargo igual ou superior ao seu.")
            return
        await membro.ban(reason=f"{motivo} | Moderador: {ctx.author}")
        await ctx.send(embed=success_embed(f"{membro.mention} foi banido. Motivo: `{motivo}`"))

    @commands.hybrid_command(name="expulsar", description="Expulsa um membro do servidor.")
    @commands.guild_only()
    @commands.has_guild_permissions(kick_members=True)
    @commands.bot_has_guild_permissions(kick_members=True)
    async def expulsar(self, ctx: commands.Context, membro: discord.Member, *, motivo: str = "Sem motivo informado") -> None:
        if membro.top_role >= ctx.author.top_role and ctx.guild.owner_id != ctx.author.id:
            await ctx.send("❌ Você não pode expulsar alguém com cargo igual ou superior ao seu.")
            return
        await membro.kick(reason=f"{motivo} | Moderador: {ctx.author}")
        await ctx.send(embed=success_embed(f"{membro.mention} foi expulso. Motivo: `{motivo}`"))

    @commands.hybrid_command(name="limpar", description="Apaga mensagens de um canal.")
    @commands.guild_only()
    @commands.has_guild_permissions(manage_messages=True)
    @commands.bot_has_guild_permissions(manage_messages=True)
    async def limpar(self, ctx: commands.Context, quantidade: commands.Range[int, 1, 100]) -> None:
        if ctx.interaction:
            await ctx.interaction.response.defer(ephemeral=True)
        deleted = await ctx.channel.purge(limit=quantidade)
        if ctx.interaction:
            await ctx.interaction.followup.send(f"✅ {len(deleted)} mensagens apagadas.", ephemeral=True)
        else:
            await ctx.send(f"✅ {len(deleted)} mensagens apagadas.", delete_after=5)

    @commands.hybrid_command(name="timeout", description="Silencia temporariamente um membro.")
    @commands.guild_only()
    @commands.has_guild_permissions(moderate_members=True)
    @commands.bot_has_guild_permissions(moderate_members=True)
    async def timeout(
        self,
        ctx: commands.Context,
        membro: discord.Member,
        minutos: commands.Range[int, 1, 40320],
        *,
        motivo: str = "Sem motivo informado",
    ) -> None:
        if membro.top_role >= ctx.author.top_role and ctx.guild.owner_id != ctx.author.id:
            await ctx.send("❌ Você não pode silenciar alguém com cargo igual ou superior ao seu.")
            return
        await membro.timeout(timedelta(minutes=minutos), reason=f"{motivo} | Moderador: {ctx.author}")
        await ctx.send(embed=success_embed(f"{membro.mention} recebeu timeout por `{minutos}` minutos. Motivo: `{motivo}`"))

    @commands.hybrid_command(name="untimeout", description="Remove o timeout de um membro.")
    @commands.guild_only()
    @commands.has_guild_permissions(moderate_members=True)
    @commands.bot_has_guild_permissions(moderate_members=True)
    async def untimeout(self, ctx: commands.Context, membro: discord.Member, *, motivo: str = "Sem motivo informado") -> None:
        await membro.timeout(None, reason=f"{motivo} | Moderador: {ctx.author}")
        await ctx.send(embed=success_embed(f"Timeout removido de {membro.mention}."))

    @commands.hybrid_command(name="avisar", description="Adiciona um aviso a um membro.")
    @commands.guild_only()
    @commands.has_guild_permissions(manage_messages=True)
    async def avisar(self, ctx: commands.Context, membro: discord.Member, *, motivo: str) -> None:
        await self.bot.db.execute(
            "INSERT INTO warnings (guild_id, user_id, moderator_id, reason) VALUES (?, ?, ?, ?)",
            (ctx.guild.id, membro.id, ctx.author.id, motivo),
        )
        await ctx.send(embed=success_embed(f"Aviso registrado para {membro.mention}. Motivo: `{motivo}`"))

    @commands.hybrid_command(name="avisos", description="Mostra os avisos de um membro.")
    @commands.guild_only()
    @commands.has_guild_permissions(manage_messages=True)
    async def avisos(self, ctx: commands.Context, membro: discord.Member) -> None:
        rows = await self.bot.db.fetchall(
            "SELECT id, moderator_id, reason, created_at FROM warnings WHERE guild_id = ? AND user_id = ? ORDER BY id DESC LIMIT 10",
            (ctx.guild.id, membro.id),
        )
        embed = default_embed(f"⚠️ Avisos de {membro.display_name}")
        if not rows:
            embed.description = "Este membro não possui avisos."
        else:
            embed.description = "\n".join(
                f"`#{row['id']}` • <@{row['moderator_id']}> • {row['reason']}" for row in rows
            )
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Moderacao(bot))
