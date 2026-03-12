from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import View, FormView, CreateView, DetailView
from django.urls import reverse_lazy
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
import json

from .models import Mission, ForceConfig
from assets.models import ADSSystem 
from .forms import (
    MissionCreateForm, ScenarioSelectionForm, BaseFormSet, TargetFormSet,
    DroneFormSet, ADSFormSet
)

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def calculate_readiness(mission):
    """
    Calculate system readiness percentage based on force configuration status.
    
    Args:
        mission: Mission object
        
    Returns:
        dict with readiness info:
        {
            'configured_count': int (0, 1, or 2),
            'readiness_percent': int (0, 50, or 100),
            'blue_configured': bool,
            'red_configured': bool,
            'both_configured': bool
        }
    """
    forces = ForceConfig.objects.filter(mission=mission)
    
    blue_force = forces.filter(force_type='blue').first()
    red_force = forces.filter(force_type='red').first()
    
    blue_configured = blue_force.is_configured if blue_force else False
    red_configured = red_force.is_configured if red_force else False
    
    configured_count = sum([blue_configured, red_configured])
    
    if configured_count == 0:
        readiness_percent = 0
    elif configured_count == 1:
        readiness_percent = 50
    else:  # configured_count == 2
        readiness_percent = 100
    
    return {
        'configured_count': configured_count,
        'readiness_percent': readiness_percent,
        'blue_configured': blue_configured,
        'red_configured': red_configured,
        'both_configured': (configured_count == 2)
    }


# Drone and ADS capabilities (hardcoded reference data)
DRONE_CAPABILITIES = {
    'attack': {
        'name': 'Attack Drone',
        'range': '1850 km',
        'speed': '200 knots',
        'payload': '1700 kg',
        'endurance': '27 hrs',
        'stealth': 'Medium',
        'detection_difficulty': 3
    },
    'kamikaze': {
        'name': 'Kamikaze Drone',
        'range': '200 km',
        'speed': '400 knots',
        'payload': '23 kg warhead',
        'endurance': '45 mins',
        'stealth': 'High',
        'detection_difficulty': 4
    },
    'surveillance': {
        'name': 'Surveillance Drone',
        'range': '300 km',
        'speed': '80 knots',
        'payload': 'Sensors',
        'endurance': '27 hrs',
        'stealth': 'Low',
        'detection_difficulty': 1
    }
}

ADS_CAPABILITIES = {
    's-400': {
        'name': 'S-400 Triumf',
        'detection_range': '600 km',
        'intercept_range': '400 km',
        'max_altitude': '35,000 m',
        'simultaneous_targets': 36,
        'success_probability': {
            'attack': 0.85,
            'kamikaze': 0.90,
            'surveillance': 0.95
        }
    },
    'akash-ng': {
        'name': 'Akash-NG',
        'detection_range': '150 km',
        'intercept_range': '100 km',
        'max_altitude': '30,000 m',
        'simultaneous_targets': 12,
        'success_probability': {
            'attack': 0.75,
            'kamikaze': 0.85,
            'surveillance': 0.90
        }
    },
    'barak-8': {
        'name': 'Barak-8',
        'detection_range': '100 km',
        'intercept_range': '80 km',
        'max_altitude': '25,000 m',
        'simultaneous_targets': 8,
        'success_probability': {
            'attack': 0.70,
            'kamikaze': 0.80,
            'surveillance': 0.85
        }
    },
    'iron-dome': {
        'name': 'Iron Dome',
        'detection_range': '50 km',
        'intercept_range': '40 km',
        'max_altitude': '15,000 m',
        'simultaneous_targets': 3,
        'success_probability': {
            'attack': 0.80,
            'kamikaze': 0.95,
            'surveillance': 0.90
        }
    },
    'patriot': {
        'name': 'Patriot (MIM-104)',
        'detection_range': '200 km',
        'intercept_range': '150 km',
        'max_altitude': '24,000 m',
        'simultaneous_targets': 16,
        'success_probability': {
            'attack': 0.80,
            'kamikaze': 0.88,
            'surveillance': 0.92
        }
    },
    'tor-m2': {
        'name': 'Tor-M2',
        'detection_range': '60 km',
        'intercept_range': '50 km',
        'max_altitude': '10,000 m',
        'simultaneous_targets': 4,
        'success_probability': {
            'attack': 0.75,
            'kamikaze': 0.85,
            'surveillance': 0.88
        }
    },
    'pantsir-s1': {
        'name': 'Pantsir-S1',
        'detection_range': '80 km',
        'intercept_range': '60 km',
        'max_altitude': '15,000 m',
        'simultaneous_targets': 6,
        'success_probability': {
            'attack': 0.78,
            'kamikaze': 0.87,
            'surveillance': 0.90
        }
    }
}


