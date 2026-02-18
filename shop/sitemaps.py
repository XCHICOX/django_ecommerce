from django.contrib.sitemaps import Sitemap
from django.shortcuts import reverse
from .models import Product, Tenant

class StaticViewSitemap(Sitemap):
    priority = 0.5
    changefreq = 'daily'

    def items(self):
        return ['index', 'login', 'inicio', 'shop:inicio']

    def location(self, item):
        return reverse(item)

class ProductSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return Product.objects.all()

    def lastmod(self, obj):
        # Assumindo que o produto não tem um campo updated_at, mas poderíamos adicionar.
        # Por enquanto, retornamos None ou poderíamos usar a data atual se for crítico.
        return None

class TenantSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.9

    def items(self):
        return Tenant.objects.all()

class DeliveryMenuSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.9

    def items(self):
        # Only tenants that have delivery enabled or have menu items
        return Tenant.objects.filter(business_type__in=['delivery', 'bar_delivery'])

    def location(self, obj):
        return reverse('delivery:customer_menu', kwargs={'tenant_slug': obj.slug})
