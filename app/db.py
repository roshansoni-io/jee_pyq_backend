from __future__ import annotations

import hashlib
import sqlite3
from contextlib import contextmanager
from typing import Any, Iterator

from . import config


def _connect() -> sqlite3.Connection:
    """Open a read-only connection to the SQLite artifact.

    """
    conn = sqlite3.connect(
        f"file:{config.SQLITE_PATH}?mode=ro",
        uri=True,
        timeout=10.0,
        check_same_thread=False,
    )
    conn.row_factory = sqlite3.Row
    conn.create_function(
        "md5", 2, lambda a, b: hashlib.md5(f"{a}{b}".encode()).hexdigest()
    )
    return conn


def open_pool() -> None:
    """Kept for lifespan symmetry: verify the file opens (fail fast)."""
    if not config.SQLITE_PATH.is_file():
        raise RuntimeError(f"sqlite database not found: {config.SQLITE_PATH}")
    conn = _connect()
    try:
        conn.execute("select 1").fetchone()
    finally:
        conn.close()


def close_pool() -> None:
    return None


@contextmanager
def connection() -> Iterator[sqlite3.Connection]:
    conn = _connect()
    try:
        yield conn
    finally:
        conn.close()


def _translate(sql: str) -> str:
    # All queries in this codebase use %s only as parameter placeholders
    # (LIKE patterns live in the params, not the SQL), so a plain replace
    # is safe and keeps every call site unchanged.
    return sql.replace("%s", "?")


def fetch_all(conn, sql: str, params=()) -> list[dict[str, Any]]:
    cur = conn.execute(_translate(sql), tuple(params))
    try:
        return [dict(row) for row in cur.fetchall()]
    finally:
        cur.close()


def fetch_one(conn, sql: str, params=()) -> dict[str, Any] | None:
    cur = conn.execute(_translate(sql), tuple(params))
    try:
        row = cur.fetchone()
        return dict(row) if row is not None else None
    finally:
        cur.close()
