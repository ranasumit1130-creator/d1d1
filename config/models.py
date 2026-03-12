from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import json

# ============================================================
# MISSION AND FORCE CONFIGURATION MODELS
# ============================================================

class Mission(models.Model):
    """Enhanced Mission model with status tracking."""
    name = models.CharField(max_length=255, help_text="Mission name")
    description = models.TextField(blank=True, help_text="Mission description")
    status = models.CharField(
        max_length=20,
        choices=[
            ('setup', 'Setup'),
            ('configured', 'Configured'),
            ('running', 'Running'),
            ('completed', 'Completed'),
        ],
        default='setup'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"
    
    def get_completion_percentage(self):
        """Calculate mission completion percentage."""
        try:
            blue = self.forces.get(force_type='blue')
            red = self.forces.get(force_type='red')
            
            configured = sum([
                blue.is_configured if blue else False,
                red.is_configured if red else False,
            ])
            return int((configured / 2) * 100)
        except:
            return 0
    
    def is_ready_for_simulation(self):
        """Check if mission is ready to run."""
        try:
            blue = self.forces.get(force_type='blue')
            red = self.forces.get(force_type='red')
            return blue and blue.is_configured and red and red.is_configured
        except:
            return False


class ForceConfig(models.Model):
    """Enhanced ForceConfig with JSONField for flexible data storage."""
    FORCE_CHOICES = [('blue', 'Blue Force'), ('red', 'Red Force')]
    
    mission = models.ForeignKey(
        Mission, on_delete=models.CASCADE, related_name='forces'
    )
    force_type = models.CharField(max_length=10, choices=FORCE_CHOICES)
    
    # Configuration data stored as JSON for flexibility
    config_data = models.JSONField(default=dict, blank=True, help_text="Configuration state")
    
    # Step tracking
    step1_completed = models.BooleanField(default=False, help_text="Scenario selection completed")
    step2_completed = models.BooleanField(default=False, help_text="Map placement completed")
    step3_completed = models.BooleanField(default=False, help_text="Swarm composition completed")
    step4_completed = models.BooleanField(default=False, help_text="ADS config completed")
    step5_completed = models.BooleanField(default=False, help_text="Review & save completed")
    
    is_configured = models.BooleanField(
        default=False, help_text="All steps completed and force configuration finalized"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ('mission', 'force_type')
        ordering = ['force_type']
    
    def __str__(self):
        status = "✓" if self.is_configured else "⚠"
        return f"{self.mission.name} - {self.force_type.upper()} {status}"
    
    def get_completion_steps(self):
        """Get which steps are completed."""
        return {
            'step1': self.step1_completed,
            'step2': self.step2_completed,
            'step3': self.step3_completed,
            'step4': self.step4_completed,
            'step5': self.step5_completed,
        }
    
    def get_next_incomplete_step(self):
        """Get the next step that needs completion."""
        steps = [
            ('step1', self.step1_completed),
            ('step2', self.step2_completed),
            ('step3', self.step3_completed),
            ('step4', self.step4_completed),
            ('step5', self.step5_completed),
        ]
        
        for step_name, completed in steps:
            if not completed:
                return step_name
        
        return None  # All steps completed
    
    def save_step_data(self, step_number, data):
        """Helper to save step data and mark step as completed."""
        if self.config_data is None:
            self.config_data = {}
        
        # Merge step data
        self.config_data.update(data)
        
        # Mark step as completed
        step_field = f'step{step_number}_completed'
        setattr(self, step_field, True)
        
        self.save()
    
    def finalize_configuration(self):
        """Mark force configuration as complete."""
        self.is_configured = True
        self.completed_at = timezone.now()
        self.save()


# Signal to auto-create ForceConfig entries for new missions
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=Mission)
def create_force_configs(sender, instance, created, **kwargs):
    """Auto-create Blue and Red ForceConfig when Mission is created."""
    if created:
        ForceConfig.objects.get_or_create(
            mission=instance,
            force_type='blue',
            defaults={'config_data': {}}
        )
        ForceConfig.objects.get_or_create(
            mission=instance,
            force_type='red',
            defaults={'config_data': {}}
        )


# Connect signal
models.signals.post_save.connect(create_force_configs, sender=Mission)


class MissionConfiguration(models.Model):
    """
    Stores the complete mission configuration for the Drone Swarm Impact Analysis System.
    This model represents a single simulation scenario with all parameters.
    """
    
    SCENARIO_CHOICES = [
        ('heavy_air_defense', 'Heavy Air-Defense Environment'),
        ('soft_defense', 'Soft / Low-Defense Environment'),
        ('urban', 'Urban Environment'),
        ('gps_denied', 'GPS-Denied / Jammed Environment'),
        ('long_range', 'Long-Range Mission'),
        ('recon_focused', 'Recon-Focused Mission'),
        ('balanced', 'Balanced General Mission'),
    ]
    
    DEFENSE_DENSITY_CHOICES = [
        ('low', 'Low Density'),
        ('medium', 'Medium Density'),
        ('high', 'High Density'),
    ]
    
    DETECTION_TYPE_CHOICES = [
        ('radar', 'Radar'),
        ('infrared', 'Infrared'),
        ('mixed', 'Mixed (Radar + Infrared)'),
    ]
    
    RESPONSE_SPEED_CHOICES = [
        ('slow', 'Slow (15+ minutes)'),
        ('moderate', 'Moderate (5-15 minutes)'),
        ('fast', 'Fast (<5 minutes)'),
    ]
    
    LAUNCH_DISTANCE_CHOICES = [
        ('short', 'Short (<100 km)'),
        ('medium', 'Medium (100-500 km)'),
        ('long', 'Long (>500 km)'),
    ]
    
    COMMUNICATION_QUALITY_CHOICES = [
        ('poor', 'Poor'),
        ('moderate', 'Moderate'),
        ('strong', 'Strong'),
    ]
    
    LAUNCH_PATTERN_CHOICES = [
        ('staggered', 'Staggered'),
        ('semi_sync', 'Semi-Synchronized'),
        ('fully_sync', 'Fully Synchronized'),
    ]
    
    TARGET_TYPE_CHOICES = [
        ('fixed', 'Fixed Infrastructure'),
        ('area', 'Area Target'),
        ('mobile', 'Mobile Asset'),
    ]
    
    PROTECTION_LEVEL_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]
    
    MOBILITY_CHOICES = [
        ('static', 'Static'),
        ('semi_mobile', 'Semi-Mobile'),
        ('mobile', 'Mobile'),
    ]
    
    # Basic Info
    mission = models.OneToOneField(
        Mission,
        on_delete=models.CASCADE,
        related_name='scenario_config',
        help_text="Associated mission"
    )
    name = models.CharField(
        max_length=255,
        help_text="Configuration name/identifier"
    )
    
    # Step 1: Scenario Selection
    scenario = models.CharField(
        max_length=50,
        choices=SCENARIO_CHOICES,
        default='balanced',
        help_text="Mission scenario type"
    )
    
    # Step 2: Drone Configuration
    total_drones = models.IntegerField(
        default=100,
        validators=[MinValueValidator(1)],
        help_text="Total number of drones in swarm"
    )
    # Drone composition is stored as JSON in mission_state
    
    # Step 3: ADS Configuration
    ads_density = models.CharField(
        max_length=20,
        choices=DEFENSE_DENSITY_CHOICES,
        default='medium',
        help_text="Air Defense System density"
    )
    detection_type = models.CharField(
        max_length=20,
        choices=DETECTION_TYPE_CHOICES,
        default='mixed',
        help_text="Type of detection systems"
    )
    response_speed = models.CharField(
        max_length=20,
        choices=RESPONSE_SPEED_CHOICES,
        default='moderate',
        help_text="ADS response speed"
    )
    
    # Step 4: Base / Launch Configuration
    launch_distance = models.CharField(
        max_length=20,
        choices=LAUNCH_DISTANCE_CHOICES,
        default='medium',
        help_text="Distance from launch base to target"
    )
    communication_quality = models.CharField(
        max_length=20,
        choices=COMMUNICATION_QUALITY_CHOICES,
        default='moderate',
        help_text="Quality of communication links"
    )
    launch_pattern = models.CharField(
        max_length=20,
        choices=LAUNCH_PATTERN_CHOICES,
        default='staggered',
        help_text="Drone launch pattern"
    )
    
    # Step 5: Target Configuration
    target_type = models.CharField(
        max_length=20,
        choices=TARGET_TYPE_CHOICES,
        default='fixed',
        help_text="Type of target"
    )
    protection_level = models.CharField(
        max_length=20,
        choices=PROTECTION_LEVEL_CHOICES,
        default='medium',
        help_text="Target protection level"
    )
    mobility = models.CharField(
        max_length=20,
        choices=MOBILITY_CHOICES,
        default='static',
        help_text="Target mobility"
    )
    
    # Mission State (JSON)
    mission_state = models.JSONField(
        default=dict,
        blank=True,
        help_text="Complete mission state including drone composition"
    )
    
    # Simulation Results
    simulation_results = models.JSONField(
        default=dict,
        blank=True,
        help_text="Results from simulation engine"
    )
    is_simulated = models.BooleanField(
        default=False,
        help_text="Whether simulation has been run"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    simulated_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When simulation was last run"
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Mission Configurations"
    
    def __str__(self):
        return f"{self.name} - {self.get_scenario_display()}"
    
    def get_drone_composition(self):
        """Extract drone composition from mission state."""
        return self.mission_state.get('composition', {})
    
    def get_scenario_profile(self):
        """Get the scenario profile with role percentages and constraints."""
        return SCENARIO_PROFILES.get(self.scenario, SCENARIO_PROFILES['balanced'])


# Scenario profiles (constants for business logic)
SCENARIO_PROFILES = {
    'heavy_air_defense': {
        'scenario_id': 'heavy_air_defense',
        'role_percentages': {
            'ATK': 25,
            'REC': 20,
            'DEC': 25,
            'EW': 15,
            'COM': 8,
            'CMD': 4,
            'NAV': 3
        },
        'constraints': {
            'min_total_drones': 20,
            'gps_reliability': 'low',
            'communication_stress': 'high',
            'detection_risk': 'critical'
        }
    },
    'soft_defense': {
        'scenario_id': 'soft_defense',
        'role_percentages': {
            'ATK': 40,
            'REC': 15,
            'DEC': 15,
            'EW': 10,
            'COM': 12,
            'CMD': 5,
            'NAV': 3
        },
        'constraints': {
            'min_total_drones': 10,
            'gps_reliability': 'high',
            'communication_stress': 'low',
            'detection_risk': 'low'
        }
    },
    'urban': {
        'scenario_id': 'urban',
        'role_percentages': {
            'ATK': 20,
            'REC': 30,
            'DEC': 20,
            'EW': 12,
            'COM': 10,
            'CMD': 5,
            'NAV': 3
        },
        'constraints': {
            'min_total_drones': 15,
            'gps_reliability': 'low',
            'communication_stress': 'high',
            'detection_risk': 'medium'
        }
    },
    'gps_denied': {
        'scenario_id': 'gps_denied',
        'role_percentages': {
            'ATK': 25,
            'REC': 15,
            'DEC': 20,
            'EW': 20,
            'COM': 10,
            'CMD': 7,
            'NAV': 3
        },
        'constraints': {
            'min_total_drones': 25,
            'gps_reliability': 'critical',
            'communication_stress': 'critical',
            'detection_risk': 'high'
        }
    },
    'long_range': {
        'scenario_id': 'long_range',
        'role_percentages': {
            'ATK': 30,
            'REC': 20,
            'DEC': 15,
            'EW': 12,
            'COM': 15,
            'CMD': 5,
            'NAV': 3
        },
        'constraints': {
            'min_total_drones': 30,
            'gps_reliability': 'medium',
            'communication_stress': 'critical',
            'detection_risk': 'high'
        }
    },
    'recon_focused': {
        'scenario_id': 'recon_focused',
        'role_percentages': {
            'ATK': 15,
            'REC': 50,
            'DEC': 10,
            'EW': 10,
            'COM': 8,
            'CMD': 5,
            'NAV': 2
        },
        'constraints': {
            'min_total_drones': 10,
            'gps_reliability': 'high',
            'communication_stress': 'medium',
            'detection_risk': 'medium'
        }
    },
    'balanced': {
        'scenario_id': 'balanced',
        'role_percentages': {
            'ATK': 30,
            'REC': 20,
            'DEC': 20,
            'EW': 12,
            'COM': 10,
            'CMD': 5,
            'NAV': 3
        },
        'constraints': {
            'min_total_drones': 20,
            'gps_reliability': 'medium',
            'communication_stress': 'medium',
            'detection_risk': 'medium'
        }
    }
}


# ============================================================
# STEP-BY-STEP CONFIGURATION MODELS
# ============================================================

class StepwiseForceConfig(models.Model):
    """
    NEW: Stores step-by-step force configuration with strict sequential flow.
    Replaces old form-based approach with structured state management.
    """
    SCENARIO_CHOICES = [
        ('1-1', 'One Base → One Target'),
        ('1-M', 'One Base → Multiple Targets'),
        ('M-1', 'Multiple Bases → One Target'),
        ('M-M', 'Multiple Bases → Multiple Targets'),
    ]
    
    STEP_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('LOCKED', 'Locked'),
    ]
    
    mission = models.ForeignKey(Mission, on_delete=models.CASCADE, related_name='stepwise_configs')
    force_type = models.CharField(max_length=10, choices=[('blue', 'Blue'), ('red', 'Red')])
    
    # Step 1: Scenario Selection
    scenario = models.CharField(max_length=5, choices=SCENARIO_CHOICES, null=True, blank=True)
    scenario_locked = models.BooleanField(default=False)
    
    # Step 2: Base & Target Selection
    step2_status = models.CharField(max_length=20, choices=STEP_STATUS_CHOICES, default='PENDING')
    
    # Step 3: Drone Swarm Configuration
    swarm_preset = models.ForeignKey('SwarmPreset', on_delete=models.SET_NULL, null=True, blank=True)
    total_drones = models.PositiveIntegerField(default=100)
    step3_status = models.CharField(max_length=20, choices=STEP_STATUS_CHOICES, default='PENDING')
    
    # Step 4: ADS Configuration
    ads_engagement_mode = models.CharField(max_length=20, default='ACTIVE',
        choices=[('PASSIVE', 'Passive'), ('ACTIVE', 'Active'), ('REACTIVE', 'Reactive'), ('SELECTIVE', 'Selective')])
    ads_coverage_radius_km = models.FloatField(default=120)
    step4_status = models.CharField(max_length=20, choices=STEP_STATUS_CHOICES, default='PENDING')
    
    # Final state
    final_config = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('mission', 'force_type')
    
    def __str__(self):
        return f"{self.mission.name} - {self.force_type} - {self.scenario}"


