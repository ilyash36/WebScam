#!/bin/bash
set -e

# Ждём PostgreSQL только если DB_HOST установлен
if [ -n "$DB_HOST" ] && [ "$DB_HOST" != "localhost" ] && [ "$DB_HOST" != "127.0.0.1" ]; then
    echo "Waiting for PostgreSQL at $DB_HOST:$DB_PORT..."
    while ! nc -z "$DB_HOST" "$DB_PORT"; do
        sleep 0.1
    done
    echo "PostgreSQL started"
fi

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput || true

# Создаём суперпользователя только в development режиме
if [ "$DEBUG" = "True" ] || [ "$DEBUG" = "true" ]; then
    echo "Creating superuser if needed..."
    python manage.py shell << 'EOF' || true
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin')
    print('Superuser created: admin/admin')
else:
    print('Superuser already exists')
EOF
fi

exec "$@"
