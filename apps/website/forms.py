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
        label="Год выпуска",
        required=True,
        min_value=1900,
        widget=forms.NumberInput(attrs={'placeholder': '2010'}),
    )
    vehicle_vin = forms.CharField(
        max_length=17,
        label="VIN",
        required=True,
        widget=forms.TextInput(attrs={'placeholder': '17 символов'}),
    )
    vehicle_passport_number = forms.CharField(
        max_length=30,
        label="Паспорт ТС №",
        required=True,
        widget=forms.TextInput(attrs={'placeholder': '77 XX 654321'}),
    )
    vehicle_engine_volume = forms.CharField(
        max_length=12,
        label="Объём двигателя, л",
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'например, 1,4 или 2',
            'inputmode': 'decimal',
        }),
    )
    vehicle_engine_power = forms.CharField(
        max_length=30,
        label="Мощность двигателя, л.с.",
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'например, 105'}),
    )

    # Сообщение клиента
    message = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4}),
        label="Опишите проблему или желаемую услугу",
        required=False,
    )
    
    # Согласие на обработку персональных данных
    consent_personal_data = forms.BooleanField(
        required=True,
        label=(
            "Я согласен с обработкой персональных данных "
            "в соответствии с Федеральным законом №152-ФЗ"
        ),
        error_messages={
            'required': (
                'Необходимо дать согласие на обработку персональных данных.'
            ),
        },
    )
    
    class Meta:
        model = Client
        fields = ['first_name', 'phone', 'email']
        labels = {
            'first_name': 'Имя',
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
        self.fields['email'].required = True
        # Не блокируем повторную отправку для существующих клиентов —
        # get_or_create в view обработает дубликаты.
        self.fields['phone'].validators = [
            v for v in self.fields['phone'].validators
            if not hasattr(v, 'queryset')
        ]

    def clean_vehicle_engine_volume(self):
        """
        Нормализует объём в литрах: запятая или точка, диапазон ~0,5–10 л.

        В БД сохраняется с десятичной запятой («1,4»), как в привычной записи.
        """
        val = self.cleaned_data.get('vehicle_engine_volume')
        if val is None or not str(val).strip():
            raise forms.ValidationError('Укажите объём двигателя в литрах.')
        raw = str(val).strip().replace(' ', '').replace(',', '.')
        if not re.match(r'^\d{1,2}(\.\d{1,2})?$', raw):
            raise forms.ValidationError(
                'Укажите объём в литрах, например: 1,4 или 2 (от 0,5 до 10 л).',
            )
        try:
            liters = float(raw)
        except ValueError:
            raise forms.ValidationError(
                'Некорректное значение объёма.',
            ) from None
        if not (0.5 <= liters <= 10.0):
            raise forms.ValidationError(
                'Объём должен быть в диапазоне от 0,5 до 10 литров.',
            )
        if liters == int(liters):
            disp = str(int(liters))
        else:
            disp = f'{liters:.2f}'.rstrip('0').rstrip('.')
        return disp.replace('.', ',')

    def clean_vehicle_engine_power(self):
        """Мощность в л.с.: целое или с десятичной частью."""
        val = self.cleaned_data.get('vehicle_engine_power')
        if val is None or not str(val).strip():
            raise forms.ValidationError('Укажите мощность двигателя в л.с.')
        s = str(val).strip().replace(',', '.').replace(' ', '')
        if not re.match(r'^\d{1,4}(\.\d{1,2})?$', s):
            raise forms.ValidationError(
                'Укажите мощность числом, например: 105 или 97.5.',
            )
        try:
            hp = float(s)
        except ValueError:
            raise forms.ValidationError('Некорректное значение мощности.') from None
        if not (20.0 <= hp <= 2000.0):
            raise forms.ValidationError(
                'Проверьте значение мощности (л.с.).',
            )
        if abs(hp - round(hp)) < 1e-6:
            return str(int(round(hp)))
        return str(hp).replace('.', ',')

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
