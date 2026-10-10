from __future__ import annotations

import os
from pathlib import Path

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


def _load_env_file(path: Path) -> None:
    """Overlay KEY=VALUE pairs from a dotenv file. Real environment variables
    always win, so exported values and container env keep precedence."""
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
SERVER_PORT = _env_int("PYQ_PORT", 8000)
# Single worker by default.
SERVER_WORKERS = _env_int("PYQ_WORKERS", 1)
