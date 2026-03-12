"""
Mission Configuration Views
Handles the multi-step mission configuration workflow.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import View, FormView
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.utils import timezone
import json

from .models import Mission, MissionConfiguration, SCENARIO_PROFILES
from .simulation_engine import MissionSimulator


class MissionConfigurationStep1View(View):
    """
    Step 1: Mission Scenario Selection
    Allows user to select from predefined scenarios.
    """
    template_name = 'config/mission_config_step1.html'
    
    def get(self, request, mission_id):
        mission = get_object_or_404(Mission, id=mission_id)
        
        # Get or create mission configuration
        config, created = MissionConfiguration.objects.get_or_create(
            mission=mission,
            defaults={
                'name': f"{mission.name} - Config",
                'scenario': 'balanced'
            }
        )
        
        context = {
            'mission': mission,
            'config': config,
            'scenarios': SCENARIO_PROFILES,
            'selected_scenario': config.scenario,
        }
        
        return render(request, self.template_name, context)
    
    def post(self, request, mission_id):
        mission = get_object_or_404(Mission, id=mission_id)
        config = MissionConfiguration.objects.get(mission=mission)
        
        scenario = request.POST.get('scenario', 'balanced')
        
        # Update configuration
        config.scenario = scenario
        config.save()
        
        # Initialize mission state with scenario profile
        profile = SCENARIO_PROFILES.get(scenario, SCENARIO_PROFILES['balanced'])
        config.mission_state['scenario_profile'] = profile
        config.save()
        
        messages.success(request, f"Scenario '{scenario}' selected.")
        
        return redirect('config:mission_config_step2', mission_id=mission_id)


class MissionConfigurationStep2View(View):
    """
    Step 2: Drone Configuration
    Configure total drone count and display auto-calculated composition.
    """
    template_name = 'config/mission_config_step2.html'
    
    def get(self, request, mission_id):
        mission = get_object_or_404(Mission, id=mission_id)
        config = get_object_or_404(MissionConfiguration, mission=mission)
        
        # Get scenario profile
        profile = config.get_scenario_profile()
        
        # Calculate composition based on total drones
        composition = self._calculate_composition(config.total_drones, profile['role_percentages'])
        
        context = {
            'mission': mission,
            'config': config,
            'profile': profile,
            'composition': composition,
            'total_drones': config.total_drones,
            'role_info': {
                'ATK': 'Strike / Impact capability',
                'REC': 'Reconnaissance / Surveillance',
                'DEC': 'Decoy / Defense saturation',
                'EW': 'Electronic Support / Detection degradation',
                'COM': 'Communication Relay',
                'CMD': 'Command / Coordination',
                'NAV': 'Navigation / Mapping support',
            }
        }
        
        return render(request, self.template_name, context)
    
    def post(self, request, mission_id):
        mission = get_object_or_404(Mission, id=mission_id)
        config = get_object_or_404(MissionConfiguration, mission=mission)
        
        try:
            total_drones = int(request.POST.get('total_drones', 100))
            if total_drones < 1:
                total_drones = 1
        except ValueError:
            total_drones = 100
        
        config.total_drones = total_drones
        config.save()
        
        # Calculate and store composition
        profile = config.get_scenario_profile()
        composition = self._calculate_composition(total_drones, profile['role_percentages'])
        
        config.mission_state['total_drones'] = total_drones
        config.mission_state['composition'] = composition
        config.save()
        
        messages.success(request, f"Configured {total_drones} drones with auto-calculated composition.")
        
        return redirect('config:mission_config_step3', mission_id=mission_id)
    
    @staticmethod
    def _calculate_composition(total_drones: int, percentages: dict) -> dict:
        """Calculate drone count per role based on percentages."""
        composition = {}
        total_calculated = 0
        
        for role, percentage in percentages.items():
            count = round(total_drones * percentage / 100)
            composition[role] = count
            total_calculated += count
        
        # Adjust for rounding errors
        if total_calculated != total_drones:
            difference = total_drones - total_calculated
            # Add difference to ATK role
            composition['ATK'] += difference
        
        return composition


class MissionConfigurationStep3View(View):
    """
    Step 3: Air Defense System (ADS) Configuration
    Configure defense density, detection type, and response speed.
    """
    template_name = 'config/mission_config_step3.html'
    
    def get(self, request, mission_id):
        mission = get_object_or_404(Mission, id=mission_id)
        config = get_object_or_404(MissionConfiguration, mission=mission)
        
        context = {
            'mission': mission,
            'config': config,
            'density_choices': MissionConfiguration.DEFENSE_DENSITY_CHOICES,
            'detection_choices': MissionConfiguration.DETECTION_TYPE_CHOICES,
            'response_choices': MissionConfiguration.RESPONSE_SPEED_CHOICES,
        }
        
        return render(request, self.template_name, context)
    
    def post(self, request, mission_id):
        mission = get_object_or_404(Mission, id=mission_id)
        config = get_object_or_404(MissionConfiguration, mission=mission)
        
        config.ads_density = request.POST.get('ads_density', 'medium')
        config.detection_type = request.POST.get('detection_type', 'mixed')
        config.response_speed = request.POST.get('response_speed', 'moderate')
        config.save()
        
        # Store in mission state
        config.mission_state['ads_density'] = config.ads_density
        config.mission_state['detection_type'] = config.detection_type
        config.mission_state['response_speed'] = config.response_speed
        config.save()
        
        messages.success(request, "ADS configuration updated.")
        
        return redirect('config:mission_config_step4', mission_id=mission_id)


class MissionConfigurationStep4View(View):
    """
    Step 4: Base / Launch Configuration
    Configure launch distance, communication quality, and launch pattern.
    """
    template_name = 'config/mission_config_step4.html'
    
    def get(self, request, mission_id):
        mission = get_object_or_404(Mission, id=mission_id)
        config = get_object_or_404(MissionConfiguration, mission=mission)
        
        context = {
            'mission': mission,
            'config': config,
            'distance_choices': MissionConfiguration.LAUNCH_DISTANCE_CHOICES,
            'communication_choices': MissionConfiguration.COMMUNICATION_QUALITY_CHOICES,
            'pattern_choices': MissionConfiguration.LAUNCH_PATTERN_CHOICES,
        }
        
        return render(request, self.template_name, context)
    
    def post(self, request, mission_id):
        mission = get_object_or_404(Mission, id=mission_id)
        config = get_object_or_404(MissionConfiguration, mission=mission)
        
        config.launch_distance = request.POST.get('launch_distance', 'medium')
        config.communication_quality = request.POST.get('communication_quality', 'moderate')
        config.launch_pattern = request.POST.get('launch_pattern', 'staggered')
        config.save()
        
        # Store in mission state
        config.mission_state['launch_distance'] = config.launch_distance
        config.mission_state['communication_quality'] = config.communication_quality
        config.mission_state['launch_pattern'] = config.launch_pattern
        config.save()
        
        messages.success(request, "Base/Launch configuration updated.")
        
        return redirect('config:mission_config_step5', mission_id=mission_id)


class MissionConfigurationStep5View(View):
    """
    Step 5: Target Configuration
    Configure target type, protection level, and mobility.
    """
    template_name = 'config/mission_config_step5.html'
    
    def get(self, request, mission_id):
        mission = get_object_or_404(Mission, id=mission_id)
        config = get_object_or_404(MissionConfiguration, mission=mission)
        
        context = {
            'mission': mission,
            'config': config,
            'target_choices': MissionConfiguration.TARGET_TYPE_CHOICES,
            'protection_choices': MissionConfiguration.PROTECTION_LEVEL_CHOICES,
            'mobility_choices': MissionConfiguration.MOBILITY_CHOICES,
        }
        
        return render(request, self.template_name, context)
    
    def post(self, request, mission_id):
        mission = get_object_or_404(Mission, id=mission_id)
        config = get_object_or_404(MissionConfiguration, mission=mission)
        
        config.target_type = request.POST.get('target_type', 'fixed')
        config.protection_level = request.POST.get('protection_level', 'medium')
        config.mobility = request.POST.get('mobility', 'static')
        config.save()
        
        # Store in mission state
        config.mission_state['target_type'] = config.target_type
        config.mission_state['protection_level'] = config.protection_level
        config.mission_state['mobility'] = config.mobility
        config.save()
        
        messages.success(request, "Target configuration updated.")
        
        return redirect('config:mission_config_review', mission_id=mission_id)


class MissionConfigurationReviewView(View):
    """
    Review step: Show complete configuration before running simulation.
    """
    template_name = 'config/mission_config_review.html'
    
    def get(self, request, mission_id):
        mission = get_object_or_404(Mission, id=mission_id)
        config = get_object_or_404(MissionConfiguration, mission=mission)
        
        context = {
            'mission': mission,
            'config': config,
            'scenario_profile': config.get_scenario_profile(),
            'composition': config.get_drone_composition(),
        }
        
        return render(request, self.template_name, context)
    
    def post(self, request, mission_id):
        mission = get_object_or_404(Mission, id=mission_id)
        config = get_object_or_404(MissionConfiguration, mission=mission)
        
        # Run simulation
        return redirect('config:mission_run_simulation', mission_id=mission_id)


class MissionRunSimulationView(View):
    """
    Run the simulation and display results.
    """
    template_name = 'config/mission_results_dashboard.html'
    
    def get(self, request, mission_id):
        mission = get_object_or_404(Mission, id=mission_id)
        config = get_object_or_404(MissionConfiguration, mission=mission)
        
        # Prepare simulation input
        sim_input = {
            'scenario_profile': config.get_scenario_profile(),
            'drone_composition': config.get_drone_composition(),
            'total_drones': config.total_drones,
            'ads_density': config.ads_density,
            'detection_type': config.detection_type,
            'response_speed': config.response_speed,
            'launch_distance': config.launch_distance,
            'communication_quality': config.communication_quality,
            'launch_pattern': config.launch_pattern,
            'target_type': config.target_type,
            'protection_level': config.protection_level,
            'mobility': config.mobility,
        }
        
        # Run simulation
        results = MissionSimulator.simulate_mission(sim_input)
        
        # Save results
        config.simulation_results = results
        config.is_simulated = True
        config.simulated_at = timezone.now()
        config.save()
        
        context = {
            'mission': mission,
            'config': config,
            'results': results,
        }
        
        return render(request, self.template_name, context)


# AJAX Endpoints for real-time updates

@require_http_methods(["POST"])
def get_scenario_profile(request):
    """AJAX: Get scenario profile with role percentages."""
    scenario = request.POST.get('scenario', 'balanced')
    profile = SCENARIO_PROFILES.get(scenario, SCENARIO_PROFILES['balanced'])
    
    return JsonResponse({
        'success': True,
        'profile': profile,
    })


@require_http_methods(["POST"])
def calculate_drone_composition(request):
    """AJAX: Calculate drone composition for given total and scenario."""
    try:
        total_drones = int(request.POST.get('total_drones', 100))
        scenario = request.POST.get('scenario', 'balanced')
        
        profile = SCENARIO_PROFILES.get(scenario, SCENARIO_PROFILES['balanced'])
        percentages = profile['role_percentages']
        
        composition = {}
        total_calc = 0
        
        for role, pct in percentages.items():
            count = round(total_drones * pct / 100)
            composition[role] = count
            total_calc += count
        
        # Fix rounding
        if total_calc != total_drones:
            composition['ATK'] += total_drones - total_calc
        
        return JsonResponse({
            'success': True,
            'composition': composition,
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})