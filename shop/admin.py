from django.contrib import admin
from .models import Tenant, Category

class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)

admin.site.register(Tenant)
admin.site.register(Category, CategoryAdmin)
