#!/data/data/com.termux/files/usr/bin/bash
# Detached launcher for the local PostgreSQL cluster, then for the API.
# Logs go to .local/log/: /tmp is wiped under this environment.
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd)"
PGDATA="${PYQ_PGDATA:-/data/data/com.termux/files/usr/var/lib/postgresql}"
LOGDIR="$HERE/.local/log"
mkdir -p "$LOGDIR"

if ! pg_isready -q -h 127.0.0.1 -p 5432 2>/dev/null; then
  pg_ctl -D "$PGDATA" -l "$LOGDIR/pg.log" start >/dev/null 2>&1 &
  for _ in $(seq 1 30); do
    pg_isready -q -h 127.0.0.1 -p 5432 2>/dev/null && break
    sleep 1
  done
fi

pg_isready -h 127.0.0.1 -p 5432 >/dev/null 2>&1 || { echo "postgres failed to start"; exit 1; }
echo "postgres ready"

if curl -sf -o /dev/null --max-time 3 http://127.0.0.1:8000/api/v1/health 2>/dev/null; then
  echo "api already up"
  exit 0
fi

cd "$HERE" || exit 1
setsid python3 -m app >"$LOGDIR/api.log" 2>&1 </dev/null &
echo "api starting -> $LOGDIR/api.log"