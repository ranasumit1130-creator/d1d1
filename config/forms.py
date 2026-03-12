# config/forms.py
from django import forms
from django.forms import formset_factory, BaseFormSet
import json


class MissionCreateForm(forms.Form):
    """Form for creating a new mission."""
    mission_name = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter Mission Name',
            'id': 'missionNameInput'
        })
    )


class ScenarioSelectionForm(forms.Form):
    """Form to select drone deployment scenario."""
    SCENARIO_CHOICES = [
        ('one-to-one', 'One Base → One Target'),
        ('one-to-many', 'One Base → Multiple Targets'),
        ('many-to-one', 'Many Bases → One Target'),
        ('many-to-many', 'Many Bases → Many Targets'),
    ]
    
    scenario = forms.ChoiceField(
        choices=SCENARIO_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'scenarioSelect'
        })
    )


class BaseForm(forms.Form):
    """Form for drone base (starting location)."""
    name = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Base Name'
        })
    )
    latitude = forms.FloatField(
        required=True,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Latitude',
            'step': '0.0001'
        })
    )
    longitude = forms.FloatField(
        required=True,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Longitude',
            'step': '0.0001'
        })
    )


class TargetForm(forms.Form):
    """Form for target location."""
    name = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Target Name'
        })
    )
    latitude = forms.FloatField(
        required=True,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Latitude',
            'step': '0.0001'
        })
    )
    longitude = forms.FloatField(
        required=True,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Longitude',
            'step': '0.0001'
        })
    )


class DroneForm(forms.Form):
    """Form for drone type and configuration."""
    DRONE_TYPE_CHOICES = [
        ('attack', 'Attack Drone'),
        ('kamikaze', 'Kamikaze Drone'),
        ('surveillance', 'Surveillance Drone'),
    ]
    
    ATTACK_PATTERN_CHOICES = [
        ('swarm', 'Swarm'),
        ('line', 'Line'),
        ('dispersed', 'Dispersed'),
        ('loitering', 'Loitering'),
    ]
    
    drone_type = forms.ChoiceField(
        choices=DRONE_TYPE_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select drone-type-select',
        })
    )
    quantity = forms.IntegerField(
        min_value=1,
        required=True,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Quantity'
        })
    )
    attack_pattern = forms.ChoiceField(
        choices=ATTACK_PATTERN_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select',
        })
    )


class BaseFormSet(BaseFormSet):
    """Custom formset for bases with validation."""
    def clean(self):
        super().clean()
        # Ensure at least one base is provided
        if not any(self.cleaned_data and not self.cleaned_data[0].get('DELETE', False) 
                   for self.cleaned_data in self.cleaned_data if self.cleaned_data):
            if self.total_form_count() > 0:
                raise forms.ValidationError("At least one base is required.")


class BaseFormSetFactory(BaseFormSet):
    """Formset factory for bases."""
    pass


class TargetFormSetFactory(BaseFormSet):
    """Formset factory for targets."""
    pass


# Create formsets
BaseFormSet = formset_factory(BaseForm, extra=1, can_delete=False)
TargetFormSet = formset_factory(TargetForm, extra=1, can_delete=False)
DroneFormSet = formset_factory(DroneForm, extra=1, can_delete=False, max_num=5)


class ADSForm(forms.Form):
    """Form for Air Defense System placement."""
    ADS_TYPE_CHOICES = [
        ('s-400', 'S-400 Triumf'),
        ('akash-ng', 'Akash-NG'),
        ('barak-8', 'Barak-8'),
        ('iron-dome', 'Iron Dome'),
        ('patriot', 'Patriot (MIM-104)'),
        ('tor-m2', 'Tor-M2'),
        ('pantsir-s1', 'Pantsir-S1'),
    ]
    
    ads_type = forms.ChoiceField(
        choices=ADS_TYPE_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select ads-type-select',
        })
    )
    latitude = forms.FloatField(
        required=True,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Latitude',
            'step': '0.0001'
        })
    )
    longitude = forms.FloatField(
        required=True,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Longitude',
            'step': '0.0001'
        })
    )


ADSFormSet = formset_factory(ADSForm, extra=0, can_delete=False)