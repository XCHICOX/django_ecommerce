from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db import models
from decimal import Decimal
import json
import datetime
from datetime import datetime, timedelta
from shop.models import Tenant
from .models import BarCategory, BarMenuItem, BarComanda, BarComandaItem, BarSystemNotice
from .forms import BarCategoryForm, BarMenuItemForm

@login_required(login_url='login')
def bar_dashboard(request):
    try:
        tenant = request.user.tenant
    except Tenant.DoesNotExist:
        return render(request, 'error.html', {'message': 'Você não tem uma loja associada.'})
    
    system_notices = BarSystemNotice.objects.filter(is_active=True)
    return render(request, 'bar/bar_inicio.html', {'system_notices': system_notices})

@login_required(login_url='login')
def toggle_bar_status(request):
    try:
        tenant = request.user.tenant
        tenant.is_open = not tenant.is_open
        tenant.save()
        status = "aberto" if tenant.is_open else "fechado"
        messages.success(request, f"Seu bar agora está {status} para pedidos!")
    except Tenant.DoesNotExist:
        messages.error(request, 'Você não tem um bar associado.')
    return redirect('bar:dashboard')

@login_required(login_url='login')
def menu_admin_view(request):
    try:
        tenant = request.user.tenant
    except Tenant.DoesNotExist:
        return render(request, 'error.html', {'message': 'Você não tem um bar associado.'})

    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        if form_type == 'category':
            category_form = BarCategoryForm(request.POST)
            if category_form.is_valid():
                category = category_form.save(commit=False)
                category.tenant = tenant
                category.save()
                messages.success(request, 'Categoria adicionada com sucesso!')
                return redirect('bar:menu_admin')
        elif form_type == 'item':
            item_form = BarMenuItemForm(request.POST, request.FILES, tenant=tenant)
            if item_form.is_valid():
                item = item_form.save(commit=False)
                item.tenant = tenant
                item.save()
                messages.success(request, 'Item adicionado com sucesso!')
                return redirect('bar:menu_admin')
    
    # Sempre criar formulários para GET requests
    category_form = BarCategoryForm()
    item_form = BarMenuItemForm(tenant=tenant)
    
    menu_items = BarMenuItem.objects.filter(tenant=tenant).select_related('category')
    categories = BarCategory.objects.filter(tenant=tenant)
    
    context = {
        'category_form': category_form,
        'item_form': item_form,
        'menu_items': menu_items,
        'categories': categories,
    }
    return render(request, 'bar/menu_admin.html', context)

def customer_menu_view(request, tenant_slug):
    tenant = get_object_or_404(Tenant, slug=tenant_slug)
    menu_items = BarMenuItem.objects.filter(tenant=tenant, is_available=True).select_related('category')
    context = {
        'tenant': tenant,
        'menu_items': menu_items,
    }
    return render(request, 'delivery/customer_menu.html', context)

@login_required(login_url='login')
def bar_reports_view(request):
    try:
        tenant = request.user.tenant
    except Tenant.DoesNotExist:
        return render(request, 'error.html', {'message': 'Você não tem um bar associado.'})
    
    # Filtro de Datas
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')

    # Define padrão: últimos 30 dias se não informado
    if not start_date_str:
        start_date = timezone.now().date() - timedelta(days=30)
    else:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()

    if not end_date_str:
        end_date = timezone.now().date()
    else:
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

    # Buscar comandas fechadas no intervalo
    comandas_fechadas = BarComanda.objects.filter(
        tenant=tenant,
        status='fechada',
        data_fechamento__date__range=[start_date, end_date]
    ).order_by('-data_fechamento')
    
    # Agregação por dia para o gráfico
    from django.db.models.functions import TruncDate
    from django.db.models import Sum, Count

    daily_sales = comandas_fechadas.annotate(date=TruncDate('data_fechamento')).values('date').annotate(total=Sum('total')).order_by('date')

    # Prepara dados para o Chart.js
    dates = []
    values = []
    sales_dict = {entry['date']: entry['total'] for entry in daily_sales}
    
    delta = end_date - start_date
    for i in range(delta.days + 1):
        day = start_date + timedelta(days=i)
        dates.append(day.strftime('%d/%m'))
        values.append(float(sales_dict.get(day, 0)))
    
    total_sales = comandas_fechadas.aggregate(Sum('total'))['total__sum'] or 0
    total_orders = comandas_fechadas.count()

    context = {
        'comandas_fechadas': comandas_fechadas,
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
        'dates_json': json.dumps(dates),
        'values_json': json.dumps(values),
        'total_sales': total_sales,
        'total_orders': total_orders,
        'tenant': tenant,
    }
    
    return render(request, 'bar/reports.html', context)

