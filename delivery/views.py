from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from django.utils import timezone
from datetime import timedelta, datetime
from django.db.models import Sum, Count, Max
from django.db.models.functions import TruncDate
from urllib.parse import quote
from shop.models import Tenant # Importamos o Tenant do app shop (Core)
from .models import DeliveryCategory, MenuItem, DeliveryZone, Combo, DeliveryOrder, DeliveryOrderItem, DeliveryOptional, MenuOnlineImage
from .forms import DeliveryCategoryForm, MenuItemForm, DeliveryZoneForm, ComboForm, ComboSlotFormSet, DeliveryOrderForm, DeliveryOptionalForm

@login_required(login_url='login')
def delivery_dashboard(request):
    try:
        tenant = request.user.tenant
    except Tenant.DoesNotExist:
        return render(request, 'error.html', {'message': 'Você não tem uma loja associada.'})

    # Aqui futuramente carregaremos pedidos de delivery, cardápio, etc.
    # Por enquanto, renderiza o template base do delivery
    return render(request, 'delivery_inicio.html')

@login_required(login_url='login')
def toggle_store_status(request):
    try:
        tenant = request.user.tenant
        tenant.is_open = not tenant.is_open
        tenant.save()
        status = "aberta" if tenant.is_open else "fechada"
        messages.success(request, f"Sua loja agora está {status} para pedidos!")
    except Tenant.DoesNotExist:
        messages.error(request, 'Você não tem uma loja associada.')
    return redirect('delivery:dashboard')

@login_required(login_url='login')
def menu_admin_view(request):
    try:
        tenant = request.user.tenant
    except Tenant.DoesNotExist:
        return render(request, 'error.html', {'message': 'Você não tem uma loja associada.'})

    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        
        if form_type == 'category':
            category_form = DeliveryCategoryForm(request.POST)
            if category_form.is_valid():
                category = category_form.save(commit=False)
                category.tenant = tenant
                category.save()
                messages.success(request, 'Categoria adicionada com sucesso!')
                return redirect('delivery:menu_admin')
        
        elif form_type == 'item':
            item_form = MenuItemForm(request.POST, request.FILES, tenant=tenant)
            if item_form.is_valid():
                item = item_form.save(commit=False)
                item.tenant = tenant
                item.save()
                messages.success(request, 'Item adicionado com sucesso!')
                return redirect('delivery:menu_admin')

        elif form_type == 'zone':
            zone_form = DeliveryZoneForm(request.POST)
            if zone_form.is_valid():
                zone = zone_form.save(commit=False)
                zone.tenant = tenant
                zone.save()
                messages.success(request, 'Bairro adicionado com sucesso!')
                return redirect('delivery:menu_admin')

        elif form_type == 'optional':
            optional_form = DeliveryOptionalForm(request.POST, tenant=tenant)
            if optional_form.is_valid():
                optional = optional_form.save(commit=False)
                optional.tenant = tenant
                optional.save()
                messages.success(request, 'Opcional adicionado com sucesso!')
                return redirect('delivery:menu_admin')

        # Lógica de Exclusão
        elif form_type == 'delete_item':
            item_id = request.POST.get('item_id')
            item = get_object_or_404(MenuItem, id=item_id, tenant=tenant)
            item.delete()
            messages.success(request, 'Item excluído com sucesso!')
            return redirect('delivery:menu_admin')

        elif form_type == 'delete_category':
            cat_id = request.POST.get('category_id')
            category = get_object_or_404(DeliveryCategory, id=cat_id, tenant=tenant)
            category.delete()
            messages.success(request, 'Categoria excluída com sucesso!')
            return redirect('delivery:menu_admin')

        elif form_type == 'delete_optional':
            opt_id = request.POST.get('optional_id')
            optional = get_object_or_404(DeliveryOptional, id=opt_id, tenant=tenant)
            optional.delete()
            messages.success(request, 'Opcional excluído com sucesso!')
            return redirect('delivery:menu_admin')

        elif form_type == 'delete_zone':
            zone_id = request.POST.get('zone_id')
            zone = get_object_or_404(DeliveryZone, id=zone_id, tenant=tenant)
            zone.delete()
            messages.success(request, 'Bairro excluído com sucesso!')
            return redirect('delivery:menu_admin')
    
    category_form = DeliveryCategoryForm()
    item_form = MenuItemForm(tenant=tenant)
    zone_form = DeliveryZoneForm()
    optional_form = DeliveryOptionalForm(tenant=tenant)

    categories = DeliveryCategory.objects.filter(tenant=tenant)
    menu_items = MenuItem.objects.filter(tenant=tenant).select_related('category')
    delivery_zones = DeliveryZone.objects.filter(tenant=tenant)
    optionals = DeliveryOptional.objects.filter(tenant=tenant).select_related('category')

    context = {
        'category_form': category_form, 'item_form': item_form, 'zone_form': zone_form, 'optional_form': optional_form,
        'categories': categories, 'menu_items': menu_items, 'delivery_zones': delivery_zones, 'optionals': optionals,
    }
    return render(request, 'delivery/menu_admin.html', context)

