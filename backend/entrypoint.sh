#!/bin/sh
echo "=== ENTRYPOINT STARTED ==="
echo "PORT=${PORT}"
echo "DATABASE_URL prefix: $(echo $DATABASE_URL | cut -c1-30)"
echo "REDIS_URL prefix: $(echo $REDIS_URL | cut -c1-30)"
echo "=== Running alembic ==="
alembic upgrade head
EXIT_CODE=$?
echo "=== Alembic exit code: $EXIT_CODE ==="
if [ $EXIT_CODE -ne 0 ]; then
  echo "ALEMBIC FAILED"
  exit 1
fi
echo "=== Starting ARQ worker in background ==="
arq jobs.worker.WorkerSettings &
WORKER_PID=$!
echo "=== Starting uvicorn on port ${PORT:-8000} ==="
uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}" --log-level info
kill $WORKER_PID 2>/dev/null
