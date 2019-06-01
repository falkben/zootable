from django.forms import ModelForm

from .models import AnimalCount, SpeciesExhibitCount


class AnimalCountForm(ModelForm):
    class Meta:
        model = AnimalCount
        # hide animal form element
        fields = ["condition", "animal"]


class SpeciesExhibitCountForm(ModelForm):
    class Meta:
        model = SpeciesExhibitCount
        # hide species/exhibit form elements
        fields = ["count", "species", "exhibit"]
