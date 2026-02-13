from django.contrib import admin
from .models import SystemNotice, DeliveryOrder, MenuItem, DeliveryCategory, DeliveryZone, Combo, DeliveryOptional

@admin.register(SystemNotice)
class SystemNoticeAdmin(admin.ModelAdmin):
    list_display = ('content', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('content',)

@admin.register(DeliveryOrder)
class DeliveryOrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'tenant', 'customer_name', 'final_total', 'status', 'created_at')
    list_filter = ('status', 'tenant')
    search_fields = ('customer_name', 'customer_whatsapp')

admin.site.register(MenuItem)
admin.site.register(DeliveryCategory)
admin.site.register(DeliveryZone)
admin.site.register(Combo)
admin.site.register(DeliveryOptional)
