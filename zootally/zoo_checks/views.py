from datetime import datetime

from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.forms import inlineformset_factory
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render

from .forms import AnimalCountForm, SpeciesExhibitCountForm
from .models import Animal, AnimalCount, Exhibit, Species, SpeciesExhibitCount


def create_combined_form(exhibits):
    # TODO: counts should default to maximum (across users) for the day
    # TODO: condition should default to median? condition (across users) for the day

    form_dict = {}

    for exhibit in exhibits:
        form_dict[exhibit] = {}
        form_dict[exhibit]["species"] = []
        form_dict[exhibit]["animals"] = []
        for spec in exhibit.species.all():
            spec_count = SpeciesExhibitCount(species=spec, exhibit=exhibit)
            form_dict[exhibit]["species"].append(
                {spec: SpeciesExhibitCountForm(instance=spec_count)}
            )

            # animals of this species on this exhibit

            anim_spec_exhib = Animal.objects.filter(exhibit=exhibit, species=spec)
            for anim in anim_spec_exhib:
                anim_count = AnimalCount(animal=anim)
                # TODO: only users w/ specific privaledges can mark certain conditions

                form_dict[exhibit]["animals"].append(
                    {spec: {anim: AnimalCountForm(instance=anim_count)}}
                )

    return form_dict


@login_required
def home(request):
    exhibits = Exhibit.objects.filter(user=request.user)

    return render(request, "home.html", {"exhibits": exhibits})


@login_required
def count(request, exhibit_id):
    exhibit = get_object_or_404(Exhibit, pk=exhibit_id)

    SpeciesCountFormset = inlineformset_factory(
        Exhibit, SpeciesExhibitCount, fields=("count",), can_delete=False
    )
    AnimalCountFormset = inlineformset_factory(
        Exhibit, AnimalCount, fields=("condition",), can_delete=False
    )

    # if this is a POST request we need to process the form data
    if request.method == "POST":
        # create a form instance and populate it with data from the request:
        species_formset = SpeciesCountFormset(
            request.POST, request.FILES, instance=exhibit
        )
        animal_formset = AnimalCountFormset(
            request.POST, request.FILES, instance=exhibit
        )
        # check whether it's valid:
        if species_formset.is_valid() and animal_formset.is_valid():
            # process the data in form.cleaned_data as required
            # ...
            # redirect to a new URL:
            return HttpResponseRedirect("/table/")

    # if a GET (or any other method) we'll create a blank form
    else:
        species_formset = SpeciesCountFormset(instance=exhibit)
        animal_formset = AnimalCountFormset(instance=exhibit)

    return render(
        request,
        "tally.html",
        {
            "exhibit": exhibit,
            "species_formset": species_formset,
            "animal_formset": animal_formset,
        },
    )
