from __future__ import annotations

import os


def _env(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    return value if value not in (None, "") else default


def _env_int(name: str, default: int) -> int:
    value = _env(name)
    return int(value) if value is not None else default


DB_USER = _env("PYQ_DB_USER", "u0_a320")
DB_NAME = _env("PYQ_DB_NAME", "pyq")
DB_HOST = _env("PYQ_DB_HOST", "127.0.0.1")
DB_PORT = _env("PYQ_DB_PORT", "5432")
DB_PASSWORD = _env("PYQ_DB_PASSWORD")
# Pool size per worker process.
DB_POOL_SIZE = _env_int("PYQ_DB_POOL_SIZE", 10)
DB_POOL_MAX_OVERFLOW = _env_int("PYQ_DB_POOL_MAX_OVERFLOW", 10)

# libpq conninfo string.
DATABASE_URL = _env(
    "PYQ_DATABASE_URL",
    f"postgresql://{DB_USER}{':' + DB_PASSWORD if DB_PASSWORD else ''}@{DB_HOST}:{DB_PORT}/{DB_NAME}",
)

SERVER_HOST = _env("PYQ_HOST", "0.0.0.0")
SERVER_PORT = int(_env("PYQ_PORT", "8000"))
# Single worker by default.
SERVER_WORKERS = _env_int("PYQ_WORKERS", 1)
