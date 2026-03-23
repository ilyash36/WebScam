# Инструкция по первому запуску проекта

> **Канонический порядок чтения** — [AI_CONTEXT.md](./AI_CONTEXT.md) §1. Этот файл (**SETUP**) — шаг **5** (после AI_CONTEXT → PHILOSOPHY → CLAUDE → dev_cache).

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
   - `YANDEX_VISION_API_KEY`, `YANDEX_FOLDER_ID` - для распознавания СТС (см. `.env.example`)
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

## Почта (подтверждение email при записи)

1. **Локально (`manage.py runserver`)** по умолчанию включён `console.EmailBackend` — письма **не** уходят на реальный адрес, текст письма выводится **в терминал**, где запущен Django. Чтобы проверить доставку в ящик, в `.env` укажите `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend` и заполните `EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL` (см. `.env.example`).

   **Если письма нет в терминале:** в `.env` не должно быть строки `EMAIL_BACKEND=...smtp...` (или закомментируйте её). Проверка одной командой: `python manage.py mail_selftest` — при `console` backend в том же окне появится блок `Content-Type: ...` с телом письма.

2. **Production / Docker** использует `config.settings.production` и **SMTP**. Обязательно задайте в `.env`: `EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL` (часто совпадает с логином SMTP), **`SITE_URL`** — публичный URL сайта с `https://` для ссылки в письме.

3. Если SMTP не настроен или неверен, отправка падает; в интерфейсе показывается предупреждение, детали — в `logs/django.log`.

4. **Ручное подтверждение email в админке** (`Клиент` → «Email подтверждён»): статусы заявок **`pending_confirmation` → `confirmed`** подтягиваются автоматически при сохранении клиента (сигнал `apps/core/signals.py`). Если заявка «зависла» со старым статусом — откройте клиента в админке и нажмите **Сохранить** ещё раз.

5. **Код входа (6 цифр)** при passwordless-авторизации хранится в поле **`auth_code`** модели клиента; в логах не выводится; в админке — блок «Вход по коду из email».

## Следующие шаги

После успешного запуска проекта можно:
1. Настроить админ-панель для управления данными
2. Добавить больше услуг и контента на сайт
3. Настроить отправку email-уведомлений (см. раздел выше и `.env.example`)
4. Подготовить проект к следующему этапу (CRM функционал)
