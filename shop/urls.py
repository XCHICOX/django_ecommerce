from django.urls import path
from . import views

urlpatterns = [
    # A URL principal do painel do lojista agora é a 'inicio_view'
    path('', views.inicio_view, name='inicio'),
    # A página de gerenciamento de produtos foi movida
    path('produtos/', views.product_view, name='produtos'),
    path('produtos/editar/<int:product_id>/', views.edit_product_view, name='edit_product'),
    path('produtos/excluir/<int:product_id>/', views.delete_product_view, name='delete_product'),
    path('get-category-fields/<int:category_id>/', views.get_category_fields, name='get_category_fields'),
    path('configurar-vitrine/', views.storefront_settings_view, name='storefront_settings'),
    path('configuracoes/', views.settings_view, name='configuracoes'),
    path('guest-login/', views.guest_login_view, name='guest_login'),
    path('carrinho/', views.view_cart, name='view_cart'),
    path('checkout/', views.checkout_view, name='checkout'),
    path('checkout/pagar/<str:gateway>/', views.create_cart_payment_view, name='create_cart_payment'),
    path('carrinho/remover/<int:item_id>/', views.remove_from_cart_view, name='remove_from_cart'),
    path('carrinho/atualizar/<int:item_id>/', views.update_cart_item_view, name='update_cart_item'),
    # Rotas para status de pagamento
    path('pagamento/sucesso/', views.payment_success_view, name='payment_success'),
    path('pagamento/falha/', views.payment_failure_view, name='payment_failure'),
    path('pagamento/pendente/', views.payment_pending_view, name='payment_pending'),
    # Webhook para notificações do Mercado Pago
    path('webhook/mercadopago/<int:tenant_id>/', views.mercadopago_webhook_view, name='mercadopago_webhook'),
    # Área do Cliente
    path('meus-pedidos/', views.client_orders_view, name='client_orders'),
    # Excluir carrinho do painel
    path('painel/carrinho/excluir/<int:cart_id>/', views.delete_cart_view, name='delete_cart_dashboard'),
]
