from __future__ import annotations

import logging
import os
import shutil
import sqlite3
import urllib.request
from pathlib import Path

from . import config

logger = logging.getLogger("pyq.migrations")

REQUIRED_TABLES = (
    "subjects",
    "chapters",
    "topics",
    "questions",
    "question_stats",
)


def fetch_database(url: str, dest: Path) -> int:
    """Download the SQLite artifact to `dest` atomically. Returns its size."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".sqlite3.download")
    tmp.unlink(missing_ok=True)
    with urllib.request.urlopen(url, timeout=60) as response, open(tmp, "wb") as out:
        shutil.copyfileobj(response, out, length=1024 * 256)
    with open(tmp, "rb") as check:
        if check.read(16) != b"SQLite format 3\x00":
            tmp.unlink()
            raise RuntimeError(f"downloaded file from {url} is not a SQLite database")
    os.replace(tmp, dest)
    return dest.stat().st_size


def apply_migrations() -> None:
    """Preflight for SQLite serving: ensure the artifact, then verify it.

    If `pyq.sqlite3` is missing and `PYQ_SQLITE_URL` is set, the database is
    downloaded first — a fresh deploy boots with no manual steps. Otherwise
    fail fast with a clear message.
    """
    if not config.SQLITE_PATH.is_file():
        if not config.SQLITE_URL:
            raise RuntimeError(
                f"sqlite database not found: {config.SQLITE_PATH} "
                "(set PYQ_SQLITE_URL or run python3 scripts/download_sqlite.py)"
            )
        logger.info("sqlite database missing, downloading from %s", config.SQLITE_URL)
        size = fetch_database(config.SQLITE_URL, config.SQLITE_PATH)
        logger.info("downloaded sqlite database: %s (%,d bytes)", config.SQLITE_PATH, size)
    conn = sqlite3.connect(f"file:{config.SQLITE_PATH}?mode=ro", uri=True)
    try:
        tables = {
            r[0]
            for r in conn.execute("select name from sqlite_master where type = 'table'")
        }
    finally:
        conn.close()
    missing = [t for t in REQUIRED_TABLES if t not in tables]
    if missing:
        raise RuntimeError(
            f"sqlite database {config.SQLITE_PATH} is missing tables: {missing} "
            "(fetch a fresh copy with python3 scripts/download_sqlite.py)"
        )
    logger.info("sqlite database ready: %s", config.SQLITE_PATH)
