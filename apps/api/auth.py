from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.auth.service import begin_oauth, consume_state, create_session, discord_identity, exchange_code, get_session_user, oauth_authorize_url, upsert_identity
from packages.database.session import SessionFactory
from packages.auth.models import DashboardSession, Tenant, TenantMembership

router = APIRouter(prefix="/api/v1/auth/discord", tags=["auth"])

SESSION_COOKIE = "commerce_session"


async def db() -> AsyncSession:
    return SessionFactory()


async def current_context(session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE)):
    session = SessionFactory()
    try:
        user = await get_session_user(session, session_token)
        if user is None:
            raise HTTPException(401, "authentication_required")
        return session, user
    except Exception:
        await session.close()
        raise


@router.get("/login")
async def login() -> Response:
    session = SessionFactory()
    try:
        async with session.begin():
            state = await begin_oauth(session)
        return Response(content=oauth_authorize_url(state), media_type="text/plain", headers={"Cache-Control": "no-store"})
    finally:
        await session.close()


@router.get("/callback")
async def callback(code: str, state: str, response: Response) -> dict[str, object]:
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
        response.set_cookie(SESSION_COOKIE, session_token, max_age=604800, httponly=True, secure=True, samesite="lax", path="/")
        return {"authenticated": True, "user_id": str(user.id)}
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
            row = await session.scalar(select(DashboardSession).where(DashboardSession.token_hash == __import__("hashlib").sha256(session_token.encode()).hexdigest()).with_for_update())
            if row is not None:
                row.revoked_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
                await session.commit()
        response.delete_cookie(SESSION_COOKIE, path="/")
    finally:
        await session.close()


async def require_member(
    tenant_id: str,
    session_token: str | None,
) -> tuple[AsyncSession, object, TenantMembership]:
    session = SessionFactory()
    user = await get_session_user(session, session_token)
    if user is None:
        await session.close()
        raise HTTPException(401, "authentication_required")
    membership = await session.scalar(select(TenantMembership).join(Tenant, Tenant.id == TenantMembership.tenant_id).where(Tenant.id == tenant_id, TenantMembership.user_id == user.id, TenantMembership.active.is_(True), Tenant.active.is_(True)))
    if membership is None:
        await session.close()
        raise HTTPException(403, "tenant_access_denied")
    return session, user, membership


@router.get("/me")
async def me(session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE)) -> dict[str, object]:
    session = SessionFactory()
    try:
        user = await get_session_user(session, session_token)
        if user is None:
            raise HTTPException(401, "authentication_required")
        memberships = await session.execute(select(Tenant.id, Tenant.discord_guild_id, Tenant.name, TenantMembership.role).join(TenantMembership, TenantMembership.tenant_id == Tenant.id).where(TenantMembership.user_id == user.id, TenantMembership.active.is_(True), Tenant.active.is_(True)).order_by(Tenant.name))
        return {"id": str(user.id), "discord_user_id": user.discord_user_id, "username": user.username, "global_name": user.global_name, "tenants": [{"id": str(row.id), "guild_id": row.discord_guild_id, "name": row.name, "role": row.role} for row in memberships]}
    finally:
        await session.close()
