from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse # Importe JsonResponse
from django.urls import reverse # Importar a função reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
from .models import Product, Tenant, ProductImage, Category, Cart, CartItem, Order, OrderItem
from .forms import ProductForm, ProductImageFormSet, SettingsForm, StorefrontSettingsForm # Importe o novo formulário
import mercadopago
from django.db.models import Case, When, Value, IntegerField

@login_required
def inicio_view(request):
    """
    Exibe o painel do lojista com pedidos concluídos e carrinhos ativos.
    """
    try:
        tenant = request.user.tenant
    except Tenant.DoesNotExist:
        # Se o usuário não for um lojista, redireciona ou mostra um erro.
        return render(request, 'error.html', {'message': 'Você não tem uma loja associada.'})

    if tenant.business_type == 'delivery':
        # Redireciona para a view dashboard dentro do app 'delivery'
        return redirect('delivery:dashboard')

    # Busca os pedidos pagos para o tenant do lojista
    completed_orders = Order.objects.filter(tenant=tenant, status='paid').prefetch_related('items').order_by('-created_at')
    
    # DEBUG: Mostra no terminal quantos pedidos foram encontrados para este lojista
    print(f"DEBUG PAINEL: Tenant '{tenant.name}' (ID {tenant.id}) - Pedidos encontrados: {completed_orders.count()}")

    # Busca os carrinhos ativos que contêm produtos do tenant do lojista
    active_carts = Cart.objects.filter(
        items__product__tenant=tenant
    ).prefetch_related(
        'items__product'  # Otimiza a busca pelos itens e seus produtos
    ).distinct().order_by('-updated_at')

    context = {
        'completed_orders': completed_orders,
        'active_carts': active_carts,
    }
    return render(request, 'inicio.html', context)

@login_required
def product_view(request):
    # Lógica para lidar com o envio do formulário (POST)
    if request.method == 'POST':
        # Adicionamos request.FILES para lidar com o upload da imagem
        form = ProductForm(request.POST, request.FILES)
        # Instancia o formset com os dados POST e arquivos, para um novo produto
        formset = ProductImageFormSet(request.POST, request.FILES, instance=Product())

        if form.is_valid() and formset.is_valid():
            # 1. Cria a instância do produto sem salvar no banco de dados
            
            # Coleta os dados dos campos dinâmicos
            extra_data = {}
            for key, value in request.POST.items():
                if key.startswith('extra_field_'):
                    field_name = key.replace('extra_field_', '')
                    extra_data[field_name] = value

            product = form.save(commit=False)
            # 2. Busca o objeto Tenant associado ao usuário logado.
            try:
                tenant = request.user.tenant
            except Tenant.DoesNotExist:
                # Opcional: Lidar com o caso de um usuário não ter um tenant.
                # Poderia redirecionar com uma mensagem de erro. Por agora, vamos falhar.
                return render(request, 'error.html', {'message': 'Usuário não possui um tenant associado.'})
            product.tenant = tenant
            product.extra_data = extra_data # Salva os dados extras
            # 3. Agora salva a instância completa no banco
            product.save()
            # 4. Associa o formset ao produto recém-criado e salva as imagens
            formset.instance = product
            formset.save()
            return redirect('shop:produtos') # Redireciona para limpar o formulário
    else:
        # Se não for POST, cria um formulário vazio
        form = ProductForm()
        formset = ProductImageFormSet(instance=Product()) # Instancia o formset para um novo produto

    # Busca apenas os produtos que pertencem ao tenant do usuário logado.
    try:
        # Pega o tenant associado ao usuário
        user_tenant = request.user.tenant
        # Filtra os produtos que têm esse tenant
        lista_produtos = Product.objects.filter(tenant=user_tenant)
    except Tenant.DoesNotExist:
        # Se o usuário não tiver um tenant, a lista de produtos estará vazia.
        lista_produtos = []

    context = {'form': form, 'formset': formset, 'produtos': lista_produtos} # Passa o formset para o template
    return render(request, 'produtos.html', context)

