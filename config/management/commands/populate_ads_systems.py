from django.core.management.base import BaseCommand
from config.models import ADSSystem
from decimal import Decimal


class Command(BaseCommand):
    help = 'Populate ADS Systems database with 9 systems (3 outer, 3 middle, 3 inner)'

    def handle(self, *args, **kwargs):
        self.stdout.write("Populating ADS Systems...")
        
        systems_data = [
            # OUTER LAYER (Long Range)
            {
                'name': 'S-400 Triumf',
                'layer': 'outer',
                'system_type': 'missile',
                'country': 'Russia',
                'detection_range': 600,
                'intercept_range': 400,
                'max_targets': 36,
                'effectiveness_percent': 95,
                'cost_million_usd': Decimal('1200.00'),
                'color_hex': '#FF0000',
                'icon': '🔴'
            },
            {
                'name': 'THAAD',
                'layer': 'outer',
                'system_type': 'missile',
                'country': 'USA',
                'detection_range': 290,
                'intercept_range': 200,
                'max_targets': 6,
                'effectiveness_percent': 98,
                'cost_million_usd': Decimal('800.00'),
                'color_hex': '#0000FF',
                'icon': '🔵'
            },
            {
                'name': 'HQ-9',
                'layer': 'outer',
                'system_type': 'missile',
                'country': 'China',
                'detection_range': 500,
                'intercept_range': 300,
                'max_targets': 12,
                'effectiveness_percent': 92,
                'cost_million_usd': Decimal('600.00'),
                'color_hex': '#FFD700',
                'icon': '🟡'
            },
            
            # MIDDLE LAYER (Medium Range)
            {
                'name': 'Patriot PAC-3',
                'layer': 'middle',
                'system_type': 'missile',
                'country': 'USA',
                'detection_range': 150,
                'intercept_range': 60,
                'max_targets': 4,
                'effectiveness_percent': 96,
                'cost_million_usd': Decimal('500.00'),
                'color_hex': '#0000FF',
                'icon': '🟦'
            },
            {
                'name': 'Buk-M2',
                'layer': 'middle',
                'system_type': 'missile',
                'country': 'Russia',
                'detection_range': 160,
                'intercept_range': 50,
                'max_targets': 6,
                'effectiveness_percent': 90,
                'cost_million_usd': Decimal('300.00'),
                'color_hex': '#FF6B00',
                'icon': '🟧'
            },
            {
                'name': 'IRIS-T',
                'layer': 'middle',
                'system_type': 'missile',
                'country': 'Germany',
                'detection_range': 90,
                'intercept_range': 25,
                'max_targets': 8,
                'effectiveness_percent': 94,
                'cost_million_usd': Decimal('400.00'),
                'color_hex': '#00FF00',
                'icon': '🟩'
            },
            
            # INNER LAYER (Close Defense)
            {
                'name': 'Gepard',
                'layer': 'inner',
                'system_type': 'gun',
                'country': 'Germany',
                'detection_range': 35,
                'intercept_range': 30,
                'max_targets': 2,
                'effectiveness_percent': 85,
                'cost_million_usd': Decimal('120.00'),
                'color_hex': '#FF8C00',
                'icon': '🟠'
            },
            {
                'name': 'Phalanx CIWS',
                'layer': 'inner',
                'system_type': 'gun',
                'country': 'USA',
                'detection_range': 50,
                'intercept_range': 30,
                'max_targets': 10,
                'effectiveness_percent': 98,
                'cost_million_usd': Decimal('200.00'),
                'color_hex': '#1E90FF',
                'icon': '🟦'
            },
            {
                'name': 'Pantsir-S1',
                'layer': 'inner',
                'system_type': 'gun',
                'country': 'Russia',
                'detection_range': 40,
                'intercept_range': 20,
                'max_targets': 8,
                'effectiveness_percent': 90,
                'cost_million_usd': Decimal('80.00'),
                'color_hex': '#34C759',
                'icon': '🟢'
            },
        ]
        
        created_count = 0
        for sys_data in systems_data:
            system, created = ADSSystem.objects.get_or_create(
                name=sys_data['name'],
                defaults=sys_data
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'✓ Created: {system.name}'))
                created_count += 1
            else:
                self.stdout.write(f'  Already exists: {system.name}')
        
        total = ADSSystem.objects.count()
        self.stdout.write(self.style.SUCCESS(f'\n✅ Total: {total} ADS systems in database'))