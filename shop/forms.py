from django import forms
from django.forms import inlineformset_factory
from .models import Product, ProductImage, Tenant

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        # Removemos 'image' pois ele não existe mais no modelo Product
        fields = ['category', 'name', 'description', 'price', 'stock']

class ProductImageForm(forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = ['image']

# Cria um formset para ProductImage, permitindo até 4 imagens
ProductImageFormSet = inlineformset_factory(
    Product, ProductImage, form=ProductImageForm, extra=4, max_num=4, can_delete=True
)

class SettingsForm(forms.ModelForm):
    class Meta:
        model = Tenant
        fields = ['mercadopago_api_key', 'pagseguro_api_key']
        labels = {
            'mercadopago_api_key': 'Chave da API do Mercado Pago',
            'pagseguro_api_key': 'Chave da API do PagSeguro',
        }
        widgets = {
            'mercadopago_api_key': forms.TextInput(attrs={'placeholder': 'Cole sua chave de API do Mercado Pago aqui', 'class': 'form-control'}),
            'pagseguro_api_key': forms.TextInput(attrs={'placeholder': 'Cole sua chave de API do PagSeguro aqui', 'class': 'form-control'}),
        }

class StorefrontSettingsForm(forms.ModelForm):
    class Meta:
        model = Tenant
        fields = ['logo', 'whatsapp_number', 'promotion_category', 'display_order']
        labels = {
            'whatsapp_number': 'WhatsApp (apenas números)',
        }
        widgets = {
            'whatsapp_number': forms.TextInput(attrs={'placeholder': 'Ex: 11999999999'}),
        }
