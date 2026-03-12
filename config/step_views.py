# config/step_views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.mixins import LoginRequiredMixin
import json

from .models import (
    Mission, StepwiseForceConfig, Base, Target, SwarmPreset, SwarmConfig,
    ADSConfig, ScenarioProfile, ConfigurationSnapshot
)


# ============================================================
# STEP 1: SCENARIO SELECTION (MANDATORY FIRST STEP)
# ============================================================

class Step1ScenarioSelectionView(LoginRequiredMixin, View):
    """Scenario selection - MUST be completed first."""
    
    def get(self, request, mission_id):
        mission = get_object_or_404(Mission, id=mission_id)
        config, created = StepwiseForceConfig.objects.get_or_create(
            mission=mission,
            force_type=request.GET.get('force_type', 'blue')
        )
        
        scenarios = [
            {'code': '1-1', 'name': 'One Base → One Target', 'icon': '🎯'},
            {'code': '1-M', 'name': 'One Base → Multiple Targets', 'icon': '🎯🎯'},
            {'code': 'M-1', 'name': 'Multiple Bases → One Target', 'icon': '🚀🎯'},
            {'code': 'M-M', 'name': 'Multiple Bases → Multiple Targets', 'icon': '🚀🎯🎯'},
        ]
        
        return render(request, 'config/step1_scenario.html', {
            'mission': mission,
            'config': config,
            'scenarios': scenarios,
        })
    
    def post(self, request, mission_id):
        data = json.loads(request.body)
        mission = get_object_or_404(Mission, id=mission_id)
        config = StepwiseForceConfig.objects.get(mission=mission)
        
        scenario = data.get('scenario')
        if scenario not in dict([('1-1', ''), ('1-M', ''), ('M-1', ''), ('M-M', '')]):
            return JsonResponse({'error': 'Invalid scenario'}, status=400)
        
        config.scenario = scenario
        config.scenario_locked = True
        config.save()
        
        return JsonResponse({'success': True, 'next_step': 'step2'})


# ============================================================
# STEP 2: BASE & TARGET PLACEMENT (MAP-DRIVEN)
# ============================================================

class Step2MapPlacementView(LoginRequiredMixin, View):
    """Base and target placement using CesiumJS map."""
    
    def get(self, request, mission_id):
        mission = get_object_or_404(Mission, id=mission_id)
        config = get_object_or_404(StepwiseForceConfig, mission=mission)
        
        # Check if step 1 is completed
        if not config.scenario_locked:
            return redirect('config:step1_scenario', mission_id=mission_id)
        
        # Get scenario requirements
        scenario_profile = ScenarioProfile.objects.get(scenario_type=config.scenario)
        
        bases = config.bases.all()
        targets = config.targets.all()
        
        can_proceed = (
            scenario_profile.min_bases <= bases.count() <= scenario_profile.max_bases and
            scenario_profile.min_targets <= targets.count() <= scenario_profile.max_targets
        )
        
        return render(request, 'config/step2_map_placement.html', {
            'mission': mission,
            'config': config,
            'scenario_profile': scenario_profile,
            'bases': bases,
            'targets': targets,
            'can_proceed': can_proceed,
            'cesium_base_url': '/static/Cesium',
        })
    
    @csrf_exempt
    def post(self, request, mission_id):
        """AJAX: Save base or target."""
        try:
            data = json.loads(request.body)
            config = StepwiseForceConfig.objects.get(mission_id=mission_id)
            
            entity_type = data.get('type')  # 'base' or 'target'
            action = data.get('action')  # 'add', 'delete', 'confirm'
            
            if action == 'add':
                if entity_type == 'base':
                    Base.objects.create(
                        config=config,
                        name=data.get('name', f'Base {config.bases.count() + 1}'),
                        latitude=data.get('lat'),
                        longitude=data.get('lon'),
                    )
                elif entity_type == 'target':
                    Target.objects.create(
                        config=config,
                        name=data.get('name', f'Target {config.targets.count() + 1}'),
                        latitude=data.get('lat'),
                        longitude=data.get('lon'),
                        target_type=data.get('target_type', 'fixed'),
                    )
            
            elif action == 'delete':
                entity_id = data.get('id')
                if entity_type == 'base':
                    Base.objects.filter(id=entity_id, config=config).delete()
                elif entity_type == 'target':
                    Target.objects.filter(id=entity_id, config=config).delete()
            
            elif action == 'confirm':
                config.step2_status = 'COMPLETED'
                config.save()
                return JsonResponse({'success': True, 'next_step': 'step3'})
            
            # Return updated lists
            bases = list(config.bases.values('id', 'name', 'latitude', 'longitude'))
            targets = list(config.targets.values('id', 'name', 'latitude', 'longitude'))
            
            return JsonResponse({
                'success': True,
                'bases': bases,
                'targets': targets,
            })
        
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)


# ============================================================
# STEP 3: DRONE SWARM CONFIGURATION (HYBRID PRESETS)
# ============================================================

