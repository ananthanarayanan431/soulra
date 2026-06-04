from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.core.exceptions import SoulraException
from app.core.middleware import RequestIDMiddleware, TimingMiddleware
from app.api.v1.health import router as health_router
from app.api.v1.ingest import router as ingest_router
from app.api.v1.passages import router as passages_router
from app.api.v1.conversations import router as conversations_router

app = FastAPI(title="Soulra Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TimingMiddleware)
app.add_middleware(RequestIDMiddleware)

app.include_router(health_router, prefix="/api/v1")
app.include_router(ingest_router, prefix="/api/v1")
app.include_router(passages_router, prefix="/api/v1")
app.include_router(conversations_router, prefix="/api/v1")


_STATUS_MAP = {
    "NOT_FOUND": 404,
    "INGESTION_FAILED": 500,
    "RETRIEVAL_FAILED": 500,
    "INTERNAL_ERROR": 500,
}


@app.exception_handler(SoulraException)
async def soulra_exception_handler(_request: Request, exc: SoulraException):
    status_code = _STATUS_MAP.get(exc.code, 500)
    return JSONResponse(
        status_code=status_code,
        content={"type": exc.code, "message": exc.message},
    )
