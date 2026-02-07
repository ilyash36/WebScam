"""
Представления для публичного сайта.
"""
import logging
from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.generic import TemplateView
from django.views import View
from .forms import BookingForm, FeedbackForm, EstimateRequestForm
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
                vehicle, vehicle_created = Vehicle.objects.get_or_create(
                    client=client,
                    license_plate=license_plate,
                    defaults={
                        'brand': form.cleaned_data['vehicle_brand'],
                        'model': form.cleaned_data['vehicle_model'],
                        'year': form.cleaned_data.get('vehicle_year'),
                    }
                )
                
                if not vehicle_created:
                    vehicle.brand = form.cleaned_data['vehicle_brand']
                    vehicle.model = form.cleaned_data['vehicle_model']
                    if form.cleaned_data.get('vehicle_year'):
                        vehicle.year = form.cleaned_data['vehicle_year']
                    vehicle.save()
                
                # Сохраняем сообщение в заметки автомобиля
                if form.cleaned_data.get('message'):
                    if vehicle.notes:
                        vehicle.notes += f"\n\n{form.cleaned_data['message']}"
                    else:
                        vehicle.notes = form.cleaned_data['message']
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
