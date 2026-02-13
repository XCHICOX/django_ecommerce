from django.core.management.base import BaseCommand, CommandError
from shop.models import Tenant
from delivery.models import DeliveryCategory, MenuItem, Combo, ComboSlot, DeliveryOptional, DeliveryZone
from bar.models import BarCategory, BarMenuItem

class Command(BaseCommand):
    help = 'Copia dados de cardápio (Delivery e Bar) de um tenant para outro.'

    def add_arguments(self, parser):
        parser.add_argument('source_slug', type=str, help='Slug do tenant de origem (de onde copiar)')
        parser.add_argument('target_slug', type=str, help='Slug do tenant de destino (para onde copiar)')
        parser.add_argument('--app', type=str, choices=['delivery', 'bar', 'all'], default='all', help='Qual app copiar (delivery, bar ou all)')
        parser.add_argument('--clear', action='store_true', help='Limpa os dados do destino antes de copiar (CUIDADO!)')

    def handle(self, *args, **options):
        source_slug = options['source_slug']
        target_slug = options['target_slug']
        app_choice = options['app']
        clear = options['clear']

        try:
            source_tenant = Tenant.objects.get(slug=source_slug)
            self.stdout.write(self.style.SUCCESS(f'Tenant de origem encontrado: {source_tenant.name}'))
        except Tenant.DoesNotExist:
            raise CommandError(f'Tenant de origem "{source_slug}" não encontrado.')

        try:
            target_tenant = Tenant.objects.get(slug=target_slug)
            self.stdout.write(self.style.SUCCESS(f'Tenant de destino encontrado: {target_tenant.name}'))
        except Tenant.DoesNotExist:
            raise CommandError(f'Tenant de destino "{target_slug}" não encontrado.')
        
        self.stdout.write(self.style.WARNING(f'Iniciando cópia de "{source_tenant.name}" para "{target_tenant.name}"...'))

        if app_choice in ['delivery', 'all']:
            self._copy_delivery_data(source_tenant, target_tenant, clear)
        
        if app_choice in ['bar', 'all']:
            self._copy_bar_data(source_tenant, target_tenant, clear)

        self.stdout.write(self.style.SUCCESS('Cópia concluída com sucesso!'))

    def _copy_delivery_data(self, source, target, clear):
        self.stdout.write(f'--- Copiando dados do Delivery ---')
        
        # Limpa dados se solicitado
        if clear:
           self.stdout.write('Limpando dados de Delivery no destino...')
           # Deletar itens primeiro por causa das dependencias
           Combo.objects.filter(tenant=target).delete() 
           MenuItem.objects.filter(tenant=target).delete()
           DeliveryOptional.objects.filter(tenant=target).delete()
           DeliveryCategory.objects.filter(tenant=target).delete()
           DeliveryZone.objects.filter(tenant=target).delete()

        # 1. Categories
        cat_map = {} # Maps old_id -> new_instance
        categories = DeliveryCategory.objects.filter(tenant=source)
        self.stdout.write(f'Copiando {categories.count()} categorias...')
        
        for cat in categories:
            new_cat, created = DeliveryCategory.objects.get_or_create(
                tenant=target,
                name=cat.name
            )
            cat_map[cat.id] = new_cat

        # 2. Items
        items = MenuItem.objects.filter(tenant=source)
        self.stdout.write(f'Copiando {items.count()} itens...')
        count = 0
        for item in items:
            if item.category_id in cat_map:
                MenuItem.objects.create(
                    tenant=target,
                    category=cat_map[item.category_id],
                    name=item.name,
                    description=item.description,
                    price=item.price,
                    image=item.image, # Reutiliza o arquivo (caminho)
                    is_available=item.is_available
                )
                count += 1
        self.stdout.write(f'{count} itens copiados.')

        # 3. Optionals
        optionals = DeliveryOptional.objects.filter(tenant=source)
        self.stdout.write(f'Copiando {optionals.count()} opcionais...')
        count = 0
        for opt in optionals:
            if opt.category_id in cat_map:
                DeliveryOptional.objects.create(
                    tenant=target,
                    category=cat_map[opt.category_id],
                    name=opt.name,
                    price=opt.price
                )
                count += 1
        self.stdout.write(f'{count} opcionais copiados.')

        # 4. Combos
        combos = Combo.objects.filter(tenant=source)
        self.stdout.write(f'Copiando {combos.count()} combos...')
        for combo in combos:
            new_combo = Combo.objects.create(
                tenant=target,
                name=combo.name,
                description=combo.description,
                price=combo.price,
                image=combo.image,
                is_available=combo.is_available
            )
            # Combo Slots
            for slot in combo.slots.all():
                if slot.allowed_category_id in cat_map:
                    ComboSlot.objects.create(
                        combo=new_combo,
                        allowed_category=cat_map[slot.allowed_category_id]
                    )

        # 5. Zones
        zones = DeliveryZone.objects.filter(tenant=source)
        self.stdout.write(f'Copiando {zones.count()} zonas de entrega...')
        for zone in zones:
            DeliveryZone.objects.get_or_create(
                tenant=target,
                neighborhood=zone.neighborhood,
                defaults={'delivery_fee': zone.delivery_fee}
            )

    def _copy_bar_data(self, source, target, clear):
        self.stdout.write(f'--- Copiando dados do Bar ---')

        if clear:
            self.stdout.write('Limpando dados de Bar no destino...')
            BarMenuItem.objects.filter(tenant=target).delete()
            BarCategory.objects.filter(tenant=target).delete()

        # 1. Categories
        cat_map = {}
        categories = BarCategory.objects.filter(tenant=source)
        self.stdout.write(f'Copiando {categories.count()} categorias...')
        for cat in categories:
            new_cat, created = BarCategory.objects.get_or_create(
                tenant=target,
                name=cat.name
            )
            cat_map[cat.id] = new_cat

        # 2. Items
        items = BarMenuItem.objects.filter(tenant=source)
        self.stdout.write(f'Copiando {items.count()} itens...')
        count = 0
        for item in items:
            if item.category_id in cat_map:
                BarMenuItem.objects.create(
                    tenant=target,
                    category=cat_map[item.category_id],
                    name=item.name,
                    price=item.price,
                    is_available=item.is_available
                )
                count += 1
        self.stdout.write(f'{count} itens copiados.')