@login_required
def edit_product_view(request, product_id):
    try:
        tenant = request.user.tenant
        product = get_object_or_404(Product, id=product_id, tenant=tenant)
    except Tenant.DoesNotExist:
        return render(request, 'error.html', {'message': 'Usuário não possui um tenant associado.'})

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        formset = ProductImageFormSet(request.POST, request.FILES, instance=product)

        if form.is_valid() and formset.is_valid():
            # Coleta os dados dos campos dinâmicos
            extra_data = {}
            for key, value in request.POST.items():
                if key.startswith('extra_field_'):
                    field_name = key.replace('extra_field_', '')
                    extra_data[field_name] = value
            
            product = form.save(commit=False)
            product.extra_data = extra_data
            product.save()
            formset.save()
            messages.success(request, 'Produto atualizado com sucesso!')
            return redirect('shop:produtos')
    else:
        form = ProductForm(instance=product)
        formset = ProductImageFormSet(instance=product)
    
    # Prepara os campos extras para o template preencher via JS ou manualmente
    # Passamos o extra_data atual para o contexto
    return render(request, 'edit_product.html', {
        'form': form, 
        'formset': formset, 
        'product': product,
        'extra_data': product.extra_data
    })

@login_required
def delete_product_view(request, product_id):
    try:
        tenant = request.user.tenant
        product = get_object_or_404(Product, id=product_id, tenant=tenant)
        
        product.delete()
        messages.success(request, 'Produto excluído com sucesso!')
            
    except Tenant.DoesNotExist:
        pass
    except Exception as e:
        messages.error(request, f'Erro ao excluir produto: {e}')

    return redirect('shop:produtos')

@login_required
def get_category_fields(request, category_id):
    try:
        category = Category.objects.get(id=category_id)
        fields = category.extra_fields
        return JsonResponse({'fields': fields})
    except Category.DoesNotExist:
        return JsonResponse({'fields': []})

@login_required
def storefront_settings_view(request):
    try:
        tenant = request.user.tenant
    except Tenant.DoesNotExist:
        return render(request, 'error.html', {'message': 'Usuário não possui uma loja associada.'})

    if request.method == 'POST':
        form = StorefrontSettingsForm(request.POST, request.FILES, instance=tenant)
        if form.is_valid():
            form.save()
            messages.success(request, 'Configurações da vitrine atualizadas com sucesso!')
            return redirect('shop:storefront_settings')
    
    # Se não for POST ou se o form for inválido, renderiza com os dados atuais
    # Precisamos passar o form para o template, mas inicializando com a instância do tenant
    form = StorefrontSettingsForm(instance=tenant)
    return render(request, 'configurar_vitrine.html', {'form': form, 'tenant': tenant})

