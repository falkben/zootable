from datetime import date

from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Max
from django.forms import inlineformset_factory
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render

from .forms import (
    AnimalCountForm,
    BaseAnimalCountFormset,
    BaseSpeciesCountFormset,
    SpeciesCountForm,
)
from .models import (
    Animal,
    AnimalCount,
    Exhibit,
    Group,
    GroupCount,
    Species,
    SpeciesCount,
)


@login_required
# TODO: logins may not be sufficient - user a part of a group?
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
        # should be ordered by name here already, but just in case...
        spec_anim_list = exhibit_animals.filter(species=spec).order_by("name")
        spec_anim_index = list(range(anim_total, spec_anim_list.count() + anim_total))
        anim_total += spec_anim_list.count()

        species_formset.forms[ind].initial.update(species_formset.initial_extra[ind])

        # store in dictionary, using id because that's known unique
        formset_dict[spec.id] = {}
        formset_dict[spec.id]["species"] = spec
        formset_dict[spec.id]["formset"] = species_formset[ind]

        # this updates the animal formset with initial values
        [
            animals_formset[i].initial.update(animals_formset.initial_extra[i])
            for i in spec_anim_index
        ]
        formset_dict[spec.id]["animalformset_index"] = zip(
            spec_anim_list, [animals_formset[i] for i in spec_anim_index]
        )

    return formset_dict, species_formset, animals_formset


def get_init_spec_count_form(exhibit, exhibit_species, species_counts_today):
    # TODO: counts should default to maximum (across users) for the day
    # TODO: eliminate for loop

    # this loop is to create the list of counts for the species *in order of exhibit_species*
    init_sp_counts = [0] * exhibit_species.count()
    # * note: this unpacks the queryset into a list and should be avoideds
    for i, sp in enumerate(exhibit_species):
        sp_count = species_counts_today.filter(species=sp)
        if sp_count.count() > 0:
            # should only be one... but in case there is more than one this takes the max
            init_sp_counts[i] = sp_count.aggregate(Max("count"))["count__max"]

    # sets the initial dict
    init_spec = [
        {"species": obj, "count": c} for obj, c in zip(exhibit_species, init_sp_counts)
    ]
    return init_spec


def get_init_anim_count_form(exhibit, exhibit_animals, animal_conditions_today):
    # TODO: condition should default to median? condition (across users) for the day
    init_anim = [{"animal": obj} for obj in exhibit_animals]

    anims_conds = []
    for anim in exhibit_animals:
        # * there can be more than one condition per animal
        conds = animal_conditions_today.filter(animal=anim)
        if conds.exists():
            # getting the conditions
            cond_vals = conds.values_list("condition", flat=True)
            # creates a condition "order"
            cv_order = [
                AnimalCount.SEEN,
                AnimalCount.NEEDSATTENTION,
                AnimalCount.BAR,
                AnimalCount.MISSING,
            ]
            # get's the "worst" condition (highest index in list)
            cond = cv_order[max([cv_order.index(cv) for cv in cond_vals])]
        else:
            cond = ""
        anims_conds.append(cond)

    [init.update({"condition": c}) for init, c in zip(init_anim, anims_conds)]

    return init_anim


def get_exhibit_species(animals, groups):
    """Combines all the animal species and group species together
    Given queryset of animals and groups returns a "distinct" queryset of species
    """

    animal_species = Species.objects.filter(animal__in=animals)
    group_species = Species.objects.filter(group__in=groups)

    return (animal_species | group_species).distinct()


@login_required
def count(request, exhibit_id):
    exhibit = get_object_or_404(Exhibit, pk=exhibit_id)

    exhibit_animals = exhibit.animals.all().order_by("species__common_name", "name")
    exhibit_groups = exhibit.groups.all().order_by("species__common_name", "name")

    exhibit_species = get_exhibit_species(exhibit_animals, exhibit_groups).order_by(
        "common_name"
    )

    species_counts_today = SpeciesCount.objects.filter(
        species__in=exhibit_species
    ).filter(datecounted=date.today())
    animal_conditions_today = AnimalCount.objects.filter(
        animal__in=exhibit_animals
    ).filter(datecounted=date.today())

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

    # TODO: initial values aren't being passed into the formset correctly by default, figure out how to do it without manually editing each form
    init_spec = get_init_spec_count_form(exhibit, exhibit_species, species_counts_today)
    init_anim = get_init_anim_count_form(
        exhibit, exhibit_animals, animal_conditions_today
    )

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

        # needed in the case the form wasn't submitted properly and we have to re-render the form
        formset_order, species_formset, animals_formset = get_formset_order(
            exhibit_species, exhibit_animals, species_formset, animals_formset
        )

        # ! a hack because empty permitted is occassionally set to False!
        for form in animals_formset:
            form.empty_permitted = True

        # check whether it's valid:
        if species_formset.is_valid() and animals_formset.is_valid():
            # process the data in form.cleaned_data as required
            for form in species_formset:
                if form.has_changed():
                    # TODO: move this into mmodel/(form?) and overwrite the save method
                    spec = form.save(commit=False)
                    spec.user = request.user

                    # forcing a new object stored to database on each save because otherwise it always updated
                    spec.id = None
                    spec.save()

            for form in animals_formset:
                if form.has_changed():
                    anim = form.save(commit=False)
                    anim.user = request.user
                    # forcing a new object stored to database on each save because otherwise it always updated
                    anim.id = None
                    anim.save()

            # redirect to a new URL:
            return HttpResponseRedirect("/")

    # if a GET (or any other method) we'll create a blank form
    else:
        species_formset = SpeciesCountFormset(
            instance=exhibit, initial=init_spec, prefix="species_formset"
        )
        animals_formset = AnimalCountFormset(
            instance=exhibit, initial=init_anim, prefix="animals_formset"
        )
        formset_order, species_formset, animals_formset = get_formset_order(
            exhibit_species, exhibit_animals, species_formset, animals_formset
        )

    return render(
        request,
        "tally.html",
        {
            "exhibit": exhibit,
            "species_formset": species_formset,
            "animals_formset": animals_formset,
            "formset_order": formset_order,
        },
    )