@login_required(login_url='login')
def combo_admin_view(request):
    try:
        tenant = request.user.tenant
    except Tenant.DoesNotExist:
        return render(request, 'error.html', {'message': 'Você não tem uma loja associada.'})

    # Inicializa formulários vazios por padrão (evita erro UnboundLocalError)
    form = ComboForm()
    formset = ComboSlotFormSet(instance=Combo(), form_kwargs={'tenant': tenant})

    if request.method == 'POST':
        form = ComboForm(request.POST, request.FILES)
        
        if form.is_valid():
            combo = form.save(commit=False)
            combo.tenant = tenant
            combo.save()
            
            formset = ComboSlotFormSet(request.POST, instance=combo, form_kwargs={'tenant': tenant})
            if formset.is_valid():
                formset.save()
                messages.success(request, f"Combo '{combo.name}' criado com sucesso!")
                return redirect('delivery:combo_admin')
            else:
                combo.delete()
                messages.error(request, 'Erro ao salvar as opções do combo. Verifique os campos.')
        else:
            # Se o form principal for inválido, recria o formset com os dados do POST para não perder o que foi digitado (visualização)
            formset = ComboSlotFormSet(request.POST, instance=Combo(), form_kwargs={'tenant': tenant})

    combos = Combo.objects.filter(tenant=tenant).prefetch_related('slots__allowed_category')

    context = { 'form': form, 'formset': formset, 'combos': combos }
    return render(request, 'delivery/combo_admin.html', context)

def customer_menu_view(request, tenant_slug):
    """
    Exibe o cardápio público para o cliente, com combos e itens por categoria.
    """
    tenant = get_object_or_404(Tenant, slug=tenant_slug)

    # Busca combos e itens disponíveis
    combos = Combo.objects.filter(tenant=tenant, is_available=True).prefetch_related('slots__allowed_category')
    menu_items = MenuItem.objects.filter(tenant=tenant, is_available=True).select_related('category')

    # Ordena combos por caracteres especiais/números primeiro, depois alfabéticamente
    def sort_key(combo):
        name = combo.name.strip()
        if not name:
            return ('z', '')  # Coloca vazio no final
        
        first_char = name[0]
        is_special_or_number = not first_char.isalpha()
        
        # Tupla para ordenação: (é alfabético, nome normalizado)
        # É alfabético? 1 (sim) ou 0 (não) - números e especiais vêm primeiro
        return (is_special_or_number is False, name.lower())
    
    combos = sorted(combos, key=sort_key)

    # Prepara dados em formato JSON para o JavaScript do modal de combos
    combos_list_for_js = []
    for combo in combos:
        c = {'id': combo.id, 'name': combo.name, 'price': str(combo.price), 'description': combo.description or '', 'image': combo.image.url if combo.image else None, 'slots': []}
        for slot in combo.slots.all():
            c['slots'].append({'allowed_category': {'id': slot.allowed_category.id, 'name': slot.allowed_category.name}})
        combos_list_for_js.append(c)

    menu_items_list_for_js = list(menu_items.values('id', 'name', 'price', 'category_id'))
    
    # Prepara lista de opcionais para o JS
    optionals = DeliveryOptional.objects.filter(tenant=tenant)
    optionals_list_for_js = list(optionals.values('id', 'name', 'price', 'category_id'))

    # Calcula o total de itens no carrinho para exibir no ícone flutuante
    cart = request.session.get('delivery_cart', {})
    cart_total_items = sum(cart.values())

    context = {
        'tenant': tenant,
        'combos': combos,
        'menu_items': menu_items,
        'combos_json': json.dumps(combos_list_for_js),
        'menu_items_json': json.dumps(menu_items_list_for_js, default=str),
        'optionals_json': json.dumps(optionals_list_for_js, default=str),
        'cart_total_items': cart_total_items,
    }
    return render(request, 'delivery/customer_menu.html', context)

