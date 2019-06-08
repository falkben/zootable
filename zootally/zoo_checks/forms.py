from django import forms

from .models import AnimalCount, SpeciesCount

# TODO: create form at the exhibit level
# ExhibitCountFormset (nested) https://micropyramid.com/blog/how-to-use-nested-formsets-in-django/
# Inline formset: https://docs.djangoproject.com/en/2.2/topics/forms/modelforms/#inline-formsets


class AnimalCountForm(forms.ModelForm):
    class Meta:
        model = AnimalCount
        fields = ["condition", "animal", "exhibit"]

        # hide animal form element
        widgets = {"animal": forms.HiddenInput(), "exhibit": forms.HiddenInput()}

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


class SpeciesCountForm(forms.ModelForm):
    class Meta:
        model = SpeciesCount
        fields = ["count", "species", "exhibit"]

        # hide species/exhibit form elements
        widgets = {"species": forms.HiddenInput(), "exhibit": forms.HiddenInput()}


class BaseAnimalCountFormset(forms.BaseFormSet):
    def clean(self):
        if any(self.errors):
            # Don't bother validating the formset unless each form is valid on its own
            return
        for form in self.forms:
            # Where we put validation
            pass


class BaseSpeciesCountFormset(forms.BaseFormSet):
    def clean(self):
        if any(self.errors):
            # Don't bother validating the formset unless each form is valid on its own
            return
        for form in self.forms:
            # Where we put validation
            pass
