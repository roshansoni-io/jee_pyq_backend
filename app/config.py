from __future__ import annotations

import os


def _env(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    return value if value not in (None, "") else default


DB_USER = _env("PYQ_DB_USER", "u0_a320")
DB_NAME = _env("PYQ_DB_NAME", "pyq")
DB_HOST = _env("PYQ_DB_HOST", "127.0.0.1")
DB_PORT = _env("PYQ_DB_PORT", "5432")
DB_PASSWORD = _env("PYQ_DB_PASSWORD")
DB_POOL_SIZE = int(_env("PYQ_DB_POOL_SIZE", "5"))

DATABASE_URL = _env(
    "PYQ_DATABASE_URL",
    f"postgresql+psycopg://{DB_USER}{':' + DB_PASSWORD if DB_PASSWORD else ''}@{DB_HOST}:{DB_PORT}/{DB_NAME}",
)

SERVER_HOST = _env("PYQ_HOST", "0.0.0.0")
SERVER_PORT = int(_env("PYQ_PORT", "8000"))
SERVER_WORKERS = int(_env("PYQ_WORKERS", "1"))
