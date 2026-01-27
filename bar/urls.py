from django.urls import path
from . import views

app_name = 'bar'

urlpatterns = [
    path('painel/', views.bar_dashboard, name='dashboard'),
    path('toggle-status/', views.toggle_bar_status, name='toggle_status'),
    path('cardapio-admin/', views.menu_admin_view, name='menu_admin'),
    path('mesas/', views.mesas_view, name='mesas'),
    path('comanda/<int:numero_mesa>/', views.comanda_view, name='comanda'),
    path('salvar-comanda/<int:numero_mesa>/', views.salvar_comanda, name='salvar_comanda'),
    path('imprimir-comanda/<int:numero_mesa>/', views.imprimir_comanda, name='imprimir_comanda'),
    path('reimprimir-comanda/<int:comanda_id>/', views.reimprimir_comanda, name='reimprimir_comanda'),
    path('excluir-comanda/<int:comanda_id>/', views.excluir_comanda, name='excluir_comanda'),
    path('fechar-comanda/<int:numero_mesa>/', views.fechar_comanda, name='fechar_comanda'),
    path('cardapio/<slug:tenant_slug>/', views.customer_menu_view, name='cardapio'),
    path('configuracoes/', views.configuracoes_view, name='configuracoes'),
    path('relatorios/', views.bar_reports_view, name='reports'),
]