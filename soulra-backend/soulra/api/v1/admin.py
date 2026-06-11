from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from soulra.core.auth import require_admin
from soulra.core.logging import logger
from soulra.database import get_db
from soulra.models.user import LoginEvent, TokenUsageLog, User
from soulra.schemas.responses import PaginatedData, SuccessResponse
from soulra.schemas.user import LoginEventOut, TokenUsageOut, UserDetailOut, UserOut, UserUpdate

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])

RECENT_LIMIT = 20


def _login_event_out(event: LoginEvent, email: str) -> LoginEventOut:
    out = LoginEventOut.model_validate(event)
    out.user_email = email
    return out


def _token_usage_out(log: TokenUsageLog, email: str) -> TokenUsageOut:
    out = TokenUsageOut.model_validate(log)
    out.user_email = email
    return out


@router.get("/users", response_model=SuccessResponse[PaginatedData[UserOut]])
async def list_users(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    total = (await db.execute(select(func.count()).select_from(User))).scalar_one()
    rows = (
        (
            await db.execute(
                select(User).order_by(User.created_at.desc()).limit(limit).offset(offset)
            )
        )
        .scalars()
        .all()
    )
    return SuccessResponse(
        data=PaginatedData(
            items=[UserOut.model_validate(r) for r in rows],
            total=total,
            limit=limit,
            offset=offset,
        )
    )


@router.get("/users/{user_id}", response_model=SuccessResponse[UserDetailOut])
async def get_user(user_id: str, db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    logins = (
        (
            await db.execute(
                select(LoginEvent)
                .where(LoginEvent.user_id == user_id)
                .order_by(LoginEvent.created_at.desc())
                .limit(RECENT_LIMIT)
            )
        )
        .scalars()
        .all()
    )
    usage = (
        (
            await db.execute(
                select(TokenUsageLog)
                .where(TokenUsageLog.user_id == user_id)
                .order_by(TokenUsageLog.created_at.desc())
                .limit(RECENT_LIMIT)
            )
        )
        .scalars()
        .all()
    )

    detail = UserDetailOut(
        **UserOut.model_validate(user).model_dump(),
        recent_logins=[_login_event_out(e, user.email) for e in logins],
        recent_usage=[_token_usage_out(u, user.email) for u in usage],
    )
    return SuccessResponse(data=detail)


@router.patch("/users/{user_id}", response_model=SuccessResponse[UserOut])
async def update_user(
    user_id: str,
    body: UserUpdate,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_admin),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    changes = body.model_dump(exclude_unset=True)
    if "role" in changes and changes["role"] not in ("user", "admin"):
        raise HTTPException(status_code=422, detail="role must be 'user' or 'admin'")
    if "token_limit" in changes and changes["token_limit"] < 0:
        raise HTTPException(status_code=422, detail="token_limit must be >= 0")

    for field, value in changes.items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)
    logger.info("admin_user_updated", actor_id=actor.id, target_id=user.id, changes=changes)
    return SuccessResponse(data=UserOut.model_validate(user))


@router.get("/login-events", response_model=SuccessResponse[PaginatedData[LoginEventOut]])
async def list_login_events(
    user_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(LoginEvent, User.email).join(User, User.id == LoginEvent.user_id)
    count_stmt = select(func.count()).select_from(LoginEvent)
    if user_id:
        stmt = stmt.where(LoginEvent.user_id == user_id)
        count_stmt = count_stmt.where(LoginEvent.user_id == user_id)

    total = (await db.execute(count_stmt)).scalar_one()
    rows = (
        await db.execute(stmt.order_by(LoginEvent.created_at.desc()).limit(limit).offset(offset))
    ).all()
    items = [_login_event_out(event, email) for event, email in rows]
    return SuccessResponse(data=PaginatedData(items=items, total=total, limit=limit, offset=offset))


@router.get("/usage", response_model=SuccessResponse[PaginatedData[TokenUsageOut]])
async def list_token_usage(
    user_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(TokenUsageLog, User.email).join(User, User.id == TokenUsageLog.user_id)
    count_stmt = select(func.count()).select_from(TokenUsageLog)
    if user_id:
        stmt = stmt.where(TokenUsageLog.user_id == user_id)
        count_stmt = count_stmt.where(TokenUsageLog.user_id == user_id)

    total = (await db.execute(count_stmt)).scalar_one()
    rows = (
        await db.execute(stmt.order_by(TokenUsageLog.created_at.desc()).limit(limit).offset(offset))
    ).all()
    items = [_token_usage_out(log, email) for log, email in rows]
    return SuccessResponse(data=PaginatedData(items=items, total=total, limit=limit, offset=offset))