class ScenarioProfile(models.Model):
    """Defines rules and constraints for each scenario type."""
    scenario_type = models.CharField(max_length=5, choices=[
        ('1-1', 'One Base → One Target'),
        ('1-M', 'One Base → Multiple Targets'),
        ('M-1', 'Multiple Bases → One Target'),
        ('M-M', 'Multiple Bases → Multiple Targets'),
    ], unique=True)
    
    min_bases = models.PositiveIntegerField()
    max_bases = models.PositiveIntegerField()
    min_targets = models.PositiveIntegerField()
    max_targets = models.PositiveIntegerField()
    description = models.TextField()
    
    def __str__(self):
        return f"Scenario: {self.get_scenario_type_display()}"


class Base(models.Model):
    """Command base for drone launches."""
    config = models.ForeignKey(StepwiseForceConfig, on_delete=models.CASCADE, related_name='bases')
    name = models.CharField(max_length=100)
    latitude = models.FloatField()
    longitude = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} ({self.latitude}, {self.longitude})"


class Target(models.Model):
    """Target location for drone swarm attack."""
    config = models.ForeignKey(StepwiseForceConfig, on_delete=models.CASCADE, related_name='targets')
    name = models.CharField(max_length=100)
    latitude = models.FloatField()
    longitude = models.FloatField()
    target_type = models.CharField(max_length=50, default='fixed')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} ({self.latitude}, {self.longitude})"