class MissionCreateView(FormView):
    """
    Initial view to create a new mission.
    Auto-generates Mission ID and initializes both force configurations via signal.
    
    URL: /config/mission/create/
    Template: config/mission_create.html
    """
    template_name = 'config/mission_create.html'
    form_class = MissionCreateForm
    success_url = None
    
    def form_valid(self, form):
        """
        Process mission creation.
        
        Steps:
        1. Create Mission record
        2. Signal auto-creates ForceConfig entries (BLUE + RED)
        3. Set is_configured=False for both (via signal)
        4. Redirect to force-select page
        """
        mission_name = form.cleaned_data['mission_name']
        
        # Step 1: Create the mission with auto-generated ID
        # Signal will auto-create both Blue and Red ForceConfig entries
        mission = Mission.objects.create(
            name=mission_name,
            created_by=self.request.user if self.request.user.is_authenticated else None
        )
        
        # Store mission ID in session
        self.request.session['mission_id'] = mission.id
        
        messages.success(
            self.request, 
            f"✓ Mission '{mission_name}' created with ID #{mission.id}!"
        )
        
        # Step 4: Redirect to force selection
        return redirect('config:force_select', mission_id=mission.id)


class ForceSelectView(DetailView):
    """
    View to let user select which force (Blue or Red) to configure.
    
    URL: /config/mission/<mission_id>/force-select/
    Template: config/force_select.html
    
    Context includes:
    - mission: Mission object
    - blue_force: ForceConfig for blue
    - red_force: ForceConfig for red
    - readiness: Readiness dict with percent and status
    """
    model = Mission
    template_name = 'config/force_select.html'
    context_object_name = 'mission'
    pk_url_kwarg = 'mission_id'
    
    def get_context_data(self, **kwargs):
        """
        Prepare context with force configs and readiness calculation.
        """
        context = super().get_context_data(**kwargs)
        mission = self.get_object()
        
        # Fetch force configs
        blue_force = ForceConfig.objects.filter(
            mission=mission, 
            force_type='blue'
        ).first()
        red_force = ForceConfig.objects.filter(
            mission=mission, 
            force_type='red'
        ).first()
        
        # Add to context
        context['blue_force'] = blue_force
        context['red_force'] = red_force
        
        # Calculate readiness
        readiness = calculate_readiness(mission)
        context['readiness'] = readiness
        
        return context


