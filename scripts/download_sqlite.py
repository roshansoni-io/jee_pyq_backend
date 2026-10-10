"""Download the prebuilt SQLite database artifact.

    python3 scripts/download_sqlite.py
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from app.migrations import fetch_database  # noqa: E402

DB_URL = "https://example.com/pyq.sqlite3"
DB_PATH = REPO / "pyq.sqlite3"


def main() -> None:
    print(f"downloading {DB_URL}", flush=True)
    size = fetch_database(DB_URL, DB_PATH)
    print(f"saved {DB_PATH} ({size:,} bytes)", flush=True)


if __name__ == "__main__":
    main()