class SwarmPreset(models.Model):
    """Hybrid swarm preset with base composition and adjustment rules."""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    
    # Base composition (% per role)
    base_composition = models.JSONField(default=dict)
    
    # Adjustment rules (applied in order)
    adjustment_rules = models.JSONField(default=dict)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name


class SwarmConfig(models.Model):
    """Final drone swarm configuration for a mission."""
    config = models.OneToOneField(StepwiseForceConfig, on_delete=models.CASCADE, related_name='swarm_config')
    preset = models.ForeignKey(SwarmPreset, on_delete=models.SET_NULL, null=True, blank=True)
    
    total_drones = models.PositiveIntegerField()
    
    # Final composition after all adjustments
    final_composition = models.JSONField()
    
    # Applied rules for explanation
    applied_rules = models.JSONField(default=list)
    
    user_modified = models.BooleanField(default=False)
    locked = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Swarm for {self.config.mission.name}"


class ADSConfig(models.Model):
    """Air Defense System configuration (mission-wide, not per-base)."""
    ENGAGEMENT_MODES = [
        ('PASSIVE', 'Passive – Detect Only'),
        ('ACTIVE', 'Active – Engage on Detection'),
        ('REACTIVE', 'Reactive – Engage if Threatened'),
        ('SELECTIVE', 'Selective Target Engagement'),
    ]
    
    config = models.OneToOneField(StepwiseForceConfig, on_delete=models.CASCADE, related_name='ads_config')
    
    engagement_mode = models.CharField(max_length=20, choices=ENGAGEMENT_MODES, default='ACTIVE')
    coverage_radius_km = models.FloatField(default=120)
    
    # For SELECTIVE mode: which drone roles to prioritize
    selective_targets = models.JSONField(default=list)
    
    # Store placed ADS systems on map
    placed_ads = models.JSONField(default=list, blank=True)
    
    threat_score = models.PositiveIntegerField(default=0)
    
    locked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"ADS for {self.config.mission.name} - {self.get_engagement_mode_display()}"


