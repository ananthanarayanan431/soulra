from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/status")
async def status(db: AsyncSession = Depends(get_db)):
    db_ok = False
    passage_count = 0
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
        # langchain_pg_embedding may not exist in test DB — that's fine
        try:
            result = await db.execute(
                text("SELECT COUNT(*) FROM langchain_pg_embedding")
            )
            passage_count = result.scalar() or 0
        except Exception:
            passage_count = 0
    except Exception:
        pass

    return {
        "database": "ok" if db_ok else "error",
        "vector_store": {"passage_count": passage_count},
    }
