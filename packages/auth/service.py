from __future__ import annotations

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.database.models import DashboardSession, DashboardUser, OAuthState, Tenant, TenantMembership

DISCORD_API = os.getenv("DISCORD_API_BASE_URL", "https://discord.com/api/v10")
SCOPES = "identify guilds"
SESSION_DAYS = 7
STATE_MINUTES = 10
MANAGE_GUILD = 1 << 5


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def oauth_authorize_url(state: str) -> str:
    params = {
        "response_type": "code",
        "client_id": os.environ["DISCORD_APPLICATION_ID"],
        "scope": SCOPES,
        "state": state,
        "redirect_uri": os.environ["OAUTH_REDIRECT_URI"],
        "prompt": "consent",
    }
    return f"https://discord.com/oauth2/authorize?{urlencode(params)}"


async def begin_oauth(session: AsyncSession) -> str:
    state = secrets.token_urlsafe(32)
    session.add(OAuthState(state_hash=_hash(state), expires_at=_now() + timedelta(minutes=STATE_MINUTES)))
    await session.flush()
    return state


async def exchange_code(code: str) -> dict:
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": os.environ["OAUTH_REDIRECT_URI"],
    }
    auth = (os.environ["DISCORD_APPLICATION_ID"], os.environ["OAUTH_CLIENT_SECRET"])
    async with httpx.AsyncClient(base_url=DISCORD_API, timeout=15.0) as client:
        response = await client.post("/oauth2/token", data=data, auth=auth)
        response.raise_for_status()
        return response.json()


async def discord_identity(access_token: str) -> tuple[dict, list[dict]]:
    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient(base_url=DISCORD_API, timeout=15.0) as client:
        me_response = await client.get("/users/@me", headers=headers)
        guild_response = await client.get("/users/@me/guilds", headers=headers)
        me_response.raise_for_status()
        guild_response.raise_for_status()
        return me_response.json(), guild_response.json()


async def consume_state(session: AsyncSession, state: str) -> bool:
    record = await session.scalar(select(OAuthState).where(OAuthState.state_hash == _hash(state)).with_for_update())
    if record is None or record.expires_at <= _now() or record.consumed_at is not None:
        return False
    record.consumed_at = _now()
    return True


async def upsert_identity(session: AsyncSession, user_data: dict, guilds: list[dict]) -> DashboardUser:
    discord_id = int(user_data["id"])
    user = await session.scalar(select(DashboardUser).where(DashboardUser.discord_user_id == discord_id).with_for_update())
    if user is None:
        user = DashboardUser(discord_user_id=discord_id, username=str(user_data.get("username", "")), global_name=user_data.get("global_name"), avatar_hash=user_data.get("avatar"))
        session.add(user)
        await session.flush()
    else:
        user.username = str(user_data.get("username", user.username))
        user.global_name = user_data.get("global_name")
        user.avatar_hash = user_data.get("avatar")

    for guild in guilds:
        permissions = int(guild.get("permissions", 0))
        if guild.get("owner") is not True and not (permissions & MANAGE_GUILD):
            continue
        guild_id = int(guild["id"])
        tenant = await session.scalar(select(Tenant).where(Tenant.discord_guild_id == guild_id).with_for_update())
        if tenant is None:
            tenant = Tenant(discord_guild_id=guild_id, name=str(guild.get("name", guild_id)))
            session.add(tenant)
            await session.flush()
        tenant.name = str(guild.get("name", tenant.name))
        membership = await session.scalar(select(TenantMembership).where(TenantMembership.tenant_id == tenant.id, TenantMembership.user_id == user.id).with_for_update())
        role = "OWNER" if guild.get("owner") is True else "ADMIN"
        if membership is None:
            session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role=role))
        elif membership.role != "OWNER":
            membership.role = role
    await session.flush()
    return user


async def create_session(session: AsyncSession, user: DashboardUser) -> str:
    token = secrets.token_urlsafe(48)
    session.add(DashboardSession(user_id=user.id, token_hash=_hash(token), expires_at=_now() + timedelta(days=SESSION_DAYS)))
    await session.flush()
    return token


async def get_session_user(session: AsyncSession, token: str | None) -> DashboardUser | None:
    if not token:
        return None
    row = await session.scalar(select(DashboardSession).where(DashboardSession.token_hash == _hash(token)).with_for_update())
    if row is None or row.expires_at <= _now() or row.revoked_at is not None:
        return None
    row.last_seen_at = _now()
    return await session.scalar(select(DashboardUser).where(DashboardUser.id == row.user_id))