@login_required(login_url='login')
def mesas_view(request):
    try:
        tenant = request.user.tenant
    except Tenant.DoesNotExist:
        return render(request, 'error.html', {'message': 'Você não tem um bar associado.'})
    
    # Verificar se o bar está aberto
    if not tenant.is_open:
        messages.warning(request, 'O bar está fechado. Abra o bar no painel para acessar as mesas.')
        return redirect('bar:dashboard')
    
    # Buscar comandas abertas para determinar status das mesas
    comandas_abertas = BarComanda.objects.filter(tenant=tenant, status='aberta')
    mesas_ocupadas = {comanda.numero_mesa: comanda for comanda in comandas_abertas}
    
    # Criar lista de mesas
    mesas = []
    for i in range(1, tenant.numero_mesas + 1):
        if i in mesas_ocupadas:
            comanda = mesas_ocupadas[i]
            mesas.append({
                'numero': i,
                'status': 'ocupada',
                'total': comanda.total,
                'itens_count': comanda.itens.count()
            })
        else:
            mesas.append({
                'numero': i,
                'status': 'livre',
                'total': 0.00,
                'itens_count': 0
            })
    
    context = {
        'mesas': mesas,
        'tenant': tenant
    }
    return render(request, 'bar/mesas.html', context)

@login_required(login_url='login')
def comanda_view(request, numero_mesa):
    try:
        tenant = request.user.tenant
    except Tenant.DoesNotExist:
        return render(request, 'error.html', {'message': 'Você não tem um bar associado.'})
    
    # Verificar se o bar está aberto
    if not tenant.is_open:
        messages.error(request, 'O bar está fechado. Abra o bar no painel para gerenciar comandas.')
        return redirect('bar:dashboard')
    
    # Buscar ou criar comanda para a mesa
    comanda, created = BarComanda.objects.get_or_create(
        tenant=tenant,
        numero_mesa=numero_mesa,
        status='aberta',
        defaults={'total': 0.00}
    )
    
    # Buscar itens do cardápio disponíveis
    menu_items = BarMenuItem.objects.filter(tenant=tenant, is_available=True).select_related('category')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add_item':
            item_id = request.POST.get('item_id')
            quantidade = int(request.POST.get('quantidade', 1))
            observacao = request.POST.get('observacao', '')
            
            try:
                item = BarMenuItem.objects.get(id=item_id, tenant=tenant)
                
                # Verificar se item já existe na comanda
                comanda_item, item_created = BarComandaItem.objects.get_or_create(
                    comanda=comanda,
                    item=item,
                    defaults={
                        'quantidade': quantidade,
                        'preco_unitario': item.price,
                        'observacao': observacao
                    }
                )
                
                if not item_created:
                    # Se já existe, adicionar à quantidade
                    comanda_item.quantidade += quantidade
                    comanda_item.observacao = observacao
                    comanda_item.save()
                
                messages.success(request, f'{quantidade}x {item.name} adicionado(s) à comanda!')
                
            except BarMenuItem.DoesNotExist:
                messages.error(request, 'Item não encontrado!')
                
        elif action == 'remove_item':
            item_id = request.POST.get('item_id')
            try:
                item = BarComandaItem.objects.get(id=item_id, comanda=comanda)
                item_nome = item.item.name
                item.delete()
                
                # Recalcular o total da comanda após remover o item
                comanda.total = comanda.calcular_total()
                comanda.save()
                
                messages.success(request, f'{item_nome} removido da comanda!')
            except BarComandaItem.DoesNotExist:
                messages.error(request, 'Item não encontrado na comanda!')
                
        elif action == 'update_quantidade':
            item_id = request.POST.get('item_id')
            quantidade = int(request.POST.get('quantidade', 1))
            
            if quantidade <= 0:
                # Remover item se quantidade for 0
                try:
                    item = BarComandaItem.objects.get(id=item_id, comanda=comanda)
                    item_nome = item.item.name
                    item.delete()
                    
                    # Recalcular o total da comanda após remover o item
                    comanda.total = comanda.calcular_total()
                    comanda.save()
                    
                    messages.success(request, f'{item_nome} removido da comanda!')
                except BarComandaItem.DoesNotExist:
                    pass
            else:
                try:
                    item = BarComandaItem.objects.get(id=item_id, comanda=comanda)
                    item.quantidade = quantidade
                    item.save()
                    messages.success(request, f'Quantidade de {item.item.name} atualizada!')
                except BarComandaItem.DoesNotExist:
                    messages.error(request, 'Item não encontrado na comanda!')
        
        return redirect('bar:comanda', numero_mesa=numero_mesa)
    
    context = {
        'comanda': comanda,
        'menu_items': menu_items,
        'numero_mesa': numero_mesa,
        'tenant': tenant
    }
    return render(request, 'bar/comanda.html', context)

