from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from . import config

pool = ConnectionPool(
    conninfo=config.DATABASE_URL,
    min_size=config.DB_POOL_SIZE,
    max_size=config.DB_POOL_SIZE + config.DB_POOL_MAX_OVERFLOW,
    open=False,
    kwargs={"row_factory": dict_row},
)


def open_pool() -> None:
    """Open the pool and wait for `min_size` connections; a timeout is ignored."""
    pool.open()
    try:
        pool.wait(timeout=15.0)
    except Exception:  # pragma: no cover - startup convenience only
        pass


def close_pool() -> None:
    pool.close()


@contextmanager
def connection() -> Iterator[psycopg.Connection]:
    with pool.connection() as conn:
        yield conn


def fetch_all(conn, sql: str, params=()) -> list[dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(sql, tuple(params))
        if cur.description is None:
            return []
        return cur.fetchall()


def fetch_one(conn, sql: str, params=()) -> dict[str, Any] | None:
    with conn.cursor() as cur:
        cur.execute(sql, tuple(params))
        if cur.description is None:
            return None
        return cur.fetchone()
