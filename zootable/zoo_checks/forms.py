import datetime

from django import forms
from django.utils import timezone

from .models import AnimalCount, Enclosure, GroupCount, SpeciesCount


class AnimalCountForm(forms.ModelForm):
    class Meta:
        model = AnimalCount
        fields = ["condition", "comment", "animal", "enclosure"]

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
        show_hidden_initial=True,
    )


class SpeciesCountForm(forms.ModelForm):
    class Meta:
        model = SpeciesCount
        fields = ["count", "species", "enclosure"]

        # hide species/enclosure form elements
        widgets = {"species": forms.HiddenInput(), "enclosure": forms.HiddenInput()}

    count = forms.IntegerField(
        max_value=None,
        min_value=0,
        show_hidden_initial=True,
        widget=forms.NumberInput(attrs={"class": "narrow-count"}),
    )


class GroupCountForm(forms.ModelForm):
    class Meta:
        model = GroupCount
        fields = ["count_male", "count_female", "count_unknown", "group", "enclosure"]

        # TODO: figure out how to add max value in widget attrs
        widgets = {
            # hide species/enclosure form elements
            "group": forms.HiddenInput(),
            "enclosure": forms.HiddenInput(),
        }

    count_male = forms.IntegerField(
        max_value=None,
        min_value=0,
        show_hidden_initial=True,
        widget=forms.NumberInput(attrs={"class": "narrow-count"}),
    )
    count_female = forms.IntegerField(
        max_value=None,
        min_value=0,
        show_hidden_initial=True,
        widget=forms.NumberInput(attrs={"class": "narrow-count"}),
    )
    count_unknown = forms.IntegerField(
        max_value=None,
        min_value=0,
        show_hidden_initial=True,
        widget=forms.NumberInput(attrs={"class": "narrow-count"}),
    )


class UploadFileForm(forms.Form):
    file = forms.FileField()
    # TODO: validate that it's an excel file
    # TODO: validate the file is not too large?


class ExportForm(forms.Form):
    selected_enclosures = forms.ModelMultipleChoiceField(
        widget=forms.CheckboxSelectMultiple, queryset=Enclosure.objects.all()
    )
    start_date = forms.DateField(required=True)
    end_date = forms.DateField(required=True)

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        if not isinstance(start_date, datetime.date) or not isinstance(
            end_date, datetime.date
        ):
            raise forms.ValidationError("Not a date")

        if end_date < start_date:
            raise forms.ValidationError("End date should be greater than start date.")

        if start_date > timezone.localdate():
            raise forms.ValidationError(
                "Start date should be greater than current date."
            )

        return cleaned_data


class SignupForm(forms.Form):
    first_name = forms.CharField(
        max_length=30,
        label="First Name",
        widget=forms.TextInput(attrs={"placeholder": "First Name"}),
    )
    last_name = forms.CharField(
        max_length=100,
        label="Last Name",
        widget=forms.TextInput(attrs={"placeholder": "Last Name"}),
    )

    def signup(self, request, user):
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.save()


class TallyDateForm(forms.Form):
    tally_date = forms.DateField(required=True)

    def clean(self):
        cleaned_data = super().clean()
        target_date = cleaned_data.get("tally_date")

        if not isinstance(target_date, datetime.date):
            raise forms.ValidationError("Not a date")

        if target_date > timezone.localdate():
            raise forms.ValidationError("Date needs to be in the past.")

        return cleaned_data
