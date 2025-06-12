from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import UserProfile
from django import forms
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _
from .models import Order


class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    phone = forms.CharField(max_length=20, required=False)
    address = forms.CharField(widget=forms.Textarea, required=False)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2', 'phone', 'address']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            UserProfile.objects.create(
                user=user,
                phone=self.cleaned_data['phone'],
                address=self.cleaned_data['address'],
                role='user'  # Default role
            )
        return user
    
from .models import Product, Category

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'title', 
            'description', 
            'price', 
            'image', 
            'category',
            'is_active'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }


class CheckoutForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = [
            'full_name', 'email', 'phone', 'shipping_address', 
            'payment_method', 'card_number', 'card_expiry', 'card_cvv', 'comments'
        ]
        widgets = {
            'comments': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['full_name'].required = True
        self.fields['email'].required = True
        self.fields['phone'].required = True
        self.fields['shipping_address'].required = True
        
        # Добавляем валидаторы
        self.fields['phone'].validators = [
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message=_("Номер телефона должен быть в формате: '+999999999'. Максимум 15 цифр.")
            )
        ]
        
        # Для карты
        self.fields['card_number'].validators = [
            RegexValidator(
                regex=r'^\d{16}$',
                message=_("Номер карты должен содержать ровно 16 цифр.")
            )
        ]
        
        self.fields['card_expiry'].validators = [
            RegexValidator(
                regex=r'^(0[1-9]|1[0-2])\/?([0-9]{2})$',
                message=_("Формат срока действия: ММ/ГГ (например: 12/25)")
            )
        ]
        
        self.fields['card_cvv'].validators = [
            RegexValidator(
                regex=r'^\d{3}$',
                message=_("CVV код должен содержать ровно 3 цифры.")
            )
        ]
    
    def clean(self):
        cleaned_data = super().clean()
        payment_method = cleaned_data.get('payment_method')
        card_number = cleaned_data.get('card_number')
        card_expiry = cleaned_data.get('card_expiry')
        card_cvv = cleaned_data.get('card_cvv')
        
        # Проверка данных карты, если выбран соответствующий способ оплаты
        if payment_method == 'card':
            if not card_number:
                self.add_error('card_number', _('Это поле обязательно для выбранного способа оплаты.'))
            if not card_expiry:
                self.add_error('card_expiry', _('Это поле обязательно для выбранного способа оплаты.'))
            if not card_cvv:
                self.add_error('card_cvv', _('Это поле обязательно для выбранного способа оплаты.'))
        
        return cleaned_data