def force_config_view(request, mission_id, force_type):
    """
    Function-based view for force configuration.
    
    URL: /config/mission/<mission_id>/force/<force_type>/
    Methods: GET (show form), POST (save config)
    Template: config/force_config.html
    
    Handles:
    - Scenario selection
    - Base placement
    - Target placement
    - Drone configuration
    - ADS configuration
    """
    # Fetch mission
    mission = get_object_or_404(Mission, id=mission_id)
    
    # Validate force_type
    if force_type not in ['blue', 'red']:
        messages.error(request, "Invalid force type")
        return redirect('config:force_select', mission_id=mission_id)
    
    # Fetch or create force config
    force_config, created = ForceConfig.objects.get_or_create(
        mission=mission,
        force_type=force_type,
        defaults={'config_data': {}, 'is_configured': False}
    )
    
    existing_config = force_config.config_data if force_config.config_data else {}
    
    if request.method == 'GET':
        # Show configuration form
        existing_scenario = existing_config.get('scenario', 'one-to-one')
        existing_bases = existing_config.get('bases', [])
        existing_targets = existing_config.get('targets', [])
        existing_drones = existing_config.get('drones', [])
        existing_ads = existing_config.get('ads', [])
        
        # Initialize formsets with existing data
        base_data = [{'name': b['name'], 'latitude': b['latitude'], 'longitude': b['longitude']}
                    for b in existing_bases] if existing_bases else [{}]
        target_data = [{'name': t['name'], 'latitude': t['latitude'], 'longitude': t['longitude']}
                      for t in existing_targets] if existing_targets else [{}]
        drone_data = [{'drone_type': d['drone_type'], 'quantity': d['quantity'],
                      'attack_pattern': d['attack_pattern']}
                     for d in existing_drones] if existing_drones else [{}]
        ads_data = [{'ads_type': a['ads_type'], 'latitude': a['latitude'],
                    'longitude': a['longitude']}
                   for a in existing_ads] if existing_ads else []
        
        scenario_form = ScenarioSelectionForm(initial={'scenario': existing_scenario})
        base_formset = BaseFormSet(initial=base_data, prefix='bases')
        target_formset = TargetFormSet(initial=target_data, prefix='targets')
        drone_formset = DroneFormSet(initial=drone_data, prefix='drones')
        ads_formset = ADSFormSet(initial=ads_data, prefix='ads')
        
        context = {
            'mission': mission,
            'force_type': force_type,
            'force_display': 'BLUE' if force_type == 'blue' else 'RED',
            'scenario_form': scenario_form,
            'base_formset': base_formset,
            'target_formset': target_formset,
            'drone_formset': drone_formset,
            'ads_formset': ads_formset,
            'drone_capabilities': DRONE_CAPABILITIES,
            'ads_capabilities': ADS_CAPABILITIES,
        }
        
        return render(request, 'config/force_config.html', context)
    
    elif request.method == 'POST':
        # Process form submission
        scenario_form = ScenarioSelectionForm(request.POST)
        base_formset = BaseFormSet(request.POST, prefix='bases')
        target_formset = TargetFormSet(request.POST, prefix='targets')
        drone_formset = DroneFormSet(request.POST, prefix='drones')
        ads_formset = ADSFormSet(request.POST, prefix='ads')
        
        # Validate all forms
        if all([scenario_form.is_valid(), base_formset.is_valid(),
                target_formset.is_valid(), drone_formset.is_valid(),
                ads_formset.is_valid()]):
            
            # Build config data structure
            config_data = {
                'scenario': scenario_form.cleaned_data['scenario'],
                'bases': [
                    form.cleaned_data 
                    for form in base_formset 
                    if form.cleaned_data
                ],
                'targets': [
                    form.cleaned_data 
                    for form in target_formset 
                    if form.cleaned_data
                ],
                'drones': [
                    {
                        'drone_type': form.cleaned_data['drone_type'],
                        'quantity': form.cleaned_data['quantity'],
                        'attack_pattern': form.cleaned_data['attack_pattern'],
                        'capabilities': DRONE_CAPABILITIES.get(
                            form.cleaned_data['drone_type'], 
                            {}
                        )
                    }
                    for form in drone_formset 
                    if form.cleaned_data
                ],
                'ads': [
                    {
                        'ads_type': form.cleaned_data['ads_type'],
                        'latitude': form.cleaned_data['latitude'],
                        'longitude': form.cleaned_data['longitude'],
                        'capabilities': ADS_CAPABILITIES.get(
                            form.cleaned_data['ads_type'], 
                            {}
                        )
                    }
                    for form in ads_formset 
                    if form.cleaned_data
                ]
            }
            
            # Save to database
            force_config.config_data = config_data
            force_config.is_configured = True  # Mark as configured
            force_config.updated_at = timezone.now()
            force_config.save()
            
            force_display = 'BLUE' if force_type == 'blue' else 'RED'
            messages.success(
                request, 
                f"✓ {force_display} Force configured successfully!"
            )
            
            # Redirect back to force select
            return redirect('config:force_select', mission_id=mission_id)
        
        else:
            # Form validation failed - show errors
            context = {
                'mission': mission,
                'force_type': force_type,
                'force_display': 'BLUE' if force_type == 'blue' else 'RED',
                'scenario_form': scenario_form,
                'base_formset': base_formset,
                'target_formset': target_formset,
                'drone_formset': drone_formset,
                'ads_formset': ads_formset,
                'drone_capabilities': DRONE_CAPABILITIES,
                'ads_capabilities': ADS_CAPABILITIES,
            }
            
            return render(request, 'config/force_config.html', context)


