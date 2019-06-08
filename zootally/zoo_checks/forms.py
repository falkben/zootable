from django import forms

from .models import AnimalCount, GroupCount, SpeciesCount


class AnimalCountForm(forms.ModelForm):
    class Meta:
        model = AnimalCount
        fields = ["condition", "animal", "enclosure"]

        # hide animal form element
        widgets = {"animal": forms.HiddenInput(), "enclosure": forms.HiddenInput()}

    condition = forms.ChoiceField(
        choices=AnimalCount.CONDITIONS, widget=forms.RadioSelect, label=""
    )


class SpeciesCountForm(forms.ModelForm):
    class Meta:
        model = SpeciesCount
        fields = ["count", "species", "enclosure"]

        # hide species/enclosure form elements
        widgets = {
            "species": forms.HiddenInput(),
            "enclosure": forms.HiddenInput(),
            "count": forms.NumberInput(attrs={"class": "narrow-count"}),
        }


class GroupCountForm(forms.ModelForm):
    class Meta:
        model = GroupCount
        fields = ["count_male", "count_female", "count_unknown", "group", "enclosure"]

        # hide species/enclosure form elements
        widgets = {
            "group": forms.HiddenInput(),
            "enclosure": forms.HiddenInput(),
            "count_male": forms.NumberInput(attrs={"class": "narrow-count"}),
            "count_female": forms.NumberInput(attrs={"class": "narrow-count"}),
            "count_unknown": forms.NumberInput(attrs={"class": "narrow-count"}),
        }


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
