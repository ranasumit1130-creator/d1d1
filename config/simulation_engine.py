"""
Mission Impact Simulation Engine
Probabilistic model for drone swarm missions (abstract/academic).
"""

import math
from typing import Dict, List, Tuple
from datetime import timedelta


class MissionSimulator:
    """
    Simulates mission outcomes based on configuration parameters.
    Uses probabilistic and rule-based modeling (NO real-world control data).
    """
    
    # Role-to-capability mapping
    ROLE_CAPABILITIES = {
        'ATK': {'impact_potential': 0.95, 'detection_risk': 0.8, 'resilience': 0.6},
        'REC': {'awareness': 0.9, 'detection_risk': 0.3, 'resilience': 0.5},
        'DEC': {'saturation_value': 0.8, 'detection_risk': 0.9, 'resilience': 0.7},
        'EW': {'interference_capability': 0.85, 'detection_risk': 0.4, 'resilience': 0.6},
        'COM': {'coordination_boost': 0.8, 'detection_risk': 0.5, 'resilience': 0.5},
        'CMD': {'coordination_boost': 0.9, 'detection_risk': 0.6, 'resilience': 0.7},
        'NAV': {'navigation_support': 0.85, 'detection_risk': 0.2, 'resilience': 0.6},
    }
    
    # Detection probability factors
    DETECTION_FACTORS = {
        'radar': {'low': 0.6, 'medium': 0.75, 'high': 0.9},
        'infrared': {'low': 0.5, 'medium': 0.7, 'high': 0.85},
        'mixed': {'low': 0.75, 'medium': 0.85, 'high': 0.95},
    }
    
    # Response time impact
    RESPONSE_SPEED_FACTORS = {
        'slow': 0.3,      # Limited initial intercepts
        'moderate': 0.6,  # Moderate intercepts
        'fast': 0.9,      # Effective early defense
    }
    
    # Launch pattern efficiency
    LAUNCH_PATTERN_FACTORS = {
        'staggered': {'synchronization': 0.6, 'vulnerability': 0.4},
        'semi_sync': {'synchronization': 0.75, 'vulnerability': 0.6},
        'fully_sync': {'synchronization': 0.95, 'vulnerability': 0.9},
    }
    
    # Communication quality impact
    COMMUNICATION_FACTORS = {
        'poor': {'coordination': 0.4, 'reliability': 0.6},
        'moderate': {'coordination': 0.7, 'reliability': 0.8},
        'strong': {'coordination': 0.95, 'reliability': 0.95},
    }
    
    # Launch distance factors
    LAUNCH_DISTANCE_FACTORS = {
        'short': {'attrition': 0.1, 'availability': 0.95},
        'medium': {'attrition': 0.2, 'availability': 0.85},
        'long': {'attrition': 0.35, 'availability': 0.7},
    }
    
    # Target difficulty
    TARGET_DIFFICULTY_MATRIX = {
        ('fixed', 'low', 'static'): 0.3,
        ('fixed', 'medium', 'static'): 0.5,
        ('fixed', 'high', 'static'): 0.7,
        ('area', 'low', 'static'): 0.4,
        ('area', 'medium', 'static'): 0.6,
        ('area', 'high', 'static'): 0.75,
        ('mobile', 'low', 'semi_mobile'): 0.5,
        ('mobile', 'medium', 'semi_mobile'): 0.65,
        ('mobile', 'high', 'mobile'): 0.85,
    }
    
    @staticmethod
    def simulate_mission(config_data: Dict) -> Dict:
        """
        Main simulation entry point.
        
        Args:
            config_data: MissionConfiguration object or dict with all parameters
        
        Returns:
            Dictionary with simulation results
        """
        simulator = MissionSimulator()
        
        # Extract parameters
        scenario = config_data.get('scenario_profile', {})
        composition = config_data.get('drone_composition', {})
        total_drones = config_data.get('total_drones', 100)
        
        ads_density = config_data.get('ads_density', 'medium')
        detection_type = config_data.get('detection_type', 'mixed')
        response_speed = config_data.get('response_speed', 'moderate')
        
        launch_distance = config_data.get('launch_distance', 'medium')
        communication_quality = config_data.get('communication_quality', 'moderate')
        launch_pattern = config_data.get('launch_pattern', 'staggered')
        
        target_type = config_data.get('target_type', 'fixed')
        protection_level = config_data.get('protection_level', 'medium')
        mobility = config_data.get('mobility', 'static')
        
        # === PHASE 1: Detection & Early Loss ===
        detection_prob = simulator._calculate_detection_probability(
            detection_type, ads_density, composition, launch_pattern
        )
        
        early_losses = simulator._calculate_early_losses(
            total_drones, detection_prob, response_speed, composition
        )
        
        drones_after_early_loss = total_drones - early_losses
        
        # === PHASE 2: Launch Attrition ===
        launch_attrition_rate = simulator.LAUNCH_DISTANCE_FACTORS[launch_distance]['attrition']
        launch_losses = int(drones_after_early_loss * launch_attrition_rate)
        
        drones_in_transit = drones_after_early_loss - launch_losses
        
        # === PHASE 3: Communication & Coordination ===
        comm_stability = simulator._calculate_communication_stability(
            communication_quality, launch_distance, composition, detection_type
        )
        
        coordination_losses = simulator._calculate_coordination_losses(
            drones_in_transit, comm_stability, composition
        )
        
        drones_at_target = drones_in_transit - coordination_losses
        
        # === PHASE 4: Target Engagement ===
        target_difficulty = simulator.TARGET_DIFFICULTY_MATRIX.get(
            (target_type, protection_level, mobility), 0.5
        )
        
        impact_probability = simulator._calculate_impact_probability(
            composition, target_difficulty, drones_at_target, total_drones
        )
        
        # === PHASE 5: Defense Saturation ===
        saturation_effect = simulator._calculate_defense_saturation(
            drones_at_target, ads_density, detection_type, response_speed
        )
        
        # === FINAL OUTCOME ===
        final_success_prob = impact_probability * saturation_effect
        
        # === Role-specific losses ===
        role_losses = simulator._calculate_role_specific_losses(
            composition, early_losses, launch_losses, coordination_losses
        )
        
        # === Performance scores ===
        navigation_score = simulator._calculate_navigation_score(
            launch_distance, communication_quality, composition
        )
        
        # Prepare results
        results = {
            'success_probability': round(final_success_prob * 100, 1),
            'estimated_drones_lost': early_losses + launch_losses + coordination_losses,
            'estimated_drones_at_target': max(0, drones_at_target),
            'mission_feasibility': simulator._classify_feasibility(final_success_prob),
            
            'phase_analysis': {
                'phase_1_early_detection_losses': early_losses,
                'phase_2_launch_attrition': launch_losses,
                'phase_3_coordination_losses': coordination_losses,
                'phase_4_target_engagement_drones': drones_at_target,
            },
            
            'losses_by_role': role_losses,
            
            'performance_metrics': {
                'detection_probability': round(detection_prob * 100, 1),
                'communication_stability': round(comm_stability * 100, 1),
                'navigation_reliability': round(navigation_score * 100, 1),
                'defense_saturation_effect': round(saturation_effect * 100, 1),
                'impact_potential': round(impact_probability * 100, 1),
            },
            
            'risk_assessment': simulator._generate_risk_assessment(
                detection_prob, comm_stability, navigation_score, final_success_prob
            ),
        }
        
        return results
    
    @staticmethod
    def _calculate_detection_probability(
        detection_type: str, ads_density: str, composition: Dict, launch_pattern: str
    ) -> float:
        """Calculate probability of swarm detection by ADS."""
        base_detection = MissionSimulator.DETECTION_FACTORS[detection_type][ads_density]
        
        # EW (electronic support) reduces detection
        ew_count = composition.get('EW', 0)
        ew_factor = 1 - (ew_count / 100 * 0.3)  # Max 30% reduction
        
        # Staggered launches are harder to detect
        launch_factor = MissionSimulator.LAUNCH_PATTERN_FACTORS[launch_pattern]['vulnerability']
        
        final_detection = base_detection * ew_factor * (1 - launch_factor * 0.2)
        
        return min(0.99, max(0.1, final_detection))
    
    @staticmethod
    def _calculate_early_losses(
        total_drones: int, detection_prob: float, response_speed: str, composition: Dict
    ) -> int:
        """Calculate losses during detection and initial ADS response."""
        base_loss_rate = detection_prob * MissionSimulator.RESPONSE_SPEED_FACTORS[response_speed]
        
        # DEC (decoy) drones reduce losses
        dec_factor = 1 - (composition.get('DEC', 0) / 100 * 0.4)  # Max 40% reduction
        
        loss_count = int(total_drones * base_loss_rate * dec_factor)
        
        return loss_count
    
    @staticmethod
    def _calculate_communication_stability(
        quality: str, distance: str, composition: Dict, detection_type: str
    ) -> float:
        """Calculate communication link stability."""
        base_stability = MissionSimulator.COMMUNICATION_FACTORS[quality]['reliability']
        
        # Distance degrades communication
        distance_penalty = MissionSimulator.LAUNCH_DISTANCE_FACTORS[distance]['attrition']
        
        # COM drones improve stability
        com_bonus = composition.get('COM', 0) / 100 * 0.25  # Max 25% improvement
        
        # Detection type affects reliability (jammed/denied = worse)
        if detection_type == 'mixed':
            detection_penalty = 0.1
        else:
            detection_penalty = 0.05
        
        final_stability = base_stability * (1 - distance_penalty * 0.3) + com_bonus - detection_penalty
        
        return min(0.99, max(0.2, final_stability))
    
    @staticmethod
    def _calculate_coordination_losses(
        drones: int, comm_stability: float, composition: Dict
    ) -> int:
        """Calculate losses due to poor coordination and communication failure."""
        # Low communication = potential collisions, friendly fire, missed targets
        coordination_loss_rate = (1 - comm_stability) * 0.4
        
        # CMD (command) drones reduce losses
        cmd_factor = 1 - (composition.get('CMD', 0) / 100 * 0.3)
        
        loss_count = int(drones * coordination_loss_rate * cmd_factor)
        
        return loss_count
    
    @staticmethod
    def _calculate_impact_probability(
        composition: Dict, target_difficulty: float, drones_at_target: int, total_drones: int
    ) -> float:
        """Calculate probability of successful impact on target."""
        # ATK (strike) drones determine impact capability
        atk_ratio = composition.get('ATK', 0) / 100
        atk_impact = 0.3 + (atk_ratio * 0.6)  # 0.3 to 0.9
        
        # More drones = better chance (diminishing returns)
        drone_effectiveness = math.log1p(drones_at_target) / math.log1p(total_drones)
        
        # REC (recon) improves targeting
        rec_bonus = composition.get('REC', 0) / 100 * 0.15
        
        impact_prob = (atk_impact + rec_bonus) * drone_effectiveness * (1 - target_difficulty)
        
        return min(0.99, max(0.05, impact_prob))
    
    @staticmethod
    def _calculate_defense_saturation(
        drones: int, ads_density: str, detection_type: str, response_speed: str
    ) -> float:
        """
        Calculate defense saturation effect.
        More drones = higher chance some will penetrate defenses.
        """
        saturation_rates = {
            ('low', 'slow'): 0.1,
            ('low', 'moderate'): 0.15,
            ('low', 'fast'): 0.2,
            ('medium', 'slow'): 0.2,
            ('medium', 'moderate'): 0.3,
            ('medium', 'fast'): 0.4,
            ('high', 'slow'): 0.3,
            ('high', 'moderate'): 0.5,
            ('high', 'fast'): 0.6,
        }
        
        base_rate = saturation_rates.get((ads_density, response_speed), 0.3)
        
        # Logarithmic relationship: more drones help, but with diminishing returns
        swarm_multiplier = 1 + (math.log1p(drones) / 10)
        
        saturation = base_rate * swarm_multiplier
        
        return min(0.99, saturation)
    
    @staticmethod
    def _calculate_role_specific_losses(
        composition: Dict, early: int, launch: int, coord: int
    ) -> Dict:
        """
        Distribute losses across drone roles based on their characteristics.
        """
        losses = {}
        total_loss = early + launch + coord
        
        if total_loss == 0:
            return {role: 0 for role in composition.keys()}
        
        # Higher-risk roles suffer more losses
        risk_factors = {
            'ATK': 1.2,   # Highest risk
            'DEC': 1.3,   # Saturation target
            'EW': 0.9,    # Moderate risk
            'REC': 0.7,   # Lower risk
            'COM': 0.8,
            'CMD': 0.6,   # Protected
            'NAV': 0.5,   # Minimal risk
        }
        
        total_weighted = sum(composition.get(role, 0) * risk_factors[role] 
                           for role in composition.keys())
        
        for role, count in composition.items():
            if total_weighted > 0:
                loss_share = (count * risk_factors[role] / total_weighted) * total_loss
                losses[role] = {
                    'count': int(loss_share),
                    'percentage': round((loss_share / count * 100) if count > 0 else 0, 1)
                }
            else:
                losses[role] = {'count': 0, 'percentage': 0}
        
        return losses
    
    @staticmethod
    def _calculate_navigation_score(
        launch_distance: str, communication_quality: str, composition: Dict
    ) -> float:
        """Calculate navigation and route reliability."""
        distance_scores = {'short': 0.95, 'medium': 0.8, 'long': 0.6}
        comm_scores = {'poor': 0.5, 'moderate': 0.75, 'strong': 0.95}
        
        base_score = distance_scores[launch_distance] * comm_scores[communication_quality]
        
        # NAV drones improve navigation
        nav_bonus = composition.get('NAV', 0) / 100 * 0.2
        
        final_score = base_score + nav_bonus
        
        return min(0.99, final_score)
    
    @staticmethod
    def _generate_risk_assessment(
        detection_prob: float, comm_stability: float, nav_score: float, success_prob: float
    ) -> Dict:
        """Generate qualitative risk assessment."""
        risk_factors = []
        overall_risk = 'LOW'
        
        if detection_prob > 0.75:
            risk_factors.append('High detection probability')
        
        if comm_stability < 0.5:
            risk_factors.append('Poor communication reliability')
        
        if nav_score < 0.65:
            risk_factors.append('Navigation challenges')
        
        if success_prob < 0.4:
            overall_risk = 'HIGH'
        elif success_prob < 0.65:
            overall_risk = 'MEDIUM'
        
        return {
            'overall_risk_level': overall_risk,
            'risk_factors': risk_factors,
            'recommendation': _get_recommendation(success_prob, overall_risk),
        }
    
    @staticmethod
    def _classify_feasibility(success_prob: float) -> str:
        """Classify mission feasibility."""
        if success_prob >= 0.8:
            return 'HIGHLY FEASIBLE'
        elif success_prob >= 0.6:
            return 'FEASIBLE'
        elif success_prob >= 0.4:
            return 'MARGINAL'
        else:
            return 'NOT FEASIBLE'


def _get_recommendation(success_prob: float, risk_level: str) -> str:
    """Generate recommendation based on simulation."""
    if success_prob >= 0.8:
        return 'Configuration is optimized for mission success.'
    elif success_prob >= 0.6:
        return 'Configuration is acceptable. Consider increasing drone count or improving communications.'
    elif success_prob >= 0.4:
        return 'Configuration has significant risks. Recommend reducing ADS density or improving launch pattern.'
    else:
        return 'Configuration is not viable. Major restructuring required.'