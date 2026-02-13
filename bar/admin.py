from django.contrib import admin
from .models import BarCategory, BarMenuItem, BarZone, BarComanda, BarComandaItem, BarSystemNotice

@admin.register(BarSystemNotice)
class BarSystemNoticeAdmin(admin.ModelAdmin):
    list_display = ('content', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('content',)


admin.site.register(BarCategory)
admin.site.register(BarMenuItem)
admin.site.register(BarZone)
admin.site.register(BarComanda)
admin.site.register(BarComandaItem)
