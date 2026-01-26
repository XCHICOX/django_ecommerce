from django import forms
from django.forms import inlineformset_factory
from .models import DeliveryCategory, MenuItem, DeliveryZone, Combo, ComboSlot, DeliveryOrder, DeliveryOptional

class DeliveryCategoryForm(forms.ModelForm):
    class Meta:
        model = DeliveryCategory
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Ex: Pizzas Tradicionais'}),
        }

class MenuItemForm(forms.ModelForm):
    class Meta:
        model = MenuItem
        fields = ['name', 'description', 'price', 'category', 'image']

    def __init__(self, *args, **kwargs):
        tenant = kwargs.pop('tenant', None)
        super().__init__(*args, **kwargs)
        if tenant:
            self.fields['category'].queryset = DeliveryCategory.objects.filter(tenant=tenant)

class DeliveryZoneForm(forms.ModelForm):
    class Meta:
        model = DeliveryZone
        fields = ['neighborhood', 'delivery_fee']
        widgets = {
            'neighborhood': forms.TextInput(attrs={'placeholder': 'Ex: Centro'}),
            'delivery_fee': forms.NumberInput(attrs={'placeholder': 'Ex: 5.00'}),
        }

class ComboForm(forms.ModelForm):
    class Meta:
        model = Combo
        fields = ['name', 'description', 'price', 'image', 'is_available']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class ComboSlotForm(forms.ModelForm):
    class Meta:
        model = ComboSlot
        fields = ['allowed_category']

    def __init__(self, *args, **kwargs):
        tenant = kwargs.pop('tenant', None)
        super().__init__(*args, **kwargs)
        if tenant:
            self.fields['allowed_category'].queryset = DeliveryCategory.objects.filter(tenant=tenant)
            self.fields['allowed_category'].label = ""

ComboSlotFormSet = inlineformset_factory(
    Combo, ComboSlot, form=ComboSlotForm, extra=1, can_delete=True, fk_name='combo'
)

class DeliveryOrderForm(forms.ModelForm):
    class Meta:
        model = DeliveryOrder
        fields = [
            'customer_name', 'customer_whatsapp', 'delivery_address', 
            'delivery_zone', 'payment_method', 'change_for', 'observations'
        ]
        labels = {
            'customer_name': 'Seu Nome Completo',
            'customer_whatsapp': 'Seu WhatsApp (com DDD)',
            'delivery_address': 'Endereço de Entrega (Rua, Número, Complemento)',
            'delivery_zone': 'Bairro',
            'payment_method': 'Forma de Pagamento',
            'change_for': 'Precisa de troco para quanto? (Deixe em branco se não precisar)',
            'observations': 'Observações (Ex: sem cebola, ponto da carne, etc.)'
        }
        widgets = {
            'observations': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        tenant = kwargs.pop('tenant', None)
        super().__init__(*args, **kwargs)
        if tenant:
            self.fields['delivery_zone'].queryset = DeliveryZone.objects.filter(tenant=tenant)
            self.fields['delivery_zone'].empty_label = "Selecione seu bairro para ver a taxa"
            
class DeliveryOptionalForm(forms.ModelForm):
    class Meta:
        model = DeliveryOptional
        fields = ['category', 'name', 'price']

    def __init__(self, *args, **kwargs):
        tenant = kwargs.pop('tenant', None)
        super().__init__(*args, **kwargs)
        if tenant:
            self.fields['category'].queryset = DeliveryCategory.objects.filter(tenant=tenant)
            