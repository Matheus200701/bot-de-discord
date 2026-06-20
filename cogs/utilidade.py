from __future__ import annotations

import platform

import discord
from discord.ext import commands

from utils.embeds import default_embed, success_embed


class Utilidade(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.hybrid_command(name="ping", description="Mostra a latência do bot.")
    async def ping(self, ctx: commands.Context) -> None:
        latency_ms = round(self.bot.latency * 1000)
        await ctx.send(embed=success_embed(f"Pong! Latência: `{latency_ms}ms`."))

    @commands.hybrid_command(name="ajuda", description="Mostra a lista de comandos do bot.")
    async def ajuda(self, ctx: commands.Context) -> None:
        embed = default_embed(
            "📘 Central de Ajuda",
            "Use comandos com `/` ou com o prefixo configurado no `.env`.",
        )
        embed.add_field(
            name="🛠️ Moderação",
            value="`/banir`, `/expulsar`, `/limpar`, `/timeout`, `/untimeout`, `/avisar`, `/avisos`",
            inline=False,
        )
        embed.add_field(
            name="🎫 Tickets",
            value="`/ticketpainel`",
            inline=False,
        )
        embed.add_field(
            name="🔧 Utilidade",
            value="`/ping`, `/avatar`, `/userinfo`, `/serverinfo`, `/botinfo`",
            inline=False,
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="avatar", description="Mostra o avatar de um membro.")
    async def avatar(self, ctx: commands.Context, membro: discord.Member | None = None) -> None:
        membro = membro or ctx.author
        embed = default_embed(f"Avatar de {membro.display_name}")
        embed.set_image(url=membro.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="userinfo", description="Mostra informações de um membro.")
    async def userinfo(self, ctx: commands.Context, membro: discord.Member | None = None) -> None:
        membro = membro or ctx.author
        embed = default_embed(f"👤 Informações de {membro.display_name}")
        embed.set_thumbnail(url=membro.display_avatar.url)
        embed.add_field(name="ID", value=str(membro.id), inline=True)
        embed.add_field(name="Conta criada", value=discord.utils.format_dt(membro.created_at, "R"), inline=True)
        if membro.joined_at:
            embed.add_field(name="Entrou no servidor", value=discord.utils.format_dt(membro.joined_at, "R"), inline=True)
        cargos = [role.mention for role in membro.roles if role.name != "@everyone"]
        embed.add_field(name="Cargos", value=", ".join(cargos[-10:]) if cargos else "Nenhum", inline=False)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="serverinfo", description="Mostra informações do servidor.")
    @commands.guild_only()
    async def serverinfo(self, ctx: commands.Context) -> None:
        guild = ctx.guild
        assert guild is not None
        embed = default_embed(f"🏠 Informações de {guild.name}")
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        embed.add_field(name="ID", value=str(guild.id), inline=True)
        embed.add_field(name="Dono", value=guild.owner.mention if guild.owner else "Não encontrado", inline=True)
        embed.add_field(name="Membros", value=str(guild.member_count), inline=True)
        embed.add_field(name="Canais", value=str(len(guild.channels)), inline=True)
        embed.add_field(name="Cargos", value=str(len(guild.roles)), inline=True)
        embed.add_field(name="Criado", value=discord.utils.format_dt(guild.created_at, "R"), inline=True)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="botinfo", description="Mostra informações técnicas do bot.")
    async def botinfo(self, ctx: commands.Context) -> None:
        embed = default_embed("🤖 Informações do Bot")
        embed.add_field(name="Python", value=platform.python_version(), inline=True)
        embed.add_field(name="discord.py", value=discord.__version__, inline=True)
        embed.add_field(name="Servidores", value=str(len(self.bot.guilds)), inline=True)
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Utilidade(bot))
