"""
Представления для публичного сайта.
"""
import logging

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.generic import TemplateView
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .forms import BookingForm, FeedbackForm, EstimateRequestForm
from .ocr import recognize_document, mime_from_filename, parse_sts
from apps.core.models import Client, Vehicle, BookingRequest
from apps.core.services.email import (
    send_verification_email,
    send_auth_code,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Декоратор авторизации клиента
# ---------------------------------------------------------------------------

def client_required(view_func):
    """
    Декоратор: пропускает только активных верифицированных клиентов.

    Проверяет session['client_id'], загружает Client,
    проверяет is_verified и is_active. Добавляет request.client.
    """
    def wrapper(request, *args, **kwargs):
        client_id = request.session.get('client_id')
        if not client_id:
            return redirect('website:booking')
        try:
            client = Client.objects.get(
                pk=client_id,
                is_verified=True,
                is_active=True,
            )
        except Client.DoesNotExist:
            request.session.flush()
            return redirect('website:booking')
        request.client = client
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    wrapper.__doc__ = view_func.__doc__
    return wrapper


# ---------------------------------------------------------------------------
# Статические страницы
# ---------------------------------------------------------------------------

class IndexView(TemplateView):
    """Главная страница."""
    template_name = 'website/index.html'


class AboutView(TemplateView):
    """Страница \"О нас\"."""
    template_name = 'website/about.html'


class ServicesView(TemplateView):
    """Страница \"Услуги и цены\"."""
    template_name = 'website/services.html'


class ContactsView(TemplateView):
    """Страница \"Контакты\"."""
    template_name = 'website/contacts.html'


# ---------------------------------------------------------------------------
# Запись на обслуживание
# ---------------------------------------------------------------------------

class BookingView(View):
    """Форма записи на обслуживание (новые и авторизованные клиенты)."""

    def get(self, request):
        """Отображение формы записи. Авторизованные видят форму сразу."""
        initial = {}
        client = getattr(request, 'client', None)
        if client:
            initial = {
                'first_name': client.first_name,
                'phone': client.phone,
                'email': client.email or '',
            }
        form = BookingForm(initial=initial)
        return render(
            request, 'website/booking.html', {'form': form}
        )

    def post(self, request):
        """
        Создаёт Client + Vehicle + BookingRequest.

        Отправляет email подтверждения. Заявка получает статус
        'pending_confirmation' до клика по ссылке из письма.
        """
        form = BookingForm(request.POST)
        if form.is_valid():
            try:
                phone = form.cleaned_data['phone']
                email = form.cleaned_data['email']

                client, created = Client.objects.get_or_create(
                    phone=phone,
                    defaults={
                        'first_name': form.cleaned_data['first_name'],
                        'email': email,
                        'attraction_channel': 'website',
                        'consent_personal_data': True,
                    },
                )

                if not created:
                    client.first_name = form.cleaned_data['first_name']
                    if email:
                        client.email = email
                    client.consent_personal_data = True
                    client.save()

                # Автомобиль
                vin = form.cleaned_data.get('vehicle_vin') or None
                vin = (
                    vin.replace(' ', '')[:17] if vin else None
                ) or None

                defaults = {
                    'brand': form.cleaned_data['vehicle_brand'],
                    'model': form.cleaned_data['vehicle_model'],
                    'year': form.cleaned_data.get('vehicle_year'),
                }
                vehicle, v_created = Vehicle.objects.get_or_create(
                    client=client,
                    vin=vin,
                    defaults=defaults,
                )
                if not v_created:
                    for attr, val in defaults.items():
                        if val is not None:
                            setattr(vehicle, attr, val)
                    vehicle.save()

                # Заявка
                booking = BookingRequest.objects.create(
                    client=client,
                    vehicle=vehicle,
                    status='pending_confirmation',
                    message=form.cleaned_data.get('message', ''),
                    vehicle_passport_number=(
                        form.cleaned_data.get(
                            'vehicle_passport_number', ''
                        )
                    ),
                    vehicle_engine_volume=(
                        form.cleaned_data.get(
                            'vehicle_engine_volume', ''
                        )
                    ),
                    vehicle_engine_power=(
                        form.cleaned_data.get(
                            'vehicle_engine_power', ''
                        )
                    ),
                )

                logger.info(
                    "Заявка #%s создана: client=%s, vehicle=%s",
                    booking.pk, client.pk, vehicle.pk,
                )

                # Отправляем email подтверждения
                sent_ok = send_verification_email(
                    client, request=request,
                )
                if not sent_ok:
                    messages.warning(
                        request,
                        'Заявка принята, но письмо с подтверждением '
                        'не удалось отправить. Проверьте папку «Спам», '
                        'либо настройки почты на сервере. '
                        'Вы можете связаться с нами по телефону на сайте.',
                    )
                return redirect('website:booking_pending')

            except Exception as e:
                logger.error(
                    "Ошибка при создании заявки: %s",
                    e, exc_info=True,
                )
                messages.error(
                    request,
                    'Произошла ошибка при отправке заявки. '
                    'Пожалуйста, попробуйте позже.',
                )

        return render(
            request, 'website/booking.html', {'form': form}
        )


@require_http_methods(['POST'])
def check_conflicts_view(request):
    """
    AJAX: проверяет конфликты email/VIN среди активных клиентов.

    Ожидает JSON: {"email": "...", "vin": "..."}.
    Возвращает:
      - {conflict: null} — конфликтов нет
      - {conflict: {type, message, show_code_input}} — есть конфликт
    """
    import json
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, TypeError):
        return JsonResponse(
            {'error': 'Некорректный запрос'}, status=400,
        )

    email = (data.get('email') or '').strip().lower()
    vin = (data.get('vin') or '').strip().upper().replace(' ', '')

    # --- Проверка email ---
    if email:
        try:
            existing = Client.objects.get(
                email__iexact=email,
                is_active=True,
            )
        except Client.DoesNotExist:
            existing = None

        if existing:
            if existing.is_verified:
                if existing.can_send_auth_code():
                    existing.generate_auth_code()
                    existing.record_auth_code_send()
                    send_auth_code(existing)
                return JsonResponse({'conflict': {
                    'type': 'email',
                    'message': (
                        'Такой email уже зарегистрирован. '
                        'Мы отправили код авторизации.'
                    ),
                    'show_code_input': True,
                    'email': email,
                }})
            else:
                sent_ok = send_verification_email(
                    existing, request=request,
                )
                if sent_ok:
                    msg = (
                        'На этот email повторно отправлена '
                        'ссылка подтверждения. Проверьте почту и «Спам».'
                    )
                else:
                    msg = (
                        'Не удалось отправить письмо. '
                        'Проверьте настройки SMTP на сервере '
                        'или обратитесь к администратору сайта.'
                    )
                return JsonResponse({'conflict': {
                    'type': 'email_unverified',
                    'message': msg,
                    'show_code_input': False,
                    'email_send_failed': not sent_ok,
                }})

    # --- Проверка VIN ---
    if vin and len(vin) >= 5:
        active_vehicle = (
            Vehicle.objects
            .filter(vin=vin, client__is_active=True)
            .select_related('client')
            .first()
        )
        if active_vehicle:
            owner = active_vehicle.client
            if owner.can_send_auth_code():
                owner.generate_auth_code()
                owner.record_auth_code_send()
                send_auth_code(owner)
            return JsonResponse({'conflict': {
                'type': 'vin',
                'message': (
                    'Автомобиль с данным VIN уже привязан '
                    f'к аккаунту {owner.masked_email}. '
                    'Код авторизации отправлен. '
                    'В случае, если у Вас больше нет доступа '
                    'к данному email, обратитесь в '
                    '<a href="https://t.me/+79507570606" '
                    'target="_blank">Телеграм</a>.'
                ),
                'show_code_input': True,
                'email': owner.email,
            }})

    return JsonResponse({'conflict': None})


