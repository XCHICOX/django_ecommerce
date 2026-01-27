from django.db import models
from decimal import Decimal
from shop.models import Tenant

class BarCategory(models.Model):
	tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='bar_categories')
	name = models.CharField(max_length=100, verbose_name="Nome da Categoria")

	class Meta:
		verbose_name = "Categoria do Bar"
		verbose_name_plural = "Categorias do Bar"
		unique_together = ('tenant', 'name')

	def __str__(self):
		return self.name

class BarMenuItem(models.Model):
	tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='bar_menu_items')
	category = models.ForeignKey(BarCategory, on_delete=models.CASCADE, related_name='items', verbose_name="Categoria")
	name = models.CharField(max_length=100, verbose_name="Nome do Item")
	price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Preço")
	is_available = models.BooleanField(default=True, verbose_name="Disponível")

	class Meta:
		verbose_name = "Item do Bar"
		verbose_name_plural = "Itens do Bar"
		ordering = ['category__name', 'name']

	def __str__(self):
		return self.name

class BarZone(models.Model):
	tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='bar_zones')
	neighborhood = models.CharField(max_length=100, verbose_name="Bairro")
	service_fee = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Taxa de Serviço (R$)")

	class Meta:
		verbose_name = "Zona do Bar"
		verbose_name_plural = "Zonas do Bar"
class BarComanda(models.Model):
    STATUS_CHOICES = [
        ('aberta', 'Aberta'),
        ('fechada', 'Fechada'),
        ('paga', 'Paga'),
    ]
    
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='bar_comandas')
    numero_mesa = models.PositiveIntegerField(verbose_name="Número da Mesa")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='aberta', verbose_name="Status")
    data_abertura = models.DateTimeField(auto_now_add=True, verbose_name="Data de Abertura")
    data_fechamento = models.DateTimeField(null=True, blank=True, verbose_name="Data de Fechamento")
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Total")
    gorjeta_10 = models.BooleanField(default=False, verbose_name="Taxa 10% Serviço")

    class Meta:
        verbose_name = "Comanda"
        verbose_name_plural = "Comandas"
        ordering = ['-data_abertura']

    def __str__(self):
        return f"Mesa {self.numero_mesa} - {self.get_status_display()}"

    def calcular_total(self):
        total = sum(item.subtotal for item in self.itens.all())
        if self.gorjeta_10:
            total *= Decimal('1.10')
        return total

class BarComandaItem(models.Model):
    comanda = models.ForeignKey(BarComanda, on_delete=models.CASCADE, related_name='itens')
    item = models.ForeignKey(BarMenuItem, on_delete=models.CASCADE, verbose_name="Item")
    quantidade = models.PositiveIntegerField(default=1, verbose_name="Quantidade")
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Preço Unitário")
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Subtotal")
    observacao = models.TextField(blank=True, verbose_name="Observação")

    class Meta:
        verbose_name = "Item da Comanda"
        verbose_name_plural = "Itens da Comanda"

    def __str__(self):
        return f"{self.quantidade}x {self.item.name}"

    def save(self, *args, **kwargs):
        self.subtotal = self.quantidade * self.preco_unitario
        super().save(*args, **kwargs)
        # Atualiza o total da comanda
        self.comanda.total = self.comanda.calcular_total()
        self.comanda.save()