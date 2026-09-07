from __future__ import annotations

import os
from typing import Any

import httpx


class DiscordDeliveryError(RuntimeError):
    pass


class DiscordRoleDelivery:
    def __init__(self, bot_token: str | None = None) -> None:
        self.bot_token = bot_token or os.environ["DISCORD_TOKEN"]
        self.base_url = os.getenv("DISCORD_API_BASE_URL", "https://discord.com/api/v10")

    async def _request(self, method: str, path: str) -> httpx.Response:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=15.0) as client:
            response = await client.request(
                method,
                path,
                headers={
                    "Authorization": f"Bot {self.bot_token}",
                    "User-Agent": "DiscordCommercePlatform/2026",
                },
            )
        if response.is_error:
            raise DiscordDeliveryError(f"discord_http_{response.status_code}")
        return response

    async def _role_exists_and_not_managed(self, guild_id: int, role_id: int) -> None:
        response = await self._request("GET", f"/guilds/{guild_id}/roles")
        roles: list[dict[str, Any]] = response.json()
        target = next((role for role in roles if int(role["id"]) == role_id), None)
        if target is None:
            raise DiscordDeliveryError("role_not_found")
        if bool(target.get("managed")):
            raise DiscordDeliveryError("managed_role_not_assignable")

    async def add_role(self, guild_id: int, user_id: int, role_id: int) -> None:
        await self._role_exists_and_not_managed(guild_id, role_id)
        await self._request("PUT", f"/guilds/{guild_id}/members/{user_id}/roles/{role_id}")

    async def remove_role(self, guild_id: int, user_id: int, role_id: int) -> None:
        await self._role_exists_and_not_managed(guild_id, role_id)
        await self._request("DELETE", f"/guilds/{guild_id}/members/{user_id}/roles/{role_id}")