def sales_view(request, tenant_slug):
    """
    Exibe os produtos de um tenant específico.
    """
    # Salva o slug do tenant na sessão para saber para onde voltar
    request.session['last_visited_tenant_slug'] = tenant_slug
    # Busca o tenant pelo slug ou retorna um erro 404 se não encontrar
    tenant = get_object_or_404(Tenant, slug=tenant_slug)
    
    # Busca categorias disponíveis nesta loja para o filtro
    categories = Category.objects.filter(product__tenant=tenant).distinct()

    # Busca produtos da categoria de promoção para o banner rotativo (limite de 5)
    promo_products = []
    if tenant.promotion_category:
        promo_products = Product.objects.filter(tenant=tenant, category=tenant.promotion_category).prefetch_related('images')[:5]

    # Define a ordenação com base na configuração do lojista
    # Se o campo não existir no banco ainda, usa 'category' como padrão
    sort_pref = getattr(tenant, 'display_order', 'category')
    
    # Filtra os produtos
    produtos = Product.objects.filter(tenant=tenant).select_related('category').prefetch_related('images')
    
    # Filtro por Categoria
    selected_category_id = request.GET.get('category')
    if selected_category_id:
        try:
            selected_category_id = int(selected_category_id)
            produtos = produtos.filter(category_id=selected_category_id)
        except ValueError:
            selected_category_id = None

    # Lógica para colocar itens da Categoria de Promoção no topo
    if tenant.promotion_category:
        produtos = produtos.annotate(
            is_promo=Case(
                When(category=tenant.promotion_category, then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            )
        )
    else:
        produtos = produtos.annotate(is_promo=Value(0, output_field=IntegerField()))

    # Define a lista de ordenação: Promoção > Categoria > (Critério Escolhido)
    if sort_pref == 'price_asc':
        produtos = produtos.order_by('-is_promo', 'category__name', 'price')
    elif sort_pref == 'price_desc':
        produtos = produtos.order_by('-is_promo', 'category__name', '-price')
    else: # Padrão (category)
        # Ordenação personalizada em Python para:
        # 1. Promoção (is_promo)
        # 2. Categorias com itens mais recentes primeiro (Recently Added)
        # 3. Itens mais recentes dentro da categoria
        produtos_list = list(produtos)
        
        # Mapa para guardar o ID do produto mais recente de cada categoria
        cat_max_ids = {}
        for p in produtos_list:
            cid = p.category_id
            if cid not in cat_max_ids or p.id > cat_max_ids[cid]:
                cat_max_ids[cid] = p.id
        
        # Ordena a lista: Promoção > Categoria mais nova > Item mais novo
        produtos_list.sort(key=lambda p: (-p.is_promo, -cat_max_ids.get(p.category_id, 0), -p.id))
        produtos = produtos_list
    
    return render(request, 'vendas.html', {
        'produtos': produtos, 
        'tenant': tenant, 
        'categories': categories, 
        'selected_category_id': selected_category_id,
        'promo_products': promo_products
    })

def product_detail_view(request, tenant_slug, product_id):
    """
    Exibe os detalhes de um único produto.
    """
    # Salva o slug do tenant na sessão também aqui, para garantir
    request.session['last_visited_tenant_slug'] = tenant_slug
    tenant = get_object_or_404(Tenant, slug=tenant_slug)
    produto = get_object_or_404(Product, id=product_id, tenant=tenant)
    return render(request, 'product_detail.html', {'produto': produto, 'tenant': tenant})

def create_payment_view(request, tenant_slug, product_id, gateway):
    """
    Cria uma preferência de pagamento e redireciona o usuário.
    Suporta múltiplos gateways.
    """
    tenant = get_object_or_404(Tenant, slug=tenant_slug)
    produto = get_object_or_404(Product, id=product_id, tenant=tenant)

    if gateway == 'mercadopago':
        if not tenant.mercadopago_api_key:
            return render(request, 'error.html', {'message': 'O lojista não configurou o Mercado Pago.'})

        sdk = mercadopago.SDK(tenant.mercadopago_api_key)

        # 1. Cria os dados da preferência de pagamento para Mercado Pago
        preference_data = {
            "items": [
                {
                    "title": produto.name,
                    "quantity": 1,
                    "unit_price": float(produto.price),
                    "currency_id": "BRL",
                }
            ],
            "back_urls": {
                "success": f"https://5771db14f55a.ngrok-free.app{reverse('shop:payment_success')}",
                "failure": f"https://5771db14f55a.ngrok-free.app{reverse('shop:payment_failure')}",
                "pending": f"https://5771db14f55a.ngrok-free.app{reverse('shop:payment_pending')}",
            },
            "auto_return": "approved",
            "binary_mode": True,
            "payment_methods": {
                "excluded_payment_types": [
                    {"id": "ticket"}
                ],
                "installments": 1
            },
        }

        # 2. Cria a preferência e obtém a resposta
        preference_response = sdk.preference().create(preference_data)

        # 3. Verifica se a chamada foi bem-sucedida e redireciona
        if preference_response["status"] == 201:
            preference = preference_response["response"]
            return redirect(preference["init_point"])
        else:
            error_message = f"Erro ao criar pagamento com Mercado Pago: {preference_response['response'].get('message', 'Erro desconhecido')}"
            return render(request, 'error.html', {'message': error_message})

    elif gateway == 'pagseguro':
        if not tenant.pagseguro_api_key:
            return render(request, 'error.html', {'message': 'O lojista não configurou o PagSeguro.'})
        # Lógica para criar pagamento com PagSeguro viria aqui.
        # Por enquanto, vamos exibir uma mensagem de "não implementado".
        return render(request, 'error.html', {'message': 'O pagamento com PagSeguro ainda não foi implementado.'})

    else:
        return render(request, 'error.html', {'message': 'Gateway de pagamento inválido.'})

def create_cart_payment_view(request, gateway):
    """
    Cria uma preferência de pagamento para o carrinho inteiro e redireciona o usuário.
    """
    phone_number = request.session.get('guest_phone_number')
    if not phone_number:
        return redirect('shop:guest_login')

    try:
        cart = Cart.objects.get(phone_number=phone_number)
    except Cart.DoesNotExist:
        return render(request, 'error.html', {'message': 'Seu carrinho está vazio.'})

    if not cart.items.exists():
        return render(request, 'error.html', {'message': 'Seu carrinho está vazio.'})

    # Pega o tenant do primeiro item do carrinho.
    tenant = cart.items.first().product.tenant

    if gateway == 'mercadopago':
        if not tenant.mercadopago_api_key:
            return render(request, 'error.html', {'message': 'O lojista não configurou o Mercado Pago.'})

        sdk = mercadopago.SDK(tenant.mercadopago_api_key.strip())

        # Cria a lista de itens a partir do carrinho
        items = [
            {
                "title": str(item.product.name),
                "quantity": int(item.quantity),
                "unit_price": float(item.product.price),
                "currency_id": "BRL",
            }
            for item in cart.items.all()
        ]

        # Define as URLs de retorno explicitamente para garantir que são strings válidas
        base_url = "https://5771db14f55a.ngrok-free.app"
        success_url = f"{base_url}{reverse('shop:payment_success')}"
        failure_url = f"{base_url}{reverse('shop:payment_failure')}"
        pending_url = f"{base_url}{reverse('shop:payment_pending')}"
        webhook_url = f"{base_url}{reverse('shop:mercadopago_webhook', kwargs={'tenant_id': tenant.id})}"

        preference_data = {
            "items": items,
            "external_reference": str(cart.id), # Associa o ID do carrinho ao pagamento
            "auto_return": "approved",
            "binary_mode": True,
            "notification_url": webhook_url,
            "back_urls": {
                "success": success_url,
                "failure": failure_url,
                "pending": pending_url,
            },
            "payment_methods": {
                "excluded_payment_types": [
                    {"id": "ticket"}
                ],
                "installments": 1
            },
        }

        print("DEBUG MP Payload:", preference_data) # Para ajudar a debugar no terminal se der erro
        preference_response = sdk.preference().create(preference_data)

        if preference_response["status"] == 201:
            return redirect(preference_response["response"]["init_point"])
        else:
            # Captura o erro detalhado do Mercado Pago
            error_data = preference_response.get("response", {})
            error_msg = error_data.get("message", "Erro desconhecido")
            error_details = error_data.get("cause", [])
            return render(request, 'error.html', {'message': f'Erro Mercado Pago: {error_msg} | Detalhes: {error_details}'})

    # A lógica para o PagSeguro viria aqui
    return render(request, 'error.html', {'message': 'Gateway de pagamento inválido.'})

def payment_success_view(request):
    """
    Lida com o retorno de um pagamento bem-sucedido.
    Converte o carrinho em um pedido.
    """
    # Debug para ver o que o Mercado Pago está enviando no terminal
    print("DEBUG Retorno MP:", request.GET)

    cart_id = request.GET.get('external_reference')
    payment_status = request.GET.get('collection_status') or request.GET.get('status')

    if not cart_id or payment_status != 'approved':
        return render(request, 'error.html', {'message': 'Pagamento não confirmado ou referência inválida.'})

    try:
        cart = Cart.objects.get(id=cart_id)
        tenant = cart.items.first().product.tenant
        
        # Usa a função auxiliar para criar o pedido
        order = _create_order_from_cart(cart)
        print(f"DEBUG SUCESSO: Pedido {order.id} criado com sucesso.")

    except Cart.DoesNotExist:
        # Se o carrinho não existe, mas o status é approved, o Webhook já processou o pedido.
        print(f"DEBUG INFO: Carrinho {cart_id} não encontrado. O pedido já foi criado e processado via Webhook.")

    except Exception as e:
        print(f"DEBUG ERRO: Falha inesperada no retorno do pagamento: {e}")

    return render(request, 'payment_status.html', {'status': 'sucesso'})

def _create_order_from_cart(cart):
    """
    Função auxiliar para transformar um Carrinho em Pedido.
    Usada tanto pela view de sucesso quanto pelo Webhook.
    """
    tenant = cart.items.first().product.tenant
    
    # Cria o Pedido (Order)
    order = Order.objects.create(
        tenant=tenant,
        customer_phone=cart.phone_number,
        total_amount=cart.total,
        status='paid'
    )

    # Copia os itens
    for item in cart.items.all():
        OrderItem.objects.create(
            order=order,
            product_name=item.product.name,
            quantity=item.quantity,
            price=item.product.price
        )
    
    # Limpa o carrinho
    cart.delete()
    return order

@csrf_exempt
@require_POST
def mercadopago_webhook_view(request, tenant_id):
    """
    Recebe notificações do Mercado Pago e processa o pedido em segundo plano.
    """
    try:
        tenant = Tenant.objects.get(id=tenant_id)
        if not tenant.mercadopago_api_key:
            return JsonResponse({'error': 'Tenant sem chave API'}, status=400)

        data = json.loads(request.body)
        print(f"DEBUG WEBHOOK RECEBIDO: {data}")

        payment_id = None

        # 1. Tenta pegar ID da estrutura Webhook V2 (type = payment)
        if data.get('type') == 'payment':
            payment_id = data.get('data', {}).get('id')
        
        # 2. Tenta pegar ID da estrutura IPN / Webhook V1 (topic = payment)
        elif data.get('topic') == 'payment':
            payment_id = data.get('resource')
            # Se o resource for vazio, tenta pegar da URL
            if not payment_id:
                payment_id = request.GET.get('id')
        
        # 3. Fallback: Verifica se veio na URL (query params)
        if not payment_id and request.GET.get('topic') == 'payment':
            payment_id = request.GET.get('id')

        if payment_id:
            # Se o resource vier como URL completa, extrai apenas o ID
            if str(payment_id).startswith('http'):
                payment_id = str(payment_id).split('/')[-1]

            sdk = mercadopago.SDK(tenant.mercadopago_api_key.strip())
            payment_info = sdk.payment().get(payment_id)
            
            if payment_info['status'] == 200:
                payment = payment_info['response']
                status = payment.get('status')
                external_reference = payment.get('external_reference')

                if status == 'approved' and external_reference:
                    try:
                        cart = Cart.objects.get(id=external_reference)
                        order = _create_order_from_cart(cart)
                        print(f"DEBUG WEBHOOK: Pedido {order.id} criado via Webhook!")
                    except Cart.DoesNotExist:
                        print(f"DEBUG WEBHOOK: Carrinho {external_reference} não encontrado (provavelmente já processado).")

        return JsonResponse({'status': 'OK'})
    except Exception as e:
        print(f"DEBUG WEBHOOK ERRO: {e}")
        return JsonResponse({'error': str(e)}, status=500)

def payment_failure_view(request):
    """
    Lida com o retorno de um pagamento com falha.
    """
    # Aqui você poderia adicionar lógica para registrar a falha, se quisesse.
    return render(request, 'payment_status.html', {'status': 'falha'})

def payment_pending_view(request):
    """
    Lida com o retorno de um pagamento pendente.
    """
    # Aqui você poderia atualizar o status do pedido para 'pendente', se quisesse.
    return render(request, 'payment_status.html', {'status': 'pendente'})

def client_orders_view(request):
    """
    Exibe a área do cliente para consultar pedidos pelo telefone.
    """
    phone = request.GET.get('phone')
    tenant_slug = request.GET.get('tenant_slug')
    orders = None
    current_tenant = None

    if tenant_slug:
        current_tenant = get_object_or_404(Tenant, slug=tenant_slug)

    if phone:
        # Busca pedidos associados ao telefone, ordenados do mais recente para o mais antigo
        orders = Order.objects.filter(customer_phone=phone).prefetch_related('items', 'tenant').order_by('-created_at')
        # Se estiver acessando através de uma loja específica, filtra apenas os pedidos dela
        if current_tenant:
            orders = orders.filter(tenant=current_tenant)

    return render(request, 'client_orders.html', {'orders': orders, 'phone': phone, 'current_tenant': current_tenant})

@login_required
def settings_view(request):
    """
    Página de configurações para o tenant (lojista).
    """
    try:
        tenant = request.user.tenant
    except Tenant.DoesNotExist:
        return render(request, 'error.html', {'message': 'Usuário não possui uma loja associada.'})

    if request.method == 'POST':
        form = SettingsForm(request.POST, instance=tenant)
        if form.is_valid():
            form.save()
            return redirect('shop:configuracoes') # Redireciona para a mesma página
    else:
        form = SettingsForm(instance=tenant)

    return render(request, 'configuracoes.html', {'form': form})

def add_to_cart_view(request, tenant_slug, product_id):
    """
    Adiciona um produto ao carrinho. Se o cliente não tiver um carrinho,
    ele é redirecionado para informar o telefone.
    """
    # Verifica se o telefone do cliente já está na sessão
    phone_number = request.session.get('guest_phone_number')

    if not phone_number:
        # Se não houver telefone, redireciona para uma página para inseri-lo.
        # Passamos a URL atual como 'next' para redirecionar de volta após o login.
        return redirect(reverse('shop:guest_login') + f'?next={request.path}')

    # Busca ou cria o carrinho para o número de telefone
    cart, created = Cart.objects.get_or_create(phone_number=phone_number)
    produto = get_object_or_404(Product, id=product_id)

    # Pega a quantidade do formulário, com padrão 1 se não for fornecida.
    try:
        quantity_to_add = int(request.POST.get('quantity', 1))
    except (ValueError, TypeError):
        quantity_to_add = 1

    # Busca ou cria o item no carrinho
    cart_item, created = CartItem.objects.get_or_create(cart=cart, product=produto, defaults={'quantity': 0})

    # Adiciona a quantidade desejada ao item do carrinho
    cart_item.quantity += quantity_to_add
    cart_item.save()

    # Redireciona para a página do carrinho para ver os itens
    return redirect('shop:view_cart')

def guest_login_view(request):
    """
    Página para o cliente convidado inserir o número de telefone.
    """
    if request.method == 'POST':
        phone = request.POST.get('phone')
        if phone:
            # Salva o telefone na sessão
            request.session['guest_phone_number'] = phone
            # Redireciona para a URL 'next' se ela existir, ou para a página inicial.
            next_url = request.GET.get('next', '/')
            return redirect(next_url)

    return render(request, 'guest_login.html')

def view_cart(request):
    """
    Exibe os itens no carrinho do cliente.
    """
    cart = None
    phone_number = request.session.get('guest_phone_number')
    last_visited_tenant_slug = request.session.get('last_visited_tenant_slug')

    if phone_number:
        try:
            # Usamos prefetch_related para otimizar a busca dos produtos e suas imagens
            cart = Cart.objects.prefetch_related('items__product__images').get(phone_number=phone_number)
        except Cart.DoesNotExist:
            # O carrinho pode não existir se o cliente ainda não adicionou itens
            pass
    
    return render(request, 'cart.html', {'cart': cart, 'last_visited_tenant_slug': last_visited_tenant_slug})

def checkout_view(request):
    """
    Exibe a página de checkout com o resumo do carrinho e as opções de pagamento.
    """
    phone_number = request.session.get('guest_phone_number')
    if not phone_number:
        # Se não houver identificação, não há carrinho para finalizar
        return redirect('shop:guest_login')

    try:
        cart = Cart.objects.prefetch_related('items__product__tenant').get(phone_number=phone_number)
    except Cart.DoesNotExist:
        # Se o carrinho não existe, redireciona para a página do carrinho (que mostrará que está vazio)
        return redirect('shop:view_cart')

    if not cart.items.exists():
        # Não permitir checkout de carrinho vazio
        return redirect('shop:view_cart')

    # Assumindo que todos os produtos no carrinho são do mesmo lojista.
    # Pegamos o tenant do primeiro item do carrinho.
    tenant = cart.items.first().product.tenant

    context = {'cart': cart, 'tenant': tenant}
    return render(request, 'checkout.html', context)

def remove_from_cart_view(request, item_id):
    """
    Remove um item específico do carrinho.
    """
    phone_number = request.session.get('guest_phone_number')
    if not phone_number:
        return redirect('shop:guest_login')

    try:
        cart = Cart.objects.get(phone_number=phone_number)
        # Garante que o item a ser removido pertence ao carrinho do usuário
        item_to_remove = CartItem.objects.get(id=item_id, cart=cart)
        item_to_remove.delete()
    except (Cart.DoesNotExist, CartItem.DoesNotExist):
        # Se o carrinho ou o item não existem, não há nada a fazer.
        pass

    return redirect('shop:view_cart')

def update_cart_item_view(request, item_id):
    """
    Atualiza a quantidade de um item no carrinho.
    """
    if request.method == 'POST':
        phone_number = request.session.get('guest_phone_number')
        if not phone_number:
            return redirect('shop:guest_login')

        try:
            cart = Cart.objects.get(phone_number=phone_number)
            item_to_update = CartItem.objects.get(id=item_id, cart=cart)
            
            quantity = int(request.POST.get('quantity', 1))

            if quantity > 0:
                item_to_update.quantity = quantity
                item_to_update.save()
        except (Cart.DoesNotExist, CartItem.DoesNotExist, ValueError):
            pass

    return redirect('shop:view_cart')

@login_required
def delete_cart_view(request, cart_id):
    """
    Permite ao lojista excluir um carrinho ativo do painel.
    """
    try:
        tenant = request.user.tenant
        # Verifica se o carrinho existe e se contém itens deste lojista para garantir segurança
        cart = Cart.objects.filter(id=cart_id, items__product__tenant=tenant).first()
        if cart:
            cart.delete()
    except Tenant.DoesNotExist:
        pass

    return redirect('shop:inicio')