class ConfigurationSnapshot(models.Model):
    """Stores final configuration before simulation execution."""
    config = models.OneToOneField(StepwiseForceConfig, on_delete=models.CASCADE, related_name='snapshot')
    
    # Complete snapshot as JSON
    complete_config = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Snapshot of {self.config.mission.name}"


# ============================================================
# MISSION REPORT MODEL - For Simulation Results & Replay
# ============================================================

class MissionReport(models.Model):
    """
    Stores simulation results and mission data for reporting and replay.
    Allows users to view and re-run the same mission simulation.
    """
    REPORT_STATUS = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('ARCHIVED', 'Archived'),
    ]
    
    mission = models.ForeignKey(
        Mission,
        on_delete=models.CASCADE,
        related_name='reports'
    )
    
    # Simulation metadata
    simulation_date = models.DateTimeField(auto_now_add=True)
    simulation_mode = models.CharField(
        max_length=50,
        default='single',
        help_text="Simulation mode (single, monte_carlo, etc)"
    )
    num_runs = models.IntegerField(default=1)
    
    # Mission configuration snapshot at time of report
    mission_snapshot = models.JSONField(
        default=dict,
        blank=True,
        help_text="Complete mission config (Blue+Red forces, bases, targets, ADS, drones)"
    )
    
    # Simulation results
    simulation_results = models.JSONField(
        default=dict,
        blank=True,
        help_text="Detailed simulation results (timeline, analytics, losses)"
    )
    
    # Summary statistics
    total_drones_launched = models.IntegerField(default=0)
    total_drones_lost = models.IntegerField(default=0)
    total_drones_at_target = models.IntegerField(default=0)
    success_probability = models.FloatField(default=0.0)
    
    # Metadata
    status = models.CharField(
        max_length=20,
        choices=REPORT_STATUS,
        default='COMPLETED'
    )
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-simulation_date']
        verbose_name = "Mission Report"
        verbose_name_plural = "Mission Reports"
    
    def __str__(self):
        return f"Report #{self.id} - {self.mission.name} ({self.simulation_date.strftime('%Y-%m-%d %H:%M')})"
    
    def get_mission_config(self):
        """Return the complete mission configuration from snapshot."""
        return self.mission_snapshot
    
    def can_replay(self):
        """Check if report has enough data to replay."""
        return bool(self.mission_snapshot and self.mission_snapshot.get('blue_force'))


