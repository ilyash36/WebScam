# Инструкция по первому запуску проекта

## Шаг 1: Установка зависимостей

1. Создайте виртуальное окружение:
```bash
python -m venv venv
```

2. Активируйте виртуальное окружение:
```bash
# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

## Шаг 2: Настройка переменных окружения

1. Создайте файл `.env` на основе `.env.example`:
```bash
# Windows PowerShell
Copy-Item .env.example .env

# Linux/Mac
cp .env.example .env
```

2. Откройте `.env` и заполните настройки:
   - `SECRET_KEY` - сгенерируйте новый секретный ключ (можно использовать команду ниже)
   - `DEBUG=True` - для разработки
   - `WORKFLOW_OCR_URL`, `WORKFLOW_OCR_SECRET` - для распознавания СТС (см. `.env.example`)
   - Остальные настройки можно оставить по умолчанию для разработки

3. Для генерации SECRET_KEY выполните в Python:
```python
from django.core.management.utils import get_random_secret_key
print(get_random_secret_key())
```

## Шаг 3: Применение миграций

```bash
python manage.py makemigrations
python manage.py migrate
```

## Шаг 4: Создание суперпользователя

```bash
python manage.py createsuperuser
```

Следуйте инструкциям для создания администратора.

## Шаг 5: Сбор статических файлов (опционально)

```bash
python manage.py collectstatic --noinput
```

## Шаг 6: Запуск сервера разработки

```bash
python manage.py runserver
```

Откройте браузер и перейдите по адресу: http://127.0.0.1:8000/

## Доступные страницы

- Главная: http://127.0.0.1:8000/
- О нас: http://127.0.0.1:8000/about/
- Услуги: http://127.0.0.1:8000/services/
- Контакты: http://127.0.0.1:8000/contacts/
- Записаться: http://127.0.0.1:8000/booking/
- Обратная связь: http://127.0.0.1:8000/feedback/
- Заявка на расчёт: http://127.0.0.1:8000/estimate/
- Админ-панель: http://127.0.0.1:8000/admin/

## Структура проекта

```
автосервис/
├── apps/
│   ├── core/          # Базовые модели (Client, Vehicle)
│   └── website/       # Публичный сайт
├── config/            # Настройки Django
├── templates/         # HTML шаблоны
├── static/           # Статические файлы (CSS, JS)
├── logs/             # Логи приложения
└── manage.py         # Точка входа Django
```

## Следующие шаги

После успешного запуска проекта можно:
1. Настроить админ-панель для управления данными
2. Добавить больше услуг и контента на сайт
3. Настроить отправку email-уведомлений
4. Подготовить проект к следующему этапу (CRM функционал)