class BookingPendingView(TemplateView):
    """Страница ожидания подтверждения email."""
    template_name = 'website/booking_pending.html'


class BookingSuccessView(TemplateView):
    """Страница успешной отправки заявки."""
    template_name = 'website/booking_success.html'


# ---------------------------------------------------------------------------
# Подтверждение email
# ---------------------------------------------------------------------------

def verify_email_view(request, token):
    """
    Подтверждает email клиента по токену из письма.

    Активирует Client.is_verified, переводит заявки в 'confirmed'.
    """
    try:
        client = Client.objects.get(
            verification_token=token,
            is_active=True,
        )
    except Client.DoesNotExist:
        return render(
            request,
            'website/verify_email_done.html',
            {'success': False, 'error': 'Ссылка недействительна.'},
        )

    if not client.is_verification_token_valid():
        return render(
            request,
            'website/verify_email_done.html',
            {'success': False, 'error': 'Срок действия ссылки истёк.'},
        )

    client.is_verified = True
    client.verification_token = ''
    client.verification_token_created_at = None
    client.save(update_fields=[
        'is_verified',
        'verification_token',
        'verification_token_created_at',
    ])

    # Подтверждаем ожидающие заявки
    BookingRequest.objects.filter(
        client=client,
        status='pending_confirmation',
    ).update(status='confirmed')

    # Логиним клиента
    request.session['client_id'] = client.pk

    logger.info("Email подтверждён: client=%s", client.pk)

    return render(
        request,
        'website/verify_email_done.html',
        {'success': True, 'client': client},
    )


