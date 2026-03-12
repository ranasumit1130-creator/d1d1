# config/wizard_views.py
"""
Multi-step mission configuration wizard views.
Handles Steps 1-5 of force configuration workflow.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
import json

from .models import Mission, ForceConfig, StepwiseForceConfig, ADSConfig, ADSSystem, ADSPlacement


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_force_config_or_404(mission_id, force_type):
    """Get ForceConfig or redirect to force_select."""
    mission = get_object_or_404(Mission, id=mission_id)
    force_config = get_object_or_404(
        ForceConfig, 
        mission=mission, 
        force_type=force_type
    )
    return mission, force_config


def check_prerequisites(force_config, required_steps):
    """
    Check if required steps are completed.
    
    Args:
        force_config: ForceConfig object
        required_steps: List of step numbers (e.g., [1, 2])
    
    Returns:
        (is_valid, missing_step) tuple
    """
    steps_map = {
        1: 'step1_completed',
        2: 'step2_completed',
        3: 'step3_completed',
        4: 'step4_completed',
        5: 'step5_completed',
    }
    
    for step in required_steps:
        field = steps_map.get(step)
        if field and not getattr(force_config, field):
            return False, step
    
    return True, None


# ============================================================
# STEP 1: SCENARIO SELECTION
# ============================================================

def step1_scenario_selection(request, mission_id, force_type):
    """
    View for Step 1: Scenario Selection.
    
    URL: /config/mission/<mission_id>/force/<force_type>/step1/
    Methods: GET (render form), POST (save scenario)
    Template: config/step1_scenario.html
    """
    mission, force_config = get_force_config_or_404(mission_id, force_type)
    
    context = {
        'mission': mission,
        'force_type': force_type,
        'force_config': force_config,
        'existing_scenario': force_config.config_data.get('scenario'),
        'scenarios': [
            ('one-to-one', '1 Base → 1 Target'),
            ('one-to-many', '1 Base → Many Targets'),
            ('many-to-one', 'Many Bases → 1 Target'),
            ('many-to-many', 'Many Bases → Many Targets'),
        ],
    }
    
    return render(request, 'config/step1_scenario.html', context)


# ============================================================
# STEP 2: MAP-BASED BASE & TARGET PLACEMENT
# ============================================================

def step2_base_target_selection(request, mission_id, force_type):
    """
    View for Step 2: Base & Target Selection on Cesium Map.
    
    URL: /config/mission/<mission_id>/force/<force_type>/step2/
    Requires: Step 1 completed
    Template: config/step2_map.html
    """
    mission, force_config = get_force_config_or_404(mission_id, force_type)
    
    # Check prerequisites
    is_valid, missing_step = check_prerequisites(force_config, [1])
    if not is_valid:
        messages.error(request, f"Please complete Step {missing_step} first")
        return redirect('config:step1_scenario', mission_id=mission_id, force_type=force_type)
    
    scenario = force_config.config_data.get('scenario')
    existing_bases = force_config.config_data.get('bases', [])
    existing_targets = force_config.config_data.get('targets', [])
    
    context = {
        'mission': mission,
        'force_type': force_type,
        'force_config': force_config,
        'scenario': scenario,
        'existing_bases': json.dumps(existing_bases),
        'existing_targets': json.dumps(existing_targets),
    }
    
    return render(request, 'config/step2_map.html', context)


# ============================================================
# STEP 3: SWARM COMPOSITION CONFIGURATION
# ============================================================

def step3_swarm_composition(request, mission_id, force_type):
    """
    View for Step 3: Drone Swarm Composition.
    
    URL: /config/mission/<mission_id>/force/<force_type>/step3/
    Requires: Steps 1, 2 completed
    Template: config/step3_swarm.html
    """
    mission, force_config = get_force_config_or_404(mission_id, force_type)
    
    # Check prerequisites
    is_valid, missing_step = check_prerequisites(force_config, [1, 2])
    if not is_valid:
        messages.error(request, f"Please complete Step {missing_step} first")
        return redirect('config:force_select', mission_id=mission_id)
    
    # Get existing swarm config
    existing_swarm = force_config.config_data.get('swarm', {})
    existing_analysis = force_config.config_data.get('analysis', {})
    
    context = {
        'mission': mission,
        'force_type': force_type,
        'force_config': force_config,
        'existing_swarm': json.dumps(existing_swarm),
        'existing_analysis': json.dumps(existing_analysis),
        'total_drones': existing_swarm.get('total_drones', 100),
    }
    
    return render(request, 'config/step3_swarm.html', context)


# ============================================================
# STEP 4: ADS CONFIGURATION
# ============================================================

def step4_ads_configuration(request, mission_id, force_type):
    """
    View for Step 4: ADS Configuration on Cesium Map.
    
    URL: /config/mission/<mission_id>/force/<force_type>/step4/
    Requires: Steps 1, 2, 3 completed
    Template: config/step4_ads.html
    """
    mission, force_config = get_force_config_or_404(mission_id, force_type)
    
    # Check prerequisites
    is_valid, missing_step = check_prerequisites(force_config, [1, 2, 3])
    if not is_valid:
        messages.error(request, f"Please complete Step {missing_step} first")
        return redirect('config:force_select', mission_id=mission_id)
    
    existing_ads = force_config.config_data.get('ads', [])
    bases = force_config.config_data.get('bases', [])
    targets = force_config.config_data.get('targets', [])
    
    context = {
        'mission': mission,
        'force_type': force_type,
        'force_config': force_config,
        'existing_ads': json.dumps(existing_ads),
        'bases': json.dumps(bases),
        'targets': json.dumps(targets),
    }
    
    return render(request, 'config/step4_ads.html', context)


# ============================================================
# STEP 5: REVIEW & FINALIZE
# ============================================================

def step5_review_and_save(request, mission_id, force_type):
    """
    View for Step 5: Final Review and Save.
    
    URL: /config/mission/<mission_id>/force/<force_type>/step5/
    Requires: Steps 1, 2, 3, 4 completed
    Template: config/step5_review.html
    """
    mission, force_config = get_force_config_or_404(mission_id, force_type)
    
    # Check prerequisites
    is_valid, missing_step = check_prerequisites(force_config, [1, 2, 3, 4])
    if not is_valid:
        messages.error(request, f"Please complete Step {missing_step} first")
        return redirect('config:force_select', mission_id=mission_id)
    
    # Prepare review data from config
    config_data = force_config.config_data
    
    context = {
        'mission': mission,
        'force_type': force_type,
        'force_config': force_config,
        'scenario': config_data.get('scenario'),
        'bases': config_data.get('bases', []),
        'targets': config_data.get('targets', []),
        'swarm': config_data.get('swarm', {}),
        'ads': config_data.get('ads', []),
        'analysis': config_data.get('analysis', {}),
    }
    
    return render(request, 'config/step5_review.html', context)


# ============================================================
# API VIEWS
# ============================================================

@csrf_exempt
@require_http_methods(["POST"])
def step4_save_ads(request):
    """POST /config/api/step4/save-ads/"""
    try:
        data = json.loads(request.body)
        mission = get_object_or_404(Mission, id=data.get('mission_id'))
        force_type = data.get('force_type', 'blue')
        
        config = StepwiseForceConfig.objects.get(mission=mission, force_type=force_type)
        
        # Store placed ADS systems
        placed_ads = data.get('placed_ads', [])
        
        ADSConfig.objects.update_or_create(
            config=config,
            defaults={
                'engagement_mode': 'ACTIVE',  # Default mode
                'coverage_radius_km': 120,  # Default radius
                'selective_targets': [],
                'placed_ads': placed_ads,  # Store the ADS placements
                'locked': True,
            }
        )
        
        config.step4_status = 'COMPLETED'
        config.save()
        
        return JsonResponse({'success': True})
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# ============================================================
# STEP 1 API: SELECT SCENARIO
# ============================================================

@csrf_exempt
@require_http_methods(["POST"])
def step1_select_scenario(request):
    """
    POST /config/api/step1/select-scenario/
    Save scenario selection and proceed to step 2.
    
    Request:
    {
        "mission_id": <ID>,
        "force_type": "blue",
        "scenario": "ONE_BASE_ONE_TARGET"
    }
    """
    try:
        data = json.loads(request.body)
        mission_id = data.get('mission_id')
        force_type = data.get('force_type', 'blue').lower()
        scenario = data.get('scenario')
        
        # Validate input
        if not mission_id or not scenario:
            return JsonResponse({'success': False, 'error': 'Missing mission_id or scenario'}, status=400)
        
        # Get mission and force config
        mission = get_object_or_404(Mission, id=mission_id)
        force_config, created = ForceConfig.objects.get_or_create(
            mission=mission,
            force_type=force_type,
            defaults={'config_data': {}}
        )
        
        # Save scenario to config_data
        if force_config.config_data is None:
            force_config.config_data = {}
        force_config.config_data['scenario'] = scenario
        force_config.step1_completed = True
        force_config.save()
        
        # Return success with redirect URL
        return JsonResponse({
            'success': True,
            'message': 'Scenario selected successfully',
            'next_url': f'/config/mission/{mission_id}/force/{force_type}/step2/'
        })
        
    except Mission.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Mission not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


# ============================================================
# STEP 2 API: SAVE PLACEMENT
# ============================================================

@csrf_exempt
@require_http_methods(["POST"])
def step2_save_placement(request):
    """
    POST /config/api/step2/save-placement/
    Save base and target placements from map.
    
    Request:
    {
        "mission_id": <ID>,
        "force_type": "blue",
        "bases": [{"name": "Base 1", "lat": 28.5, "lon": 77.2}, ...],
        "targets": [{"name": "Target 1", "lat": 28.6, "lon": 77.3}, ...]
    }
    """
    try:
        data = json.loads(request.body)
        mission_id = data.get('mission_id')
        force_type = data.get('force_type', 'blue').lower()
        bases = data.get('bases', [])
        targets = data.get('targets', [])
        
        # Validate input
        if not mission_id:
            return JsonResponse({'success': False, 'error': 'Missing mission_id'}, status=400)
        
        # Get mission and force config
        mission = get_object_or_404(Mission, id=mission_id)
        force_config = get_object_or_404(
            ForceConfig, 
            mission=mission, 
            force_type=force_type
        )
        
        # Check step 1 is completed
        if not force_config.step1_completed:
            return JsonResponse({'success': False, 'error': 'Please complete Step 1 first'}, status=400)
        
        # Save bases and targets to config_data
        if force_config.config_data is None:
            force_config.config_data = {}
        force_config.config_data['bases'] = bases
        force_config.config_data['targets'] = targets
        force_config.step2_completed = True
        force_config.save()
        
        # Return success with redirect URL
        return JsonResponse({
            'success': True,
            'message': 'Placement saved successfully',
            'next_url': f'/config/mission/{mission_id}/force/{force_type}/step3/'
        })
        
    except Mission.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Mission not found'}, status=404)
    except ForceConfig.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Force configuration not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


# ============================================================
# STEP 4 API: ADS CONFIGURATION
# ============================================================

@csrf_exempt
@require_http_methods(["POST"])
def step4_get_ads_systems(request):
    """
    POST /config/api/step4/get-ads-systems/
    Returns all ADS systems organized by layer.
    """
    try:
        systems_by_layer = {
            'outer': [],
            'middle': [],
            'inner': [],
            'jammer': []
        }
        
        for system in ADSSystem.objects.all():
            systems_by_layer[system.layer].append(system.to_dict())
        
        return JsonResponse({
            'success': True,
            'systems_by_layer': systems_by_layer
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def step4_place_ads(request):
    """
    POST /config/api/step4/place-ads/
    Place an ADS system at a specific location on the map.
    
    Request:
    {
        "mission_id": <ID>,
        "force_type": "red",
        "ads_system_id": <ID>,
        "latitude": 28.5,
        "longitude": 77.2
    }
    """
    try:
        data = json.loads(request.body)
        mission_id = data.get('mission_id')
        force_type = data.get('force_type', 'red').lower()
        ads_system_id = data.get('ads_system_id')
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        
        mission = get_object_or_404(Mission, id=mission_id)
        ads_system = get_object_or_404(ADSSystem, id=ads_system_id)
        
        # Create placement
        placement = ADSPlacement.objects.create(
            mission=mission,
            force_type=force_type,
            ads_system=ads_system,
            latitude=latitude,
            longitude=longitude
        )
        
        return JsonResponse({
            'success': True,
            'placement': placement.to_dict()
        })
    
    except Mission.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Mission not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def step4_remove_ads(request):
    """
    POST /config/api/step4/remove-ads/
    Remove an ADS placement.
    """
    try:
        data = json.loads(request.body)
        placement_id = data.get('placement_id')
        
        placement = get_object_or_404(ADSPlacement, id=placement_id)
        placement.delete()
        
        return JsonResponse({'success': True})
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def step5_save_config(request):
    """
    POST /config/api/step5/save-config/
    Final save of configuration and mark force as complete.
    """
    try:
        data = json.loads(request.body)
        mission_id = data.get('mission_id')
        force_type = data.get('force_type', 'blue').lower()
        
        mission = get_object_or_404(Mission, id=mission_id)
        force_config = get_object_or_404(
            ForceConfig, 
            mission=mission, 
            force_type=force_type
        )
        
        # Mark configuration as complete
        force_config.step5_completed = True
        force_config.is_configured = True
        force_config.save()
        
        # Determine next redirect
        if force_type == 'blue':
            next_url = f'/config/mission/{mission_id}/force-select/?msg=Blue_force_configured_now_configure_red'
        else:
            next_url = f'/config/mission/{mission_id}/simulation-ready/?msg=Both_forces_configured'
        
        return JsonResponse({
            'success': True,
            'message': f'{force_type.upper()} force configuration saved successfully',
            'next_url': next_url
        })
    
    except Mission.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Mission not found'}, status=404)
    except ForceConfig.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Force configuration not found'}, status=404)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def step4_save_ads_placements(request):
    """
    POST /config/api/step4/save-ads-placements/
    Save ADS placements for a mission/force combination.
    
    Request:
    {
        "mission_id": <ID>,
        "force_type": "red",
        "ads_placements": [
            {
                "ads_type_name": "Patriot SAM",
                "latitude": 28.5,
                "longitude": 77.2,
                "detection_range": 100,
                "intercept_range": 60
            }
        ]
    }
    """
    # Mapping from frontend names to database names
    ADS_NAME_MAPPING = {
        'Patriot SAM': 'Patriot PAC-3',
        'S-300 System': 'S-400 Triumf',
        'Pantsir-S1': 'Pantsir-S1',
        'IRIS-T System': 'IRIS-T',
        'Hawk System': 'THAAD System',
        'Avenger MANPAD': 'Phalanx CIWS',
        'Tor System': 'Buk-M2',
    }
    
    try:
        data = json.loads(request.body)
        mission_id = data.get('mission_id')
        force_type = data.get('force_type', 'red').lower()
        ads_placements = data.get('ads_placements', [])
        
        mission = get_object_or_404(Mission, id=mission_id)
        force_config = get_object_or_404(
            ForceConfig,
            mission=mission,
            force_type=force_type
        )
        
        # Check step 3 is completed
        if not force_config.step3_completed:
            return JsonResponse({
                'success': False,
                'error': 'Please complete Step 3 first'
            }, status=400)
        
        # Delete existing placements for this mission/force
        ADSPlacement.objects.filter(mission=mission, force_type=force_type).delete()
        
        # Create new placements
        created_placements = []
        for placement_data in ads_placements:
            ads_type_name = placement_data.get('ads_type_name')
            
            # Map frontend name to database name
            db_name = ADS_NAME_MAPPING.get(ads_type_name, ads_type_name)
            
            # Try to find ADS system by name
            try:
                ads_system = ADSSystem.objects.get(name=db_name)
            except ADSSystem.DoesNotExist:
                # If exact match fails, try partial match
                try:
                    ads_system = ADSSystem.objects.get(name__icontains=db_name.split()[0])
                except (ADSSystem.DoesNotExist, ADSSystem.MultipleObjectsReturned):
                    # If still not found, get a default high-range system
                    ads_systems = ADSSystem.objects.all().order_by('-detection_range')
                    if ads_systems.exists():
                        ads_system = ads_systems.first()
                    else:
                        return JsonResponse({
                            'success': False,
                            'error': f'No ADS systems found in database. Please run: python manage.py populate_ads_systems'
                        }, status=400)
            
            placement = ADSPlacement.objects.create(
                mission=mission,
                force_type=force_type,
                ads_system=ads_system,
                latitude=float(placement_data.get('latitude')),
                longitude=float(placement_data.get('longitude'))
            )
            created_placements.append(placement.to_dict())
        
        # Update force config
        if force_config.config_data is None:
            force_config.config_data = {}
        
        force_config.config_data['ads'] = {
            'placements': created_placements,
            'total_systems': len(created_placements),
            'total_cost': sum(float(p.get('cost_million_usd', 0)) for p in created_placements)
        }
        force_config.step4_completed = True
        force_config.save()
        
        return JsonResponse({
            'success': True,
            'message': 'ADS configuration saved successfully',
            'placements_count': len(created_placements),
            'next_url': f'/config/mission/{mission_id}/force/{force_type}/step5/'
        })
    
    except Mission.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Mission not found'}, status=404)
    except ForceConfig.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Force configuration not found'}, status=404)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


# config/management/commands/populate_ads_systems.py
"""
Command to populate ADS systems database with real-world systems.
"""

from django.core.management.base import BaseCommand
from config.models import ADSSystem

class Command(BaseCommand):
    help = 'Populate ADS systems database with real-world systems'

    def handle(self, *args, **options):
        systems = [
            # OUTER LAYER - Long Range (100+ km)
            {
                'name': 'S-400 Triumf',
                'layer': 'outer',
                'system_type': 'missile',
                'country': 'Russia',
                'detection_range': 400,
                'intercept_range': 250,
                'max_targets': 36,
                'cost_million_usd': 300.0,
                'color_hex': '#FF3B30',
                'icon': '🎯',
            },
            {
                'name': 'THAAD System',
                'layer': 'outer',
                'system_type': 'missile',
                'country': 'USA',
                'detection_range': 350,
                'intercept_range': 200,
                'max_targets': 8,
                'cost_million_usd': 1200.0,
                'color_hex': '#FF3B30',
                'icon': '🛡️',
            },
            {
                'name': 'HQ-9 System',
                'layer': 'outer',
                'system_type': 'missile',
                'country': 'China',
                'detection_range': 200,
                'intercept_range': 125,
                'max_targets': 6,
                'cost_million_usd': 180.0,
                'color_hex': '#FF3B30',
                'icon': '📡',
            },
            
            # MIDDLE LAYER - Medium Range (30-100 km)
            {
                'name': 'Patriot PAC-3',
                'layer': 'middle',
                'system_type': 'missile',
                'country': 'USA',
                'detection_range': 160,
                'intercept_range': 80,
                'max_targets': 4,
                'cost_million_usd': 100.0,
                'color_hex': '#FF9500',
                'icon': '🚀',
            },
            {
                'name': 'Buk-M2 System',
                'layer': 'middle',
                'system_type': 'missile',
                'country': 'Russia',
                'detection_range': 120,
                'intercept_range': 70,
                'max_targets': 6,
                'cost_million_usd': 150.0,
                'color_hex': '#FF9500',
                'icon': '🎯',
            },
            {
                'name': 'IRIS-T System',
                'layer': 'middle',
                'system_type': 'missile',
                'country': 'Germany',
                'detection_range': 100,
                'intercept_range': 50,
                'max_targets': 4,
                'cost_million_usd': 180.0,
                'color_hex': '#FF9500',
                'icon': '🛡️',
            },
            
            # INNER LAYER - Close Defense (5-30 km)
            {
                'name': 'Gepard CIWS',
                'layer': 'inner',
                'system_type': 'gun',
                'country': 'Germany',
                'detection_range': 35,
                'intercept_range': 25,
                'max_targets': 1,
                'cost_million_usd': 45.0,
                'color_hex': '#34C759',
                'icon': '🔫',
            },
            {
                'name': 'Phalanx CIWS',
                'layer': 'inner',
                'system_type': 'gun',
                'country': 'USA',
                'detection_range': 50,
                'intercept_range': 35,
                'max_targets': 2,
                'cost_million_usd': 150.0,
                'color_hex': '#34C759',
                'icon': '💥',
            },
            {
                'name': 'Pantsir-S1',
                'layer': 'inner',
                'system_type': 'gun',
                'country': 'Russia',
                'detection_range': 40,
                'intercept_range': 30,
                'max_targets': 4,
                'cost_million_usd': 80.0,
                'color_hex': '#34C759',
                'icon': '🎯',
            },
            
            # JAMMER SYSTEMS - Electronic Warfare
            {
                'name': 'EW Jammer - Generic',
                'layer': 'jammer',
                'system_type': 'jammer',
                'country': 'Multi',
                'detection_range': 150,
                'intercept_range': 100,
                'max_targets': 10,
                'effectiveness_percent': 60,
                'cost_million_usd': 50.0,
                'color_hex': '#FFFF00',
                'icon': '📶',
            },
        ]
        
        created = 0
        updated = 0
        
        for sys_data in systems:
            obj, created_flag = ADSSystem.objects.update_or_create(
                name=sys_data['name'],
                defaults=sys_data
            )
            if created_flag:
                created += 1
                self.stdout.write(self.style.SUCCESS(f'Created: {sys_data["name"]}'))
            else:
                updated += 1
                self.stdout.write(self.style.WARNING(f'Updated: {sys_data["name"]}'))
        
        self.stdout.write(self.style.SUCCESS(f'\n✓ {created} systems created, {updated} updated'))
