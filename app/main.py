from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager

from fastapi.exceptions import RequestValidationError
from fastapi import Depends, FastAPI, Request
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import config
from .db import close_pool, connection, open_pool
from .migrations import apply_migrations
from .api import router
from .api.errors import (
    ErrorCode,
    error_response,
    handle_http_error,
    handle_validation_error,
)

logger = logging.getLogger("pyq")


def get_conn(request: Request) -> Iterator:
    """Yield one read-only SQLite connection for the request.
    
    """
    with connection() as conn:
        request.state.conn = conn
        yield conn


@asynccontextmanager
async def _lifespan(_: FastAPI) -> AsyncIterator[None]:
    apply_migrations()
    open_pool()
    logger.info("pyq api ready: workers=%s sqlite=%s", config.SERVER_WORKERS, config.SQLITE_PATH)
    yield
    close_pool()


def create_app() -> FastAPI:
    app = FastAPI(
        title="JEE PYQ API",
        version="1.0.0",
        docs_url="/docs",
        openapi_url="/openapi.json",
        lifespan=_lifespan,
    )

    app.include_router(router, dependencies=[Depends(get_conn)])

    app.add_exception_handler(StarletteHTTPException, handle_http_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)

    @app.exception_handler(Exception)
    async def unhandled(_: Request, exc: Exception):
        logger.exception("unhandled error")
        return error_response(500, ErrorCode.INTERNAL_ERROR, "internal server error")

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=config.SERVER_HOST,
        port=config.SERVER_PORT,
        workers=config.SERVER_WORKERS,
        log_level="info",
    )
