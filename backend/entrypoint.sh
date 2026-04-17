#!/bin/sh
set -e
echo "Veritabani migrasyonu calistiriliyor..."
alembic upgrade head
echo "Migrasyon tamamlandi."
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"
