from django import forms

from .models import AnimalCount, GroupCount, SpeciesCount


class AnimalCountForm(forms.ModelForm):
    class Meta:
        model = AnimalCount
        fields = ["condition", "animal", "enclosure"]

        # hide animal form element
        widgets = {"animal": forms.HiddenInput(), "enclosure": forms.HiddenInput()}

    def __init__(self, *args, **kwargs):
        is_staff = kwargs.pop("is_staff", None)
        super(AnimalCountForm, self).__init__(*args, **kwargs)
        if is_staff:
            self.fields["condition"].choices = AnimalCount.STAFF_CONDITIONS

    condition = forms.ChoiceField(
        choices=AnimalCount.CONDITIONS,
        widget=forms.RadioSelect,
        label="",
        required=False,
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

        # TODO: figure out how to add max value in widget attrs
        widgets = {
            # hide species/enclosure form elements
            "group": forms.HiddenInput(),
            "enclosure": forms.HiddenInput(),
            # make the input boxes smaller
            "count_male": forms.NumberInput(attrs={"class": "narrow-count"}),
            "count_female": forms.NumberInput(attrs={"class": "narrow-count"}),
            "count_unknown": forms.NumberInput(attrs={"class": "narrow-count"}),
        }


class BaseAnimalCountFormset(forms.BaseInlineFormSet):
    def clean(self):
        if any(self.errors):
            # Don't bother validating the formset unless each form is valid on its own
            return
        for form in self.forms:
            # Where we put validation
            pass


class BaseSpeciesCountFormset(forms.BaseInlineFormSet):
    def clean(self):
        if any(self.errors):
            # Don't bother validating the formset unless each form is valid on its own
            return
        for form in self.forms:
            # Where we put validation
            pass