@login_required(login_url='login')
def salvar_comanda(request, numero_mesa):
    try:
        tenant = request.user.tenant
    except Tenant.DoesNotExist:
        return render(request, 'error.html', {'message': 'Você não tem um bar associado.'})
    
    try:
        comanda = BarComanda.objects.get(
            tenant=tenant,
            numero_mesa=numero_mesa,
            status='aberta'
        )
        
        # Verificar se o usuário selecionou gorjeta via GET ou POST
        incluir_gorjeta = request.GET.get('gorjeta_10') == 'on' or request.POST.get('gorjeta_10') == 'on'
        

        # Calcular total temporário com ou sem gorjeta
        total_base = sum(item.subtotal for item in comanda.itens.all())
        total_com_gorjeta = total_base * Decimal('1.1') if incluir_gorjeta else total_base
        total_sem_gorjeta = total_base
        
        # Preparar dados para impressão
        itens_impressao = []
        for item in comanda.itens.all():
            itens_impressao.append({
                'nome': item.item.name,
                'quantidade': item.quantidade,
                'preco_unitario': item.preco_unitario,
                'subtotal': item.subtotal,
                'observacao': item.observacao
            })
        
        dados_impressao = {
            'tenant_nome': tenant.name,
            'numero_mesa': numero_mesa,
            'data_hora': comanda.data_abertura,
            'itens': itens_impressao,
            'total_sem_gorjeta': total_sem_gorjeta,
            'gorjeta_10': incluir_gorjeta,
            'total_com_gorjeta': total_com_gorjeta
        }
        
        # Aqui seria integrada a impressora 80mm
        # Por enquanto, apenas salva no banco e mostra mensagem
        
        messages.success(request, f'Comanda da Mesa {numero_mesa} salva e enviada para impressão!')
        return redirect('bar:mesas')
        
    except BarComanda.DoesNotExist:
        messages.error(request, f'Não há comanda aberta para a Mesa {numero_mesa}!')
        return redirect('bar:mesas')

@login_required(login_url='login')
def imprimir_comanda(request, numero_mesa):
    try:
        tenant = request.user.tenant
    except Tenant.DoesNotExist:
        return render(request, 'error.html', {'message': 'Você não tem um bar associado.'})
    
    try:
        comanda = BarComanda.objects.get(
            tenant=tenant,
            numero_mesa=numero_mesa,
            status='aberta'
        )
        
        # Verificar se o usuário selecionou gorjeta via parâmetro GET
        incluir_gorjeta = request.GET.get('gorjeta_10') == 'on'
        
        # Calcular total temporário com ou sem gorjeta
        total_base = sum(item.subtotal for item in comanda.itens.all())
        total_com_gorjeta = total_base * Decimal('1.1') if incluir_gorjeta else total_base
        total_sem_gorjeta = total_base
        
        # Preparar dados para impressão 80mm térmica
        itens_impressao = []
        for item in comanda.itens.all():
            itens_impressao.append({
                'nome': item.item.name,
                'quantidade': item.quantidade,
                'preco_unitario': item.preco_unitario,
                'subtotal': item.subtotal,
                'observacao': item.observacao
            })
        
        dados_impressao = {
            'tenant_nome': tenant.name,
            'numero_mesa': numero_mesa,
            'data_hora': comanda.data_abertura,
            'itens': itens_impressao,
            'total_sem_gorjeta': total_sem_gorjeta,
            'gorjeta_10': incluir_gorjeta,
            'total_com_gorjeta': total_com_gorjeta
        }
        
        context = {
            'dados': dados_impressao,
            'comanda': comanda,
        }
        
        return render(request, 'bar/imprimir_comanda.html', context)
        
    except BarComanda.DoesNotExist:
        messages.error(request, f'Não há comanda aberta para a Mesa {numero_mesa}!')
        return redirect('bar:mesas')