@require_http_methods(["POST"])
@csrf_exempt
def get_drone_capabilities(request):
    """
    AJAX endpoint to get drone capabilities.
    """
    drone_type = request.POST.get('drone_type')
    
    if drone_type in DRONE_CAPABILITIES:
        return JsonResponse({
            'success': True,
            'capabilities': DRONE_CAPABILITIES[drone_type]
        })
    
    return JsonResponse({'success': False, 'error': 'Invalid drone type'})


@require_http_methods(["POST"])
@csrf_exempt
def get_ads_capabilities(request):
    """
    AJAX endpoint to get ADS capabilities.
    """
    ads_type = request.POST.get('ads_type')
    
    if ads_type in ADS_CAPABILITIES:
        return JsonResponse({
            'success': True,
            'capabilities': ADS_CAPABILITIES[ads_type]
        })
    
    return JsonResponse({'success': False, 'error': 'Invalid ADS type'})


def simulation_start(request, mission_id):
    """
    Start the simulation visualization on the Cesium map.
    Renders the 3D tactical map with force configurations.
    """
    mission = get_object_or_404(Mission, id=mission_id)
    
    # Get both force configurations
    blue_config = get_object_or_404(ForceConfig, mission=mission, force_type='blue')
    red_config = get_object_or_404(ForceConfig, mission=mission, force_type='red')
    
    # Ensure config_data is properly formatted
    blue_data = blue_config.config_data if isinstance(blue_config.config_data, dict) else {}
    red_data = red_config.config_data if isinstance(red_config.config_data, dict) else {}
    
    context = {
        'mission': mission,
        'mission_id': mission_id,
        'mission_name': mission.name,
        'blue_force_config': json.dumps(blue_data, indent=2),
        'red_force_config': json.dumps(red_data, indent=2),
    }
    
    print(f"[SIMULATION START] Mission {mission_id}: {mission.name}")
    print(f"[SIMULATION START] Blue Force: {json.dumps(blue_data, indent=2)[:200]}...")
    print(f"[SIMULATION START] Red Force: {json.dumps(red_data, indent=2)[:200]}...")
    
    return render(request, 'droneApp/simulation_viewer.html', context)


def simulation_cesium(request, mission_id):
    """
    Cesium 3D simulation viewer with 100 drones per side
    """
    mission = get_object_or_404(Mission, id=mission_id)
    
    try:
        blue_config = ForceConfig.objects.get(mission=mission, force_type='blue')
        red_config = ForceConfig.objects.get(mission=mission, force_type='red')
    except ForceConfig.DoesNotExist:
        messages.error(request, "Force configurations incomplete")
        return redirect('config:force_select', mission_id=mission_id)
    
    context = {
        'mission_id': mission_id,
        'mission': mission,
    }
    
    return render(request, 'droneApp/simulation_cesium.html', context)


# ============================================================
# STEP-BY-STEP CONFIGURATION VIEWS
# ============================================================

def step1_scenario_selection(request, mission_id, force_type):
    """Serve Step 1: Scenario Selection"""
    mission = get_object_or_404(Mission, id=mission_id)
    force_config = ForceConfig.objects.filter(mission=mission, force_type=force_type).first()
    
    # Load existing scenario if present
    existing_scenario = None
    if force_config and force_config.config_data:
        existing_scenario = force_config.config_data.get('scenario')
    
    context = {
        'mission': mission,
        'force_type': force_type,
        'force_config': force_config,
        'existing_scenario': existing_scenario,
        'csrf_token': request.META.get('CSRF_TOKEN'),
    }
    
    return render(request, 'config/step1_scenario_selection.html', context)


def step2_base_target_selection(request, mission_id, force_type):
    """Serve Step 2: Base & Target Selection with Cesium Map"""
    mission = get_object_or_404(Mission, id=mission_id)
    force_config = ForceConfig.objects.filter(mission=mission, force_type=force_type).first()
    
    if not force_config or not force_config.config_data.get('scenario'):
        messages.error(request, "Please complete Step 1 first")
        return redirect('config:step1_scenario', mission_id=mission_id, force_type=force_type)
    
    scenario = force_config.config_data.get('scenario')
    existing_bases = force_config.config_data.get('bases', [])
    existing_targets = force_config.config_data.get('targets', [])
    existing_paths = force_config.config_data.get('paths', [])
    
    context = {
        'mission': mission,
        'force_type': force_type,
        'force_config': force_config,
        'scenario': scenario,
        'existing_bases': existing_bases,
        'existing_targets': existing_targets,
        'existing_paths': existing_paths,
        'csrf_token': request.META.get('CSRF_TOKEN'),
    }
    
    # Use new map-based template instead of form-based
    return render(request, 'config/step2_map_placement.html', context)


