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
- Python 3.14 system packages: fastapi, uvicorn, psycopg, psycopg-pool, numpy, pgvector

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
| `PYQ_DATABASE_URL` | `postgresql://<user>[:<password>]@127.0.0.1:5432/pyq` (plain libpq conninfo) |
| `PYQ_DB_USER` / `PYQ_DB_NAME` / `PYQ_DB_HOST` / `PYQ_DB_PORT` / `PYQ_DB_PASSWORD` | `u0_a320` / `pyq` / `127.0.0.1` / `5432` / unset |
| `PYQ_DB_POOL_SIZE` / `PYQ_DB_POOL_MAX_OVERFLOW` | `10` / `10` |
| `PYQ_HOST` / `PYQ_PORT` / `PYQ_WORKERS` | `0.0.0.0` / `8000` / `1` |

Only real environment variables are read — nothing loads `.env`.

## Run the server

```bash
python3 -m app
```

Single worker by default (`PYQ_WORKERS`); the workload is CPU-bound on JSON
serialisation, so more workers measured no faster. Interactive docs:
http://localhost:8000/docs
