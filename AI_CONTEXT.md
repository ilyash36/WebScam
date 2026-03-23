# Контекст разработки для AI и новых разработчиков

> **Назначение**: единая точка входа для переноса контекста в другую IDE, чат или модель. Прочитайте этот файл первым, затем документы в порядке ниже.

---

## 1. Канонический порядок чтения документации

**Читайте в этом порядке** при переносе контекста в другой чат, модель или IDE.  
Тот же порядок продублирован в [README.md](./README.md), [CLAUDE.md](./CLAUDE.md), [.cursor/dev_cache.md](./.cursor/dev_cache.md), [CONTRIBUTING.md](./CONTRIBUTING.md), [SETUP.md](./SETUP.md), [DOCKER.md](./DOCKER.md).

1. **[AI_CONTEXT.md](./AI_CONTEXT.md)** (этот файл) — индекс, снимок архитектуры, URL, переменные, устаревшее.
2. **[PHILOSOPHY.md](./PHILOSOPHY.md)** — продукт, этапы, доменная модель, принципы.
3. **[CLAUDE.md](./CLAUDE.md)** — полная техника: структура, модели, OCR, почта, формы, шаблоны, правила кода.
4. **[.cursor/dev_cache.md](./.cursor/dev_cache.md)** — сжатый обзор и **хронология решений** (что уже сделано / не трогать).
5. **[SETUP.md](./SETUP.md)** — установка, почта (console vs SMTP), `mail_selftest`, ручное подтверждение email.
6. **[DOCKER.md](./DOCKER.md)** — контейнеры и деплой (если задача связана с Docker).
7. **[.env.example](./.env.example)** — обязательные и опциональные переменные окружения.

**Дополнительно (по необходимости):** [CONTRIBUTING.md](./CONTRIBUTING.md) (стиль кода), [README.md](./README.md) (обзор репозитория).

| № | Файл | Содержание |
|---|------|------------|
| 1 | [AI_CONTEXT.md](./AI_CONTEXT.md) | Точка входа: индекс, снимок, URL, устаревшее |
| 2 | [PHILOSOPHY.md](./PHILOSOPHY.md) | Продукт, этапы, домен, принципы |
| 3 | [CLAUDE.md](./CLAUDE.md) | Полная техническая документация |
| 4 | [.cursor/dev_cache.md](./.cursor/dev_cache.md) | Кэш + хронология решений |
| 5 | [SETUP.md](./SETUP.md) | Установка, почта, `mail_selftest` |
| 6 | [DOCKER.md](./DOCKER.md) | Docker / compose (по задаче) |
| 7 | [.env.example](./.env.example) | Переменные окружения |

---

## 2. Снимок проекта (на что опираться)

- **Название / бренд**: Chernyavskiy A-Tech (Автосервис Андрея Чернявского), Воронеж.
- **Стек**: Python 3.11+, Django 5.x, PostgreSQL (prod), SQLite (dev), шаблоны Django, Docker.
- **Приложения Django**: `apps.core` (модели, email, **signals**), `apps.website` (сайт, формы, OCR, auth views), `apps.crm` / `apps.api` — заглушки.
- **Текущий этап**: «Сайт и витрина» **расширенный** — лендинг, формы, **OCR СТС**, **passwordless auth** (код по email), **личный кабинет**, конфликты email/VIN, мягкая деактивация клиентов.

---

## 3. Модели и бизнес-правила (кратко)

| Модель | Важно |
|--------|--------|
| **Client** | `phone` — **unique** в БД. `email` — **не** unique в БД; уникальность среди `is_active=True` в логике views / `check-conflicts`. Поля: `is_verified`, `is_active`, `verification_token`, `auth_code` (+ rate limiting поля). |
| **Vehicle** | `vin` — **без** `unique` в БД; конфликты только среди активных клиентов. |
| **BookingRequest** | Статусы: `pending_confirmation`, `confirmed`, `in_progress`, `completed`, `cancelled`. Связь с Client и Vehicle. Поля ТС: ПТС, объём в **литрах** (строка с запятой), мощность л.с. |