@csrf_exempt
def add_to_delivery_cart(request, tenant_slug):
    # Verifica se a loja está aberta antes de adicionar
    tenant = get_object_or_404(Tenant, slug=tenant_slug)
    if not tenant.is_open:
        return JsonResponse({'status': 'error', 'message': 'A loja está fechada no momento.'}, status=400)

    if request.method == 'POST':
        data = json.loads(request.body)
        item_key = data.get('item_key') # Chave pode ser 'item_1' ou 'combo_1_10_12'
        
        # Se não vier a chave pronta (item_key), tentamos construir baseada no ID e Tipo
        if not item_key:
            item_id = data.get('item_id')
            item_type = data.get('item_type')
            if item_id and item_type:
                if item_type == 'item':
                    item_key = f"item_{item_id}"
                elif item_type == 'combo':
                    item_key = f"combo_{item_id}"

        if not item_key:
            return JsonResponse({'status': 'error', 'message': 'Chave do item não fornecida.'}, status=400)
        
        cart = request.session.get('delivery_cart', {})
        
        cart[item_key] = cart.get(item_key, 0) + 1
        request.session['delivery_cart'] = cart
        
        total_items = sum(cart.values())
        
        return JsonResponse({'status': 'ok', 'cart_total_items': total_items})
    return JsonResponse({'status': 'error'}, status=400)

def remove_from_delivery_cart(request, tenant_slug, cart_key):
    cart = request.session.get('delivery_cart', {})
    
    if cart_key in cart:
        del cart[cart_key]
    
    request.session['delivery_cart'] = cart
    
    return redirect('delivery:checkout', tenant_slug=tenant_slug)

