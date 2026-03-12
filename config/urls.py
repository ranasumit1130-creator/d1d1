# config/urls.py
from django.urls import path
from . import views
from . import views_mission_config
from . import api_views
from . import api_step_views

app_name = 'config'

urlpatterns = [
    # Mission creation
    path('mission/create/', views.MissionCreateView.as_view(), name='mission_create'),
    
    # Force selection
    path('mission/<int:mission_id>/force-select/', views.ForceSelectView.as_view(), name='force_select'),
    
    # Force configuration (main configuration page) - Function-based view
    path('mission/<int:mission_id>/force/<str:force_type>/',
         views.force_config_view, name='force_config'),
    
    # Step-by-step configuration views
    path('mission/<int:mission_id>/force/<str:force_type>/step1/',
         views.step1_scenario_selection, name='step1_scenario'),
    
    path('mission/<int:mission_id>/force/<str:force_type>/step2/',
         views.step2_base_target_selection, name='step2_base_target'),
    
    path('mission/<int:mission_id>/force/<str:force_type>/step3/',
         views.step3_swarm_composition, name='step3_swarm'),
    
    path('mission/<int:mission_id>/force/<str:force_type>/step4/',
         views.step4_ads_config, name='step4_ads'),
    
    path('mission/<int:mission_id>/force/<str:force_type>/step5/',
         views.step5_review, name='step5_review'),
    
    # AJAX endpoints for capabilities
    path('api/drone-capabilities/', views.get_drone_capabilities, name='drone_capabilities'),
    path('api/ads-capabilities/', views.get_ads_capabilities, name='ads_capabilities'),
    
    # Simulation ready (show configured data before starting)
    path('mission/<int:mission_id>/simulation-ready/',
         views.simulation_ready, name='simulation_ready'),
    
    # Simulation start (actual simulation visualization)
    path('mission/<int:mission_id>/simulation-start/',
         views.simulation_start, name='simulation_start'),

    # Mission Configuration workflow
    path('mission/<int:mission_id>/config/step1/', 
         views_mission_config.MissionConfigurationStep1View.as_view(), 
         name='mission_config_step1'),

    path('mission/<int:mission_id>/config/step2/', 
         views_mission_config.MissionConfigurationStep2View.as_view(), 
         name='mission_config_step2'),

    path('mission/<int:mission_id>/config/step3/', 
         views_mission_config.MissionConfigurationStep3View.as_view(), 
         name='mission_config_step3'),

    path('mission/<int:mission_id>/config/step4/', 
         views_mission_config.MissionConfigurationStep4View.as_view(), 
         name='mission_config_step4'),

    path('mission/<int:mission_id>/config/step5/', 
         views_mission_config.MissionConfigurationStep5View.as_view(), 
         name='mission_config_step5'),

    path('mission/<int:mission_id>/config/review/', 
         views_mission_config.MissionConfigurationReviewView.as_view(), 
         name='mission_config_review'),

    path('mission/<int:mission_id>/simulate/', 
         views_mission_config.MissionRunSimulationView.as_view(), 
         name='mission_run_simulation'),

    # API endpoints that exist in api_views.py
    path('api/force-config/', api_views.get_force_config, name='api_force_config'),
    path('api/mission-data/', api_views.get_mission_data, name='api_mission_data'),
    path('api/simulate-mission/', api_views.simulate_mission, name='api_simulate_mission'),
    path('api/check-ads-range/', api_views.check_drone_in_ads_range, name='api_check_ads_range'),
    path('api/save-report/', api_views.save_mission_report, name='api_save_report'),
    path('api/save-mission-report/', api_views.save_mission_report, name='api_save_mission_report'),
    path('api/mission-reports/', api_views.get_mission_reports, name='api_mission_reports'),
    path('api/report-detail/', api_views.get_report_detail, name='api_report_detail'),
    path('api/replay-report/', api_views.replay_mission_from_report, name='api_replay_report'),

    # API endpoints for step workflow - api_step_views.py
    path('api/step1/select-scenario/', api_step_views.step1_select_scenario, name='api_step1_select_scenario'),
    path('api/step2/save-placement/', api_step_views.step2_save_placement, name='api_step2_save_placement'),

    # Step 3 API endpoints - api_views.py
    path('api/target-types/', api_views.get_target_types, name='api_target_types'),
    path('api/drone-types/', api_views.get_drone_types, name='api_drone_types'),
    path('api/step3/calculate-swarm-cost/', api_views.step3_calculate_swarm_cost, name='api_step3_calculate'),
    path('api/step3/save-swarm-config/', api_views.step3_save_swarm_config, name='api_step3_save'),

    # Step 4 API endpoints - api_step_views.py
    path('api/step4/get-ads-systems/', api_step_views.step4_get_ads_systems, name='api_step4_get_ads'),
    path('api/step4/place-ads/', api_step_views.step4_place_ads, name='api_step4_place_ads'),
    path('api/step4/remove-ads/', api_step_views.step4_remove_ads, name='api_step4_remove_ads'),
    path('api/step4/save-ads-placements/', api_step_views.step4_save_ads_placements, name='api_step4_save_ads_placements'),
    path('api/step5/save-config/', api_step_views.step5_save_config, name='api_step5_save'),

    path('mission/<int:mission_id>/simulation-cesium/',
         views.simulation_cesium, name='simulation_cesium'),

    # Strike Planning — step in the main flow (between ADS and Review)
    path('mission/<int:mission_id>/force/<str:force_type>/strike-planning/',
         views.step_strike_planning, name='strike_planning'),
    path('api/strike-planning/save/', api_views.step_strike_planning_save, name='api_strike_planning_save'),

    # MissionReport save — used by strike_planning.html (fire-and-forget)
    path('api/save-strike-record/', api_views.save_strike_record, name='api_save_strike_record'),


     # Ankush Api endpoints for step 2 - map placement
     path("tiles/<int:z>/<int:x>/<int:y>.png", views.tile_view),
     path("terrain/<str:tile_name>", views.terrain_view),
     path("3dtiles/<str:file_name>", views.tileset_3d_view),
     path("api/geocode/", views.geocode, name="geocode"),
]