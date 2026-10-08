#!/data/data/com.termux/files/usr/bin/bash
# Detached launcher for the PostgreSQL cluster, then for the API.
# Host/port come from app/config.py (real env vars, then .env) — nothing here
# is hardcoded. Logs go to .local/log/: /tmp is wiped under this environment.
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd)"
PGDATA="${PYQ_PGDATA:-/data/data/com.termux/files/usr/var/lib/postgresql}"
LOGDIR="$HERE/.local/log"
mkdir -p "$LOGDIR"

DB_HOST=""
DB_PORT=""
API_HOST=""
API_PORT=""
read -r DB_HOST DB_PORT API_HOST API_PORT < <(
  cd "$HERE" && python3 -c \
    'from app import config; print(config.DB_HOST, config.DB_PORT, config.SERVER_HOST, config.SERVER_PORT)'
)
if [ -z "$DB_HOST" ] || [ -z "$DB_PORT" ]; then
  echo "could not read db host/port from config" >&2
  exit 1
fi
case "$API_HOST" in
  0.0.0.0 | "::" | "") API_HOST="127.0.0.1" ;;
esac

case "$DB_HOST" in
  127.0.0.1 | localhost | ::1)
    if ! pg_isready -q -h "$DB_HOST" -p "$DB_PORT" 2>/dev/null; then
      pg_ctl -D "$PGDATA" -l "$LOGDIR/pg.log" start >/dev/null 2>&1 &
      for _ in $(seq 1 30); do
        pg_isready -q -h "$DB_HOST" -p "$DB_PORT" 2>/dev/null && break
        sleep 1
      done
    fi
    ;;
esac

pg_isready -h "$DB_HOST" -p "$DB_PORT" >/dev/null 2>&1 ||
  { echo "postgres not reachable at $DB_HOST:$DB_PORT"; exit 1; }
echo "postgres ready ($DB_HOST:$DB_PORT)"

if curl -sf -o /dev/null --max-time 3 "http://$API_HOST:$API_PORT/api/v1/health" 2>/dev/null; then
  echo "api already up"
  exit 0
fi

cd "$HERE" || exit 1
setsid python3 -m app >"$LOGDIR/api.log" 2>&1 </dev/null &
echo "api starting on $API_HOST:$API_PORT -> $LOGDIR/api.log"
