# Chernyavskiy A-Tech

Цифровой «мозг» автосервиса — CRM-платформа с поэтапным развитием.

## Этапы развития

1. **Сайт и витрина** (текущий этап)
   - Лендинг/сайт автосервиса
   - Формы записи и обратной связи
   - Базовый личный кабинет клиента

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
- OCR СТС: облачный Yandex Workflow (Vision + AI Agent)

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
- `WORKFLOW_OCR_URL` и `WORKFLOW_OCR_SECRET` — для распознавания СТС на странице записи
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

- [PHILOSOPHY.md](./PHILOSOPHY.md) - Философия проекта
- [CLAUDE.md](./CLAUDE.md) - Техническая документация
- [SETUP.md](./SETUP.md) - Подробная инструкция по установке
- [.cursor/dev_cache.md](./.cursor/dev_cache.md) - Кэш разработки
