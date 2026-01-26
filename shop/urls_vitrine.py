from django.urls import path
from . import views

urlpatterns = [
    path('', views.sales_view, name='vitrine'),
    path('produto/<int:product_id>/', views.product_detail_view, name='product_detail'),
    path('produto/<int:product_id>/pagar/<str:gateway>/', views.create_payment_view, name='create_payment'),
    path('produto/<int:product_id>/adicionar-carrinho/', views.add_to_cart_view, name='add_to_cart'),
]