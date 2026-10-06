# JEE PYQ backend (FastAPI + PostgreSQL + pgvector)

Serves 14,973 JEE Main previous-year questions over HTTP. See `API.md` for the endpoint spec.

## Layout

- `app/` — FastAPI application (`main.py` entry point)
- `scripts/migrate_pkl_to_psql.py` — one-off loader from the old pkl cache into Postgres
- `schema.sql` — tables, indexes, pgvector extension
- `API.md` — API reference

## Prerequisites

- PostgreSQL 18 running locally (socket dir `/data/data/com.termux/files/usr/tmp`, TCP 127.0.0.1:5432)
- pgvector extension available in the cluster
- Python 3.14 system packages: fastapi, uvicorn, sqlalchemy, psycopg, numpy, pgvector

Start Postgres:

```bash
pg_ctl -D /data/data/com.termux/files/usr/var/lib/postgresql -l /data/data/com.termux/files/usr/tmp/pg.log start
```

Stop Postgres:

```bash
pg_ctl -D /data/data/com.termux/files/usr/var/lib/postgresql stop
```

## One-time database setup

```bash
psql -d postgres -c "create database pyq"
psql -d pyq -f schema.sql
python3 scripts/migrate_pkl_to_psql.py
```

Expected counts: 3 subjects, 91 chapters, 486 topics, 14973 questions, 14973 embeddings.

## Config (environment variables)

| var | default |
| --- | --- |
| `PYQ_DATABASE_URL` | `postgresql+psycopg://u0_a320@127.0.0.1:5432/pyq` |
| `PYQ_DB_USER` / `PYQ_DB_NAME` / `PYQ_DB_HOST` / `PYQ_DB_PORT` / `PYQ_DB_PASSWORD` | `u0_a320` / `pyq` / `127.0.0.1` / `5432` / unset |
| `PYQ_DB_POOL_SIZE` | `5` |
| `PYQ_HOST` / `PYQ_PORT` / `PYQ_WORKERS` | `0.0.0.0` / `8000` / `1` |

## Run the server

Development:

```bash
python3 -m app  # dev: PYQ_WORKERS=1, for reload use uvicorn directly
```

Production:

```bash
PYQ_WORKERS=2 python3 -m app
```

Interactive docs: http://localhost:8000/docs
