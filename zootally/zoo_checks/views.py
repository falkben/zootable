from datetime import datetime

from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.forms import inlineformset_factory
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render

from .forms import AnimalCountForm, SpeciesExhibitCountForm
from .models import Animal, AnimalCount, Exhibit, Species, SpeciesExhibitCount


@login_required
# TODO: logins may not be sufficient - they need to be a part of a group
def home(request):
    exhibits = Exhibit.objects.filter(user=request.user)

    return render(request, "home.html", {"exhibits": exhibits})


def create_formsets(exhibit, exhibit_species, exhibit_animals, request=None):
    """
    Creates formsets in a dictionary in a particular order that we can 
    render in the template
    """

    SpeciesCountFormset = inlineformset_factory(
        Exhibit,
        SpeciesExhibitCount,
        form=SpeciesExhibitCountForm,
        can_delete=False,
        can_order=False,
        extra=1,  # one species at a time in "our" order
        # extra=len(exhibit_species),  # exhibit.species.count(),
    )
    AnimalCountFormset = inlineformset_factory(
        Exhibit,
        AnimalCount,
        form=AnimalCountForm,
        can_delete=False,
        can_order=False,
        extra=1,  # one animal at a time, in "our" order
        # extra=len(exhibit_animals),  # exhibit.animals.count(),
    )

    # to set the order
    formset_dict = {}
    for spec in exhibit_species:
        # create species formset
        species_formset = SpeciesCountFormset(
            instance=exhibit, initial={"species": spec}
        )
        species_formset = SpeciesCountFormset(
            instance=exhibit, initial={"species": spec}
        )

        spec_anim_list = []
        spec_anim_formset = []
        for animal in exhibit_animals.filter(species=spec):
            spec_anim_list.append(animal)
            animal_formset = AnimalCountFormset(
                instance=exhibit, initial={"animal": animal}
            )
            spec_anim_formset.append(animal_formset)

        # store in dictionary, using id because that's known unique
        formset_dict[spec.id] = {}
        formset_dict[spec.id]["species"] = spec
        formset_dict[spec.id]["specformset"] = species_formset
        formset_dict[spec.id]["animals"] = spec_anim_list
        formset_dict[spec.id]["animalformset"] = spec_anim_formset

    return formset_dict


@login_required
def count(request, exhibit_id):
    # TODO: counts should default to maximum (across users) for the day
    # TODO: condition should default to median? condition (across users) for the day

    exhibit = get_object_or_404(Exhibit, pk=exhibit_id)
    exhibit_species = exhibit.species.all()
    exhibit_animals = exhibit.animals.all()

    # if this is a POST request we need to process the form data
    if request.method == "POST":
        # create a form instance and populate it with data from the request:
        species_formset = SpeciesCountFormset(
            request.POST, request.FILES, instance=exhibit, initial=init_sp_vals
        )
        animal_formset = AnimalCountFormset(
            request.POST, request.FILES, instance=exhibit, initial=init_anim_vals
        )
        # check whether it's valid:
        if species_formset.is_valid() and animal_formset.is_valid():
            # process the data in form.cleaned_data as required
            # ...
            # redirect to a new URL:
            return HttpResponseRedirect("/")

    # if a GET (or any other method) we'll create a blank form
    else:
        formset_dict = create_formsets(exhibit, exhibit_species, exhibit_animals)

    return render(
        request,
        "tally.html",
        {
            "exhibit": exhibit,
            "exhibit_animals": list(exhibit_animals),
            "exhibit_species": list(exhibit_species),
            "formset_dict": formset_dict,
        },
    )
