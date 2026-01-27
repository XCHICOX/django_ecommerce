from django import forms
from .models import BarCategory, BarMenuItem

class BarCategoryForm(forms.ModelForm):
    class Meta:
        model = BarCategory
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Ex: Bebidas'}),
        }

class BarMenuItemForm(forms.ModelForm):
    class Meta:
        model = BarMenuItem
        fields = ['name', 'price', 'category']

    def __init__(self, *args, **kwargs):
        tenant = kwargs.pop('tenant', None)
        super().__init__(*args, **kwargs)
        if tenant:
            self.fields['category'].queryset = BarCategory.objects.filter(tenant=tenant)
