from __future__ import annotations

import re
from typing import Any, Iterator

from sqlalchemy import create_engine, text

from . import config

engine = create_engine(config.DATABASE_URL, pool_size=config.DB_POOL_SIZE, max_overflow=10)


def _to_named(sql: str, params: tuple) -> tuple[str, dict]:
    counter = {"i": 0}

    def repl(_):
        key = f"p{counter['i']}"
        counter["i"] += 1
        return f":{key}"

    named_sql = re.sub(r"%s", repl, sql)
    return named_sql, {f"p{i}": v for i, v in enumerate(params)}


def get_conn() -> Iterator:
    with engine.connect() as conn:
        yield conn


def fetch_all(conn, sql: str, params=()) -> list[dict[str, Any]]:
    named_sql, named_params = _to_named(sql, tuple(params))
    result = conn.execute(text(named_sql), named_params)
    return [dict(row._mapping) for row in result]


def fetch_one(conn, sql: str, params=()) -> dict[str, Any] | None:
    rows = fetch_all(conn, sql, params)
    return rows[0] if rows else None
