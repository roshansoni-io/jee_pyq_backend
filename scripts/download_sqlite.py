
from __future__ import annotations

import sys
from pathlib import Path

# Resolve the repository root so we can import from the `app` package
REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from app.migrations import fetch_database 

DB_URL = "https://github.com/roshansoni-io/jee_pyq_backend/releases/download/v1.0/pyq.sqlite3"
DB_PATH = REPO / "pyq.sqlite3"


def main() -> None:
    # Skip if the file is already present
    if DB_PATH.is_file():
        print(f"{DB_PATH} already exists, skipping download.", flush=True)
        return

    print(f"downloading {DB_URL}", flush=True)
    size = fetch_database(DB_URL, DB_PATH)
    print(f"saved {DB_PATH} ({size:,} bytes)", flush=True)


if __name__ == "__main__":
    main()