"""
URL-маршруты для публичного сайта.
"""
from django.urls import path
from . import views

app_name = 'website'

urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    path('about/', views.AboutView.as_view(), name='about'),
    path('services/', views.ServicesView.as_view(), name='services'),
    path('contacts/', views.ContactsView.as_view(), name='contacts'),
    path('booking/', views.BookingView.as_view(), name='booking'),
    path('booking/ocr-sts/', views.ocr_sts_view, name='ocr_sts'),
    path('booking/success/', views.BookingSuccessView.as_view(), name='booking_success'),
    path('feedback/', views.FeedbackView.as_view(), name='feedback'),
    path('feedback/success/', views.FeedbackSuccessView.as_view(), name='feedback_success'),
    path('estimate/', views.EstimateRequestView.as_view(), name='estimate_request'),
    path('estimate/success/', views.EstimateSuccessView.as_view(), name='estimate_success'),
]