def delivery_checkout_view(request, tenant_slug):
    tenant = get_object_or_404(Tenant, slug=tenant_slug)
    cart_session = request.session.get('delivery_cart', {})
    
    if not cart_session:
        messages.warning(request, "Seu carrinho está vazio.")
        return redirect('delivery:customer_menu', tenant_slug=tenant.slug)

    cart_items = []
    items_total = 0
    for key, quantity in cart_session.items():
        parts = key.split('_')
        item_type = parts[0]
        
        if item_type == 'item':
            try:
                item_id = parts[1]
                # Verifica se há IDs de opcionais na chave (item_ID_Opt1_Opt2)
                optional_ids = parts[2:] if len(parts) > 2 else []

                item = MenuItem.objects.get(id=item_id, tenant=tenant)
                
                # Calcula custo dos opcionais
                selected_optionals = []
                optionals_cost = 0
                if optional_ids:
                    selected_optionals = list(DeliveryOptional.objects.filter(id__in=optional_ids, tenant=tenant))
                    optionals_cost = sum(opt.price for opt in selected_optionals)

                subtotal = (item.price + optionals_cost) * quantity
                items_total += subtotal
                cart_items.append({
                    'key': key, 
                    'name': item.name,
                    'quantity': quantity, 
                    'subtotal': subtotal,
                    'is_combo': False,
                    'optionals': selected_optionals # Passa os objetos para o template
                })
            except (MenuItem.DoesNotExist, IndexError):
                continue
        elif item_type == 'combo':
            try:
                combo_id = parts[1]
                choice_ids = parts[2:]
                combo = Combo.objects.get(id=combo_id, tenant=tenant)
                choices = []
                for choice_id in choice_ids:
                    try:
                        item = MenuItem.objects.get(id=choice_id, tenant=tenant)
                        choices.append(item)
                    except MenuItem.DoesNotExist:
                        pass
                
                subtotal = combo.price * quantity
                items_total += subtotal
                cart_items.append({
                    'key': key, 
                    'name': combo.name,
                    'choices': choices,
                    'quantity': quantity, 
                    'subtotal': subtotal, 
                    'is_combo': True
                })
            except (Combo.DoesNotExist, IndexError):
                continue

    if request.method == 'POST':
        form = DeliveryOrderForm(request.POST, tenant=tenant)
        if form.is_valid():
            order = form.save(commit=False)
            order.tenant = tenant
            order.items_total = items_total
            order.delivery_fee = form.cleaned_data.get('delivery_zone').delivery_fee if form.cleaned_data.get('delivery_zone') else 0
            order.final_total = order.items_total + order.delivery_fee
            order.save()

            # Salva os itens do pedido no banco de dados
            for cart_item in cart_items:
                if cart_item['is_combo']:
                    # Para combos, salva o nome do combo e as escolhas
                    choices_formatted = "\n".join([f"* {c.category.name}: {c.name}" for c in cart_item['choices']])
                    item_name_with_choices = f"{cart_item['name']}\n{choices_formatted}"
                    DeliveryOrderItem.objects.create(
                        order=order, 
                        item_name=item_name_with_choices, 
                        quantity=cart_item['quantity'], 
                        price=cart_item['subtotal'] / cart_item['quantity'], # Preço de um combo
                        original_cart_key=cart_item['key']
                    )
                else:
                    # Para itens normais
                    item_name_desc = cart_item['name']
                    if cart_item.get('optionals'):
                        opts_str = ", ".join([f"*{opt.name}" for opt in cart_item['optionals']])
                        item_name_desc += f" ({opts_str})"

                    DeliveryOrderItem.objects.create(
                        order=order, 
                        item_name=item_name_desc, 
                        quantity=cart_item['quantity'], 
                        price=cart_item['subtotal'] / cart_item['quantity'], # Preço de um item
                        original_cart_key=cart_item['key']
                    )
            
            del request.session['delivery_cart']
            return redirect('delivery:order_confirmation', order_id=order.id)
    else:
        form = DeliveryOrderForm(tenant=tenant)

    delivery_zones = DeliveryZone.objects.filter(tenant=tenant)
    zones_data = {zone.id: float(zone.delivery_fee) for zone in delivery_zones}

    context = {
        'tenant': tenant,
        'form': form,
        'cart_items': cart_items,
        'items_total': items_total,
        'zones_data_json': json.dumps(zones_data),
    }
    return render(request, 'delivery/checkout.html', context)

def delivery_order_confirmation_view(request, order_id):
    order = get_object_or_404(DeliveryOrder, id=order_id)
    
    items_list = [f"{item.quantity}x {item.item_name}" for item in order.items.all()]
    items_text = "\n".join(items_list)

    address_full = f"{order.delivery_address}"
    if order.delivery_zone:
        address_full += f" - {order.delivery_zone.neighborhood}"

    payment_full = order.get_payment_method_display()
    if order.payment_method == 'dinheiro' and order.change_for:
        payment_full += f" (Troco para R$ {order.change_for:.2f})"

    whatsapp_message = (
        f"*Pedido #{order.id} Realizado!*\n"
        f"------------------------------\n"
        f"*Cliente:* {order.customer_name}\n"
        f"*Telefone:* {order.customer_whatsapp}\n"
        f"*Endereço:* {address_full}\n"
        f"------------------------------\n"
        f"*Itens:*\n{items_text}\n"
    )

    if order.observations:
        whatsapp_message += f"*Obs:* {order.observations}\n"

    whatsapp_message += (
        f"------------------------------\n"
        f"*Taxa Entrega:* R$ {order.delivery_fee:.2f}\n"
        f"*Total:* R$ {order.final_total:.2f}\n"
        f"*Pagamento:* {payment_full}"
    )

    whatsapp_message = quote(whatsapp_message)

    context = {'order': order, 'whatsapp_message': whatsapp_message}
    return render(request, 'delivery/order_confirmation.html', context)