# ============================================================
# SIGNALS FOR AUTO-CREATION OF FORCE CONFIGS
# ============================================================

from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Mission)
def create_force_configs_on_mission_creation(sender, instance, created, **kwargs):
    """
    Signal handler: Auto-create ForceConfig entries (BLUE + RED) when Mission is created.
    
    This ensures every Mission automatically gets both force configuration objects
    initialized with is_configured=False.
    """
    if created:  # Only on creation, not on updates
        for force_type in ['blue', 'red']:
            ForceConfig.objects.get_or_create(
                mission=instance,
                force_type=force_type,
                defaults={
                    'config_data': {},
                    'is_configured': False
                }
            )


# ============================================================
# DRONE AND SWARM COMPOSITION MODELS
# ============================================================

class DroneType(models.Model):
    """
    Represents a drone type with specifications and costs.
    Data imported from Excel specifications.
    """
    DRONE_ROLE_CHOICES = [
        ('ATK', 'Attack/Kamikaze'),
        ('REC', 'Reconnaissance'),
        ('DEC', 'Decoy'),
        ('EW', 'Electronic Warfare'),
        ('COM', 'Communication Relay'),
        ('NAV', 'Navigation/INS'),
        ('CMD', 'Command & Control'),
    ]
    
    name = models.CharField(max_length=100, unique=True)
    role = models.CharField(max_length=10, choices=DRONE_ROLE_CHOICES)
    description = models.TextField(blank=True)
    
    # Technical specifications (from Excel import)
    cost = models.DecimalField(max_digits=12, decimal_places=2, help_text="Unit cost in USD")
    range_km = models.FloatField(help_text="Maximum operational range in km")
    payload_kg = models.FloatField(default=0, help_text="Payload capacity in kg")
    endurance_minutes = models.IntegerField(help_text="Flight time in minutes")
    stealth_factor = models.FloatField(default=1.0, help_text="Stealth rating (0.0-1.0)")
    
    # Availability constraints
    min_quantity = models.PositiveIntegerField(default=1)
    max_quantity = models.PositiveIntegerField(default=500)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['role', 'name']
        verbose_name_plural = "Drone Types"
    
    def __str__(self):
        return f"{self.name} ({self.get_role_display()})"
    
    def to_dict(self):
        """Serialize to dictionary for JSON response."""
        return {
            'id': self.id,
            'name': self.name,
            'role': self.role,
            'cost': float(self.cost),
            'range_km': self.range_km,
            'payload_kg': self.payload_kg,
            'endurance_minutes': self.endurance_minutes,
            'stealth_factor': self.stealth_factor,
            'min_quantity': self.min_quantity,
            'max_quantity': self.max_quantity,
        }


