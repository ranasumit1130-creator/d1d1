# config/api_views.py
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
import json
import math
from datetime import datetime

from .models import (
    StepwiseForceConfig, Base, Target, SwarmPreset, SwarmConfig,
    ADSConfig, ScenarioProfile, Mission, ForceConfig, MissionReport, ADSSystem
)

# ============================================================
# HYBRID SWARM ADJUSTMENT ENGINE
# ============================================================

class HybridSwarmEngine:
    """Applies bounded, explainable adjustments to base swarm composition."""
    
    # Hard limits for each role
    HARD_LIMITS = {
        'ATK': (15, 45),
        'REC': (10, 40),
        'DEC': (10, 35),
        'EW': (5, 20),
        'COM': (5, 25),
        'NAV': (3, 20),
        'CMD': (2, 10),
    }
    
    def __init__(self, base_composition, mission_context):
        self.base_composition = base_composition.copy()
        self.context = mission_context
        self.applied_rules = []
        self.adjustments = {}
    
    def calculate_distance(self, lat1, lon1, lat2, lon2):
        """Haversine formula to calculate distance in km."""
        R = 6371  # Earth radius in km
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lat2 - lon1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        return R * c
    
    def apply_rule_set_1_distance(self):
        """RULE SET 1: Distance-based adjustments."""
        if not self.context['bases'] or not self.context['targets']:
            return
        
        # Calculate average base-to-target distance
        total_distance = 0
        count = 0
        for base in self.context['bases']:
            for target in self.context['targets']:
                dist = self.calculate_distance(
                    base['lat'], base['lon'],
                    target['lat'], target['lon']
                )
                total_distance += dist
                count += 1
        
        avg_distance = total_distance / count if count > 0 else 0
        
        if avg_distance > 300:
            self.adjustments['COM'] = self.adjustments.get('COM', 0) + 5
            self.adjustments['NAV'] = self.adjustments.get('NAV', 0) + 3
            self.adjustments['DEC'] = self.adjustments.get('DEC', 0) - 5
            self.adjustments['ATK'] = self.adjustments.get('ATK', 0) - 3
            self.applied_rules.append(
                f"Distance > 300km ({avg_distance:.0f}km) → +COM, +NAV, -DEC, -ATK"
            )
    
    def apply_rule_set_2_ads_threat(self):
        """RULE SET 2: ADS threat adjustments."""
        threat_score = self.context.get('ads_threat_score', 0)
        
        if threat_score >= 6:
            self.adjustments['DEC'] = self.adjustments.get('DEC', 0) + 10
            self.adjustments['EW'] = self.adjustments.get('EW', 0) + 5
            self.adjustments['ATK'] = self.adjustments.get('ATK', 0) - 10
            self.adjustments['REC'] = self.adjustments.get('REC', 0) - 5
            self.applied_rules.append(
                f"High ADS threat (score={threat_score}) → +DEC, +EW, -ATK, -REC"
            )
    
    def apply_rule_set_3_gps_denied(self):
        """RULE SET 3: GPS-denied environment adjustments."""
        if self.context.get('gps_denied', False):
            self.adjustments['NAV'] = self.adjustments.get('NAV', 0) + 8
            self.adjustments['COM'] = self.adjustments.get('COM', 0) + 5
            self.adjustments['ATK'] = self.adjustments.get('ATK', 0) - 5
            self.adjustments['DEC'] = self.adjustments.get('DEC', 0) - 3
            self.applied_rules.append(
                "GPS-Denied → +NAV, +COM, -ATK, -DEC"
            )
    
    def apply_rule_set_4_terrain(self):
        """RULE SET 4: Urban/terrain complexity adjustments."""
        terrain = self.context.get('terrain', 'open')
        
        if terrain == 'urban':
            self.adjustments['REC'] = self.adjustments.get('REC', 0) + 5
            self.adjustments['NAV'] = self.adjustments.get('NAV', 0) + 5
            self.adjustments['DEC'] = self.adjustments.get('DEC', 0) - 5
            self.adjustments['ATK'] = self.adjustments.get('ATK', 0) - 5
            self.applied_rules.append(
                "Urban terrain → +REC, +NAV, -DEC, -ATK"
            )
    
    def apply_rule_set_5_scenario(self):
        """RULE SET 5: Multi-base/target scenario adjustments."""
        num_bases = len(self.context.get('bases', []))
        num_targets = len(self.context.get('targets', []))
        scenario = self.context.get('scenario', '1-1')
        
        # Multiple targets require more reconnaissance and command
        if num_targets > 1:
            self.adjustments['REC'] = self.adjustments.get('REC', 0) + 5
            self.adjustments['CMD'] = self.adjustments.get('CMD', 0) + 5
            self.adjustments['ATK'] = self.adjustments.get('ATK', 0) - 5
            self.adjustments['DEC'] = self.adjustments.get('DEC', 0) - 5
            self.applied_rules.append(
                f"Multiple targets ({num_targets}) → +REC, +CMD, -ATK, -DEC"
            )
        
        # Multiple bases require communication overhead
        if num_bases > 1:
            self.adjustments['COM'] = self.adjustments.get('COM', 0) + 5
            self.adjustments['CMD'] = self.adjustments.get('CMD', 0) + 2
            self.applied_rules.append(
                f"Multiple bases ({num_bases}) → +COM, +CMD"
            )
    
    def clamp_values(self, composition):
        """Enforce hard limits per role."""
        for role, (min_val, max_val) in self.HARD_LIMITS.items():
            if composition[role] < min_val:
                composition[role] = min_val
            elif composition[role] > max_val:
                composition[role] = max_val
        return composition
    
    def normalize(self, composition):
        """Normalize composition to 100%."""
        total = sum(composition.values())
        if total == 0:
            return composition
        
        return {role: round(val * 100 / total) for role, val in composition.items()}
    
    def execute(self):
        """Run all adjustment rules in sequence."""
        # Start with base composition
        composition = self.base_composition.copy()
        
        # Apply all rule sets
        self.apply_rule_set_1_distance()
        self.apply_rule_set_2_ads_threat()
        self.apply_rule_set_3_gps_denied()
        self.apply_rule_set_4_terrain()
        self.apply_rule_set_5_scenario()
        
        # Apply adjustments to composition
        for role, adjustment in self.adjustments.items():
            composition[role] = composition.get(role, 0) + adjustment
        
        # Enforce limits
        composition = self.clamp_values(composition)
        
        # Normalize to 100%
        composition = self.normalize(composition)
        
        return {
            'final_composition': composition,
            'applied_rules': self.applied_rules,
            'adjustments_made': self.adjustments
        }