@login_required(login_url='login')
def orders_list_view(request):
    try:
        tenant = request.user.tenant
    except Tenant.DoesNotExist:
        return render(request, 'error.html', {'message': 'Você não tem uma loja associada.'})

    # Filtro de Data
    filter_date = request.GET.get('filter_date', 'today') # Padrão: Hoje
    
    orders = DeliveryOrder.objects.filter(tenant=tenant)

    today = datetime.now().date()

    if filter_date == 'today':
        orders = orders.filter(created_at__date=today)

    elif filter_date == 'yesterday':
        orders = orders.filter(created_at__date=today - timedelta(days=1))

    elif filter_date == 'week':
        orders = orders.filter(created_at__date__gte=today - timedelta(days=7))
    
    orders = orders.order_by('-id')
    
    # Pega o ID do último pedido GLOBAL (sem filtro) para controle de notificações no frontend
    latest_global_order = DeliveryOrder.objects.filter(tenant=tenant).order_by('-id').first()
    latest_order_id = latest_global_order.id if latest_global_order else 0

    context = {'orders': orders, 'latest_order_id': latest_order_id, 'filter_date': filter_date}
    return render(request, 'delivery/orders_list.html', context)

def get_customer_orders(request, tenant_slug):
    """Busca os últimos pedidos de um cliente pelo telefone."""
    tenant = get_object_or_404(Tenant, slug=tenant_slug)
    phone = request.GET.get('phone')
    
    if not phone:
        return JsonResponse({'status': 'error', 'message': 'Telefone não informado.'}, status=400)

    # Limpa o telefone para busca (remove caracteres não numéricos se necessário, 
    # mas aqui assumiremos que a busca é exata ou 'contains')
    orders = DeliveryOrder.objects.filter(
        tenant=tenant, 
        customer_whatsapp__icontains=phone
    ).order_by('-created_at')[:5] # Pega os últimos 5

    orders_data = []
    for order in orders:
        items_desc = ", ".join([f"{item.quantity}x {item.item_name}" for item in order.items.all()])
        orders_data.append({
            'id': order.id,
            'date': order.created_at.strftime('%d/%m/%Y %H:%M'),
            'total': float(order.final_total),
            'items': items_desc,
            'status': order.get_status_display()
        })

    return JsonResponse({'status': 'ok', 'orders': orders_data})

def repeat_order(request, tenant_slug, order_id):
    """Recria o carrinho com base em um pedido anterior e redireciona para o checkout."""
    order = get_object_or_404(DeliveryOrder, id=order_id, tenant__slug=tenant_slug)
    
    new_cart = {}
    for item in order.items.all():
        if item.original_cart_key:
            new_cart[item.original_cart_key] = item.quantity
    
    if not new_cart:
        messages.error(request, "Não foi possível repetir este pedido (pedido antigo ou itens indisponíveis).")
        return redirect('delivery:customer_menu', tenant_slug=tenant_slug)

    request.session['delivery_cart'] = new_cart
    request.session.modified = True # Força o salvamento da sessão
    return redirect('delivery:checkout', tenant_slug=tenant_slug)

@login_required(login_url='login')
def get_latest_order_id(request):
    """Retorna o ID do pedido mais recente para verificação via AJAX."""
    try:
        tenant = request.user.tenant
        latest_order = DeliveryOrder.objects.filter(tenant=tenant).order_by('-id').first()
        latest_id = latest_order.id if latest_order else 0
        return JsonResponse({'latest_id': latest_id})
    except:
        return JsonResponse({'latest_id': 0})

@login_required(login_url='login')
def delete_combo_view(request, combo_id):
    if request.method == 'POST':
        try:
            tenant = request.user.tenant
        except Tenant.DoesNotExist:
            messages.error(request, 'Você não tem uma loja associada.')
            return redirect('delivery:combo_admin')

        combo = get_object_or_404(Combo, id=combo_id)

        if combo.tenant != tenant:
            messages.error(request, 'Você não tem permissão para excluir este combo.')
            return redirect('delivery:combo_admin')

        combo_name = combo.name
        combo.delete()
        messages.success(request, f"Combo '{combo_name}' excluído com sucesso!")
    
    return redirect('delivery:combo_admin')

@login_required(login_url='login')
def toggle_combo_availability(request, combo_id):
    if request.method == 'POST':
        try:
            tenant = request.user.tenant
        except Tenant.DoesNotExist:
            messages.error(request, 'Você não tem uma loja associada.')
            return redirect('delivery:combo_admin')

        combo = get_object_or_404(Combo, id=combo_id, tenant=tenant)

        combo.is_available = not combo.is_available
        combo.save()
        status = "ativado" if combo.is_available else "desativado"
        messages.success(request, f"Combo '{combo.name}' {status} com sucesso!")
    
    return redirect('delivery:combo_admin')

