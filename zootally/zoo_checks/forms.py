from datetime import datetime

from django import forms

from .models import AnimalCount, SpeciesExhibitCount


class DateInput(forms.Form):
    date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date", "value": datetime.now().date})
    )


class AnimalCountForm(forms.ModelForm):
    class Meta:
        model = AnimalCount
        # hide animal form element
        fields = ["condition"]


class SpeciesExhibitCountForm(forms.ModelForm):
    class Meta:
        model = SpeciesExhibitCount
        # hide species/exhibit form elements
        fields = ["count"]