class Step3SwarmConfigView(LoginRequiredMixin, View):
    """Select and configure drone swarm with hybrid adjustments."""
    
    def get(self, request, mission_id):
        mission = get_object_or_404(Mission, id=mission_id)
        config = get_object_or_404(StepwiseForceConfig, mission=mission)
        
        # Check prerequisites
        if config.step2_status != 'COMPLETED':
            return redirect('config:step2_map', mission_id=mission_id)
        
        presets = SwarmPreset.objects.all()
        
        return render(request, 'config/step3_swarm_config.html', {
            'mission': mission,
            'config': config,
            'presets': presets,
            'bases': config.bases.all(),
            'targets': config.targets.all(),
        })
    
    @csrf_exempt
    def post(self, request, mission_id):
        """AJAX: Save swarm configuration."""
        try:
            data = json.loads(request.body)
            config = StepwiseForceConfig.objects.get(mission_id=mission_id)
            
            # Save swarm config
            SwarmConfig.objects.update_or_create(
                config=config,
                defaults={
                    'preset_id': data.get('preset_id'),
                    'total_drones': data.get('total_drones'),
                    'final_composition': data.get('final_composition'),
                    'applied_rules': data.get('applied_rules', []),
                    'locked': True,
                }
            )
            
            config.step3_status = 'COMPLETED'
            config.save()
            
            return JsonResponse({'success': True, 'next_step': 'step4'})
        
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)


# ============================================================
# STEP 4: ADS CONFIGURATION
# ============================================================

class Step4ADSConfigView(LoginRequiredMixin, View):
    """Configure Air Defense Systems."""
    
    def get(self, request, mission_id):
        mission = get_object_or_404(Mission, id=mission_id)
        config = get_object_or_404(StepwiseForceConfig, mission=mission)
        
        if config.step3_status != 'COMPLETED':
            return redirect('config:step3_swarm', mission_id=mission_id)
        
        ads_config, created = ADSConfig.objects.get_or_create(config=config)
        
        return render(request, 'config/step4_ads_config.html', {
            'mission': mission,
            'config': config,
            'ads_config': ads_config,
        })
    
    @csrf_exempt
    def post(self, request, mission_id):
        """AJAX: Save ADS configuration."""
        try:
            data = json.loads(request.body)
            config = StepwiseForceConfig.objects.get(mission_id=mission_id)
            
            ADSConfig.objects.update_or_create(
                config=config,
                defaults={
                    'engagement_mode': data.get('engagement_mode'),
                    'coverage_radius_km': data.get('coverage_radius_km'),
                    'selective_targets': data.get('selective_targets', []),
                    'locked': True,
                }
            )
            
            config.step4_status = 'COMPLETED'
            config.save()
            
            return JsonResponse({'success': True, 'next_step': 'step5'})
        
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)


# ============================================================
# STEP 5: FINAL REVIEW & SAVE
# ============================================================

class Step5ReviewView(LoginRequiredMixin, View):
    """Final review and save configuration."""
    
    def get(self, request, mission_id):
        mission = get_object_or_404(Mission, id=mission_id)
        config = get_object_or_404(StepwiseForceConfig, mission=mission)
        
        if config.step4_status != 'COMPLETED':
            return redirect('config:step4_ads', mission_id=mission_id)
        
        # Compile full configuration
        swarm_config = config.swarm_config
        ads_config = config.ads_config
        
        full_config = {
            'scenario': config.scenario,
            'bases': list(config.bases.values('id', 'name', 'latitude', 'longitude')),
            'targets': list(config.targets.values('id', 'name', 'latitude', 'longitude')),
            'swarm': {
                'total_drones': swarm_config.total_drones if swarm_config else 0,
                'composition': swarm_config.final_composition if swarm_config else {},
                'applied_rules': swarm_config.applied_rules if swarm_config else [],
            },
            'ads': {
                'engagement_mode': ads_config.engagement_mode if ads_config else 'ACTIVE',
                'coverage_radius_km': ads_config.coverage_radius_km if ads_config else 120,
            }
        }
        
        return render(request, 'config/step5_review.html', {
            'mission': mission,
            'config': config,
            'full_config': json.dumps(full_config),
        })
    
    @csrf_exempt
    def post(self, request, mission_id):
        """AJAX: Save and finalize configuration."""
        try:
            config = StepwiseForceConfig.objects.get(mission_id=mission_id)
            
            # Create configuration snapshot
            full_config = {
                'scenario': config.scenario,
                'bases': list(config.bases.values('id', 'name', 'latitude', 'longitude')),
                'targets': list(config.targets.values('id', 'name', 'latitude', 'longitude')),
                'swarm': {
                    'total_drones': config.swarm_config.total_drones,
                    'composition': config.swarm_config.final_composition,
                },
                'ads': {
                    'engagement_mode': config.ads_config.engagement_mode,
                    'coverage_radius_km': config.ads_config.coverage_radius_km,
                }
            }
            
            ConfigurationSnapshot.objects.create(
                config=config,
                complete_config=full_config,
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Configuration saved successfully',
                'redirect': f'/config/mission/{mission_id}/simulation-start/'
            })
        
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)


