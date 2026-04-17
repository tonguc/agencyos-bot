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
echo "=== Starting uvicorn on port ${PORT:-8000} ==="
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}" --log-level debug
