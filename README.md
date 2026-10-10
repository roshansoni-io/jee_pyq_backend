# JEE PYQ backend (FastAPI + SQLite)

Serves 14,973 JEE Main previous-year questions over HTTP. See `API.md` for the endpoint spec.

## Setup

Fetch the prebuilt database (a fixed URL and filename, no configuration):

```bash
python3 scripts/download_sqlite.py
```

This saves `pyq.sqlite3` in the repo root. The file is gitignored; each
deploy fetches it once. To build a new database URL, edit `DB_URL` in
`scripts/download_sqlite.py`.

If `pyq.sqlite3` is missing at startup and `PYQ_SQLITE_URL` is set, the server
downloads it automatically before serving.

## Docker deployment

```bash
cp .env.example .env
docker build -t pyq .
docker run --rm -p 127.0.0.1:8000:8000 \
  -v "$PWD/pyq.sqlite3:/app/pyq.sqlite3:ro" pyq
```

Put a TLS reverse proxy in front of it for public deployments.

Keep `.env` out of source control and use your hosting platform's secret store
for production configuration. The default loopback bind is suitable when a host
reverse proxy connects locally. If another machine or container must reach the
API, set `PYQ_BIND_ADDRESS` to the required interface and restrict access with
the host firewall or private network. Terminate TLS at a trusted reverse proxy.

Back up `pyq.sqlite3` regularly and store copies off-host; it is a single
file, so a plain copy is a complete backup.

The API container runs as an unprivileged user, has a read-only root
filesystem, drops Linux capabilities, and checks database-backed health at
`/api/v1/health`.

## Layout

- `app/` — FastAPI application (`main.py` entry point); endpoint routers are split by resource in `app/api/`
- `scripts/download_sqlite.py` — fetches the prebuilt `pyq.sqlite3` artifact
- `pyq.sqlite3` — SQLite database (gitignored, fetched at deploy time)
- `API.md` — API reference

## Prerequisites

- Python 3.12+ with `fastapi` and `uvicorn` (`pip install -r requirements.txt`)
- `pyq.sqlite3` in the repo root (see Setup)

Expected counts: 3 subjects, 91 chapters, 577 topic rows, 14973 questions.

## Config (environment variables)

| var | default |
| --- | --- |
| `PYQ_SQLITE_PATH` | `./pyq.sqlite3` |
| `PYQ_SQLITE_URL` | unset (auto-download source when the file is missing) |
| `PYQ_HOST` / `PYQ_PORT` / `PYQ_WORKERS` | `0.0.0.0` / `8000` / `1` |

`.env` in the repo root is loaded at startup; real environment variables take
precedence.

## Run the server

```bash
python3 -m app
```

Single worker by default (`PYQ_WORKERS`); the workload is CPU-bound on JSON
serialisation, so more workers measured no faster. Interactive docs:
http://localhost:8000/docs