# ============================================================
# HELPER: SCENARIO CONSTRAINTS & VALIDATION
# ============================================================

def get_scenario_constraints(scenario):
    """
    Get base and target selection constraints for each scenario.
    Returns dict with min/max bases and targets, and selection rules.
    """
    constraints = {
        '1-1': {
            'min_bases': 1,
            'max_bases': 1,
            'min_targets': 1,
            'max_targets': 1,
            'description': 'Exactly one base launches to exactly one target',
            'permissions': {
                'base_selection': 'single',      # Can only select 1 base
                'target_selection': 'single',    # Can only select 1 target
                'multiple_bases_allowed': False,
                'multiple_targets_allowed': False,
            }
        },
        '1-M': {
            'min_bases': 1,
            'max_bases': 1,
            'min_targets': 2,
            'max_targets': 10,
            'description': 'One base launches to multiple targets',
            'permissions': {
                'base_selection': 'single',      # Can only select 1 base
                'target_selection': 'multiple',  # Can select multiple targets
                'multiple_bases_allowed': False,
                'multiple_targets_allowed': True,
            }
        },
        'M-1': {
            'min_bases': 2,
            'max_bases': 10,
            'min_targets': 1,
            'max_targets': 1,
            'description': 'Multiple bases launch to one target',
            'permissions': {
                'base_selection': 'multiple',    # Can select multiple bases
                'target_selection': 'single',    # Can only select 1 target
                'multiple_bases_allowed': True,
                'multiple_targets_allowed': False,
            }
        },
        'M-M': {
            'min_bases': 2,
            'max_bases': 10,
            'min_targets': 2,
            'max_targets': 10,
            'description': 'Multiple bases launch to multiple targets',
            'permissions': {
                'base_selection': 'multiple',    # Can select multiple bases
                'target_selection': 'multiple',  # Can select multiple targets
                'multiple_bases_allowed': True,
                'multiple_targets_allowed': True,
            }
        }
    }
    return constraints.get(scenario, constraints['M-M'])


def validate_base_target_selection(scenario, bases_count, targets_count):
    """
    Validate if the current base/target selection matches scenario constraints.
    Returns (is_valid, error_message).
    """
    constraints = get_scenario_constraints(scenario)
    
    if bases_count < constraints['min_bases'] or bases_count > constraints['max_bases']:
        return False, f"Scenario {scenario} requires {constraints['min_bases']}-{constraints['max_bases']} bases"
    
    if targets_count < constraints['min_targets'] or targets_count > constraints['max_targets']:
        return False, f"Scenario {scenario} requires {constraints['min_targets']}-{constraints['max_targets']} targets"
    
    return True, "Selection is valid"


# ============================================================
# API ENDPOINTS FOR STEP 3 VALIDATION
# ============================================================

@csrf_exempt
@require_http_methods(["POST"])
def api_validate_base_target_selection(request, mission_id):
    """
    API: Validate if current base/target selection matches scenario constraints.
    Used by Step 3 UI to show/hide options dynamically.
    """
    try:
        config = StepwiseForceConfig.objects.get(mission_id=mission_id)
        scenario = config.scenario
        
        bases_count = config.bases.count()
        targets_count = config.targets.count()
        
        is_valid, message = validate_base_target_selection(scenario, bases_count, targets_count)
        constraints = get_scenario_constraints(scenario)
        
        return JsonResponse({
            'success': True,
            'valid': is_valid,
            'message': message,
            'scenario': scenario,
            'constraints': constraints,
            'current_selection': {
                'bases': bases_count,
                'targets': targets_count,
            }
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def api_can_add_base(request, mission_id):
    """
    API: Check if another base can be added based on scenario.
    Returns False if already at max_bases for the scenario.
    """
    try:
        config = StepwiseForceConfig.objects.get(mission_id=mission_id)
        scenario = config.scenario
        constraints = get_scenario_constraints(scenario)
        
        current_bases = config.bases.count()
        can_add = current_bases < constraints['max_bases']
        
        return JsonResponse({
            'success': True,
            'can_add_base': can_add,
            'current_bases': current_bases,
            'max_bases': constraints['max_bases'],
            'message': 'Cannot add more bases for this scenario' if not can_add else 'Can add more bases'
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def api_can_add_target(request, mission_id):
    """
    API: Check if another target can be added based on scenario.
    Returns False if already at max_targets for the scenario.
    """
    try:
        config = StepwiseForceConfig.objects.get(mission_id=mission_id)
        scenario = config.scenario
        constraints = get_scenario_constraints(scenario)
        
        current_targets = config.targets.count()
        can_add = current_targets < constraints['max_targets']
        
        return JsonResponse({
            'success': True,
            'can_add_target': can_add,
            'current_targets': current_targets,
            'max_targets': constraints['max_targets'],
            'message': 'Cannot add more targets for this scenario' if not can_add else 'Can add more targets'
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)