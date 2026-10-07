from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager

import psycopg
from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import config
from .db import close_pool, open_pool, pool
from .routes import router

logger = logging.getLogger("pyq")


def get_conn(request: Request) -> Iterator[psycopg.Connection]:
    """Yield one pooled connection for the request. Sync, so the checkout runs
    in the threadpool instead of on the event loop."""
    with pool.connection() as conn:
        request.state.conn = conn
        yield conn


@asynccontextmanager
async def _lifespan(_: FastAPI) -> AsyncIterator[None]:
    open_pool()
    logger.info(
        "pyq api ready: workers=%s pool_size=%s max_overflow=%s",
        config.SERVER_WORKERS,
        config.DB_POOL_SIZE,
        config.DB_POOL_MAX_OVERFLOW,
    )
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
    # No compression middleware: bulk responses travel over loopback to the
    # server-side loaders, so compressing them costs CPU for no saved bandwidth.
    # The dependency sits on the router, leaving /docs usable without a database.
    app.include_router(router, dependencies=[Depends(get_conn)])

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.status_code, "message": str(exc.detail)}},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={"error": {"code": 422, "message": str(exc.errors()[0]["msg"]) if exc.errors() else "invalid request"}},
        )

    @app.exception_handler(Exception)
    async def unhandled(_: Request, exc: Exception):
        logger.exception("unhandled error")
        return JSONResponse(
            status_code=500,
            content={"error": {"code": 500, "message": "internal server error"}},
        )

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
