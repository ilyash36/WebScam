# Кэш разработки - Автосервис CRM

> **Назначение**: Сжатая информация для быстрого понимания контекста AI-моделями + кэш истории разработки

> **Канонический порядок чтения** (как в [AI_CONTEXT.md](../AI_CONTEXT.md) §1):  
> 1) [AI_CONTEXT.md](../AI_CONTEXT.md) — точка входа; 2) [PHILOSOPHY.md](../PHILOSOPHY.md); 3) [CLAUDE.md](../CLAUDE.md); 4) этот файл (детали и хронология); 5) [SETUP.md](../SETUP.md); 6) [DOCKER.md](../DOCKER.md) — по задаче; 7) [.env.example](../.env.example).

---

## Быстрый обзор

Проект автосервиса Chernyavskiy A-Tech на Django — цифровой «мозг» автосервиса с поэтапным развитием: сайт → CRM → автоматизация. Текущий этап: сайт-витрина с формами записи. Backend: Python/Django, БД: PostgreSQL (prod), SQLite (dev). **Проект полностью контейнеризирован через Docker** — готов к деплою. Ветки: `main`, `dev`, `registration`.

**Брендинг**: Chernyavskiy A-Tech. Палитра: чёрный (#0a0a0a), золотой (#d4af37), белый. Шрифты: KOT-Eitai Gothic Bold, Century Old Style Std, Goudy Old Style (Sorts Mill Goudy), DwarvenStonecraftCyrExtended (опционально).

**OCR СТС (2026-03)**: Yandex Vision OCR API + локальный парсер `sts_parser.py`.  
- `recognize_document()` → `parse_sts()` — 1–3 сек.  
- Парсер: VIN/марка/модель/год, **номер ПТС** (шаблон **2 цифры + 2 буквы + 6 цифр**; опционально **№** между буквами и цифрами, напр. `77 УР№ 958764`; глобальный поиск по `fullText`; `_cert_last_six_digits` — не путать хвост **СТС** с ПТС; `_try_pts_reconstruct_from_eco_glitch` — типичный сбой OCR «экологический класс …659376» + «74» + «Паспорт ТС» → `77МУ…`; `_extract_broken_sts_certificate_tail` — «9 9 / 70… / 308738» → «99 70 308738»), **серия и номер СТС**, **объём** в л или из см³.  
- Кэш ответов Vision для регрессии: `scripts/_ocr_raw_<имя_файла_фото>.json` — **6** снимков (все `*.jpg` из `Desktop\СТС`); недостающий кэш: `python scripts/test_sts_parser.py --live` (нужны `YANDEX_VISION_API_KEY`, `YANDEX_FOLDER_ID`).  
- Тест: `python scripts/test_sts_parser.py` — **35** эталонных проверок полей по кэшу (100% при полном наборе JSON).  
- Облачный Workflow (AI Agent) не используется — был медленным (до 2 мин).

---

## Архитектура

**Структура**: Модульная архитектура с приложениями `core`, `website`, `crm`, `api`. Settings разделены на `base`, `development`, `production`. Модели в `apps/core/models/`, шаблоны в `templates/`, статика в `static/`.

**Принципы**: Модульность, расширяемость, событийность, API-first мышление. Ядро - Django backend + БД, n8n - внешний оркестратор, боты/фронт - тонкие клиенты.

---

## Ключевые компоненты

- **apps/core/** - базовые модели (Client, Vehicle, BookingRequest), сервисы (email), **`signals.py`** (синхронизация статусов заявок при `is_verified`), утилиты
- **apps/website/** - публичный сайт (лендинг, формы записи); OCR СТС через Vision API + `ocr/sts_parser.py`
- **apps/crm/** - CRM функционал (будущее)
- **apps/api/** - REST API (будущее)
- **config/** - настройки Django проекта
- **static/js/loader.js** - анимация загрузки (первый визит)
- **Docker конфигурация**:
  - `Dockerfile` - production образ с gunicorn
  - `Dockerfile.dev` - development образ с hot-reload
  - `docker-compose.yml` - production окружение
  - `docker-compose.dev.yml` - development окружение
  - `docker-entrypoint.sh` - автоматическая инициализация

---

## Важные детали реализации

- Все модели наследуются от BaseModel с `created_at`, `updated_at`
- Человекочитаемые статусы (не "PENDING", а "Ожидает согласования")
- Валидация на уровне модели и формы
- Защита от дубликатов клиентов/автомобилей (soft-unique — только среди активных)
- **Уникальность email и VIN** — НЕ на уровне БД, а на уровне view/check-conflicts среди `is_active=True`. Деактивированные клиенты не блокируют повторную регистрацию.
- Секреты в `.env` (не коммитить!)
- Логирование важных действий
- **PEP 8 строго соблюдается**: длина строк до 79-88 символов, правильные импорты, trailing commas
- **Docstrings** для всех классов и методов (Google style)
- **Type hints** для методов и свойств (`-> str`, `-> None`)
- Длинные строки разбиваются на несколько с переносом
- **Docker**: проект полностью контейнеризирован, автоматические миграции при запуске, health checks для БД; в `Dockerfile.dev` используется `dos2unix` для `docker-entrypoint.sh` (корректная работа на Windows с CRLF)
- **Дизайн**: Палитра чёрный/золотой/белый; эллиптические скругления (кривые Безье) через CSS-переменные `--radius-bezier-sm/md/lg`; шрифты в `static/css/fonts.css`; KOT и Century — CDN приоритет (для стабильности в Docker/Windows); preload для основных шрифтов в base.html
- **Админ-панель**: Стилизована под бренд Chernyavskiy A-Tech (`templates/admin/base_site.html`, `static/admin/css/custom.css`); site_header/site_title/index_title в config/urls.py; admin actions «Деактивировать» / «Активировать» клиентов
- **Навигация**: На странице /estimate/ — кнопка «Главная»; при авторизации — «Личный кабинет» + «Выйти» вместо «Записаться»
- **Сессии**: `SESSION_COOKIE_AGE = 604800` (7 дней), `SESSION_SAVE_EVERY_REQUEST = True`; `ClientAuthMiddleware` → `request.client`
- **Почта**: в **development** по умолчанию `console.EmailBackend` — письма в терминал `runserver`, не в ящик; **`python manage.py mail_selftest`** — проверка backend; **production** — SMTP (`EMAIL_*`, `DEFAULT_FROM_EMAIL`, **`SITE_URL`**). При ошибке SMTP — предупреждение пользователю в форме. Код входа (6 цифр): поле **`Client.auth_code`** в БД; в админке блок «Вход по коду из email». **Заявки**: при подтверждении по ссылке `verify_email_view` статус `pending_confirmation` → `confirmed`; при ручном **`is_verified`** в админке — то же через **`post_save`** (`apps/core/signals.py`). См. `.env.example`, `SETUP.md`
- **OCR СТС**: Yandex Vision API + локальный парсер (`yandex_vision.py`, `sts_parser.py`); `YANDEX_VISION_API_KEY` + `YANDEX_FOLDER_ID` — обязательны; парсер не извлекает госномер и цвет (поля убраны из формы записи). **Форма записи**: **объём двигателя (л)** и **мощность (л.с.)** — оба обязательны; объём хранится по-человечески в литрах с запятой (`1,4`), не в см³. **ЛК**: в `dashboard.html` в карточке заявки показываются объём (л) и мощность при наличии
- **Контакты**: Телефон — ссылка на t.me/+79507570606; адрес «Воронеж, Кривошеина 7а» — ссылка на Яндекс.Карты (координаты 51.637890, 39.153217); режим работы Пн-Вс: 10:00–20:00, по предварительной записи; класс `.link-address` для единого стиля
- **Футер**: «Compose & Code by 1nowen» — ссылка на 1nowen.com; шрифт KOT-Eitai Gothic Bold; «wen» с белым фоном и чёрными буквами; анимация увеличения при наведении; три столбца (Chernyavskiy A-Tech, Контакты, Быстрые ссылки) выровнены по центру страницы через grid (3 колонки, max-width 960px)
- **Загрузка**: `static/js/loader.js` — анимация 1,5 с при первой загрузке (referrer не с сайта); при навигации внутри сайта — без анимации; inline-скрипт в head для мгновенного skip
- **Страница «Услуги»**: текст о принципе технической диагностики в карточке (service-item--text); выравнивание по ширине; жирные акценты на ключевых фразах

---

## Часто используемые функции

### Создание модели клиента
```python
from apps.core.models import Client

client = Client.objects.create(
    first_name="Иван",
    last_name="Иванов",
    phone="+79991234567",
    email="ivan@example.com"
)
```

### Поиск клиента по телефону
```python
try:
    client = Client.objects.get(phone=phone)
except Client.DoesNotExist:
    client = None
```

### Логирование
```python
import logging
logger = logging.getLogger(__name__)
logger.info("Действие выполнено", extra={'key': value})
```

---

## Паттерны кода

### Базовая модель
```python
from django.db import models

class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True
```

### Class-based view
```python
from django.views.generic import CreateView
from apps.core.models import Client

class ClientCreateView(CreateView):
    model = Client
    fields = ['first_name', 'last_name', 'phone', 'email']
    template_name = 'website/booking.html'
    success_url = '/success/'
```

---

## История разработки

### Архитектурные решения

- **Модульная структура приложений**: Разделение на `core`, `website`, `crm`, `api` для четкой организации кода и будущего расширения
- **Разделение settings**: `base`, `development`, `production` для разных окружений без дублирования кода
- **BaseModel**: Абстрактная модель с `created_at`/`updated_at` для единообразия всех моделей
- **Этапность разработки**: Сначала простой сайт, затем CRM, затем автоматизация - архитектура готова к росту

### Текущий контекст разработки

- **Работаем над**: Этап 1 "Сайт и витрина" - ЗАВЕРШЁН ✅
  - Создана базовая структура Django проекта
  - Реализованы модели Client и Vehicle
  - Создан публичный сайт с лендингом и формами
  - Формы: запись на обслуживание, обратная связь, заявка на расчёт
- **Важно помнить**: 
  - Архитектура готова к расширению (CRM, API, автоматизация)
  - Все модели следуют доменной модели из PHILOSOPHY.md
  - Формы валидируются на уровне формы и модели
  - Код типизирован и документирован
  - Логирование настроено для отслеживания важных действий

### Часто используемые паттерны

- **BaseModel**: Все модели наследуются от BaseModel для единообразия
- **Class-based views**: Использование CBV для стандартных операций (CreateView, ListView)
- **Логирование**: Все важные действия логируются с контекстом
- **Валидация**: На уровне формы и модели для надежности
- **Docker**: Использование docker-compose для локальной разработки и деплоя

### Важные решения (хронология)

- **2026-02**: Выбран Django как основной фреймворк для backend
- **2026-02**: Определена модульная структура приложений (core, website, crm, api)
- **2026-02**: Решено начать с простого сайта, затем развивать CRM функционал
- **2026-02**: Создана техническая документация (CLAUDE.md) и кэш разработки (dev_cache.md)
- **2026-02**: Реализован Этап 1 - простейший сайт-витрина:
  - Модели Client и Vehicle с валидацией и защитой от дубликатов
  - Формы записи на обслуживание, обратной связи и заявки на расчёт
  - Шаблоны для всех страниц сайта (главная, о нас, услуги, контакты)
  - Базовые CSS стили для современного внешнего вида
  - Логирование всех важных действий
  - Админ-панель для управления клиентами и автомобилями
- **2026-02**: Оптимизация всего кода под стандарт PEP 8:
  - Исправлены длинные строки (разбиты на несколько с переносом)
  - Добавлены docstrings для всех классов и методов (Google style)
  - Добавлены type hints для методов (`-> str`, `-> None`)
  - Исправлен порядок импортов (стандартная библиотека → сторонние → локальные)
  - Добавлены trailing commas в многострочных структурах
  - Улучшено форматирование кода для лучшей читаемости
- **2026-02**: Очистка и оптимизация проекта:
  - Удалены временные файлы (CREATE_ENV.md, CLAUDE_prompt.txt, first_question_cursor.txt)
  - Создан `.env.example` для примера конфигурации
  - Добавлены конфигурационные файлы для инструментов разработки:
    - `setup.cfg` - конфигурация для flake8, isort, mypy
    - `pyproject.toml` - конфигурация для black, isort, pytest
    - `requirements-dev.txt` - инструменты для разработки
    - `Makefile` - команды для разработки
  - Улучшен `.gitignore` (добавлены исключения для кэшей линтеров)
  - Создан `CONTRIBUTING.md` - руководство по внесению вклада
  - Обновлена документация (README.md, SETUP.md)
- **2026-02**: Docker контейнеризация проекта:
  - Создан `Dockerfile` для production (gunicorn, оптимизированный образ)
  - Создан `Dockerfile.dev` для разработки (runserver, hot-reload)
  - Создан `docker-compose.yml` для production окружения
  - Создан `docker-compose.dev.yml` для development окружения
  - Создан `docker-entrypoint.sh` - скрипт инициализации (миграции, статика, суперпользователь)
  - Создан `.dockerignore` для оптимизации сборки
  - Добавлен `gunicorn` в requirements.txt
  - Обновлены настройки production для работы с Docker
  - Создан `DOCKER.md` с подробными инструкциями
  - Проект готов к деплою через Docker
- **2026-02**: Git-ветки: `main` (базовая), `dev` (от main), `registration` (от dev). Локальный запуск через Docker: `docker-compose -f docker-compose.dev.yml up --build -d`; требуется `.env` из `.env.example`.
- **2026-02**: Исправление сообщений об ошибках уникальности на корректный русский: для поля «Телефон» в модели Client — «Клиент с таким телефоном уже существует.»; для поля «VIN номер» в модели Vehicle — «Автомобиль с таким VIN номером уже существует.» Добавлено переопределение в `BookingForm` для поля `phone`. В `Dockerfile.dev` добавлен `dos2unix` для корректной работы entrypoint на Windows.
- **2026-02**: Ребрендинг и редизайн (ветка registration):
  - Бренд: Chernyavskiy A-Tech (вместо «Автосервис»)
  - Палитра: чёрный (#0a0a0a), золотой (#d4af37), белый
  - Шрифты: KOT-Eitai Gothic Bold, Century Old Style Std, Goudy Old Style (Sorts Mill Goudy), DwarvenStonecraftCyrExtended (локально)
  - Эллиптические скругления (кривые Безье) вместо стандартного border-radius
  - Услуги: Диагностика, Техническое обслуживание, Ремонт узлов и агрегатов (убраны шиномонтаж и др.)
  - Контактный телефон: +7 (950) 757-06-06
  - Страница /estimate/: «Запись на приём» вместо «Заявка на расчёт»; кнопка «Главная» в шапке; без кнопки «Записаться»
  - На странице услуг кнопка «Записаться» вместо «Запросить расчёт»
- **2026-02**: Доработки UI и UX:
  - Футер «Compose & Code by 1nowen» (1nowen_futer.md): ссылка на 1nowen.com, шрифт сайта, «wen» с белым фоном, анимация scale при наведении
  - Контакты: адрес «Воронеж, Кривошеина 7а» — ссылка на Яндекс.Карты; телефон — ссылка на Telegram
  - Заголовок главной: «Автосервис Андрея Чернявского»
  - Карточки услуг: центрирование текста (flex, align-items, justify-content)
  - Плавная загрузка: `static/js/loader.js` + inline-скрипт в head; показ только при первой загрузке (document.referrer); при навигации внутри сайта — без анимации (html.skip-loader)
  - Убрана фраза «Все права защищены» из футера
- **2026-02**: Страница «Услуги»:
  - Заголовок «Услуги»; карточки заменены на текст о принципе технической диагностики
  - Текст в карточке service-item--text; выравнивание по ширине (text-align: justify)
  - Жирные акценты: «принцип технической диагностики», «избегая ненужных замен...»
  - CTA: «Точную стоимость работ можно узнать после диагностики» (шрифт KOT), кнопка «Записаться»
  - Длительность лоадера увеличена до 1,5 с
- **2026-02**: Контент страниц:
  - Контакты: режим работы Пн-Вс 10:00–20:00, по предварительной записи
  - О нас: «Профессионализм — труд исключительно опытного мастера»; добавлена ценность «Кайдзен — философия постоянного совершенствования Toyota Production System»
- **2026-02**: Шрифты и футер:
  - KOT-Eitai Gothic Bold: CDN приоритет (db.onlinewebfonts.com) для стабильной работы в Docker на Windows; локальные woff2 как fallback
  - Preload шрифтов KOT и Century в base.html для ускорения загрузки
  - Футер «Compose & Code by 1nowen» — шрифт KOT
  - Три столбца футера (Chernyavskiy A-Tech, Контакты, Быстрые ссылки): grid 3 колонки, центрирование (max-width 960px, margin auto)
- **2026-02**: OCR СТС полностью перенесён в облако — `sts_parser.py`, `yandex_vision.py` удалены, Workflow (Vision + AI Agent) — единственный путь.
- **2026-03**: Восстановлен быстрый путь OCR (причина: AI Agent в Workflow давал задержку до 2 минут из-за cold start serverless-функции и LLM-петли при плохом OCR):
  - **Добавлено**: `apps/website/ocr/yandex_vision.py` — прямой вызов Vision OCR API (1–3 сек)
  - **Добавлено**: `apps/website/ocr/sts_parser.py` — локальный парсер полей СТС из textAnnotation
    - VIN: приоритет Кузов-поля, затем VIN-метка, сборка из фрагментов
    - Марка/Модель: предпочтение латинице, коррекция OCR-ошибок (RKODA→SKODA) через WMI-словарь
    - Сертификат: Yandex entities["phone"] — надёжный источник номера СТС
    - Диакритика: нормализация PRÍORA → PRIORA
  - **ocr_sts_view**: только Vision API → парсер (Workflow удалён)
  - **Тест**: `python scripts/test_sts_parser.py` (100% на 6 фото), `python scripts/test_live_ocr.py` (live API)
  - **Обязательные переменные**: `YANDEX_VISION_API_KEY`, `YANDEX_FOLDER_ID`
  - **Удалено**: `workflow_ocr.py`, `ocr_callback_view`, `generate_workflow_secret`, `test_workflow_ocr.py`, WORKFLOW_* настройки
- **2026-03**: Стилизация админ-панели под бренд Chernyavskiy A-Tech:
  - `templates/admin/base_site.html` — брендинг, подключение fonts.css и custom.css
  - `static/admin/css/custom.css` — палитра чёрный/золотой/белый, шрифты KOT и Century, эллиптические скругления
  - `config/urls.py` — site_header, site_title, index_title для AdminSite
- **2026-03**: Парсер СТС — нормализация brand/model в латиницу:
  - `_BRAND_NORMALIZE` (~60 записей), `_MODEL_NORMALIZE`, `_TRANSLIT`, homoglyph detection (`_HOMOGLYPH_CYR_TO_LAT`)
  - WMI-коррекция, Levenshtein distance для fuzzy matching
  - 100% тестов пройдено на 6 фотографиях СТС
- **2026-03**: Удалён Workflow OCR (AI Agent):
  - Удалены `workflow_ocr.py`, `ocr_callback_view`, `generate_workflow_secret`, `test_workflow_ocr.py`
  - Удалены `WORKFLOW_*` настройки из `settings/base.py` и `.env.example`
- **2026-03**: Форма записи (booking) — рефакторинг полей:
  - Убраны: `last_name` (необязательно), `certificate_series_number`
  - Добавлены: `consent_personal_data` (единый чекбокс вместо sms/email)
  - `email` — обязательное поле
  - VIN — обязательное поле (идентификация + подбор запчастей)
- **2026-03**: Passwordless auth (вход по коду из email):
  - Шлюз на `/booking/`: «Вы уже были у нас?» → «Да» (auth) / «Ещё нет» (форма)
  - `auth_send_code_view` → отправляет 6-значный код на email
  - `auth_verify_code_view` → проверяет код, логинит в session
  - `verify_email_view` → подтверждение email по токену из письма
  - Модель `Client`: `is_verified`, `verification_token`, `auth_code` + helper-методы
  - `apps/core/services/email.py` — `send_verification_email()`, `send_auth_code()`
  - Шаблоны: `booking_pending.html`, `verify_email_done.html`, `email/verify_email.html`, `email/auth_code.html`
- **2026-03**: Личный кабинет клиента:
  - `dashboard_view` — профиль, автомобили, история заявок
  - Декоратор `client_required` — проверка session + `is_verified` + `is_active`
  - Шаблон `dashboard.html` со стилями `.dashboard`, `.profile-card`, `.vehicle-card`, `.booking-card`
- **2026-03**: Модель `BookingRequest` (`apps/core/models/booking_request.py`):
  - Статусы: `pending_confirmation`, `confirmed`, `in_progress`, `completed`, `cancelled`
  - Связи: `client` (FK), `vehicle` (FK)
  - Поля: `message`, `vehicle_passport_number`, `vehicle_engine_volume` (**литры**, строка с запятой), `vehicle_engine_power`, `notes`
  - Миграция **`core.0006_booking_engine_volume_liters`** — `vehicle_engine_volume`: семантика литров, `verbose_name` «Объём двигателя, л»
- **2026-03**: Парсер СТС/ПТС и форма записи (объём в литрах):
  - `sts_parser.py`: расширенный поиск **номера ПТС** после метки «Паспорт ТС» (в т.ч. 6 цифр); защита от подстановки того же номера в **серию СТС**; объём: литры или перевод см³ → л для автозаполнения `vehicle_engine_volume`
  - `BookingForm`: объём и мощность **обязательны**; валидация объёма ~0,5–10 л, мощности ~20–2000 л.с.; нормализация десятичного разделителя (запятая)
  - `templates/website/booking.html`: убрана подсказка «хотя бы одно из полей»; `dashboard.html` — строка «Объём: … л»
  - Документация и кэш обновлены (этот файл, CLAUDE.md)
- **2026-03**: Доработка парсера ПТС/СТС и полный набор кэшей OCR:
  - `_PTS_RE`: учёт символа **№** между буквами серии и 6 цифрами; `_cert_last_six_digits`; эвристика **eco + 74 + Паспорт ТС**; разбор разбитого номера СТС внизу бланка
  - Все **6** фото из `Desktop\СТС` имеют `scripts/_ocr_raw_*.json`; `test_sts_parser.py` — **35** проверок по эталону (в т.ч. `photo_2024-10-24_18-06-12`)
- **2026-03**: Конфликты email/VIN, деактивация аккаунтов, безопасность:
  - `Client.is_active` — мягкая деактивация (только через админ-панель)
  - `Vehicle.vin` — убран `unique=True`; уникальность проверяется только среди активных клиентов в view
  - `Client.email` — НЕ unique на уровне БД; проверка только среди `is_active=True`
  - AJAX `/booking/check-conflicts/` — проверка email + VIN перед submit формы
    - Email совпал с активным → отправка кода авторизации
    - VIN совпал с активным → код на masked email (`i*******@gmail.com`) + ссылка на Telegram
    - Деактивированные — не блокируют: разрешаем создание нового аккаунта
  - `Client.masked_email` property — `"i*******@gmail.com"`
  - Rate limiting: max 3 отправки кода за 15 мин (`auth_code_send_count`, `auth_code_last_send_at`)
  - Brute-force защита: блокировка после 5 ошибок на 15 мин (`auth_code_failed_attempts`, `auth_code_failed_at`)
  - `verify_auth_code()` обновлён: инкремент ошибок при неудаче, полный сброс при успехе
  - Admin actions: «Деактивировать» / «Активировать» клиентов
  - `client_required`, `auth_send_code_view`, `auth_verify_code_view`, `verify_email_view` — все проверяют `is_active=True`
  - Frontend: JS перехват submit → проверка через check-conflicts → показ сообщения → переключение на auth-панель
- **2026-03**: Сессии и UI авторизованного клиента:
  - `SESSION_COOKIE_AGE = 604800` (7 дней), `SESSION_SAVE_EVERY_REQUEST = True`
  - `ClientAuthMiddleware` — загружает `request.client` по `session['client_id']`
  - `client_context` — передаёт `client` в шаблоны
  - base.html: при `client` — «Личный кабинет» + «Выйти» вместо «Записаться»
  - /booking/: авторизованные видят форму сразу (шлюз скрыт), предзаполнение имени/телефона/email
- **2026-03**: Почта, ЛК и админка (доработки):
  - Настройки **`SITE_URL`**, **`DEFAULT_FROM_EMAIL`**, SMTP в `base.py`; `EMAIL_BACKEND` из `.env` в development/production; предупреждение при сбое отправки письма
  - Команда **`mail_selftest`** — диагностика console/SMTP
  - **`apps/core/signals.py`**: при сохранении клиента с `is_verified=True` заявки `pending_confirmation` → `confirmed` (в т.ч. ручное подтверждение email в админке)
  - В админке клиента: поля **`auth_code`**, **`auth_code_created_at`** (readonly); **`.conflict-message`** в CSS — тёмный текст на светлом фоне (читаемость)

---

## Ссылки

- [AI_CONTEXT.md](../AI_CONTEXT.md) — **точка входа для AI**; §1 — **канонический порядок чтения** (дублируется в README, CLAUDE, CONTRIBUTING, SETUP, DOCKER)
- [CLAUDE.md](../CLAUDE.md) — полная техническая документация
- [PHILOSOPHY.md](../PHILOSOPHY.md) — философия проекта