@login_required(login_url='login')
def delete_order_view(request, order_id):
    if request.method == 'POST':
        try:
            tenant = request.user.tenant
        except Tenant.DoesNotExist:
            messages.error(request, 'Você não tem uma loja associada.')
            return redirect('delivery:orders_list')

        order = get_object_or_404(DeliveryOrder, id=order_id)

        if order.tenant != tenant:
            messages.error(request, 'Você não tem permissão para excluir este pedido.')
            return redirect('delivery:orders_list')

        order.delete()
        messages.success(request, f"Pedido #{order_id} excluído com sucesso!")
    
    return redirect('delivery:orders_list')

@login_required(login_url='login')
def delivery_reports_view(request):
    try:
        tenant = request.user.tenant
    except Tenant.DoesNotExist:
        return render(request, 'error.html', {'message': 'Você não tem uma loja associada.'})

    # Filtro de Datas
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')

    # Define padrão: últimos 30 dias se não informado
    if not start_date_str:
        start_date = datetime.now().date() - timedelta(days=30)
    else:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()

    if not end_date_str:
        end_date = datetime.now().date()

    else:
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

    # Busca pedidos (excluindo cancelados) no intervalo
    orders = DeliveryOrder.objects.filter(
        tenant=tenant, 
        created_at__date__range=[start_date, end_date]
    ).exclude(status='cancelled')

    # Agregação por dia para o gráfico
    daily_sales = orders.annotate(date=TruncDate('created_at')).values('date').annotate(total=Sum('final_total')).order_by('date')

    # Prepara dados para o Chart.js (preenchendo dias vazios com 0)
    dates = []
    values = []
    sales_dict = {entry['date']: entry['total'] for entry in daily_sales}
    
    delta = end_date - start_date
    for i in range(delta.days + 1):
        day = start_date + timedelta(days=i)
        dates.append(day.strftime('%d/%m'))
        values.append(float(sales_dict.get(day, 0)))

    # Top 10 Clientes por Telefone (Agrupamento)
    top_customers = orders.values('customer_whatsapp').annotate(
        order_count=Count('id'),
        total_spent=Sum('final_total'),
        customer_name=Max('customer_name') # Pega o nome mais recente/alfabético associado ao número
    ).order_by('-order_count')[:10]

    context = {
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
        'dates_json': json.dumps(dates),
        'values_json': json.dumps(values),
        'total_sales': orders.aggregate(Sum('final_total'))['final_total__sum'] or 0,
        'total_orders': orders.count(),
        'top_customers': top_customers,
    }
    return render(request, 'delivery/reports.html', context)

