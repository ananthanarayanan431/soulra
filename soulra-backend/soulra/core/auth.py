from datetime import datetime, timedelta, timezone
from functools import lru_cache

import jwt
from jwt import PyJWKClient
from fastapi import Depends, HTTPException, Request, WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from soulra.config import settings
from soulra.database import get_db
from soulra.models.user import LoginEvent, User

LOGIN_EVENT_DEDUPE_WINDOW = timedelta(minutes=30)


@lru_cache
def _get_jwk_client() -> PyJWKClient:
    return PyJWKClient(settings.clerk_jwks_url)


def verify_clerk_token(token: str) -> dict:
    """Verify a Clerk session JWT and return its claims. Raises 401 on failure."""
    try:
        signing_key = _get_jwk_client().get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc
    return claims


async def _get_or_create_user(
    db: AsyncSession, claims: dict, ip_address: str | None, user_agent: str | None
) -> User:
    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token missing subject")

    email = claims.get("email") or ""
    name = claims.get("name")
    now = datetime.now(timezone.utc)

    user = await db.get(User, user_id)
    if user is None:
        user = User(
            id=user_id,
            email=email,
            name=name,
            role="user",
            token_limit=settings.default_token_limit,
            tokens_used=0,
            created_at=now,
            last_login_at=now,
        )
        db.add(user)
        await db.flush()
        db.add(
            LoginEvent(
                user_id=user.id,
                event_type="signup",
                ip_address=ip_address,
                user_agent=user_agent,
            )
        )
        return user

    if email and user.email != email:
        user.email = email

    if user.last_login_at is None or now - user.last_login_at > LOGIN_EVENT_DEDUPE_WINDOW:
        db.add(
            LoginEvent(
                user_id=user.id,
                event_type="login",
                ip_address=ip_address,
                user_agent=user_agent,
            )
        )
    user.last_login_at = now
    return user


async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    auth_header = request.headers.get("authorization", "")
    if not auth_header.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = auth_header[len("bearer ") :]
    claims = verify_clerk_token(token)
    return await _get_or_create_user(
        db,
        claims,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


async def get_current_user_ws(websocket: WebSocket, db: AsyncSession) -> User | None:
    """Like get_current_user but for WS connections (token via ?token= query param)."""
    token = websocket.query_params.get("token")
    if not token:
        return None
    try:
        claims = verify_clerk_token(token)
        return await _get_or_create_user(
            db,
            claims,
            ip_address=websocket.client.host if websocket.client else None,
            user_agent=websocket.headers.get("user-agent"),
        )
    except HTTPException:
        return None


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
