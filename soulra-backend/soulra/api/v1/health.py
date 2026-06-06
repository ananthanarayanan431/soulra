from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from soulra.database import get_db
from soulra.schemas.responses import SuccessResponse
from soulra.services import cache as job_cache

router = APIRouter(tags=["health"])


class HealthData(BaseModel):
    status: str


class StatusData(BaseModel):
    database: str
    redis: str
    vector_store: dict


@router.get("/health", response_model=SuccessResponse[HealthData])
async def health():
    return SuccessResponse(data=HealthData(status="ok"))


@router.get("/status", response_model=SuccessResponse[StatusData])
async def status(db: AsyncSession = Depends(get_db)):
    db_ok = False
    passage_count = 0
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
        try:
            result = await db.execute(text("SELECT COUNT(*) FROM langchain_pg_embedding"))
            passage_count = result.scalar() or 0
        except Exception:
            passage_count = 0
    except Exception:
        pass

    redis_ok = False
    try:
        await job_cache.get_redis().ping()
        redis_ok = True
    except Exception:
        pass

    return SuccessResponse(data=StatusData(
        database="ok" if db_ok else "error",
        redis="ok" if redis_ok else "error",
        vector_store={"passage_count": passage_count},
    ))