**Синхронизация заявок с подтверждением email**: при `Client.is_verified=True` заявки в `pending_confirmation` переводятся в `confirmed` — в `verify_email_view` и дублируется сигналом **`post_save`** в `apps/core/signals.py` (в т.ч. при ручной галочке в админке).

---

## 4. OCR СТС/ПТС (актуальная архитектура)

- **Нет** отдельного Yandex Workflow / AI Agent для OCR (удалён как медленный).
- Цепочка: **Yandex Vision API** (`apps/website/ocr/yandex_vision.py`) → **`parse_sts()`** (`apps/website/ocr/sts_parser.py`).
- Обязательные env: `YANDEX_VISION_API_KEY`, `YANDEX_FOLDER_ID`.
- Парсер: ПТС формата 2+2 буквы+6 цифр, учёт «№», отделение хвоста СТС от ПТС, эвристики OCR-ошибок; см. CLAUDE.md и dev_cache.
- Регрессия: `scripts/_ocr_raw_*.json` + `python scripts/test_sts_parser.py` (~35 проверок при полном наборе кэшей).

---

## 5. Почта и авторизация

- **Development**: по умолчанию `console.EmailBackend` — письма в **терминал** `runserver`, не в ящик. Диагностика: `python manage.py mail_selftest`.
- **Production**: SMTP через `EMAIL_*`, `DEFAULT_FROM_EMAIL`, **`SITE_URL`** (ссылки в письмах за reverse-proxy).
- Подтверждение email: `/verify-email/<token>/`. Код входа: 6 цифр в `Client.auth_code` (в админке — блок «Вход по коду из email»; в логах код не дублируется).

---

## 6. Основные URL (`apps/website/urls.py`, префикс без корневого конфига)

| Путь | Назначение |
|------|------------|
| `/`, `/about/`, `/services/`, `/contacts/` | Статика сайта |
| `/booking/` | Форма записи + шлюз auth + check-conflicts (AJAX) |
| `/booking/ocr-sts/` | POST фото → JSON полей OCR |
| `/booking/check-conflicts/` | POST JSON email/vin |
| `/booking/pending/` | Страница после отправки заявки |
| `/verify-email/<token>/` | Подтверждение email |
| `/auth/send-code/`, `/auth/verify-code/` | Passwordless |
| `/dashboard/`, `/logout/` | ЛК клиента |
| `/feedback/`, `/estimate/` | Обратная связь, запись на приём |

Точный `ROOT_URLCONF`: см. `config/urls.py`.

---

## 7. Стили и бренд

- Палитра: чёрный `#0a0a0a`, золотой `#d4af37`, белый; шрифты KOT / Century — см. `static/css/fonts.css`, `CLAUDE.md` (дизайн).
- Сообщения конфликта на форме записи: класс `.conflict-message` (`static/css/style.css`) — тёмный текст на светлом фоне.

---

## 8. Что устарело / не искать в коде

- **Workflow OCR**, `workflow_ocr.py`, callback workflow, переменные `WORKFLOW_*` — **удалены**.
- Поля госномера / цвета в форме записи — **убраны** (парсер их не заполняет для формы).

---

## 9. Команды для проверки после изменений

```bash
python manage.py check
python manage.py migrate
python scripts/test_sts_parser.py
python manage.py mail_selftest   # почта: console или SMTP
```

---

## 10. Связь с правилами Cursor / IDE

- В репозитории используется подробный **[CLAUDE.md](./CLAUDE.md)** как основной «системный» гайд для ассистента.
- Этот файл (**AI_CONTEXT.md**) — **навигация и снимок состояния**; при противоречии с кодом приоритет у **кода** и **CLAUDE.md**, затем **dev_cache** (хронология).
- **Порядок чтения** — см. [§1](#1-канонический-порядок-чтения-документации); при изменении порядка обновляйте все файлы, где он продублирован (список в §1).

---

*Обновляйте [PHILOSOPHY.md](./PHILOSOPHY.md), [CLAUDE.md](./CLAUDE.md) и [.cursor/dev_cache.md](./.cursor/dev_cache.md) при существенных изменениях архитектуры; этот файл — при добавлении новых «осей» контекста (новый сервис, этап CRM).*
