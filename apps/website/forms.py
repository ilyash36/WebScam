"""
Формы для публичного сайта.
"""
from django import forms
from django.core.validators import RegexValidator
from apps.core.models import Client, Vehicle


class BookingForm(forms.ModelForm):
    """Форма записи на обслуживание."""
    
    phone_validator = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Телефон должен быть в формате: '+79991234567'"
    )
    
    # Данные автомобиля
    vehicle_brand = forms.CharField(
        max_length=100,
        label="Марка автомобиля",
        required=True
    )
    vehicle_model = forms.CharField(
        max_length=100,
        label="Модель автомобиля",
        required=True
    )
    vehicle_year = forms.IntegerField(
        label="Год выпуска",
        required=False,
        min_value=1900
    )
    vehicle_license_plate = forms.CharField(
        max_length=20,
        label="Госномер",
        required=False
    )
    
    # Сообщение клиента
    message = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4}),
        label="Опишите проблему или желаемую услугу",
        required=False,
    )
    
    # Согласия
    consent_sms = forms.BooleanField(
        required=False,
        label="Согласен получать SMS-уведомления",
    )
    consent_email = forms.BooleanField(
        required=False,
        label="Согласен получать Email-уведомления",
    )
    
    class Meta:
        model = Client
        fields = ['first_name', 'last_name', 'phone', 'email']
        labels = {
            'first_name': 'Имя',
            'last_name': 'Фамилия',
            'phone': 'Телефон',
            'email': 'Email',
        }
        widgets = {
            'phone': forms.TextInput(
                attrs={'placeholder': '+79991234567'}
            ),
            'email': forms.EmailInput(
                attrs={'placeholder': 'email@example.com'}
            ),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['phone'].validators.append(self.phone_validator)
        self.fields['phone'].required = True
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True


class FeedbackForm(forms.Form):
    """Форма обратной связи."""
    
    phone_validator = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Телефон должен быть в формате: '+79991234567'",
    )
    
    name = forms.CharField(
        max_length=200,
        label="Ваше имя",
        required=True,
    )
    phone = forms.CharField(
        max_length=20,
        label="Телефон",
        required=True,
        validators=[phone_validator],
        widget=forms.TextInput(attrs={'placeholder': '+79991234567'}),
    )
    email = forms.EmailField(
        label="Email",
        required=False,
        widget=forms.EmailInput(
            attrs={'placeholder': 'email@example.com'}
        ),
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 5}),
        label="Сообщение",
        required=True,
    )


class EstimateRequestForm(forms.Form):
    """Форма заявки на расчёт стоимости."""
    
    phone_validator = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Телефон должен быть в формате: '+79991234567'",
    )
    
    name = forms.CharField(
        max_length=200,
        label="Ваше имя",
        required=True,
    )
    phone = forms.CharField(
        max_length=20,
        label="Телефон",
        required=True,
        validators=[phone_validator],
        widget=forms.TextInput(attrs={'placeholder': '+79991234567'}),
    )
    email = forms.EmailField(
        label="Email",
        required=False,
        widget=forms.EmailInput(
            attrs={'placeholder': 'email@example.com'}
        ),
    )
    
    # Данные автомобиля
    vehicle_brand = forms.CharField(
        max_length=100,
        label="Марка автомобиля",
        required=True,
    )
    vehicle_model = forms.CharField(
        max_length=100,
        label="Модель автомобиля",
        required=True,
    )
    vehicle_year = forms.IntegerField(
        label="Год выпуска",
        required=False,
        min_value=1900,
    )
    
    # Описание работ
    work_description = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 5}),
        label="Опишите необходимые работы",
        required=True,
    )
