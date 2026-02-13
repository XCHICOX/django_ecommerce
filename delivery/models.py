from django.db import models
from django.utils import timezone
from shop.models import Tenant # Reutiliza o modelo Tenant do app principal

class DeliveryCategory(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='delivery_categories')
    name = models.CharField(max_length=100, verbose_name="Nome da Categoria")

    class Meta:
        verbose_name = "Categoria de Delivery"
        verbose_name_plural = "Categorias de Delivery"
        unique_together = ('tenant', 'name') # Evita nomes de categoria duplicados para a mesma loja

    def __str__(self):
        return self.name

class MenuItem(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='menu_items')
    category = models.ForeignKey(DeliveryCategory, on_delete=models.CASCADE, related_name='items', verbose_name="Categoria")
    name = models.CharField(max_length=100, verbose_name="Nome do Item")
    description = models.TextField(blank=True, verbose_name="Descrição")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Preço")
    image = models.ImageField(upload_to='menu_items/', blank=True, null=True, verbose_name="Imagem")
    is_available = models.BooleanField(default=True, verbose_name="Disponível")

    class Meta:
        verbose_name = "Item do Cardápio"
        verbose_name_plural = "Itens do Cardápio"
        ordering = ['category__name', 'name']

    def __str__(self):
        return self.name

class DeliveryZone(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='delivery_zones')
    neighborhood = models.CharField(max_length=100, verbose_name="Bairro")
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor da Entrega (R$)")

    class Meta:
        verbose_name = "Zona de Entrega"
        verbose_name_plural = "Zonas de Entrega"
        unique_together = ('tenant', 'neighborhood')
        ordering = ['neighborhood']

    def __str__(self):
        return f"{self.neighborhood} - R$ {self.delivery_fee}"

class DeliveryOrder(models.Model):
    PAYMENT_CHOICES = [
        ('dinheiro', 'Dinheiro'),
        ('cartao', 'Cartão de Crédito/Débito'),
        ('pix', 'PIX'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pendente'),
        ('confirmed', 'Confirmado'),
        ('on_the_way', 'Saiu para Entrega'),
        ('delivered', 'Entregue'),
        ('cancelled', 'Cancelado'),
    ]

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='delivery_orders')
    customer_name = models.CharField(max_length=100, verbose_name="Nome do Cliente")
    customer_whatsapp = models.CharField(max_length=20, verbose_name="WhatsApp")
    delivery_address = models.CharField(max_length=255, verbose_name="Endereço de Entrega")
    delivery_zone = models.ForeignKey(DeliveryZone, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Bairro")
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES, verbose_name="Forma de Pagamento")
    change_for = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Troco para")
    observations = models.TextField(blank=True, verbose_name="Observações")
    
    items_total = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Total dos Itens")
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Taxa de Entrega")
    final_total = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Total Final")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Status")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Pedido #{self.id} - {self.customer_name}"

class DeliveryOrderItem(models.Model):
    order = models.ForeignKey(DeliveryOrder, on_delete=models.CASCADE, related_name='items')
    item_name = models.CharField(max_length=200) # Snapshot of the name
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2) # Snapshot of the price
    original_cart_key = models.CharField(max_length=255, null=True, blank=True) # Chave para reconstruir o carrinho

    def __str__(self):
        return f"{self.quantity}x {self.item_name}"

class Combo(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='combos')
    name = models.CharField(max_length=100, verbose_name="Nome do Combo")
    description = models.TextField(blank=True, verbose_name="Descrição")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Preço do Combo")
    image = models.ImageField(upload_to='combo_images/', blank=True, null=True, verbose_name="Imagem do Combo")
    is_available = models.BooleanField(default=True, verbose_name="Disponível")

    class Meta:
        verbose_name = "Combo"
        verbose_name_plural = "Combos"
        ordering = ['name']

    def __str__(self):
        return self.name

class ComboSlot(models.Model):
    combo = models.ForeignKey(Combo, on_delete=models.CASCADE, related_name='slots')
    allowed_category = models.ForeignKey(DeliveryCategory, on_delete=models.CASCADE, verbose_name="Categoria Permitida")

    class Meta:
        verbose_name = "Opção do Combo"
        verbose_name_plural = "Opções do Combo"

    def __str__(self):
        return f"Opção de {self.allowed_category.name} para o combo {self.combo.name}"

class DeliveryOptional(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    category = models.ForeignKey(DeliveryCategory, on_delete=models.CASCADE, related_name='optionals', verbose_name="Categoria")
    name = models.CharField(max_length=100, verbose_name="Nome do Opcional")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Preço Adicional")

    class Meta:
        verbose_name = "Opcional"
        verbose_name_plural = "Opcionais"

    def __str__(self):
        return f"{self.name} (+R$ {self.price})"

class MenuOnlineImage(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='menu_online_images')
    image = models.ImageField(upload_to='menu_online/', verbose_name="Imagem do Cardápio")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Imagem do Cardápio Online"
        verbose_name_plural = "Imagens do Cardápio Online"
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"Imagem {self.id} - {self.tenant.name}"

class SystemNotice(models.Model):
    content = models.CharField(max_length=255, verbose_name="Texto do Aviso")
    is_active = models.BooleanField(default=True, verbose_name="Ativo")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Aviso do Sistema"
        verbose_name_plural = "Avisos do Sistema"
        ordering = ['-created_at']

    def __str__(self):
        return self.content

    