# Chernyavskiy A-Tech

Цифровой «мозг» автосервиса — CRM-платформа с поэтапным развитием.

## Этапы развития

1. **Сайт и витрина** (текущий этап — расширенный)
   - Лендинг/сайт автосервиса
   - Формы записи (OCR СТС; объём в л и мощность обязательны) и обратной связи
   - Passwordless авторизация (вход по коду из email); подтверждение email и SMTP — см. [SETUP.md](./SETUP.md)
   - Личный кабинет клиента (профиль, авто, история заявок)
   - Проверка конфликтов email/VIN, мягкая деактивация аккаунтов

2. **CRM и учёт** (будущее)
   - Полноценная CRM система
   - Внутренние кабинеты для сотрудников
   - Отчёты и аналитика

3. **Автоматизация и боты** (будущее)
   - Интеграция с n8n
   - Боты для Telegram/WhatsApp
   - Автоматизация маркетинга

## Технологии

- Python 3.11+
- Django 5.0+
- PostgreSQL (production)
- SQLite (development)
- OCR СТС/ПТС: Yandex Vision API + локальный парсер (`sts_parser.py`; ПТС/СТС, литры/см³→л); регрессия: `python scripts/test_sts_parser.py` (кэши `scripts/_ocr_raw_*.json`)

## Установка

1. Создайте виртуальное окружение:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Создайте файл `.env` в корне проекта (см. пример в `.env.example`):
```bash
# Windows PowerShell
Copy-Item .env.example .env

# Linux/Mac
cp .env.example .env
```

Откройте `.env` и заполните:
- `SECRET_KEY` (можно сгенерировать командой ниже)
- `YANDEX_VISION_API_KEY` и `YANDEX_FOLDER_ID` — для распознавания СТС на странице записи
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

4. Примените миграции:
```bash
python manage.py migrate
```

5. Создайте суперпользователя:
```bash
python manage.py createsuperuser
```

6. Запустите сервер разработки:
```bash
python manage.py runserver
```

## Docker

Проект готов к запуску через Docker. Подробные инструкции в [DOCKER.md](./DOCKER.md).

### Быстрый старт с Docker:

```bash
# Разработка
docker-compose -f docker-compose.dev.yml up --build

# Production
docker-compose up --build -d
```

## Разработка

### Проверка качества кода

Установите инструменты разработки:
```bash
pip install -r requirements-dev.txt
```

Проверка кода:
```bash
make lint      # Проверить код линтерами
make format    # Отформатировать код
make check     # Проверить форматирование без изменений
```

Или вручную:
```bash
flake8 .       # Проверка стиля кода
black .         # Форматирование кода
isort .         # Сортировка импортов
mypy .          # Проверка типов
```

## Документация

**Канонический порядок чтения** (перенос контекста в другую IDE / чат / модель) — подробно в [AI_CONTEXT.md](./AI_CONTEXT.md) §1:

1. [AI_CONTEXT.md](./AI_CONTEXT.md) — точка входа: индекс, снимок, URL, устаревшее
2. [PHILOSOPHY.md](./PHILOSOPHY.md) — философия и этапы продукта
3. [CLAUDE.md](./CLAUDE.md) — полная техническая документация
4. [.cursor/dev_cache.md](./.cursor/dev_cache.md) — сжатый кэш и хронология решений
5. [SETUP.md](./SETUP.md) — установка, почта, SMTP, ручное подтверждение email
6. [DOCKER.md](./DOCKER.md) — контейнеры и деплой (по задаче)
7. [.env.example](./.env.example) — переменные окружения

**Дополнительно:** [CONTRIBUTING.md](./CONTRIBUTING.md) (стиль кода и вклад).
