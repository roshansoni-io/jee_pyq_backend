# JEE PYQ backend (FastAPI + PostgreSQL + pgvector)

Serves 14,973 JEE Main previous-year questions over HTTP. See `API.md` for the endpoint spec.

## Docker deployment

The Compose stack runs the API and PostgreSQL 18 with pgvector. The database
data lives in a named volume, and the API is bound to `127.0.0.1:8000` by
default. Host and port for both the API (`PYQ_HOST`, `PYQ_PORT`) and the
database connection (`PYQ_DB_HOST`, `PYQ_DB_PORT`) come from `.env` — nothing
is hardcoded in the Compose file or Dockerfile. Put a TLS reverse proxy in
front of it for public deployments.

```bash
cp .env.example .env
# Edit .env and replace POSTGRES_PASSWORD with a unique, strong secret.
docker compose up -d --build
docker compose ps
docker compose logs -f api
```

On a fresh database, Compose applies `schema.sql` automatically. The Postgres
image only runs init scripts when its data directory is empty. It does not
import question data: load the source dataset separately using the existing
loader workflow, and refresh aggregates afterward with
`scripts/refresh-question-stats.sql`. Existing databases are not overwritten.
The API applies pending SQL migrations during startup. A database advisory lock
prevents multiple workers or replicas from applying them at once, and successful
versions are recorded in `public.pyq_schema_migrations`. Manually applied
migrations are detected and adopted. The configured database role needs
permission to alter the schema and create extensions and indexes used by
migrations. Back up the database before deploying schema changes.
If a migration's data preconditions are not met, startup logs a warning and
leaves that migration pending rather than changing or deleting existing data.

`schema.sql` remains the complete bootstrap schema for a new database;
incremental changes belong in numbered files under `migrations/`.

Keep `.env` out of source control and use your hosting platform's secret store
for production credentials. The default loopback bind is suitable when a host
reverse proxy connects locally. If another machine or container must reach the
API, set `PYQ_BIND_ADDRESS` to the required interface and restrict access with
the host firewall or private network. Terminate TLS at a trusted reverse proxy.

Back up PostgreSQL regularly with `pg_dump` and store backups off-host. For
example, `docker compose exec -T db pg_dump -U pyq pyq > pyq.sql` writes a
logical backup on the host; adjust the role and database if changed in `.env`.
Restore into a compatible PostgreSQL 18 + pgvector instance. Keep the database
volume when upgrading or recreating containers; `docker compose down -v`
deletes it and permanently removes the database.

The API container runs as an unprivileged user, has a read-only root
filesystem, drops Linux capabilities, and checks database-backed health at
`/api/v1/health`. Pool limits are per worker: size the total across all API
replicas below PostgreSQL's connection limit. The default is one worker with a
pool of up to ten connections.

## Layout

- `app/` — FastAPI application (`main.py` entry point); endpoint routers are split by resource in `app/api/`
- `scripts/migrate_pkl_to_psql.py` — one-off loader from the old pkl cache into Postgres
- `schema.sql` — complete bootstrap schema for fresh databases
- `migrations/` — incremental schema changes applied at API startup
- `DATABASE_STRUCTURE.md` — intended schema and external database snapshot
- `API.md` — API reference

## Prerequisites

- PostgreSQL 18 running locally (socket dir `/data/data/com.termux/files/usr/tmp`, TCP 127.0.0.1:5432)
- pgvector extension available in the cluster
- Python 3.14 system packages: fastapi, uvicorn, psycopg, psycopg-pool, pgvector

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

Expected counts: 3 subjects, 91 chapters, 577 topic rows (486 named topics plus 91 empty-topic sentinels), 14973 questions, 14973 embeddings.

Fresh databases get the current schema from `schema.sql`, and the loader writes
dates, shifts, and chapter numbers. The API applies pending migrations before
opening its connection pool.

## Config (environment variables)

| var | default |
| --- | --- |
| `PYQ_DATABASE_URL` | `postgresql://<user>[:<password>]@127.0.0.1:5432/pyq` (plain libpq conninfo) |
| `PYQ_DB_USER` / `PYQ_DB_NAME` / `PYQ_DB_HOST` / `PYQ_DB_PORT` / `PYQ_DB_PASSWORD` | `u0_a320` / `pyq` / `127.0.0.1` / `5432` / unset |
| `PYQ_DB_POOL_SIZE` / `PYQ_DB_POOL_MAX_OVERFLOW` | `10` / `10` |
| `PYQ_HOST` / `PYQ_PORT` / `PYQ_WORKERS` | `0.0.0.0` / `8000` / `1` |

`.env` in the repo root is loaded at startup; real environment variables take
precedence. Inside Compose, `PYQ_DB_HOST`/`PYQ_DB_PORT` default to the `db`
service and `5432`; everywhere else they default to `127.0.0.1`/`5432`.

## Run the server

```bash
python3 -m app
```

Single worker by default (`PYQ_WORKERS`); the workload is CPU-bound on JSON
serialisation, so more workers measured no faster. Interactive docs:
http://localhost:8000/docs