def step3_swarm_composition(request, mission_id, force_type):
    """Serve Step 3: Drone Swarm Composition"""
    mission = get_object_or_404(Mission, id=mission_id)
    force_config = ForceConfig.objects.filter(mission=mission, force_type=force_type).first()
    
    if not force_config or not force_config.config_data.get('bases'):
        messages.error(request, "Please complete Step 2 first")
        return redirect('config:step2_base_target', mission_id=mission_id, force_type=force_type)
    
    existing_swarm = force_config.config_data.get('swarm', {})
    existing_analysis = force_config.config_data.get('analysis', {})
    
    context = {
        'mission': mission,
        'force_type': force_type,
        'force_config': force_config,
        'existing_swarm': existing_swarm,
        'existing_analysis': existing_analysis,
        'csrf_token': request.META.get('CSRF_TOKEN'),
    }
    
    return render(request, 'config/step3_swarm_config.html', context)


def step4_ads_config(request, mission_id, force_type):
    """Serve Step 4: ADS Configuration with dynamic ADS systems from database"""
    mission = get_object_or_404(Mission, id=mission_id)
    
    # Fetch all ADS systems from database
    all_ads_systems = ADSSystem.objects.all().values(
        'id', 'name', 'detection_range_km', 'engagement_range_km', 'coverage_radius_km'
    )
    
    # Format for JavaScript consumption
    ads_types_data = [
        {
            'id': ads.get('id'),
            'name': ads.get('name'),
            'value': f"ads_{ads.get('id')}",
            'rangeMin': max(int(ads.get('engagement_range_km', 25)) // 2, 10),
            'rangeMax': int(ads.get('detection_range_km', 100))
        }
        for ads in all_ads_systems
    ]
    
    context = {
        'mission': mission,
        'force_type': force_type,
        'csrf_token': request.META.get('CSRF_TOKEN'),
        'ads_systems_json': json.dumps(ads_types_data),  # Pass as JSON
    }
    
    return render(request, 'config/step4_ads_config.html', context)


def step_strike_planning(request, mission_id, force_type):
    """Serve Strike Planning: formation suggestion + impact report (between ADS and Review)."""
    mission = get_object_or_404(Mission, id=mission_id)
    force_config = ForceConfig.objects.filter(mission=mission, force_type=force_type).first()

    if not force_config or not force_config.config_data.get('bases'):
        messages.error(request, "Please complete Step 2 first.")
        return redirect('config:step2_base_target', mission_id=mission_id, force_type=force_type)

    config_data   = force_config.config_data
    bases         = config_data.get('bases', [])
    targets       = config_data.get('targets', [])
    swarm         = config_data.get('swarm', {})
    composition   = swarm.get('final_composition', {})

    # Build drone list: merge composition counts with full AssetDroneType physics fields
    from assets.models import DroneType as AssetDroneType
    drone_ids   = [int(v['id']) for v in composition.values() if v.get('id')]
    asset_map   = {dt.id: dt for dt in AssetDroneType.objects.filter(id__in=drone_ids)}
    drones_data = []
    for comp in composition.values():
        dt = asset_map.get(int(comp.get('id', 0)))
        if not dt:
            continue
        drones_data.append({
            'id':                    dt.id,
            'name':                  dt.name,
            'category':              dt.category,
            'role':                  comp.get('role', dt.category),
            'count':                 int(comp.get('count', 1)),
            'cruise_speed_kmh':      dt.cruise_speed_kmh,
            'max_speed_kmh':         dt.max_speed_kmh,
            'max_range_km':          dt.max_range_km,
            'endurance_hours':       dt.endurance_hours,
            'service_ceiling_m':     dt.service_ceiling_m,
            'weight_kg':             dt.weight_kg,
            'payload_capacity_kg':   dt.payload_capacity_kg,
            'warhead_type':          dt.warhead_type,
            'warhead_weight_kg':     dt.warhead_weight_kg,
            'guidance_system':       dt.guidance_system,
            'target_lock_capacity':  dt.target_lock_capacity,
            'stealth_rating':        dt.stealth_rating,
            'swarm_capable':         dt.swarm_capable,
            'anti_jam_resistance_pct': dt.anti_jam_resistance_pct,
            'communication_range_km':  dt.communication_range_km,
            'ai_enabled':            dt.ai_enabled,
            'unit_cost_usd':         dt.unit_cost_usd,
            'launch_cost_usd':       dt.launch_cost_usd,
            'base_success_rate_pct': dt.base_success_rate_pct,
            'evasion_probability_pct': dt.evasion_probability_pct,
            'radar_cross_section':   dt.radar_cross_section,
        })

    from .models import ADSPlacement
    ads_count = ADSPlacement.objects.filter(
        mission=mission, force_type=force_type, is_active=True
    ).count()

    existing_plan = config_data.get('strike_plan', {})

    context = {
        'mission':       mission,
        'mission_id':    mission_id,
        'force_type':    force_type,
        'bases_json':    json.dumps(bases),
        'targets_json':  json.dumps(targets),
        'drones_json':   json.dumps(drones_data),
        'ads_count':     ads_count,
        'existing_plan': json.dumps(existing_plan),
    }
    return render(request, 'config/strike_planning.html', context)


def step5_review(request, mission_id, force_type):
    """Serve Step 5: Final Review & Save"""
    mission = get_object_or_404(Mission, id=mission_id)
    
    context = {
        'mission': mission,
        'force_type': force_type,
        'csrf_token': request.META.get('CSRF_TOKEN'),
    }
    
    return render(request, 'config/step5_review.html', context)



def simulation_ready(request, mission_id):
    """
    View to show configured mission data before simulation starts.
    Displays both force configurations with ability to view details.
    """
    mission = get_object_or_404(Mission, id=mission_id)
    
    # Get both force configs
    try:
        blue_config = ForceConfig.objects.get(mission=mission, force_type='blue')
        red_config = ForceConfig.objects.get(mission=mission, force_type='red')
    except ForceConfig.DoesNotExist:
        messages.error(request, "Force configurations not complete!")
        return redirect('config:force_select', mission_id=mission_id)
    
    context = {
        'mission': mission,
        'blue_config': blue_config,
        'red_config': red_config,
        'mission_id': mission_id,
    }
    
    return render(request, 'config/simulation_ready.html', context)


# Ankush's API endpoints for Step 2 - Map Placement
from django.http import FileResponse, Http404
import os
from django.shortcuts import render
from django.conf import settings

BASE_DIR = settings.BASE_DIR

def tile_view(request, z, x, y):
    path = os.path.join(BASE_DIR, "tiles", str(z), str(x), f"{y}.png")
    print("tile path =============>>>>>",path)
    if os.path.exists(path):
        return FileResponse(open(path, "rb"))
    raise Http404()

def terrain_view(request, tile_name):
    path = os.path.join(BASE_DIR, "terrain", tile_name)
    if os.path.exists(path):
        return FileResponse(open(path, "rb"))
    raise Http404()

def tileset_3d_view(request, file_name):
    path = os.path.join(BASE_DIR, "3dtiles", file_name)
    if os.path.exists(path):
        return FileResponse(open(path, "rb"))
    raise Http404()

from django.http import JsonResponse
from django.db import connection
from django.views.decorators.http import require_GET

@require_GET
def geocode(request):
    q = (request.GET.get("q") or "").strip().lower()
    if len(q) < 2:
        return JsonResponse({"results": []})

    qprefix = q + "%"
    limit = 8

    sql = """
      SELECT
        COALESCE(NULLIF(asciiname,''), name) AS label,
        latitude, longitude, country_code,
        feature_class, population
      FROM geonames_allcountries
      WHERE lower(asciiname) LIKE %s OR lower(name) LIKE %s
      ORDER BY (feature_class='P') DESC, population DESC NULLS LAST
      LIMIT %s;
    """

    with connection.cursor() as cur:
        cur.execute(sql, [qprefix, qprefix, limit])
        rows = cur.fetchall()

    results = [
        {"name": r[0], "lat": float(r[1]), "lon": float(r[2]), "cc": r[3]}
        for r in rows
    ]
    return JsonResponse({"results": results})

