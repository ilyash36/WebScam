"""
Представления для публичного сайта.
"""
import base64
import logging
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.generic import TemplateView
from django.views import View
from django.views.decorators.http import require_http_methods

from .forms import BookingForm, FeedbackForm, EstimateRequestForm
from .ocr import ocr_via_workflow
from apps.core.models import Client, Vehicle

logger = logging.getLogger(__name__)


class IndexView(TemplateView):
    """Главная страница."""
    template_name = 'website/index.html'


class AboutView(TemplateView):
    """Страница "О нас"."""
    template_name = 'website/about.html'


class ServicesView(TemplateView):
    """Страница "Услуги и цены"."""
    template_name = 'website/services.html'


class ContactsView(TemplateView):
    """Страница "Контакты"."""
    template_name = 'website/contacts.html'


class BookingView(View):
    """Форма записи на обслуживание."""
    
    def get(self, request):
        """
        Отображение формы записи на обслуживание.
        
        Args:
            request: HTTP запрос
            
        Returns:
            HTTP ответ с формой записи
        """
        form = BookingForm()
        return render(request, 'website/booking.html', {'form': form})
    
    def post(self, request):
        """
        Обработка формы записи на обслуживание.
        
        Args:
            request: HTTP запрос с данными формы
            
        Returns:
            HTTP ответ с редиректом или формой с ошибками
        """
        form = BookingForm(request.POST)
        if form.is_valid():
            try:
                # Получаем или создаём клиента
                phone = form.cleaned_data['phone']
                client, created = Client.objects.get_or_create(
                    phone=phone,
                    defaults={
                        'first_name': form.cleaned_data['first_name'],
                        'last_name': form.cleaned_data['last_name'],
                        'email': form.cleaned_data.get('email'),
                        'attraction_channel': 'website',
                        'consent_sms': form.cleaned_data.get('consent_sms', False),
                        'consent_email': form.cleaned_data.get('consent_email', False),
                    }
                )
                
                # Обновляем данные клиента, если он уже существует
                if not created:
                    client.first_name = form.cleaned_data['first_name']
                    client.last_name = form.cleaned_data['last_name']
                    if form.cleaned_data.get('email'):
                        client.email = form.cleaned_data['email']
                    client.save()
                
                # Создаём или обновляем автомобиль
                license_plate = (
                    form.cleaned_data.get('vehicle_license_plate') or None
                )
                vin = form.cleaned_data.get('vehicle_vin') or None
                vin = (vin.replace(' ', '')[:17] if vin else None) or None
                color = form.cleaned_data.get('vehicle_color') or None
                defaults = {
                    'brand': form.cleaned_data['vehicle_brand'],
                    'model': form.cleaned_data['vehicle_model'],
                    'year': form.cleaned_data.get('vehicle_year'),
                    'vin': vin,
                    'color': color,
                }
                vehicle, vehicle_created = Vehicle.objects.get_or_create(
                    client=client,
                    license_plate=license_plate,
                    defaults=defaults
                )
                if not vehicle_created:
                    vehicle.brand = form.cleaned_data['vehicle_brand']
                    vehicle.model = form.cleaned_data['vehicle_model']
                    if form.cleaned_data.get('vehicle_year'):
                        vehicle.year = form.cleaned_data['vehicle_year']
                    vehicle.vin = vin
                    vehicle.color = color
                    vehicle.license_plate = license_plate
                    vehicle.save()
                
                # Собираем заметки: ПТС, СТС, объём двигателя + сообщение клиента
                sts_parts = []
                for key, label in [
                    ('vehicle_passport_number', 'Паспорт ТС №'),
                    ('certificate_series_number', 'Серия и номер СТС'),
                    ('vehicle_engine_volume', 'Объём двигателя'),
                    ('vehicle_engine_power', 'Мощность двигателя'),
                ]:
                    val = form.cleaned_data.get(key)
                    if val:
                        sts_parts.append(f"{label}: {val}")
                if sts_parts:
                    sts_block = "Данные СТС:\n" + "\n".join(sts_parts)
                    vehicle.notes = (
                        f"{sts_block}\n\n{vehicle.notes}"
                        if vehicle.notes else sts_block
                    )
                if form.cleaned_data.get('message'):
                    vehicle.notes = (
                        f"{vehicle.notes}\n\n{form.cleaned_data['message']}"
                        if vehicle.notes else form.cleaned_data['message']
                    )
                vehicle.save()
                
                logger.info(
                    (
                        f"Создана заявка на запись: клиент {client.id}, "
                        f"автомобиль {vehicle.id}"
                    ),
                    extra={
                        'client_id': client.id,
                        'vehicle_id': vehicle.id
                    }
                )
                
                messages.success(
                    request,
                    (
                        'Спасибо! Ваша заявка принята. '
                        'Мы свяжемся с вами в ближайшее время.'
                    )
                )
                return redirect('website:booking_success')
            
            except Exception as e:
                logger.error(
                    f"Ошибка при создании заявки: {e}",
                    exc_info=True
                )
                messages.error(
                    request,
                    (
                        'Произошла ошибка при отправке заявки. '
                        'Пожалуйста, попробуйте позже.'
                    )
                )
        
        return render(request, 'website/booking.html', {'form': form})


class BookingSuccessView(TemplateView):
    """Страница успешной отправки заявки."""
    template_name = 'website/booking_success.html'


