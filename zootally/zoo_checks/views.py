from datetime import date
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Max
from django.forms import inlineformset_factory, formset_factory
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render

from .forms import (
    AnimalCountForm,
    BaseAnimalCountFormset,
    BaseSpeciesCountFormset,
    SpeciesCountForm,
)
from .models import Animal, AnimalCount, Exhibit, Species, SpeciesCount


@login_required
# TODO: logins may not be sufficient - they need to be a part of a group
def home(request):
    exhibits = Exhibit.objects.filter(user=request.user)

    return render(request, "home.html", {"exhibits": exhibits})


def get_formset_order(
    exhibit_species, exhibit_animals, species_formset, animals_formset
):
    """
    Creates an order to display the formsets that we can call in the template
    """

    # to set the order
    formset_dict = {}
    anim_total = 0
    for ind, spec in enumerate(exhibit_species):
        spec_anim_list = exhibit_animals.filter(species=spec).order_by("name")
        spec_anim_index = list(range(anim_total, spec_anim_list.count() + anim_total))
        anim_total += spec_anim_list.count()

        species_formset.forms[ind].initial.update(species_formset.initial_extra[ind])
        # species_formset.forms[ind].initial["count"] = species_formset

        # store in dictionary, using id because that's known unique
        formset_dict[spec.id] = {}
        formset_dict[spec.id]["species"] = spec
        formset_dict[spec.id]["formset"] = species_formset[ind]
        formset_dict[spec.id]["animalformset_index"] = zip(
            spec_anim_list, [animals_formset[i] for i in spec_anim_index]
        )

    return formset_dict


def get_init_spec_count_form(exhibit, exhibit_species, species_counts_today):
    # TODO: counts should default to maximum (across users) for the day
    init_sp_counts = [0] * exhibit_species.count()
    for i, sp in enumerate(exhibit_species):
        sp_count = species_counts_today.filter(species=sp)
        if sp_count.count() > 0:
            init_sp_counts[i] = sp_count.aggregate(Max("count"))["count__max"]

    init_spec = [
        {"species": obj} for obj in exhibit_species.all().order_by("common_name")
    ]
    [init.update({"count": c}) for init, c in zip(init_spec, init_sp_counts)]

    return init_spec


def get_init_anim_count_form(exhibit, exhibit_animals):
    # TODO: condition should default to median? condition (across users) for the day
    init_anim = [{"animal": obj} for obj in exhibit_animals]

    return init_anim


@login_required
def count(request, exhibit_id):
    exhibit = get_object_or_404(Exhibit, pk=exhibit_id)
    exhibit_species = exhibit.species.all()
    exhibit_animals = exhibit.animals.all().order_by("species", "name")
    species_counts_today = (
        SpeciesCount.objects.filter(species__in=exhibit_species)
        .filter(datecounted__gte=date.today())
        .order_by("species")
    )

    SpeciesCountFormset = inlineformset_factory(
        Exhibit,
        SpeciesCount,
        form=SpeciesCountForm,
        # formset=BaseSpeciesCountFormset,
        extra=exhibit_species.count(),
        max_num=exhibit_species.count(),
        can_order=False,
        can_delete=False,
    )

    AnimalCountFormset = inlineformset_factory(
        Exhibit,
        AnimalCount,
        form=AnimalCountForm,
        # formset=BaseAnimalCountFormset,
        extra=exhibit_animals.count(),
        max_num=exhibit_animals.count(),
        can_order=False,
        can_delete=False,
    )

    init_spec = get_init_spec_count_form(exhibit, exhibit_species, species_counts_today)
    init_anim = get_init_anim_count_form(exhibit, exhibit_animals)

    # if this is a POST request we need to process the form data
    if request.method == "POST":
        # create a form instance and populate it with data from the request:
        species_formset = SpeciesCountFormset(
            request.POST, instance=exhibit, initial=init_spec, prefix="species_formset"
        )
        # TODO: Need to test to make sure we are editing the right animal counts
        animals_formset = AnimalCountFormset(
            request.POST, instance=exhibit, initial=init_anim, prefix="animals_formset"
        )

        # check whether it's valid:
        if species_formset.is_valid() and animals_formset.is_valid():
            # process the data in form.cleaned_data as required
            for form in species_formset.save():
                form.users.add(request.user)

            for form in animals_formset.save():
                form.users.add(request.user)

            # redirect to a new URL:
            return HttpResponseRedirect("/")

        # needed in the case the form wasn't submitted properly and we have to re-render the form
        formset_order = get_formset_order(
            exhibit_species, exhibit_animals, species_formset, animals_formset
        )

    # if a GET (or any other method) we'll create a blank form
    else:
        species_formset = SpeciesCountFormset(
            instance=exhibit, initial=init_spec, prefix="species_formset"
        )
        animals_formset = AnimalCountFormset(
            instance=exhibit, initial=init_anim, prefix="animals_formset"
        )
        formset_order = get_formset_order(
            exhibit_species, exhibit_animals, species_formset, animals_formset
        )

    return render(
        request,
        "tally.html",
        {
            "exhibit": exhibit,
            "exhibit_animals": list(exhibit_animals),
            "exhibit_species": list(exhibit_species),
            "species_formset": species_formset,
            "animals_formset": animals_formset,
            "formset_order": formset_order,
        },
    )
