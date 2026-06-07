import logging
import os
import warnings

import structlog

# LangChain fires this on every structured-output call — it's cosmetic noise
# from Pydantic's internal serialiser, not an application error.
_SUPPRESS = [
    "Pydantic serializer warnings",
    "PydanticSerializationUnexpectedValue",
]


def configure_logging() -> None:
    for msg in _SUPPRESS:
        warnings.filterwarnings("ignore", message=msg)

    log_format = os.getenv("LOG_FORMAT", "pretty")

    shared: list = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(
            fmt="%H:%M:%S" if log_format == "pretty" else "iso"
        ),
    ]

    if log_format == "json":
        processors = shared + [structlog.processors.JSONRenderer()]
    else:
        processors = shared + [structlog.dev.ConsoleRenderer(colors=True)]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )

    # TimingMiddleware already emits request_handled with method/path/status/ms —
    # suppress the duplicate uvicorn per-request access line.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


logger = structlog.get_logger()