class TargetType(models.Model):
    """
    Defines target categories that drive swarm composition.
    Each target type has recommended drone role distributions.
    """
    TARGET_CATEGORY_CHOICES = [
        ('FIXED', 'Fixed Infrastructure'),
        ('MOBILE', 'Mobile Asset'),
        ('AIR', 'Air Defense'),
        ('AREA', 'Area Target'),
        ('VIP', 'High Value Target'),
    ]
    
    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(max_length=20, choices=TARGET_CATEGORY_CHOICES)
    description = models.TextField(blank=True)
    
    # Recommended composition (% per role)
    recommended_composition = models.JSONField(
        default=dict,
        help_text="Recommended drone role percentages for this target type"
    )
    
    # Example: {
    #     'ATK': 35,
    #     'REC': 20,
    #     'DEC': 15,
    #     'EW': 12,
    #     'COM': 10,
    #     'NAV': 5,
    #     'CMD': 3
    # }
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['category', 'name']
        verbose_name_plural = "Target Types"
    
    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"


class SwarmCompositionTemplate(models.Model):
    """
    Stores swarm composition templates by target type.
    Links DroneTypes with recommended percentages.
    """
    target_type = models.ForeignKey(TargetType, on_delete=models.CASCADE, related_name='composition_templates')
    drone_type = models.ForeignKey(DroneType, on_delete=models.CASCADE)
    percentage = models.FloatField(help_text="Recommended percentage for this drone type")
    
    class Meta:
        unique_together = ('target_type', 'drone_type')
        ordering = ['target_type', '-percentage']
    
    def __str__(self):
        return f"{self.target_type.name} - {self.drone_type.name}: {self.percentage}%"


class MissionSwarmConfig(models.Model):
    """
    Stores the finalized swarm configuration with costs for a mission.
    """
    mission = models.ForeignKey(Mission, on_delete=models.CASCADE, related_name='swarm_configs')
    force_type = models.CharField(max_length=10, choices=[('blue', 'Blue'), ('red', 'Red')], default='blue')
    target_type = models.ForeignKey(TargetType, on_delete=models.SET_NULL, null=True, blank=True)

    total_drones = models.PositiveIntegerField()
    final_composition = models.JSONField(default=dict)
    total_cost = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    applied_rules = models.JSONField(default=list, blank=True)
    validation_warnings = models.JSONField(default=list, blank=True)
    is_valid = models.BooleanField(default=True)
    locked = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Mission Swarm Configs"
        unique_together = ('mission', 'force_type')
    
    def __str__(self):
        return f"Swarm for {self.mission.name} ({self.force_type})"
    
    def recalculate_costs(self):
        """Recalculate total cost based on final composition."""
        total = 0
        for drone_id, allocation in self.final_composition.items():
            total += allocation.get('subtotal', 0)
        self.total_cost = total
        self.save()


# ============================================================
# AIR DEFENSE SYSTEM (ADS) CONFIGURATION MODELS
# ============================================================

