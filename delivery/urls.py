from django.urls import path
from . import views

app_name = 'delivery'

urlpatterns = [
    path('painel/', views.delivery_dashboard, name='dashboard'),
    path('toggle-status/', views.toggle_store_status, name='toggle_status'),
    path('cardapio-admin/', views.menu_admin_view, name='menu_admin'),
    path('combos/', views.combo_admin_view, name='combo_admin'),
    path('delete_combo/<int:combo_id>/', views.delete_combo_view, name='delete_combo'),
    path('toggle_combo/<int:combo_id>/', views.toggle_combo_availability, name='toggle_combo'),
    path('cardapio/<slug:tenant_slug>/', views.customer_menu_view, name='customer_menu'),
    path('cart/add/<slug:tenant_slug>/', views.add_to_delivery_cart, name='add_to_cart'),
    path('cart/remove/<slug:tenant_slug>/<str:cart_key>/', views.remove_from_delivery_cart, name='remove_from_cart'),
    path('checkout/<slug:tenant_slug>/', views.delivery_checkout_view, name='checkout'),
    path('pedido-confirmado/<int:order_id>/', views.delivery_order_confirmation_view, name='order_confirmation'),
    path('pedidos/', views.orders_list_view, name='orders_list'),
    path('delete_order/<int:order_id>/', views.delete_order_view, name='delete_order'),
    path('meus-pedidos/<slug:tenant_slug>/', views.get_customer_orders, name='get_customer_orders'),
    path('repetir-pedido/<slug:tenant_slug>/<int:order_id>/', views.repeat_order, name='repeat_order'),
    path('api/ultimos-pedidos/', views.get_latest_order_id, name='get_latest_order_id'),
    path('relatorios/', views.delivery_reports_view, name='reports'),
    path('vendas/', views.delivery_pos_view, name='pos'),
    path('cardapio-online/', views.menu_online_view, name='menu_online'),
    path('menu-online/<slug:tenant_slug>/', views.menu_online_public_view, name='menu_online_public'),
]
