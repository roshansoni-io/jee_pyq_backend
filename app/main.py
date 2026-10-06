from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import config
from .db import engine
from .routes import router

logger = logging.getLogger("pyq")


def create_app() -> FastAPI:
    app = FastAPI(
        title="JEE PYQ API",
        version="1.0.0",
        docs_url="/docs",
        openapi_url="/openapi.json",
    )
    app.include_router(router)

    @app.middleware("http")
    async def db_conn(request: Request, call_next):
        conn = engine.connect()
        request.state.conn = conn
        try:
            return await call_next(request)
        finally:
            conn.close()

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