# ---------------------------------------------------------------------------
# Passwordless auth (вход по коду из email)
# ---------------------------------------------------------------------------

@require_http_methods(['POST'])
def auth_send_code_view(request):
    """
    AJAX: отправляет 6-значный код на email клиента.

    Ожидает JSON: {"email": "..."}.
    Проверяет is_active, is_verified, rate limit.
    """
    import json
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, TypeError):
        return JsonResponse(
            {'error': 'Некорректный запрос'}, status=400,
        )

    email = (data.get('email') or '').strip().lower()
    if not email:
        return JsonResponse(
            {'error': 'Укажите email'}, status=400,
        )

    try:
        client = Client.objects.get(
            email__iexact=email,
            is_active=True,
        )
    except Client.DoesNotExist:
        return JsonResponse(
            {'error': 'Клиент с таким email не найден'},
            status=404,
        )

    if not client.is_verified:
        return JsonResponse(
            {
                'error': (
                    'Email ещё не подтверждён. '
                    'Проверьте почту — мы отправляли ссылку.'
                ),
            },
            status=403,
        )

    if not client.can_send_auth_code():
        return JsonResponse(
            {
                'error': (
                    'Слишком много запросов кода. '
                    'Подождите 15 минут.'
                ),
            },
            status=429,
        )

    client.generate_auth_code()
    client.record_auth_code_send()
    ok = send_auth_code(client)
    if not ok:
        return JsonResponse(
            {'error': 'Не удалось отправить код'},
            status=500,
        )

    return JsonResponse({'success': True})


@require_http_methods(['POST'])
def auth_verify_code_view(request):
    """
    AJAX: проверяет 6-значный код и логинит клиента.

    Ожидает JSON: {"email": "...", "code": "..."}.
    Проверяет is_active, brute-force блокировку.
    """
    import json
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, TypeError):
        return JsonResponse(
            {'error': 'Некорректный запрос'}, status=400,
        )

    email = (data.get('email') or '').strip().lower()
    code = (data.get('code') or '').strip()

    if not email or not code:
        return JsonResponse(
            {'error': 'Укажите email и код'}, status=400,
        )

    try:
        client = Client.objects.get(
            email__iexact=email,
            is_active=True,
        )
    except Client.DoesNotExist:
        return JsonResponse(
            {'error': 'Клиент не найден'}, status=404,
        )

    if client.is_auth_code_blocked():
        return JsonResponse(
            {
                'error': (
                    'Слишком много неверных попыток. '
                    'Подождите 15 минут.'
                ),
            },
            status=429,
        )

    if not client.verify_auth_code(code):
        return JsonResponse(
            {'error': 'Неверный или просроченный код'},
            status=400,
        )

    request.session['client_id'] = client.pk
    logger.info("Passwordless login: client=%s", client.pk)

    return JsonResponse({
        'success': True,
        'redirect': '/dashboard/',
    })


# ---------------------------------------------------------------------------
# Выход
# ---------------------------------------------------------------------------

def logout_view(request):
    """Выход клиента из личного кабинета."""
    request.session.flush()
    return redirect('website:index')


# ---------------------------------------------------------------------------
# Личный кабинет
# ---------------------------------------------------------------------------

@client_required
def dashboard_view(request):
    """Личный кабинет клиента."""
    client = request.client
    vehicles = Vehicle.objects.filter(client=client)
    bookings = BookingRequest.objects.filter(client=client)

    return render(request, 'website/dashboard.html', {
        'client': client,
        'vehicles': vehicles,
        'bookings': bookings,
    })


# ---------------------------------------------------------------------------
# OCR СТС
# ---------------------------------------------------------------------------

