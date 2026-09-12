#!/bin/sh
set -eu

echo "Running migrations"
alembic upgrade head

WORKER_PID=""
API_PID=""
cleanup() {
  [ -z "$WORKER_PID" ] || kill "$WORKER_PID" 2>/dev/null || true
  [ -z "$API_PID" ] || kill "$API_PID" 2>/dev/null || true
  wait 2>/dev/null || true
}
trap cleanup EXIT
trap 'exit 0' INT TERM

# Compose has a separate worker; a single-container deployment embeds one.
if [ "${RUN_EMBEDDED_WORKER:-1}" = "1" ]; then
  arq jobs.worker.WorkerSettings &
  WORKER_PID=$!
fi
uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}" --log-level info &
API_PID=$!

while kill -0 "$API_PID" 2>/dev/null; do
  if [ -n "$WORKER_PID" ] && ! kill -0 "$WORKER_PID" 2>/dev/null; then
    echo "ARQ worker exited; stopping container for restart" >&2
    exit 1
  fi
  sleep 2
done
wait "$API_PID"
