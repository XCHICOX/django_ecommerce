from django.contrib import admin
from .models import BarCategory, BarMenuItem, BarZone, BarComanda, BarComandaItem

admin.site.register(BarCategory)
admin.site.register(BarMenuItem)
admin.site.register(BarZone)
admin.site.register(BarComanda)
admin.site.register(BarComandaItem)
