from django.contrib import admin
from decimal import Decimal
from .models import (
    DroneType, TargetType, SwarmCompositionTemplate, 
    MissionSwarmConfig, Mission, ForceConfig
)

# Register models
admin.site.register(Mission)
admin.site.register(ForceConfig)
admin.site.register(DroneType)
admin.site.register(TargetType)
admin.site.register(SwarmCompositionTemplate)
admin.site.register(MissionSwarmConfig)


# Seed data on first admin access
def seed_initial_data():
    """Populate database with initial drone and target data"""
    
    # Only seed if database is empty
    if DroneType.objects.exists():
        return
    
    drones_data = [
        {
            'name': 'Attack Drone v2',
            'role': 'ATK',
            'description': 'High-payload strike platform',
            'cost': Decimal('15000.00'),
            'range_km': 250,
            'payload_kg': 5,
            'endurance_minutes': 45,
            'stealth_factor': 0.6,
        },
        {
            'name': 'Recon Quad',
            'role': 'REC',
            'description': 'Fast reconnaissance platform',
            'cost': Decimal('8500.00'),
            'range_km': 180,
            'payload_kg': 2,
            'endurance_minutes': 35,
            'stealth_factor': 0.8,
        },
        {
            'name': 'Decoy Swarm',
            'role': 'DEC',
            'description': 'Small decoy platform for jamming',
            'cost': Decimal('3200.00'),
            'range_km': 120,
            'payload_kg': 0.5,
            'endurance_minutes': 25,
            'stealth_factor': 0.7,
        },
        {
            'name': 'EW Jammer',
            'role': 'EW',
            'description': 'Electronic warfare platform',
            'cost': Decimal('22000.00'),
            'range_km': 200,
            'payload_kg': 8,
            'endurance_minutes': 50,
            'stealth_factor': 0.4,
        },
        {
            'name': 'Comm Relay',
            'role': 'COM',
            'description': 'Communication relay drone',
            'cost': Decimal('18500.00'),
            'range_km': 300,
            'payload_kg': 3,
            'endurance_minutes': 60,
            'stealth_factor': 0.5,
        },
        {
            'name': 'Nav INS',
            'role': 'NAV',
            'description': 'Navigation and INS platform',
            'cost': Decimal('12000.00'),
            'range_km': 150,
            'payload_kg': 2,
            'endurance_minutes': 40,
            'stealth_factor': 0.6,
        },
        {
            'name': 'Command Unit',
            'role': 'CMD',
            'description': 'Command and control platform',
            'cost': Decimal('45000.00'),
            'range_km': 400,
            'payload_kg': 10,
            'endurance_minutes': 90,
            'stealth_factor': 0.3,
        },
    ]
    
    drones = {}
    for drone_data in drones_data:
        drone = DroneType.objects.create(**drone_data)
        drones[drone.role] = drone
    
    targets_data = [
        {
            'name': 'Fixed Infrastructure',
            'category': 'FIXED',
            'description': 'Stationary targets like buildings, bridges',
            'composition': {
                'ATK': 40, 'REC': 15, 'DEC': 15, 'EW': 10, 'COM': 12, 'CMD': 5, 'NAV': 3
            }
        },
        {
            'name': 'Mobile Asset',
            'category': 'MOBILE',
            'description': 'Moving targets like convoys, aircraft',
            'composition': {
                'ATK': 35, 'REC': 25, 'DEC': 12, 'EW': 8, 'COM': 10, 'CMD': 7, 'NAV': 3
            }
        },
        {
            'name': 'Air Defense System',
            'category': 'AIR',
            'description': 'Anti-air radar and SAM sites',
            'composition': {
                'ATK': 30, 'REC': 20, 'DEC': 20, 'EW': 15, 'COM': 8, 'CMD': 5, 'NAV': 2
            }
        },
        {
            'name': 'Area Target',
            'category': 'AREA',
            'description': 'Dispersed targets across area',
            'composition': {
                'ATK': 25, 'REC': 30, 'DEC': 15, 'EW': 12, 'COM': 10, 'CMD': 5, 'NAV': 3
            }
        },
        {
            'name': 'High Value Target',
            'category': 'VIP',
            'description': 'Critical strategic targets',
            'composition': {
                'ATK': 45, 'REC': 20, 'DEC': 10, 'EW': 12, 'COM': 8, 'CMD': 3, 'NAV': 2
            }
        },
    ]
    
    for target_data in targets_data:
        composition = target_data.pop('composition')
        target = TargetType.objects.create(**target_data, recommended_composition=composition)
        
        # Create composition templates
        for role, percentage in composition.items():
            drone = drones.get(role)
            if drone:
                SwarmCompositionTemplate.objects.create(
                    target_type=target,
                    drone_type=drone,
                    percentage=percentage
                )


# Trigger seeding when admin is accessed
try:
    seed_initial_data()
except Exception as e:
    print(f"Seeding error (can be ignored): {e}")
