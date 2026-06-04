import contextlib
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from soulra.config import settings
from soulra.core.exceptions import SoulraException
from soulra.schemas.responses import ErrorResponse, ErrorDetail
from soulra.core.logging import configure_logging, logger
from soulra.core.middleware import RequestIDMiddleware, TimingMiddleware
from soulra.api.v1.health import router as health_router
from soulra.api.v1.ingest import router as ingest_router
from soulra.api.v1.passages import router as passages_router
from soulra.api.v1.conversations import router as conversations_router
from soulra.api.websocket import router as ws_router, set_graph


@contextlib.asynccontextmanager
async def lifespan(_app: FastAPI):
    configure_logging()
    logger.info("startup")

    # Run Alembic migrations
    import subprocess
    try:
        subprocess.run(
            ["alembic", "upgrade", "head"],
            check=True,
            capture_output=True,
            cwd="/app",  # Docker working dir; fails gracefully outside Docker
        )
    except Exception as e:
        logger.warning("alembic_skipped", reason=str(e))

    # Build LangGraph graph with Postgres checkpointer
    try:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        from soulra.dependencies import get_retriever, get_fast_llm, get_smart_llm
        from soulra.graph.builder import build_graph

        # AsyncPostgresSaver needs a sync-style postgres URL (no +asyncpg)
        sync_db_url = settings.database_url.replace("+asyncpg", "")
        async with AsyncPostgresSaver.from_conn_string(sync_db_url) as checkpointer:
            graph = build_graph(
                retriever=get_retriever(),
                fast_llm=get_fast_llm(),
                smart_llm=get_smart_llm(),
                checkpointer=checkpointer,
            )
            set_graph(graph)
            logger.info("graph_ready")
            yield
    except Exception as e:
        logger.warning("graph_unavailable", reason=str(e))
        yield  # app starts without graph (WS returns SERVICE_UNAVAILABLE)
    finally:
        set_graph(None)
        logger.info("shutdown")


app = FastAPI(title="Soulra Backend", version="0.1.0", lifespan=lifespan)

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
app.include_router(ws_router)


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
        content=ErrorResponse(
            error=ErrorDetail(code=exc.code, message=exc.message)
        ).model_dump(),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=ErrorDetail(code="HTTP_ERROR", message=str(exc.detail))
        ).model_dump(),
    )
