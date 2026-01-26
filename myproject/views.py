from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from shop.models import Tenant # Importamos o Tenant do app shop (Core)

def index(request):
    """
    Exibe a página inicial com a lista de todas as lojas (tenants).
    """
    tenants = Tenant.objects.all()
    return render(request, 'index.html', {'tenants': tenants})

def login_view(request):
    """
    Lida com o login do usuário (lojista).
    """
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            # Redireciona para a view 'inicio' que vai despachar para o painel correto
            return redirect('inicio')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})

def logout_view(request):
    """
    Lida com o logout do usuário.
    """
    logout(request)
    return redirect('index')