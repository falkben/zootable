from django.forms import ModelForm

from .models import AnimalCount, SpeciesExhibitCount


class AnimalCountForm(ModelForm):
    class Meta:
        model = AnimalCount
        fields = ["count_val"]


class SpeciesExhibitCountForm(ModelForm):
    class Meta:
        model = SpeciesExhibitCount
        fields = ["count_val"]
