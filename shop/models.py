from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify

class Tenant(models.Model):
    PAYMENT_GATEWAY_CHOICES = [
        ('mercadopago', 'Mercado Pago'),
        ('pagseguro', 'PagSeguro'),
    ]

    DISPLAY_ORDER_CHOICES = [
        ('category', 'Padrão (Por Categoria)'),
        ('price_asc', 'Menor Preço'),
        ('price_desc', 'Maior Preço'),
    ]

    BUSINESS_TYPE_CHOICES = [
        ('ecommerce', 'E-commerce (Varejo)'),
        ('delivery', 'Delivery (Restaurantes/Bebidas)'),
        ('bar', 'Bar (Bebidas e Serviços)'),
        ('bar_delivery', 'Bar & Delivery (Híbrido)'),
    ]

    name = models.CharField(max_length=100)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    slug = models.SlugField(unique=True, max_length=100, blank=True, help_text="Identificador único para a URL da vitrine.")
    # Campos para configuração de pagamento
    # O campo payment_gateway pode ser removido se você permitir múltiplos gateways simultaneamente
    # ou mantido para definir um padrão. Por agora, vamos usar campos separados.
    mercadopago_api_key = models.CharField(max_length=255, blank=True, null=True, verbose_name="Chave da API do Mercado Pago")
    pagseguro_api_key = models.CharField(max_length=255, blank=True, null=True, verbose_name="Chave da API do PagSeguro")
    display_order = models.CharField(max_length=20, choices=DISPLAY_ORDER_CHOICES, default='newest', verbose_name="Ordenação Padrão da Vitrine")
    logo = models.ImageField(upload_to='tenant_logos/', blank=True, null=True, verbose_name="Logo da Loja")
    whatsapp_number = models.CharField(max_length=20, blank=True, null=True, verbose_name="WhatsApp para Contato")
    promotion_category = models.ForeignKey('Category', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Categoria de Promoção em Destaque")
    business_type = models.CharField(max_length=20, choices=BUSINESS_TYPE_CHOICES, default='ecommerce', verbose_name="Área de Atuação")
    is_open = models.BooleanField(default=False, verbose_name="Loja Aberta")
    
    # Campos específicos para bar
    numero_mesas = models.PositiveIntegerField(default=10, verbose_name="Número de Mesas", help_text="Quantidade de mesas disponíveis no bar")
    permitir_gorjeta_10 = models.BooleanField(default=False, verbose_name="Permitir Taxa 10% Serviço", help_text="Permitir que clientes adicionem 10% de taxa de serviço opcional")

    def save(self, *args, **kwargs):
        """
        Gera o slug automaticamente a partir do nome do tenant antes de salvar.
        """
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    def __str__(self):
        return self.name

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('vitrine', kwargs={'tenant_slug': self.slug})

class Category(models.Model):
    name = models.CharField(max_length=100)
    # Campo para definir os atributos extras da categoria. Ex: [{"nome": "Tamanho", "tipo": "texto", "opcoes": "P,M,G"}]
    extra_fields = models.JSONField(default=list, blank=True, help_text='Defina campos extras para esta categoria em formato JSON.')
    
    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name

class Product(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField()
    # Campo para armazenar os valores dos atributos extras. Ex: {"Tamanho": "M", "Cor": "Azul"}
    extra_data = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('product_detail', kwargs={'tenant_slug': self.tenant.slug, 'product_id': self.id})

class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='product_images/')

    def __str__(self):
        return f"Image for {self.product.name} ({self.id})"

class Cart(models.Model):
    """
    Representa o carrinho de compras de um cliente.
    Pode ser associado a um usuário logado ou a um cliente convidado via telefone.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    phone_number = models.CharField(max_length=20, null=True, blank=True, db_index=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def total(self):
        """Calcula o valor total de todos os itens no carrinho."""
        return sum(item.subtotal for item in self.items.all())

    def __str__(self):
        if self.user:
            return f"Carrinho de {self.user.username}"
        elif self.phone_number:
            return f"Carrinho do telefone {self.phone_number}"
        return f"Carrinho ID {self.id}"

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    @property
    def subtotal(self):
        """Calcula o subtotal para este item do carrinho."""
        return self.product.price * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.product.name} no carrinho {self.cart.id}"

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pendente'),
        ('paid', 'Pago'),
        ('shipped', 'Enviado'),
        ('cancelled', 'Cancelado'),
    ]
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='orders')
    # Informações do cliente - por enquanto, apenas o telefone do carrinho de convidado
    customer_phone = models.CharField(max_length=20)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Pedido #{self.id} - {self.tenant.name}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product_name = models.CharField(max_length=200) # Salva o nome para o caso de o produto ser excluído
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2) # Salva o preço no momento da compra

    def __str__(self):
        return f"{self.quantity} x {self.product_name}"