@login_required(login_url='login')
def reimprimir_comanda(request, comanda_id):
    try:
        tenant = request.user.tenant
    except Tenant.DoesNotExist:
        return render(request, 'error.html', {'message': 'Você não tem um bar associado.'})

    comanda = get_object_or_404(BarComanda, id=comanda_id, tenant=tenant)

    # Preparar dados para impressão 80mm térmica
    itens_impressao = []
    for item in comanda.itens.all():
        itens_impressao.append({
            'nome': item.item.name,
            'quantidade': item.quantidade,
            'preco_unitario': item.preco_unitario,
            'subtotal': item.subtotal,
            'observacao': item.observacao
        })

    dados_impressao = {
        'tenant_nome': tenant.name,
        'numero_mesa': comanda.numero_mesa,
        'data_hora': comanda.data_abertura,
        'itens': itens_impressao,
        'total_sem_gorjeta': comanda.total / Decimal('1.1') if comanda.gorjeta_10 else comanda.total,
        'gorjeta_10': comanda.gorjeta_10,
        'total_com_gorjeta': comanda.total
    }

    context = {
        'dados': dados_impressao,
        'comanda': comanda,
    }

    return render(request, 'bar/imprimir_comanda.html', context)

@login_required(login_url='login')
def excluir_comanda(request, comanda_id):
    try:
        tenant = request.user.tenant
    except Tenant.DoesNotExist:
        return JsonResponse({'error': 'Você não tem um bar associado.'}, status=403)
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Método não permitido.'}, status=405)
    
    # Verificar senha
    senha = request.POST.get('senha')
    if not senha:
        return JsonResponse({'error': 'Senha é obrigatória.'}, status=400)
    
    # Verificar se a senha está correta
    if not request.user.check_password(senha):
        return JsonResponse({'error': 'Senha incorreta.'}, status=403)
    
    try:
        comanda = BarComanda.objects.get(
            id=comanda_id,
            tenant=tenant,
            status='fechada'  # Só permite excluir comandas fechadas
        )
        
        numero_mesa = comanda.numero_mesa
        comanda.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Comanda da Mesa {numero_mesa} excluída com sucesso!'
        })
        
    except BarComanda.DoesNotExist:
        return JsonResponse({'error': 'Comanda não encontrada ou não pode ser excluída.'}, status=404)
    except Exception as e:
        return JsonResponse({'error': f'Erro ao excluir comanda: {str(e)}'}, status=500)

@login_required(login_url='login')
def fechar_comanda(request, numero_mesa):
    try:
        tenant = request.user.tenant
    except Tenant.DoesNotExist:
        return render(request, 'error.html', {'message': 'Você não tem um bar associado.'})
    
    try:
        comanda = BarComanda.objects.get(
            tenant=tenant,
            numero_mesa=numero_mesa,
            status='aberta'
        )
        
        # Atualiza a taxa de serviço ANTES de calcular o total
        comanda.gorjeta_10 = request.POST.get('gorjeta_10') == 'on'
        
        # Recalcula o total final com base na taxa de serviço
        comanda.total = comanda.calcular_total()
        
        # Fecha a comanda
        comanda.status = 'fechada'
        comanda.data_fechamento = timezone.now()
        comanda.save()
        
        messages.success(request, f'Comanda da Mesa {numero_mesa} fechada e salva nos relatórios!')
        return redirect('bar:reports')
        
    except BarComanda.DoesNotExist:
        messages.error(request, f'Não há comanda aberta para a Mesa {numero_mesa}!')
        return redirect('bar:mesas')

@login_required(login_url='login')
def configuracoes_view(request):
    try:
        tenant = request.user.tenant
    except Tenant.DoesNotExist:
        return render(request, 'error.html', {'message': 'Você não tem um bar associado.'})
    
    if request.method == 'POST':
        tenant.numero_mesas = request.POST.get('numero_mesas', 10)
        tenant.permitir_gorjeta_10 = 'permitir_gorjeta_10' in request.POST
        tenant.save()
        messages.success(request, 'Configurações salvas com sucesso!')
        return redirect('bar:configuracoes')
    
    context = {
        'tenant': tenant
    }
    return render(request, 'bar/configuracoes.html', context)
