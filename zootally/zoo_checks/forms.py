from django import forms

from .models import AnimalCount, SpeciesExhibitCount


class AnimalCountForm(forms.ModelForm):
    class Meta:
        model = AnimalCount
        fields = ["condition", "animal"]

        # hide animal form element
        widgets = {"animal": forms.HiddenInput()}

    SEEN = "SE"
    NEEDSATTENTION = "NA"
    BAR = "BA"
    MISSING = "MI"

    CONDITIONS = [
        (SEEN, "seen"),
        (NEEDSATTENTION, "Needs Attention"),
        (BAR, "BAR (Sr. Avic.)"),
        (MISSING, "Missing (Avic. only)"),
    ]
    condition = forms.ChoiceField(choices=CONDITIONS, widget=forms.RadioSelect)


class SpeciesExhibitCountForm(forms.ModelForm):
    class Meta:
        model = SpeciesExhibitCount
        fields = ["count", "species", "exhibit"]

        # hide species/exhibit form elements
        widgets = {"species": forms.HiddenInput(), "exhibit": forms.HiddenInput()}
