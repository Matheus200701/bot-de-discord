import os

import discord
from discord import app_commands
from discord.ext import commands

TOKEN = os.environ["DISCORD_TOKEN"]
TEST_GUILD_ID = int(os.getenv("DISCORD_TEST_GUILD_ID", "0"))

intents = discord.Intents.none()
intents.guilds = True


class CommerceApp(commands.Bot):
    def __init__(self) -> None:
        super().__init__(command_prefix=commands.when_mentioned, intents=intents)

    async def setup_hook(self) -> None:
        if TEST_GUILD_ID:
            guild = discord.Object(id=TEST_GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()


app = CommerceApp()


@app.tree.command(name="loja", description="Abrir a loja")
async def store(interaction: discord.Interaction) -> None:
    embed = discord.Embed(title="🛒 Loja", description="Escolha uma opção abaixo.")
    view = discord.ui.View(timeout=120)
    view.add_item(discord.ui.Button(label="Produtos", style=discord.ButtonStyle.primary, custom_id="store:products:v1"))
    view.add_item(discord.ui.Button(label="Carrinho", style=discord.ButtonStyle.secondary, custom_id="store:cart:v1"))
    view.add_item(discord.ui.Button(label="Meus pedidos", style=discord.ButtonStyle.secondary, custom_id="store:orders:v1"))
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


@app.tree.command(name="carrinho", description="Consultar seu carrinho")
async def cart(interaction: discord.Interaction) -> None:
    await interaction.response.send_message("Seu carrinho está vazio.", ephemeral=True)


@app.tree.command(name="pedido", description="Consultar um pedido")
@app_commands.describe(order_id="ID do pedido")
async def order(interaction: discord.Interaction, order_id: str) -> None:
    await interaction.response.send_message(f"Consulta do pedido `{order_id}` será carregada pela API.", ephemeral=True)


@app.tree.command(name="entregas", description="Consultar as entregas dos seus pedidos")
async def deliveries(interaction: discord.Interaction) -> None:
    await interaction.response.send_message(
        "Suas entregas ficam vinculadas aos pedidos pagos e podem incluir cargo Discord ou entrega digital.",
        ephemeral=True,
    )


@app.tree.command(name="suporte", description="Abrir atendimento")
async def support(interaction: discord.Interaction) -> None:
    await interaction.response.send_message("O fluxo de suporte será iniciado em uma área privada.", ephemeral=True)


@app.event
async def on_ready() -> None:
    print(f"Discord Commerce App online: {app.user} / API v10-compatible")


if __name__ == "__main__":
    app.run(TOKEN)