# ============================================================
# API ENDPOINTS
# ============================================================

@require_http_methods(["GET"])
def get_scenario_requirements(request):
    """GET /api/scenario-requirements/{scenario_type}"""
    scenario = request.GET.get('scenario')
    
    try:
        profile = ScenarioProfile.objects.get(scenario_type=scenario)
        return JsonResponse({
            'scenario': scenario,
            'min_bases': profile.min_bases,
            'max_bases': profile.max_bases,
            'min_targets': profile.min_targets,
            'max_targets': profile.max_targets,
            'description': profile.description,
        })
    except ScenarioProfile.DoesNotExist:
        return JsonResponse({'error': 'Scenario not found'}, status=404)


@require_http_methods(["POST"])
@csrf_exempt
def calculate_hybrid_composition(request):
    """
    POST /api/swarm/calculate-composition
    Calculates final drone composition with hybrid adjustments.
    
    Request:
    {
      "preset_id": 1,
      "total_drones": 120,
      "bases": [{"lat": 28.6, "lon": 77.2}],
      "targets": [{"lat": 28.7, "lon": 77.3}],
      "ads_threat_score": 8,
      "gps_denied": false,
      "terrain": "urban"
    }
    """
    try:
        data = json.loads(request.body)
        preset_id = data.get('preset_id')
        
        preset = SwarmPreset.objects.get(id=preset_id)
        base_composition = preset.base_composition
        
        # Build mission context
        context = {
            'scenario': data.get('scenario'),
            'bases': data.get('bases', []),
            'targets': data.get('targets', []),
            'ads_threat_score': data.get('ads_threat_score', 0),
            'gps_denied': data.get('gps_denied', False),
            'terrain': data.get('terrain', 'open'),
        }
        
        # Run hybrid adjustment engine
        engine = HybridSwarmEngine(base_composition, context)
        result = engine.execute()
        
        # Calculate actual drone counts
        total_drones = data.get('total_drones', 100)
        composition_counts = {
            role: max(1, int(percentage * total_drones / 100))
            for role, percentage in result['final_composition'].items()
        }
        
        return JsonResponse({
            'success': True,
            'final_composition_percentages': result['final_composition'],
            'final_composition_counts': composition_counts,
            'total_drones': total_drones,
            'applied_rules': result['applied_rules'],
            'explanation': generate_explanation(result['applied_rules'])
        })
    
    except SwarmPreset.DoesNotExist:
        return JsonResponse({'error': 'Preset not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


def generate_explanation(rules):
    """Generate human-readable explanation of applied rules."""
    if not rules:
        return "Base composition used without adjustments."
    return "\n".join([f"• {rule}" for rule in rules])


@require_http_methods(["GET"])
def get_swarm_presets(request):
    """GET /api/swarm/presets"""
    presets = SwarmPreset.objects.all().values('id', 'name', 'description')
    return JsonResponse(list(presets), safe=False)


@require_http_methods(["POST"])
@csrf_exempt
def save_swarm_config(request):
    """POST /api/swarm/save"""
    try:
        data = json.loads(request.body)
        config_id = data.get('config_id')
        
        config = StepwiseForceConfig.objects.get(id=config_id)
        
        swarm_config, created = SwarmConfig.objects.update_or_create(
            config=config,
            defaults={
                'total_drones': data.get('total_drones'),
                'final_composition': data.get('final_composition'),
                'applied_rules': data.get('applied_rules', []),
                'user_modified': data.get('user_modified', False),
            }
        )
        
        return JsonResponse({'success': True, 'swarm_config_id': swarm_config.id})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@require_http_methods(["POST"])
@csrf_exempt
def save_ads_config(request):
    """POST /api/ads/save"""
    try:
        data = json.loads(request.body)
        config_id = data.get('config_id')
        
        config = StepwiseForceConfig.objects.get(id=config_id)
        
        ads_config, created = ADSConfig.objects.update_or_create(
            config=config,
            defaults={
                'engagement_mode': data.get('engagement_mode'),
                'coverage_radius_km': data.get('coverage_radius_km'),
                'selective_targets': data.get('selective_targets', []),
                'threat_score': data.get('threat_score', 0),
            }
        )
        
        return JsonResponse({'success': True, 'ads_config_id': ads_config.id})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@require_http_methods(["GET"])
@csrf_exempt
def get_force_config(request):
    """GET /config/api/force-config/?mission=ID&force=TYPE"""
    try:
        mission_id = request.GET.get('mission')
        force_type = request.GET.get('force', 'blue').lower()
        
        if not mission_id:
            return JsonResponse({'error': 'mission parameter required'}, status=400)
        
        from .models import ForceConfig, Mission
        mission = get_object_or_404(Mission, id=mission_id)
        config = ForceConfig.objects.get(mission=mission, force_type=force_type)
        
        # Get configuration data
        config_data = config.config_data or {}
        
        # Build response with all required fields
        response_data = {
            'scenario': config_data.get('scenario', 'Not configured'),
            'bases': config_data.get('bases', []),
            'targets': config_data.get('targets', []),
            'swarm_total': config_data.get('swarm_total', 0),
            'swarm_composition': config_data.get('swarm_composition', {}),
            'target_type': config_data.get('target_type', 'Not configured'),
            'total_cost': config_data.get('total_cost', 0),
            'ads': config_data.get('ads', []),
        }
        
        return JsonResponse(response_data)
    except ForceConfig.DoesNotExist:
        return JsonResponse({'error': 'ForceConfig not found'}, status=404)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=400)


# ============================================================
# NEW: MISSION DATA & SIMULATION ENDPOINTS
# ============================================================

class ADSHitCalculator:
    """
    Calculates ADS hit probability and drone loss based on:
    - Distance to drone
    - ADS detection range
    - Drone altitude & speed
    - ADS capabilities
    """
    
    @staticmethod
    def calculate_distance(lat1, lon1, lat2, lon2):
        """Calculate distance in km using Haversine formula."""
        R = 6371  # Earth radius in km
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lat2 - lon1)
        a = (math.sin(dlat/2)**2 + 
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
             math.sin(dlon/2)**2)
        c = 2 * math.asin(math.sqrt(a))
        return R * c
    
    @staticmethod
    def is_in_detection_range(drone_lat, drone_lon, ads_lat, ads_lon, ads_detection_range_km):
        """Check if drone is within ADS detection range."""
        distance = ADSHitCalculator.calculate_distance(
            drone_lat, drone_lon, ads_lat, ads_lon
        )
        return distance <= ads_detection_range_km
    
    @staticmethod
    def is_in_intercept_range(drone_lat, drone_lon, ads_lat, ads_lon, ads_intercept_range_km):
        """Check if drone is within ADS intercept range."""
        distance = ADSHitCalculator.calculate_distance(
            drone_lat, drone_lon, ads_lat, ads_lon
        )
        return distance <= ads_intercept_range_km
    
    @staticmethod
    def calculate_hit_probability(drone_type, ads_type, drone_lat, drone_lon, 
                                  ads_lat, ads_lon, ads_specs):
        """
        Calculate probability of ADS hitting drone.
        Uses ADS capabilities and distance-based degradation.
        """
        # Get base hit probability for drone type
        base_hit_prob = ads_specs.get('success_probability', {}).get(drone_type, 0.5)
        
        # Calculate distance factor (closer = higher hit probability)
        intercept_range = ads_specs.get('intercept_range_km', 100)
        distance = ADSHitCalculator.calculate_distance(
            drone_lat, drone_lon, ads_lat, ads_lon
        )
        
        if distance > intercept_range:
            return 0.0  # Out of range
        
        # Distance degradation: probability decreases with distance
        distance_factor = 1.0 - (distance / intercept_range * 0.4)
        
        final_hit_prob = base_hit_prob * distance_factor
        return min(final_hit_prob, 0.99)  # Cap at 99%