@require_http_methods(['POST'])
def ocr_sts_view(request):
    """
    API: распознавание СТС через облачный Workflow (Vision + AI Agent).

    Принимает POST с полем 'image' (файл изображения).
    Возвращает JSON с полями для автозаполнения формы.
    """
    image_file = request.FILES.get('image')
    if not image_file:
        return JsonResponse(
            {'error': 'Не указано изображение'},
            status=400,
        )

    if image_file.size > 10 * 1024 * 1024:  # 10 MB
        return JsonResponse(
            {'error': 'Файл слишком большой (макс. 10 МБ)'},
            status=400,
        )

    workflow_url = getattr(settings, 'WORKFLOW_OCR_URL', '') or ''
    workflow_secret = getattr(settings, 'WORKFLOW_OCR_SECRET', '') or ''

    if not workflow_url or not workflow_secret:
        return JsonResponse(
            {'error': 'WORKFLOW_OCR_URL и WORKFLOW_OCR_SECRET не настроены'},
            status=503,
        )

    try:
        image_bytes = image_file.read()
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        api_key = getattr(settings, 'YANDEX_VISION_API_KEY', '') or ''
        folder_id = getattr(settings, 'YANDEX_FOLDER_ID', '') or ''

        data, err = ocr_via_workflow(
            image_base64,
            workflow_url,
            workflow_secret,
            api_key,
            folder_id,
        )
        if data:
            return JsonResponse({'success': True, 'data': data})
        return JsonResponse(
            {'error': err or 'Ошибка распознавания', 'data': {}},
            status=200,
        )
    except Exception as e:
        logger.error("Ошибка OCR СТС: %s", e, exc_info=True)
        return JsonResponse(
            {'error': str(e), 'data': {}},
            status=500,
        )


class FeedbackView(View):
    """Форма обратной связи."""
    
    def get(self, request):
        """
        Отображение формы обратной связи.
        
        Args:
            request: HTTP запрос
            
        Returns:
            HTTP ответ с формой обратной связи
        """
        form = FeedbackForm()
        return render(request, 'website/feedback.html', {'form': form})
    
    def post(self, request):
        """
        Обработка формы обратной связи.
        
        Args:
            request: HTTP запрос с данными формы
            
        Returns:
            HTTP ответ с редиректом или формой с ошибками
        """
        form = FeedbackForm(request.POST)
        if form.is_valid():
            try:
                # Здесь можно отправить email или сохранить в БД
                # Пока просто логируем
                logger.info(
                    f"Получена обратная связь от {form.cleaned_data['name']}",
                    extra={
                        'phone': form.cleaned_data['phone'],
                        'email': form.cleaned_data.get('email'),
                        'message': form.cleaned_data['message']
                    }
                )
                
                messages.success(
                    request,
                    (
                        'Спасибо за ваше сообщение! '
                        'Мы свяжемся с вами в ближайшее время.'
                    )
                )
                return redirect('website:feedback_success')
            
            except Exception as e:
                logger.error(
                    f"Ошибка при отправке обратной связи: {e}",
                    exc_info=True
                )
                messages.error(
                    request,
                    (
                        'Произошла ошибка при отправке сообщения. '
                        'Пожалуйста, попробуйте позже.'
                    )
                )
        
        return render(request, 'website/feedback.html', {'form': form})


class FeedbackSuccessView(TemplateView):
    """Страница успешной отправки обратной связи."""
    template_name = 'website/feedback_success.html'


class EstimateRequestView(View):
    """Форма заявки на расчёт стоимости."""
    
    def get(self, request):
        """
        Отображение формы заявки на расчёт стоимости.
        
        Args:
            request: HTTP запрос
            
        Returns:
            HTTP ответ с формой заявки на расчёт
        """
        form = EstimateRequestForm()
        return render(
            request,
            'website/estimate_request.html',
            {'form': form}
        )
    
    def post(self, request):
        """
        Обработка формы заявки на расчёт стоимости.
        
        Args:
            request: HTTP запрос с данными формы
            
        Returns:
            HTTP ответ с редиректом или формой с ошибками
        """
        form = EstimateRequestForm(request.POST)
        if form.is_valid():
            try:
                # Здесь можно отправить email или сохранить в БД
                # Пока просто логируем
                vehicle_info = (
                    f"{form.cleaned_data['vehicle_brand']} "
                    f"{form.cleaned_data['vehicle_model']}"
                )
                logger.info(
                    f"Получена заявка на расчёт от {form.cleaned_data['name']}",
                    extra={
                        'phone': form.cleaned_data['phone'],
                        'email': form.cleaned_data.get('email'),
                        'vehicle': vehicle_info,
                        'work_description': (
                            form.cleaned_data['work_description']
                        )
                    }
                )
                
                messages.success(
                    request,
                    (
                        'Спасибо! Ваша заявка на расчёт принята. '
                        'Мы свяжемся с вами в ближайшее время.'
                    )
                )
                return redirect('website:estimate_success')
            
            except Exception as e:
                logger.error(
                    f"Ошибка при отправке заявки на расчёт: {e}",
                    exc_info=True
                )
                messages.error(
                    request,
                    (
                        'Произошла ошибка при отправке заявки. '
                        'Пожалуйста, попробуйте позже.'
                    )
                )
        
        return render(request, 'website/estimate_request.html', {'form': form})


class EstimateSuccessView(TemplateView):
    """Страница успешной отправки заявки на расчёт."""
    template_name = 'website/estimate_success.html'
