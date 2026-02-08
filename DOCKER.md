# Docker инструкции

## Быстрый старт

### Разработка

1. Создайте файл `.env` на основе `.env.example`:
```bash
cp .env.example .env
```

2. Запустите контейнеры:
```bash
docker-compose -f docker-compose.dev.yml up --build
```

3. Откройте браузер: http://localhost:8000/

4. Админ-панель: http://localhost:8000/admin/
   - Логин: `admin`
   - Пароль: `admin` (создаётся автоматически при первом запуске)

### Production

1. Настройте `.env` файл для production:
```bash
DEBUG=False
SECRET_KEY=your-production-secret-key
DB_NAME=autoservice_db
DB_USER=postgres
DB_PASSWORD=strong-password
```

2. Запустите контейнеры:
```bash
docker-compose up --build -d
```

3. Проверьте логи:
```bash
docker-compose logs -f web
```

## Команды

### Разработка

```bash
# Запуск в фоне
docker-compose -f docker-compose.dev.yml up -d

# Просмотр логов
docker-compose -f docker-compose.dev.yml logs -f web

# Остановка
docker-compose -f docker-compose.dev.yml down

# Пересборка
docker-compose -f docker-compose.dev.yml up --build

# Выполнение команд Django
docker-compose -f docker-compose.dev.yml exec web python manage.py migrate
docker-compose -f docker-compose.dev.yml exec web python manage.py createsuperuser
docker-compose -f docker-compose.dev.yml exec web python manage.py shell
```

### Production

```bash
# Запуск
docker-compose up -d

# Остановка
docker-compose down

# Просмотр логов
docker-compose logs -f web

# Выполнение команд
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py collectstatic --noinput
```

## Структура

- `Dockerfile` - образ для production
- `Dockerfile.dev` - образ для разработки
- `docker-compose.yml` - конфигурация для production
- `docker-compose.dev.yml` - конфигурация для разработки
- `docker-entrypoint.sh` - скрипт инициализации

## Переменные окружения

Все переменные из `.env` файла автоматически загружаются в контейнеры.

Важные переменные:
- `DEBUG` - режим отладки (True для dev, False для prod)
- `SECRET_KEY` - секретный ключ Django
- `DB_HOST` - хост базы данных (автоматически `db` в Docker)
- `DB_NAME`, `DB_USER`, `DB_PASSWORD` - настройки БД

## Volumes

- `postgres_data` - данные PostgreSQL
- `static_volume` - статические файлы
- `media_volume` - медиа файлы

## Troubleshooting

### Проблемы с миграциями

```bash
docker-compose exec web python manage.py makemigrations
docker-compose exec web python manage.py migrate
```

### Проблемы со статикой

```bash
docker-compose exec web python manage.py collectstatic --noinput
```

### Пересоздание базы данных

```bash
docker-compose down -v
docker-compose up --build
```

### Просмотр логов

```bash
docker-compose logs web
docker-compose logs db
```

### Windows: ошибка «exec /docker-entrypoint.sh: no such file or directory»

На Windows скрипт `docker-entrypoint.sh` может иметь окончания строк CRLF. В `Dockerfile.dev` используется `dos2unix` для преобразования в Unix-формат (LF) при сборке образа. Убедитесь, что образ пересобран: `docker-compose -f docker-compose.dev.yml up --build -d`.
