"""myproject URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from myproject import views as myproject_views
from shop import views as shop_views
from django.conf import settings
from django.conf.urls.static import static

from django.contrib.sitemaps.views import sitemap
from shop.sitemaps import StaticViewSitemap, ProductSitemap, TenantSitemap, DeliveryMenuSitemap

sitemaps = {
    'static': StaticViewSitemap,
    'products': ProductSitemap,
    'tenants': TenantSitemap,
    'delivery': DeliveryMenuSitemap,
}

urlpatterns = [
    path('admin/', admin.site.urls),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('robots.txt', myproject_views.robots_txt),
    path('', myproject_views.index, name='index'),
    path('login/', myproject_views.login_view, name='login'),
    path('inicio/', shop_views.inicio_view, name='inicio'),
    path('logout/', myproject_views.logout_view, name='logout'),

    # Nova URL da vitrine individual, usando o slug do tenant
    path('vitrine/<slug:tenant_slug>/', include('shop.urls_vitrine')),

    # Inclui todas as URLs do app 'shop' sob o prefixo /produtos/
    path('produtos/', include(('shop.urls', 'shop'), namespace='shop')),

    # Inclui as URLs do app 'delivery'
    path('delivery/', include('delivery.urls')),
    # Inclui as URLs do app 'bar'
    path('bar/', include('bar.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