class ADSSystem(models.Model):
    """
    Represents a real-world Air Defense System with detection, intercept, and targeting capabilities.
    Organized in layers: Outer (Long-Range), Middle, Inner (Close Defense), and Jammers (EW).
    """
    LAYER_CHOICES = [
        ('outer', 'Outer Layer - Long Range'),
        ('middle', 'Middle Layer - Medium Range'),
        ('inner', 'Inner Layer - Close Defense'),
        ('jammer', 'Electronic Warfare - Jammer'),
    ]
    
    SYSTEM_TYPE_CHOICES = [
        ('missile', 'Missile System'),
        ('gun', 'Gun System'),
        ('laser', 'Laser System'),
        ('jammer', 'Electronic Jammer'),
    ]
    
    name = models.CharField(max_length=100, unique=True)
    layer = models.CharField(max_length=10, choices=LAYER_CHOICES)
    system_type = models.CharField(max_length=20, choices=SYSTEM_TYPE_CHOICES)
    country = models.CharField(max_length=50, help_text="Country of origin")
    
    # Operational parameters (in km for missiles, m for others)
    detection_range = models.PositiveIntegerField(help_text="Detection range in km")
    intercept_range = models.PositiveIntegerField(help_text="Intercept/engagement range in km")
    max_targets = models.PositiveIntegerField(default=1, help_text="Maximum simultaneous targets")
    
    # For jammers
    effectiveness_percent = models.PositiveIntegerField(default=0, help_text="Jamming effectiveness percentage (0-100)")
    
    # Cost in millions USD
    cost_million_usd = models.DecimalField(max_digits=10, decimal_places=2, help_text="Unit cost in million USD")
    
    # UI appearance
    color_hex = models.CharField(max_length=7, default="#FFD700", help_text="HEX color code for map display")
    icon = models.CharField(max_length=50, default="🛡️", help_text="Emoji or icon")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['layer', '-detection_range']
        verbose_name = "ADS System"
        verbose_name_plural = "ADS Systems"
    
    def __str__(self):
        return f"{self.name} ({self.get_layer_display()})"
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            'id': self.id,
            'name': self.name,
            'layer': self.layer,
            'system_type': self.system_type,
            'country': self.country,
            'detection_range': self.detection_range,
            'intercept_range': self.intercept_range,
            'max_targets': self.max_targets,
            'effectiveness_percent': self.effectiveness_percent,
            'cost_million_usd': float(self.cost_million_usd),
            'color_hex': self.color_hex,
            'icon': self.icon,
        }


class ADSPlacement(models.Model):
    """
    Represents a single ADS unit placed on the map at a specific location.
    References the ADS System template and stores placement details.
    """
    mission = models.ForeignKey(Mission, on_delete=models.CASCADE, related_name='ads_placements')
    force_type = models.CharField(max_length=10, choices=[('blue', 'Blue'), ('red', 'Red')])
    ads_system = models.ForeignKey(ADSSystem, on_delete=models.CASCADE, related_name='placements')
    
    # Geographic coordinates
    latitude = models.FloatField(help_text="Deployment latitude")
    longitude = models.FloatField(help_text="Deployment longitude")
    
    # Status and priority
    is_active = models.BooleanField(default=True)
    priority = models.PositiveIntegerField(default=0, help_text="Priority order (0=highest)")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "ADS Placements"
        indexes = [
            models.Index(fields=['mission', 'force_type']),
        ]
    
    def __str__(self):
        return f"{self.ads_system.name} at ({self.latitude:.4f}, {self.longitude:.4f})"
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            'id': self.id,
            'system_id': self.ads_system.id,
            'system_name': self.ads_system.name,
            'layer': self.ads_system.layer,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'intercept_range': self.ads_system.intercept_range,
            'detection_range': self.ads_system.detection_range,
            'color_hex': self.ads_system.color_hex,
            'cost_million_usd': float(self.ads_system.cost_million_usd),
        }