@require_http_methods(["GET"])
@csrf_exempt
def get_mission_data(request):
    """
    GET /config/api/mission-data/?mission_id=ID
    
    Returns mission configuration data (Blue + Red forces, bases, targets, ADS, drones)
    """
    try:
        mission_id = request.GET.get('mission_id')
        mission = Mission.objects.get(id=mission_id)
        
        blue_config = ForceConfig.objects.get(mission=mission, force_type='blue')
        red_config = ForceConfig.objects.get(mission=mission, force_type='red')
        
        return JsonResponse({
            'status': 'SUCCESS',
            'mission': {
                'id': mission.id,
                'name': mission.name,
                'created_at': mission.created_at.isoformat(),
            },
            'blue_force': blue_config.config_data,
            'red_force': red_config.config_data,
        })
    except Mission.DoesNotExist:
        return JsonResponse({'status': 'ERROR', 'error': 'Mission not found'}, status=404)
    except ForceConfig.DoesNotExist:
        return JsonResponse({'status': 'ERROR', 'error': 'Force configuration incomplete'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'ERROR', 'error': str(e)}, status=500)


@require_http_methods(["POST"])
@csrf_exempt
def simulate_mission(request):
    """
    POST /config/api/simulate-mission/
    
    Run simulation for mission using stored force configs.
    Includes ADS hit detection and drone range calculations.
    
    Request:
    {
        "mission_id": <ID>,
        "num_runs": 1
    }
    """
    try:
        data = json.loads(request.body)
        mission_id = data.get('mission_id')
        num_runs = data.get('num_runs', 1)
        
        mission = Mission.objects.get(id=mission_id)
        blue_config = ForceConfig.objects.get(mission=mission, force_type='blue')
        red_config = ForceConfig.objects.get(mission=mission, force_type='red')
        
        # Extract configuration data
        blue_data = blue_config.config_data
        red_data = red_config.config_data
        
        # Prepare simulation input
        sim_config = {
            'mission_id': mission.id,
            'mission_name': mission.name,
            'blue_force': {
                'bases': blue_data.get('bases', []),
                'drones': blue_data.get('drones', []),
            },
            'red_force': {
                'targets': red_data.get('targets', []),
                'ads': red_data.get('ads', []),
            }
        }
        
        # Run simulation (placeholder for actual engine)
        results = _run_simulation_engine(sim_config, num_runs)
        
        return JsonResponse({
            'status': 'SUCCESS',
            'results': results,
            'message': f'Simulation completed'
        })
    except Mission.DoesNotExist:
        return JsonResponse({'status': 'ERROR', 'error': 'Mission not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'ERROR', 'error': str(e)}, status=500)


@require_http_methods(["POST"])
@csrf_exempt
def check_drone_in_ads_range(request):
    """
    POST /config/api/check-ads-range/
    
    Check if drone is in ADS detection/intercept range and calculate hit probability.
    
    Request:
    {
        "drone_lat": 28.5,
        "drone_lon": 77.2,
        "drone_type": "attack",
        "ads_type": "s-400",
        "ads_lat": 28.7,
        "ads_lon": 77.4,
        "ads_specs": {...}  // ADS capabilities
    }
    """
    try:
        data = json.loads(request.body)
        
        drone_lat = data.get('drone_lat')
        drone_lon = data.get('drone_lon')
        drone_type = data.get('drone_type')
        
        ads_lat = data.get('ads_lat')
        ads_lon = data.get('ads_lon')
        ads_type = data.get('ads_type')
        ads_specs = data.get('ads_specs', {})
        
        # Calculate detection and intercept
        in_detection = ADSHitCalculator.is_in_detection_range(
            drone_lat, drone_lon, ads_lat, ads_lon,
            ads_specs.get('detection_range', 100)
        )
        
        in_intercept = ADSHitCalculator.is_in_intercept_range(
            drone_lat, drone_lon, ads_lat, ads_lon,
            ads_specs.get('intercept_range', 100)
        )
        
        hit_prob = 0.0
        if in_intercept:
            hit_prob = ADSHitCalculator.calculate_hit_probability(
                drone_type, ads_type, drone_lat, drone_lon,
                ads_lat, ads_lon, ads_specs
            )
        
        distance = ADSHitCalculator.calculate_distance(
            drone_lat, drone_lon, ads_lat, ads_lon
        )
        
        return JsonResponse({
            'status': 'SUCCESS',
            'distance_km': round(distance, 2),
            'in_detection_range': in_detection,
            'in_intercept_range': in_intercept,
            'hit_probability': round(hit_prob, 3),
        })
    except Exception as e:
        return JsonResponse({'status': 'ERROR', 'error': str(e)}, status=500)


def _run_simulation_engine(sim_config, num_runs):
    """
    Internal function to run simulation engine with mission data.
    Integrates ADS hit detection and drone trajectory calculation.
    """
    # This will integrate with the actual simulation engine
    # For now, return placeholder results
    return {
        'mission_id': sim_config['mission_id'],
        'num_runs': num_runs,
        'total_drones_launched': sum(
            d.get('quantity', 0) for d in sim_config['blue_force']['drones']
        ),
        'ads_systems': len(sim_config['red_force']['ads']),
        'targets': len(sim_config['red_force']['targets']),
        'success_probability': 0.65,
    }


# ============================================================
# MISSION REPORT ENDPOINTS - Save & Replay
# ============================================================

@require_http_methods(["POST"])
@csrf_exempt
def save_mission_report(request):
    """
    POST /config/api/save-report/
    
    Save mission simulation results to database for reporting and replay.
    
    Request:
    {
        "mission_id": <ID>,
        "simulation_mode": "single",
        "num_runs": 1,
        "simulation_results": {...},
        "summary": {
            "total_drones_launched": 100,
            "total_drones_lost": 25,
            "total_drones_at_target": 75,
            "success_probability": 0.65
        }
    }
    """
    try:
        data = json.loads(request.body)
        mission_id = data.get('mission_id')
        
        mission = Mission.objects.get(id=mission_id)
        
        # Get current force configs for snapshot
        blue_config = ForceConfig.objects.get(mission=mission, force_type='blue')
        red_config = ForceConfig.objects.get(mission=mission, force_type='red')
        
        # Create mission snapshot
        mission_snapshot = {
            'mission_id': mission.id,
            'mission_name': mission.name,
            'created_at': mission.created_at.isoformat(),
            'blue_force': blue_config.config_data,
            'red_force': red_config.config_data,
        }
        
        # Create report
        report = MissionReport.objects.create(
            mission=mission,
            simulation_mode=data.get('simulation_mode', 'single'),
            num_runs=data.get('num_runs', 1),
            mission_snapshot=mission_snapshot,
            simulation_results=data.get('simulation_results', {}),
            total_drones_launched=data.get('summary', {}).get('total_drones_launched', 0),
            total_drones_lost=data.get('summary', {}).get('total_drones_lost', 0),
            total_drones_at_target=data.get('summary', {}).get('total_drones_at_target', 0),
            success_probability=data.get('summary', {}).get('success_probability', 0.0),
            notes=data.get('notes', ''),
        )
        
        return JsonResponse({
            'status': 'SUCCESS',
            'report_id': report.id,
            'message': f'Report #{report.id} saved successfully'
        })
    except Mission.DoesNotExist:
        return JsonResponse({'status': 'ERROR', 'error': 'Mission not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'ERROR', 'error': str(e)}, status=500)


@require_http_methods(["GET"])
@csrf_exempt
def get_mission_reports(request):
    """
    GET /config/api/mission-reports/?mission_id=ID
    
    Get all reports for a mission (for review and replay selection).
    """
    try:
        mission_id = request.GET.get('mission_id')
        mission = Mission.objects.get(id=mission_id)
        
        reports = MissionReport.objects.filter(mission=mission).values(
            'id', 'simulation_date', 'simulation_mode', 'num_runs',
            'total_drones_launched', 'total_drones_lost', 'success_probability', 'notes'
        )
        
        return JsonResponse({
            'status': 'SUCCESS',
            'mission_id': mission.id,
            'mission_name': mission.name,
            'reports': list(reports)
        })
    except Mission.DoesNotExist:
        return JsonResponse({'status': 'ERROR', 'error': 'Mission not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'ERROR', 'error': str(e)}, status=500)


@require_http_methods(["GET"])
@csrf_exempt
def get_report_detail(request):
    """
    GET /config/api/report-detail/?report_id=ID
    
    Get complete report details for display and replay.
    """
    try:
        report_id = request.GET.get('report_id')
        report = MissionReport.objects.get(id=report_id)
        
        return JsonResponse({
            'status': 'SUCCESS',
            'report': {
                'id': report.id,
                'mission_id': report.mission.id,
                'mission_name': report.mission.name,
                'simulation_date': report.simulation_date.isoformat(),
                'simulation_mode': report.simulation_mode,
                'num_runs': report.num_runs,
                'total_drones_launched': report.total_drones_launched,
                'total_drones_lost': report.total_drones_lost,
                'total_drones_at_target': report.total_drones_at_target,
                'success_probability': report.success_probability,
                'notes': report.notes,
            },
            'mission_config': report.get_mission_config(),
            'simulation_results': report.simulation_results,
        })
    except MissionReport.DoesNotExist:
        return JsonResponse({'status': 'ERROR', 'error': 'Report not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'ERROR', 'error': str(e)}, status=500)


@require_http_methods(["POST"])
@csrf_exempt
def replay_mission_from_report(request):
    """
    POST /config/api/replay-report/
    
    Re-run a mission using saved report data.
    This allows users to replay the exact same simulation.
    
    Request:
    {
        "report_id": <ID>,
        "num_runs": 1
    }
    """
    try:
        data = json.loads(request.body)
        report_id = data.get('report_id')
        num_runs = data.get('num_runs', 1)
        
        report = MissionReport.objects.get(id=report_id)
        
        if not report.can_replay():
            return JsonResponse({
                'status': 'ERROR',
                'error': 'Report does not have sufficient data for replay'
            }, status=400)
        
        # Extract configuration from snapshot
        mission_config = report.get_mission_config()
        
        # Prepare simulation
        sim_config = {
            'mission_id': report.mission.id,
            'mission_name': report.mission.name,
            'blue_force': {
                'bases': mission_config.get('blue_force', {}).get('bases', []),
                'drones': mission_config.get('blue_force', {}).get('drones', []),
            },
            'red_force': {
                'targets': mission_config.get('red_force', {}).get('targets', []),
                'ads': mission_config.get('red_force', {}).get('ads', []),
            }
        }
        
        # Run simulation engine with saved config
        results = _run_simulation_engine(sim_config, num_runs)
        
        # Optionally save new report from replay
        new_report = MissionReport.objects.create(
            mission=report.mission,
            simulation_mode='replay',
            num_runs=num_runs,
            mission_snapshot=mission_config,
            simulation_results=results,
            notes=f'Replayed from Report #{report.id}'
        )
        
        return JsonResponse({
            'status': 'SUCCESS',
            'new_report_id': new_report.id,
            'results': results,
            'message': 'Mission replayed successfully'
        })
    except MissionReport.DoesNotExist:
        return JsonResponse({'status': 'ERROR', 'error': 'Report not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'ERROR', 'error': str(e)}, status=500)


@require_http_methods(["POST"])
@csrf_exempt
def save_mission_report(request):
    """
    Save simulation results to database.
    
    POST /config/api/save-mission-report/
    
    Request body:
    {
        "mission_id": <ID>,
        "blue_stats": {
            "deployed": <int>,
            "hits": <int>,
            "lost": <int>,
            "targets": <int>
        },
        "red_stats": {
            "deployed": <int>,
            "hits": <int>,
            "lost": <int>,
            "targets": <int>
        },
        "blue_intercepts": <int>,
        "red_intercepts": <int>,
        "event_log": []
    }
    """
    try:
        data = json.loads(request.body)
        mission_id = data.get('mission_id')
        
        mission = Mission.objects.get(id=mission_id)
        
        # Prepare results
        simulation_results = {
            'blue_stats': data.get('blue_stats', {}),
            'red_stats': data.get('red_stats', {}),
            'blue_intercepts': data.get('blue_intercepts', 0),
            'red_intercepts': data.get('red_intercepts', 0),
            'event_log': data.get('event_log', []),
            'simulation_type': 'bidirectional_combat',
            'timestamp': str(datetime.now())
        }
        
        # Get force configs
        blue_config = mission.forceconfig_set.filter(force_type='BLUE').first()
        red_config = mission.forceconfig_set.filter(force_type='RED').first()
        
        mission_snapshot = {
            'blue_force': json.loads(blue_config.config_data) if blue_config else {},
            'red_force': json.loads(red_config.config_data) if red_config else {}
        }
        
        # Create report
        report = MissionReport.objects.create(
            mission=mission,
            simulation_mode='combat',
            num_runs=1,
            mission_snapshot=mission_snapshot,
            simulation_results=simulation_results,
            notes='Real-time bidirectional combat simulation'
        )
        
        return JsonResponse({
            'status': 'SUCCESS',
            'report_id': report.id,
            'message': 'Simulation results saved successfully'
        })
    except Mission.DoesNotExist:
        return JsonResponse({'status': 'ERROR', 'error': 'Mission not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'ERROR', 'error': str(e)}, status=500)


# ============================================================
# SIMULATION DATA ENDPOINTS
# ============================================================

@require_http_methods(["GET"])
@csrf_exempt
def get_simulation_data(request):
    """Get simulation data for visualization."""
    try:
        data = {
            'status': 'success',
            'data': {}
        }
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)

@require_http_methods(["GET"])
@csrf_exempt
def get_force_data(request):
    """Get force configuration data."""
    try:
        data = {
            'status': 'success',
            'forces': []
        }
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)

@require_http_methods(["POST"])
@csrf_exempt
def run_simulation(request):
    """Run simulation with provided configuration."""
    try:
        config = json.loads(request.body)
        result = {
            'status': 'success',
            'simulation_id': None,
            'message': 'Simulation initiated'
        }
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)


# ============================================================
# STEP 3 API: SWARM CONFIGURATION
# ============================================================

@require_http_methods(["GET"])
@csrf_exempt
def get_target_types(request):
    """
    GET /config/api/target-types/
    
    Returns all available target types for swarm composition selection.
    """
    try:
        from .models import TargetType
        targets = TargetType.objects.all().values('id', 'name', 'category', 'recommended_composition')
        return JsonResponse({
            'success': True,
            'targets': list(targets)
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@require_http_methods(["GET"])
@csrf_exempt
def get_drone_types(request):
    """
    GET /config/api/drone-types/
    
    Returns all available drone types for composition.
    """
    try:
        from .models import DroneType
        drones = DroneType.objects.all().values(
            'id', 'name', 'role', 'cost', 'range_km', 'payload_kg', 
            'endurance_minutes', 'stealth_factor', 'min_quantity', 'max_quantity'
        )
        return JsonResponse({
            'success': True,
            'drones': list(drones)
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@require_http_methods(["POST"])
@csrf_exempt
def step3_calculate_swarm_cost(request):
    """
    POST /config/api/step3/calculate-swarm-cost/
    
    Calculate swarm composition and costs based on target type and parameters.
    
    Request:
    {
        "mission_id": <ID>,
        "force_type": "blue",
        "target_type_id": <ID>,
        "total_drones": 100,
        "drone_allocation": {<drone_id>: percentage, ...}
    }
    """
    try:
        from .models import TargetType, DroneType, SwarmCompositionTemplate
        
        data = json.loads(request.body)
        target_type_id = data.get('target_type_id')
        total_drones = data.get('total_drones', 100)
        drone_allocation = data.get('drone_allocation', {})
        
        target_type = TargetType.objects.get(id=target_type_id)
        
        # Get recommended composition templates
        templates = SwarmCompositionTemplate.objects.filter(target_type=target_type)
        
        final_composition = {}
        total_cost = 0
        total_drones_allocated = 0
        warnings = []
        
        for template in templates:
            drone = template.drone_type
            
            # Use custom allocation if provided, otherwise use template percentage
            if str(drone.id) in drone_allocation:
                percentage = float(drone_allocation[str(drone.id)])
            else:
                percentage = template.percentage
            
            count = max(1, int(total_drones * percentage / 100))
            subtotal = float(drone.cost) * count
            
            final_composition[str(drone.id)] = {
                'id': drone.id,
                'name': drone.name,
                'role': drone.role,
                'percentage': percentage,
                'count': count,
                'unit_cost': float(drone.cost),
                'subtotal': subtotal
            }
            
            total_cost += subtotal
            total_drones_allocated += count
        
        # Validation
        is_valid = len(final_composition) > 0 and total_drones_allocated > 0
        
        if total_drones_allocated != total_drones:
            warnings.append(f"Actual drones allocated ({total_drones_allocated}) differs from target ({total_drones})")
        
        if total_cost > 10000000:  # Example: 10M budget limit
            warnings.append(f"Total cost (${total_cost:,}) exceeds typical budget constraints")
        
        return JsonResponse({
            'success': True,
            'final_composition': final_composition,
            'total_cost': total_cost,
            'is_valid': is_valid,
            'warnings': warnings
        })
    
    except TargetType.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Target type not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@require_http_methods(["POST"])
@csrf_exempt
def step3_save_swarm_config(request):
    """
    POST /config/api/step3/save-swarm-config/
    
    Save swarm configuration and mark step 3 as complete.
    
    Request:
    {
        "mission_id": <ID>,
        "force_type": "blue",
        "target_type_id": <ID>,
        "total_drones": 100,
        "final_composition": {...},
        "total_cost": 500000
    }
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
        
        # Check step 2 is completed
        if not force_config.step2_completed:
            return JsonResponse({'success': False, 'error': 'Please complete Step 2 first'}, status=400)
        
        # Save swarm configuration
        if force_config.config_data is None:
            force_config.config_data = {}
        
        force_config.config_data['swarm'] = {
            'target_type_id': data.get('target_type_id'),
            'total_drones': data.get('total_drones'),
            'final_composition': data.get('final_composition'),
            'total_cost': data.get('total_cost')
        }
        force_config.step3_completed = True
        force_config.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Swarm configuration saved successfully',
            'next_url': f'/config/mission/{mission_id}/force/{force_type}/step4/'
        })
    
    except Mission.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Mission not found'}, status=404)
    except ForceConfig.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Force configuration not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)



# ============================================================
# STRIKE PLANNING SAVE API
# Saves the user's selected formation + impact into
# ForceConfig.config_data['strike_plan'] so Step 5 can read it.
# ============================================================

@csrf_exempt
@require_http_methods(["POST"])
def step_strike_planning_save(request):
    """
    POST /config/api/strike-planning/save/

    Body (JSON):
    {
        "mission_id":      <int>,
        "force_type":      "blue" | "red",
        "formation_name":  "PRECISION STRIKE",
        "attack_drones":   [...],
        "support_drones":  [...],
        "distance_km":     <float>,
        "effectiveness":   <float>,
        "impact_data":     { combined: {...}, perDrone: [...] }
    }

    Saves to ForceConfig.config_data["strike_plan"] and returns
    { "success": true, "next_url": "/config/mission/<id>/force/<type>/step5/" }
    """
    try:
        data       = json.loads(request.body)
        mission_id = data.get('mission_id')
        force_type = (data.get('force_type') or 'blue').lower()

        if not mission_id:
            return JsonResponse({'success': False, 'error': 'mission_id required'}, status=400)

        mission      = get_object_or_404(Mission, id=mission_id)
        force_config = ForceConfig.objects.filter(mission=mission, force_type=force_type).first()

        if not force_config:
            return JsonResponse({'success': False, 'error': 'Force not configured'}, status=404)

        from datetime import datetime
        strike_plan = {
            'formation_name':  data.get('formation_name', ''),
            'attack_drones':   data.get('attack_drones',  []),
            'support_drones':  data.get('support_drones', []),
            'distance_km':     data.get('distance_km',    0),
            'effectiveness':   data.get('effectiveness',  0),
            'impact_data':     data.get('impact_data',    {}),
            'saved_at':        datetime.now().isoformat(),
        }

        cfg = force_config.config_data or {}
        cfg['strike_plan'] = strike_plan
        force_config.config_data = cfg
        force_config.save(update_fields=['config_data'])

        next_url = f'/config/mission/{mission_id}/force/{force_type}/step4/'
        return JsonResponse({'success': True, 'next_url': next_url})

    except Exception as exc:
        return JsonResponse({'success': False, 'error': str(exc)}, status=500)


# ============================================================
# STRIKE RECORD SAVE API
# Persists the strike analysis result to MissionReport so the
# Cesium page and reports module can replay/review it later.
# ============================================================

@csrf_exempt
@require_http_methods(["POST"])
def save_strike_record(request):
    """
    POST /config/api/save-strike-record/

    Body (JSON):
    {
        "mission_id":       <int>,
        "force_type":       "blue" | "red",
        "formation_name":   "PRECISION STRIKE",
        "target_id":        <int|null>,
        "base_id":          <int|null>,
        "drones_used":      <int>,
        "distance_km":      <float>,
        "effectiveness":    <float>,   // 0–100
        "impact_data":      { … },     // computeImpact() combined output
        "simulation_data":  { flights[], impact{}, mission{} }
    }

    Returns:
    { "status": "SUCCESS", "record_id": <int> }
    """
    try:
        data       = json.loads(request.body)
        mission_id = data.get('mission_id')
        if not mission_id:
            return JsonResponse({'status': 'ERROR', 'error': 'mission_id required'}, status=400)

        mission    = get_object_or_404(Mission, id=mission_id)
        force_type = data.get('force_type', 'blue')

        # Snapshot of the formation + strike config
        mission_snapshot = {
            'mission_id':     mission.id,
            'mission_name':   mission.name,
            'force_type':     force_type,
            'formation_name': data.get('formation_name', ''),
            'target_id':      data.get('target_id'),
            'base_id':        data.get('base_id'),
            'drones_used':    data.get('drones_used', 0),
            'distance_km':    data.get('distance_km', 0),
        }

        effectiveness = float(data.get('effectiveness', 0))

        # Pack all physics + Cesium data into simulation_results
        simulation_results = {
            'impact_data':     data.get('impact_data',    {}),
            'simulation_data': data.get('simulation_data', {}),
            'effectiveness':   effectiveness,
        }

        report = MissionReport.objects.create(
            mission              = mission,
            simulation_mode      = 'strike_analysis',
            num_runs             = 1,
            mission_snapshot     = mission_snapshot,
            simulation_results   = simulation_results,
            # Map effectiveness → summary fields the model already has
            total_drones_launched = data.get('drones_used', 0),
            total_drones_lost     = 0,
            total_drones_at_target= data.get('drones_used', 0),
            success_probability   = round(effectiveness / 100, 4),
            status                = 'COMPLETED',
            notes = (
                f"Strike analysis — {data.get('formation_name','')} "
                f"at {data.get('distance_km',0):.1f} km"
            ),
        )

        return JsonResponse({'status': 'SUCCESS', 'record_id': report.id})

    except Exception as exc:
        return JsonResponse({'status': 'ERROR', 'error': str(exc)}, status=500)


# ============================================================

from django.core.management.base import BaseCommand
from config.models import ADSSystem


class Command(BaseCommand):
    help = 'Populate ADSSystem table with air defense systems'

    def handle(self, *args, **options):
        systems = [
            # Outer Layer (100+ km range)
            {
                'name': 'S-400 Triumf',
                'layer': 'outer',
                'system_type': 'long_range',
                'country': 'Russia',
                'detection_range': 600,
                'intercept_range': 400,
                'max_targets': 12,
                'effectiveness_percent': 95,
                'cost_million_usd': 300.0,
                'color_hex': '#FF3B30',
                'icon': '🔴'
            },
            {
                'name': 'THAAD',
                'layer': 'outer',
                'system_type': 'long_range',
                'country': 'USA',
                'detection_range': 300,
                'intercept_range': 200,
                'max_targets': 6,
                'effectiveness_percent': 98,
                'cost_million_usd': 1200.0,
                'color_hex': '#FF3B30',
                'icon': '🔴'
            },
            {
                'name': 'HQ-9',
                'layer': 'outer',
                'system_type': 'long_range',
                'country': 'China',
                'detection_range': 200,
                'intercept_range': 125,
                'max_targets': 6,
                'effectiveness_percent': 92,
                'cost_million_usd': 180.0,
                'color_hex': '#FF3B30',
                'icon': '🔴'
            },
            # Middle Layer (30-100 km range)
            {
                'name': 'Patriot PAC-3',
                'layer': 'middle',
                'system_type': 'medium_range',
                'country': 'USA',
                'detection_range': 165,
                'intercept_range': 100,
                'max_targets': 6,
                'effectiveness_percent': 97,
                'cost_million_usd': 100.0,
                'color_hex': '#FF9500',
                'icon': '🟠'
            },
            {
                'name': 'Buk-M2',
                'layer': 'middle',
                'system_type': 'medium_range',
                'country': 'Russia',
                'detection_range': 120,
                'intercept_range': 70,
                'max_targets': 4,
                'effectiveness_percent': 88,
                'cost_million_usd': 150.0,
                'color_hex': '#FF9500',
                'icon': '🟠'
            },
            {
                'name': 'IRIS-T',
                'layer': 'middle',
                'system_type': 'medium_range',
                'country': 'Germany',
                'detection_range': 90,
                'intercept_range': 50,
                'max_targets': 4,
                'effectiveness_percent': 94,
                'cost_million_usd': 180.0,
                'color_hex': '#FF9500',
                'icon': '🟠'
            },
            # Inner Layer (5-30 km range)
            {
                'name': 'Gepard CIWS',
                'layer': 'inner',
                'system_type': 'short_range',
                'country': 'Germany',
                'detection_range': 35,
                'intercept_range': 25,
                'max_targets': 8,
                'effectiveness_percent': 85,
                'cost_million_usd': 45.0,
                'color_hex': '#34C759',
                'icon': '🟢'
            },
            {
                'name': 'Phalanx CIWS',
                'layer': 'inner',
                'system_type': 'short_range',
                'country': 'USA',
                'detection_range': 45,
                'intercept_range': 30,
                'max_targets': 10,
                'effectiveness_percent': 98,
                'cost_million_usd': 150.0,
                'color_hex': '#34C759',
                'icon': '🟢'
            },
            {
                'name': 'Pantsir-S1',
                'layer': 'inner',
                'system_type': 'short_range',
                'country': 'Russia',
                'detection_range': 40,
                'intercept_range': 20,
                'max_targets': 8,
                'effectiveness_percent': 90,
                'cost_million_usd': 80.0,
                'color_hex': '#34C759',
                'icon': '🟢'
            },
            # Jammer
            {
                'name': 'Generic EW Jammer',
                'layer': 'jammer',
                'system_type': 'jammer',
                'country': 'Multi',
                'detection_range': 100,
                'intercept_range': 0,
                'max_targets': 999,
                'effectiveness_percent': 75,
                'cost_million_usd': 50.0,
                'color_hex': '#FFFF00',
                'icon': '⚡'
            },
        ]

        created = 0
        updated = 0

        for sys_data in systems:
            obj, is_created = ADSSystem.objects.update_or_create(
                name=sys_data['name'],
                defaults=sys_data
            )
            if is_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(self.style.SUCCESS(
            f'Successfully created {created} new systems and updated {updated} existing systems'
        ))