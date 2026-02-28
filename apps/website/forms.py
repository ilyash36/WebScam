"""
Формы для публичного сайта.
"""
import re

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
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Lada, Toyota, Renault...'}),
    )
    vehicle_model = forms.CharField(
        max_length=100,
        label="Модель автомобиля",
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Vesta, Camry, Logan...'}),
    )
    vehicle_year = forms.IntegerField(
        label="Год выпуска*",
        required=True,
        min_value=1900,
        widget=forms.NumberInput(attrs={'placeholder': '2010'}),
    )
    vehicle_vin = forms.CharField(
        max_length=17,
        label="VIN*",
        required=True,
        widget=forms.TextInput(attrs={'placeholder': '17 символов'}),
    )
    vehicle_license_plate = forms.CharField(
        max_length=20,
        label="Госномер",
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'А123BC77'}),
    )
    vehicle_color = forms.CharField(
        max_length=50,
        label="Цвет",
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Белый, Синий, Серый...'}),
    )
    vehicle_passport_number = forms.CharField(
        max_length=30,
        label="Паспорт ТС №*",
        required=True,
        widget=forms.TextInput(attrs={'placeholder': '77 XX 654321'}),
    )
    certificate_series_number = forms.CharField(
        max_length=20,
        label="Серия и номер СТС",
        required=False,
        widget=forms.TextInput(attrs={'placeholder': '77 66 555555'}),
    )
    vehicle_engine_volume = forms.CharField(
        max_length=6,
        label="Объём двигателя, куб.см",
        required=False,
        widget=forms.TextInput(attrs={
            'inputmode': 'numeric',
            'pattern': '[0-9]*',
        }),
    )
    vehicle_engine_power = forms.CharField(
        max_length=30,
        label="Мощность двигателя, л.с.*",
        required=True,
        widget=forms.TextInput(),
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
        self.fields['phone'].error_messages['unique'] = (
            'Клиент с таким телефоном уже существует.'
        )

    def clean_vehicle_engine_volume(self):
        """Оставляет только цифры (объём в куб.см)."""
        val = self.cleaned_data.get('vehicle_engine_volume')
        if not val or not val.strip():
            return ''
        digits = re.sub(r'\D', '', val)
        return digits[:6] if digits else ''

    def clean_vehicle_passport_number(self):
        """Форматирует ПТС в вид «XX XX YYYYYY»."""
        val = self.cleaned_data.get('vehicle_passport_number')
        if not val or not val.strip():
            return ''
        raw = re.sub(r'\s+', '', val.strip())
        if len(raw) < 10:
            return val.strip()
        m = re.match(r'^(\d{2})([А-ЯA-Z0-9]{2})(\d{6})$', raw, re.IGNORECASE)
        if m:
            return f'{m.group(1)} {m.group(2).upper()} {m.group(3)}'
        return val.strip()


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
