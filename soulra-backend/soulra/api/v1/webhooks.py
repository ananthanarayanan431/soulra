from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from svix.webhooks import Webhook, WebhookVerificationError

from soulra.config import settings
from soulra.core.logging import logger
from soulra.database import get_db
from soulra.models.user import User

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _primary_email(data: dict) -> str:
    primary_id = data.get("primary_email_address_id")
    for entry in data.get("email_addresses", []):
        if entry.get("id") == primary_id:
            return entry.get("email_address", "")
    addresses = data.get("email_addresses") or []
    return addresses[0].get("email_address", "") if addresses else ""


def _full_name(data: dict) -> str | None:
    first = (data.get("first_name") or "").strip()
    last = (data.get("last_name") or "").strip()
    name = f"{first} {last}".strip()
    return name or None


@router.post("/clerk", include_in_schema=False)
async def clerk_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.body()
    headers = {
        "svix-id": request.headers.get("svix-id", ""),
        "svix-timestamp": request.headers.get("svix-timestamp", ""),
        "svix-signature": request.headers.get("svix-signature", ""),
    }

    wh = Webhook(settings.clerk_webhook_secret)
    try:
        payload = wh.verify(body, headers)
    except WebhookVerificationError as exc:
        raise HTTPException(status_code=400, detail="Invalid webhook signature") from exc

    event_type = payload.get("type")
    data = payload.get("data", {})

    if event_type in ("user.created", "user.updated"):
        user_id = data.get("id")
        if not user_id:
            raise HTTPException(status_code=400, detail="Missing user id")

        role = (data.get("public_metadata") or {}).get("role", "user")
        if role not in ("user", "admin"):
            role = "user"

        user = await db.get(User, user_id)
        if user is None:
            user = User(
                id=user_id,
                email=_primary_email(data),
                name=_full_name(data),
                role=role,
                token_limit=settings.default_token_limit,
                tokens_used=0,
                created_at=datetime.now(timezone.utc),
            )
            db.add(user)
        else:
            user.email = _primary_email(data) or user.email
            user.name = _full_name(data)
            user.role = role
        await db.commit()
        logger.info("clerk_webhook_user_synced", user_id=user_id, event_type=event_type)

    elif event_type == "user.deleted":
        user_id = data.get("id")
        if user_id:
            user = await db.get(User, user_id)
            if user is not None:
                await db.delete(user)
                await db.commit()
                logger.info("clerk_webhook_user_deleted", user_id=user_id)

    else:
        logger.info("clerk_webhook_ignored", event_type=event_type)

    return {"received": True}
