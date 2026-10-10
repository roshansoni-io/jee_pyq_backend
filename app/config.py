from __future__ import annotations

import os
from pathlib import Path

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_env_file(path: Path) -> None:
    """Overlay KEY=VALUE pairs from a dotenv file.
    
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key.startswith("export "):
            key = key[len("export ") :].strip()
        value = value.strip()
        if len(value) > 1 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if key and key not in os.environ:
            os.environ[key] = value


_load_env_file(ENV_FILE)


def _env(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    return value if value not in (None, "") else default


def _env_int(name: str, default: int) -> int:
    value = _env(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        raise RuntimeError(f"invalid integer for {name}: {value!r}") from None


# SQLite artifact served by the API. Fetch with scripts/download_sqlite.py.
_sqlite = _env("PYQ_SQLITE_PATH", "pyq.sqlite3")
SQLITE_PATH = (
    Path(_sqlite) if Path(_sqlite).is_absolute() else REPO_ROOT / _sqlite
)
# When the artifact is missing at startup, download it from here first.
SQLITE_URL = _env("PYQ_SQLITE_URL")

SERVER_HOST = _env("PYQ_HOST", "0.0.0.0")
SERVER_PORT = _env_int("PYQ_PORT", 8000)
# Single worker by default.
SERVER_WORKERS = _env_int("PYQ_WORKERS", 1)