@login_required(login_url='login')
def delivery_pos_view(request):
    try:
        tenant = request.user.tenant
    except Tenant.DoesNotExist:
        return render(request, 'error.html', {'message': 'Você não tem uma loja associada.'})

    if request.method == 'POST':
        form = DeliveryOrderForm(request.POST, tenant=tenant)
        cart_json = request.POST.get('cart_data')
        
        if form.is_valid() and cart_json:
            try:
                cart_items = json.loads(cart_json)
                if not cart_items:
                    messages.error(request, "O carrinho está vazio.")
                else:
                    order = form.save(commit=False)
                    order.tenant = tenant
                    
                    items_total = 0
                    final_items = []

                    for item in cart_items:
                        if item['type'] == 'item':
                            db_item = MenuItem.objects.get(id=item['id'])
                            opt_ids = item.get('optionals', [])
                            opts = DeliveryOptional.objects.filter(id__in=opt_ids)
                            opts_total = sum(o.price for o in opts)
                            
                            unit_price = float(db_item.price) + float(opts_total)
                            subtotal = unit_price * int(item['quantity'])
                            items_total += subtotal
                            
                            name_desc = db_item.name
                            if opts:
                                name_desc += " (" + ", ".join([f"*{o.name}" for o in opts]) + ")"
                            
                            final_items.append({
                                'name': name_desc,
                                'quantity': item['quantity'],
                                'price': unit_price
                            })
                            
                        elif item['type'] == 'combo':
                            db_combo = Combo.objects.get(id=item['id'])
                            unit_price = float(db_combo.price)
                            subtotal = unit_price * int(item['quantity'])
                            items_total += subtotal
                            
                            choice_ids = item.get('choices', [])
                            choices = MenuItem.objects.filter(id__in=choice_ids).select_related('category')
                            choice_names = "\n".join([f"* {c.category.name}: {c.name}" for c in choices])
                            name_desc = f"{db_combo.name}\n{choice_names}"
                            
                            final_items.append({
                                'name': name_desc,
                                'quantity': item['quantity'],
                                'price': unit_price
                            })

                    order.items_total = items_total
                    zone = form.cleaned_data.get('delivery_zone')
                    order.delivery_fee = zone.delivery_fee if zone else 0
                    order.final_total = float(items_total) + float(order.delivery_fee)
                    order.save()

                    for f_item in final_items:
                        DeliveryOrderItem.objects.create(
                            order=order,
                            item_name=f_item['name'],
                            quantity=f_item['quantity'],
                            price=f_item['price']
                        )
                    
                    messages.success(request, f"Venda #{order.id} registrada com sucesso!")
                    return redirect('delivery:orders_list')

            except Exception as e:
                messages.error(request, f"Erro ao processar venda: {str(e)}")
        else:
            messages.error(request, "Formulário inválido. Verifique os campos.")

    categories = DeliveryCategory.objects.filter(tenant=tenant)
    menu_items = MenuItem.objects.filter(tenant=tenant, is_available=True).select_related('category')
    combos = Combo.objects.filter(tenant=tenant, is_available=True).prefetch_related('slots__allowed_category')
    optionals = DeliveryOptional.objects.filter(tenant=tenant)
    
    items_js = list(menu_items.values('id', 'name', 'price', 'category_id'))
    opts_js = list(optionals.values('id', 'name', 'price', 'category_id'))
    combos_js = []
    for c in combos:
        slots = [{'allowed_category': {'id': s.allowed_category.id, 'name': s.allowed_category.name}} for s in c.slots.all()]
        combos_js.append({'id': c.id, 'name': c.name, 'price': float(c.price), 'slots': slots})
        
    zones = DeliveryZone.objects.filter(tenant=tenant)
    zones_js = {z.id: float(z.delivery_fee) for z in zones}

    form = DeliveryOrderForm(tenant=tenant)

    context = {
        'categories': categories,
        'menu_items': menu_items,
        'combos': combos,
        'form': form,
        'items_json': json.dumps(items_js, default=str),
        'opts_json': json.dumps(opts_js, default=str),
        'combos_json': json.dumps(combos_js),
        'zones_json': json.dumps(zones_js)
    }
    return render(request, 'delivery/pos.html', context)

@login_required(login_url='login')
def menu_online_view(request):
    try:
        tenant = request.user.tenant
    except Tenant.DoesNotExist:
        return render(request, 'error.html', {'message': 'Você não tem uma loja associada.'})

    if request.method == 'POST':
        if 'upload_images' in request.POST:
            images = request.FILES.getlist('images')
            for image in images:
                MenuOnlineImage.objects.create(tenant=tenant, image=image)
            messages.success(request, 'Imagens do cardápio enviadas com sucesso!')
            return redirect('delivery:menu_online')
        elif 'delete_image' in request.POST:
            image_id = request.POST.get('image_id')
            image = get_object_or_404(MenuOnlineImage, id=image_id, tenant=tenant)
            image.delete()
            messages.success(request, 'Imagem removida com sucesso!')
            return redirect('delivery:menu_online')

    images = MenuOnlineImage.objects.filter(tenant=tenant)
    menu_online_url = request.build_absolute_uri(f'/delivery/menu-online/{tenant.slug}/')
    
    context = {
        'images': images,
        'menu_online_url': menu_online_url,
    }
    return render(request, 'delivery/menu_online.html', context)

def menu_online_public_view(request, tenant_slug):
    tenant = get_object_or_404(Tenant, slug=tenant_slug)
    images = MenuOnlineImage.objects.filter(tenant=tenant)
    
    context = {
        'tenant': tenant,
        'images': images,
    }
    return render(request, 'delivery/menu_online_public.html', context)