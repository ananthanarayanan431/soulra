import asyncio
import contextlib
import os
import sys
from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
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
from soulra.services import cache as job_cache


@contextlib.asynccontextmanager
async def lifespan(_app: FastAPI):
    configure_logging()
    logger.info("startup")
    job_cache.init_redis(settings.redis_url)

    import cohere as cohere_sdk
    from soulra.dependencies import set_cohere_client
    async with cohere_sdk.AsyncClient(api_key=settings.cohere_api_key) as _cohere:
        set_cohere_client(_cohere)

        # Run Alembic migrations (async — does not block the event loop)
        _fail_fast = os.getenv("MIGRATION_FAIL_FAST", "false").lower() == "true"
        try:
            proc = await asyncio.create_subprocess_exec(
                "alembic", "upgrade", "head",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd="/app",
            )
            _, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
            if proc.returncode and proc.returncode != 0:
                logger.error("alembic_failed", returncode=proc.returncode, stderr=stderr)
                if _fail_fast:
                    sys.exit(1)
        except Exception as e:
            logger.warning("alembic_skipped", reason=str(e))

        # Build LangGraph graph with Postgres checkpointer
        from soulra.dependencies import set_vectorstore, set_retriever
        try:
            from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
            from langchain_postgres import PGVector
            from soulra.dependencies import (
                get_embeddings,
                get_fast_llm,
                get_smart_llm,
                get_cohere_client,
            )
            from soulra.services.retrieval.retriever import WisdomRetriever
            from soulra.graph.builder import build_graph

            # Initialise PGVector and retriever here so they are bound to the
            # current event loop and not held in lru_cache across reloads.
            vs = PGVector(
                embeddings=get_embeddings(),
                collection_name="wisdom_passages",
                connection=settings.database_url,
            )
            retriever = WisdomRetriever(vectorstore=vs)
            set_vectorstore(vs)
            set_retriever(retriever)

            # AsyncPostgresSaver needs a sync-style postgres URL (no +asyncpg)
            sync_db_url = settings.database_url.replace("+asyncpg", "")
            async with AsyncPostgresSaver.from_conn_string(sync_db_url) as checkpointer:
                graph = build_graph(
                    retriever=retriever,
                    fast_llm=get_fast_llm(),
                    smart_llm=get_smart_llm(),
                    checkpointer=checkpointer,
                    cohere_client=get_cohere_client(),
                )
                set_graph(graph)
                logger.info("graph_ready")
                yield
        except Exception as e:
            logger.warning("graph_unavailable", reason=str(e))
            yield  # app starts without graph (WS returns SERVICE_UNAVAILABLE)
        finally:
            set_graph(None)
            set_vectorstore(None)
            set_retriever(None)
            await job_cache.close_redis()
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


_HTTP_CODE_MAP = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    409: "CONFLICT",
    413: "PAYLOAD_TOO_LARGE",
    422: "VALIDATION_ERROR",
    503: "SERVICE_UNAVAILABLE",
}


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException):
    code = _HTTP_CODE_MAP.get(exc.status_code, "HTTP_ERROR")
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=ErrorDetail(code=code, message=str(exc.detail))
        ).model_dump(),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request: Request, _exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            error=ErrorDetail(code="VALIDATION_ERROR", message="Request validation failed")
        ).model_dump(),
    )