@require_http_methods(['POST'])
def ocr_sts_view(request):
    """
    API: распознавание СТС через Yandex Vision OCR + локальный парсер.

    1. Yandex Vision OCR API → textAnnotation (1–3 сек)
    2. Локальный парсер sts_parser.py → поля формы (мгновенно)

    Принимает POST с полем 'image' (файл изображения).
    Возвращает JSON с полями для автозаполнения формы.
    """
    image_file = request.FILES.get('image')
    if not image_file:
        return JsonResponse(
            {'error': 'Не указано изображение'},
            status=400,
        )

    if image_file.size > 10 * 1024 * 1024:
        return JsonResponse(
            {'error': 'Файл слишком большой (макс. 10 МБ)'},
            status=400,
        )

    try:
        image_bytes = image_file.read()
    except Exception as e:
        logger.error("Ошибка чтения файла: %s", e, exc_info=True)
        return JsonResponse(
            {'error': str(e), 'data': {}}, status=500
        )

    api_key = getattr(settings, 'YANDEX_VISION_API_KEY', '') or ''
    folder_id = getattr(settings, 'YANDEX_FOLDER_ID', '') or ''

    if not api_key or not folder_id:
        return JsonResponse(
            {
                'error': (
                    'OCR недоступен: настройте YANDEX_VISION_API_KEY'
                    ' и YANDEX_FOLDER_ID в .env'
                ),
                'data': {},
            },
            status=503,
        )

    try:
        mime = mime_from_filename(image_file.name or '')
        ta, vision_err = recognize_document(
            image_bytes, api_key, folder_id, mime,
        )
        if ta is not None:
            form_data = parse_sts(ta)
            logger.info(
                "OCR СТС: успешно, VIN=%s",
                form_data.get('vehicle_vin', ''),
            )
            return JsonResponse(
                {'success': True, 'data': form_data}
            )
        return JsonResponse(
            {
                'error': (
                    vision_err or 'Не удалось распознать документ'
                ),
                'data': {},
            },
            status=200,
        )
    except Exception as e:
        logger.error("Ошибка OCR СТС: %s", e, exc_info=True)
        return JsonResponse(
            {'error': str(e), 'data': {}}, status=500
        )


# ---------------------------------------------------------------------------
# Обратная связь
# ---------------------------------------------------------------------------

class FeedbackView(View):
    """Форма обратной связи."""

    def get(self, request):
        """Отображение формы обратной связи."""
        form = FeedbackForm()
        return render(
            request, 'website/feedback.html', {'form': form}
        )

    def post(self, request):
        """Обработка формы обратной связи."""
        form = FeedbackForm(request.POST)
        if form.is_valid():
            try:
                logger.info(
                    "Обратная связь от %s",
                    form.cleaned_data['name'],
                    extra={
                        'phone': form.cleaned_data['phone'],
                        'email': form.cleaned_data.get('email'),
                        'message': form.cleaned_data['message'],
                    },
                )
                messages.success(
                    request,
                    'Спасибо за ваше сообщение! '
                    'Мы свяжемся с вами в ближайшее время.',
                )
                return redirect('website:feedback_success')
            except Exception as e:
                logger.error(
                    "Ошибка обратной связи: %s",
                    e, exc_info=True,
                )
                messages.error(
                    request,
                    'Произошла ошибка. Попробуйте позже.',
                )
        return render(
            request, 'website/feedback.html', {'form': form}
        )


class FeedbackSuccessView(TemplateView):
    """Страница успешной отправки обратной связи."""
    template_name = 'website/feedback_success.html'


# ---------------------------------------------------------------------------
# Расчёт стоимости
# ---------------------------------------------------------------------------

class EstimateRequestView(View):
    """Форма заявки на расчёт стоимости."""

    def get(self, request):
        """Отображение формы заявки на расчёт."""
        form = EstimateRequestForm()
        return render(
            request,
            'website/estimate_request.html',
            {'form': form},
        )

    def post(self, request):
        """Обработка формы заявки на расчёт."""
        form = EstimateRequestForm(request.POST)
        if form.is_valid():
            try:
                vehicle_info = (
                    f"{form.cleaned_data['vehicle_brand']} "
                    f"{form.cleaned_data['vehicle_model']}"
                )
                logger.info(
                    "Заявка на расчёт от %s",
                    form.cleaned_data['name'],
                    extra={
                        'phone': form.cleaned_data['phone'],
                        'vehicle': vehicle_info,
                    },
                )
                messages.success(
                    request,
                    'Спасибо! Ваша заявка на расчёт принята.',
                )
                return redirect('website:estimate_success')
            except Exception as e:
                logger.error(
                    "Ошибка заявки на расчёт: %s",
                    e, exc_info=True,
                )
                messages.error(
                    request,
                    'Произошла ошибка. Попробуйте позже.',
                )
        return render(
            request,
            'website/estimate_request.html',
            {'form': form},
        )


class EstimateSuccessView(TemplateView):
    """Страница успешной отправки заявки на расчёт."""
    template_name = 'website/estimate_success.html'
