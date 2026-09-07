from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from fastapi import APIRouter, Cookie, HTTPException, Response
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from packages.auth.models import DashboardSession, Tenant, TenantMembership
from packages.auth.service import begin_oauth, consume_state, create_session, discord_identity, exchange_code, get_session_user, oauth_authorize_url, upsert_identity
from packages.database.session import SessionFactory

router = APIRouter(prefix="/api/v1/auth/discord", tags=["auth"])
SESSION_COOKIE = "commerce_session"


@router.get("/login", response_class=RedirectResponse)
async def login() -> RedirectResponse:
    session = SessionFactory()
    try:
        async with session.begin():
            state = await begin_oauth(session)
        return RedirectResponse(oauth_authorize_url(state), status_code=302, headers={"Cache-Control": "no-store"})
    finally:
        await session.close()


@router.get("/callback")
async def callback(code: str, state: str) -> Response:
    session = SessionFactory()
    try:
        async with session.begin():
            if not await consume_state(session, state):
                raise HTTPException(400, "invalid_oauth_state")
            token_data = await exchange_code(code)
            access_token = str(token_data["access_token"])
            user_data, guilds = await discord_identity(access_token)
            user = await upsert_identity(session, user_data, guilds)
            session_token = await create_session(session, user)
        response = RedirectResponse("/", status_code=302, headers={"Cache-Control": "no-store"})
        response.set_cookie(SESSION_COOKIE, session_token, max_age=604800, httponly=True, secure=True, samesite="lax", path="/")
        return response
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(502, "discord_oauth_failed") from exc
    finally:
        await session.close()


@router.post("/logout", status_code=204)
async def logout(response: Response, session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE)) -> None:
    session = SessionFactory()
    try:
        if session_token:
            token_hash = hashlib.sha256(session_token.encode()).hexdigest()
            row = await session.scalar(select(DashboardSession).where(DashboardSession.token_hash == token_hash).with_for_update())
            if row is not None:
                row.revoked_at = datetime.now(timezone.utc)
                await session.commit()
        response.delete_cookie(SESSION_COOKIE, path="/")
    finally:
        await session.close()


@router.get("/me")
async def me(session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE)) -> dict[str, object]:
    session = SessionFactory()
    try:
        user = await get_session_user(session, session_token)
        if user is None:
            raise HTTPException(401, "authentication_required")
        memberships = await session.execute(
            select(Tenant.id, Tenant.discord_guild_id, Tenant.name, TenantMembership.role)
            .join(TenantMembership, TenantMembership.tenant_id == Tenant.id)
            .where(TenantMembership.user_id == user.id, TenantMembership.active.is_(True), Tenant.active.is_(True))
            .order_by(Tenant.name)
        )
        return {
            "id": str(user.id),
            "discord_user_id": user.discord_user_id,
            "username": user.username,
            "global_name": user.global_name,
            "tenants": [
                {"id": str(row.id), "guild_id": row.discord_guild_id, "name": row.name, "role": row.role}
                for row in memberships
            ],
        }
    finally:
        await session.close()


def _allowed(role: str, minimum: str) -> bool:
    levels = {"VIEWER": 1, "OPERATOR": 2, "ADMIN": 3, "OWNER": 4}
    return levels.get(role, 0) >= levels[minimum]


async def tenant_context(tenant_id: str, session_token: str | None, minimum_role: str = "VIEWER"):
    try:
        tenant_uuid = __import__("uuid").UUID(tenant_id)
    except ValueError as exc:
        raise HTTPException(400, "invalid_tenant_id") from exc
    session = SessionFactory()
    user = await get_session_user(session, session_token)
    if user is None:
        await session.close()
        raise HTTPException(401, "authentication_required")
    membership = await session.scalar(
        select(TenantMembership).where(
            TenantMembership.tenant_id == tenant_uuid,
            TenantMembership.user_id == user.id,
            TenantMembership.active.is_(True),
        )
    )
    if membership is None or not _allowed(membership.role, minimum_role):
        await session.close()
        raise HTTPException(403, "tenant_access_denied")
    return session, user, membership, tenant_uuid