class ADSConfiguration(models.Model):
    """
    Complete ADS configuration for a force in a mission.
    Stores aggregate data and validation results.
    """
    mission = models.ForeignKey(Mission, on_delete=models.CASCADE, related_name='ads_configs')
    force_type = models.CharField(max_length=10, choices=[('blue', 'Blue'), ('red', 'Red')])
    
    # Aggregate costs and data
    total_cost_million = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    placement_data = models.JSONField(default=dict, help_text="Cached placement data")
    
    # Validation and warnings
    coverage_gaps = models.JSONField(default=list, help_text="Identified coverage gaps")
    overlap_inefficiencies = models.JSONField(default=list, help_text="Areas with excessive overlap")
    feasibility_warnings = models.JSONField(default=list, help_text="Operational warnings")
    
    is_complete = models.BooleanField(default=False)
    locked = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "ADS Configurations"
        unique_together = ('mission', 'force_type')
    
    def __str__(self):
        return f"ADS Config for {self.mission.name} ({self.force_type})"
    
    def calculate_total_cost(self):
        """Recalculate total cost from all placements."""
        placements = ADSPlacement.objects.filter(
            mission=self.mission,
            force_type=self.force_type,
            is_active=True
        )
        total = sum(p.ads_system.cost_million_usd for p in placements)
        self.total_cost_million = total
        self.save()
        return total
    
    def detect_coverage_gaps(self, target_locations=None):
        """
        Detect areas not covered by any ADS system.
        If target_locations provided, check if each target is covered.
        """
        placements = ADSPlacement.objects.filter(
            mission=self.mission,
            force_type=self.force_type,
            is_active=True
        )
        
        gaps = []
        if target_locations:
            from geopy.distance import distance as geopy_distance
            for target in target_locations:
                is_covered = False
                for placement in placements:
                    dist = geopy_distance(
                        (placement.latitude, placement.longitude),
                        (target['lat'], target['lon'])
                    ).km
                    if dist <= placement.ads_system.detection_range:
                        is_covered = True
                        break
                if not is_covered:
                    gaps.append({
                        'target': target.get('name', 'Unknown'),
                        'lat': target['lat'],
                        'lon': target['lon'],
                    })
        
        self.coverage_gaps = gaps
        return gaps
    
    def detect_overlaps(self, overlap_threshold=0.3):
        """
        Detect areas with excessive ADS overlap (inefficient cost usage).
        overlap_threshold: percentage of detection range where systems overlap.
        """
        placements = list(ADSPlacement.objects.filter(
            mission=self.mission,
            force_type=self.force_type,
            is_active=True
        ))
        
        overlaps = []
        for i, p1 in enumerate(placements):
            for p2 in placements[i+1:]:
                from geopy.distance import distance as geopy_distance
                dist = geopy_distance(
                    (p1.latitude, p1.longitude),
                    (p2.latitude, p2.longitude)
                ).km
                
                # Calculate overlap
                r1 = p1.ads_system.detection_range
                r2 = p2.ads_system.detection_range
                
                if dist < (r1 + r2):
                    overlap_area_percent = max(0, min(100, 100 * (1 - dist / (r1 + r2))))
                    if overlap_area_percent >= overlap_threshold * 100:
                        overlaps.append({
                            'system1': p1.ads_system.name,
                            'system2': p2.ads_system.name,
                            'distance_km': round(dist, 2),
                            'overlap_percent': round(overlap_area_percent, 1),
                            'combined_cost': float(p1.ads_system.cost_million_usd + p2.ads_system.cost_million_usd),
                        })
        
        self.overlap_inefficiencies = overlaps
        return overlaps


# # ============================================================
# # VIEWS - Configuration API Endpoints
# # ============================================================

# from django.http import JsonResponse
# from django.views.decorators.http import require_http_methods
# from django.shortcuts import get_object_or_404
# from .models import ForceConfig, Mission

# @require_http_methods(["GET"])
# def get_force_config(request):
#     """GET /config/api/force-config/?mission=ID&force=TYPE"""
#     try:
#         mission_id = request.GET.get('mission')
#         force_type = request.GET.get('force', 'blue').lower()
        
#         if not mission_id:
#             return JsonResponse({'error': 'mission parameter required'}, status=400)
        
#         mission = get_object_or_404(Mission, id=mission_id)
#         config = ForceConfig.objects.get(mission=mission, force_type=force_type)
        
#         # Get configuration data
#         config_data = config.config_data or {}
        
#         # Build response with all required fields
#         response_data = {
#             'scenario': config_data.get('scenario', 'Not configured'),
#             'bases': config_data.get('bases', []),
#             'targets': config_data.get('targets', []),
#             'swarm_total': config_data.get('swarm_total', 0),
#             'swarm_composition': config_data.get('swarm_composition', {}),
#             'target_type': config_data.get('target_type', 'Not configured'),
#             'total_cost': config_data.get('total_cost', 0),
#             'ads': config_data.get('ads', []),
#         }
        
#         return JsonResponse(response_data)
#     except ForceConfig.DoesNotExist:
#         return JsonResponse({'error': 'ForceConfig not found'}, status=404)
#     except Exception as e:
#         import traceback
#         traceback.print_exc()
#         return JsonResponse({'error': str(e)}, status=400)
