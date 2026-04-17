#!/bin/sh
set -e
echo "Veritabani migrasyonu calistiriliyor..."
alembic upgrade head
echo "Migrasyon tamamlandi."
exec "$@"
