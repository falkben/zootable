from datetime import date, timedelta

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
    GroupCountForm,
    SpeciesCountForm,
)
from .models import (
    Animal,
    AnimalCount,
    Enclosure,
    Group,
    GroupCount,
    Species,
    SpeciesCount,
)


@login_required
# TODO: logins may not be sufficient - user a part of a group?
def home(request):
    enclosures = Enclosure.objects.filter(users=request.user)

    return render(request, "home.html", {"enclosures": enclosures})


def get_formset_order(
    enclosure_species,
    enclosure_groups,
    enclosure_animals,
    species_formset,
    groups_formset,
    animals_formset,
):
    """Creates an order to display the formsets
    """

    # to set the order
    formset_dict = {}
    anim_total = 0
    group_count = 0
    for ind, spec in enumerate(enclosure_species):
        # TODO: separate spec/group/animals parts out into separate functions
        # each species is it's own dict, using id because that's known unique
        formset_dict[spec.id] = {}

        # apparently required because setting initial in inline_formset doesn't seem to do the trick
        species_formset.forms[ind].initial.update(species_formset.initial_extra[ind])
        formset_dict[spec.id]["species"] = spec
        formset_dict[spec.id]["formset"] = species_formset[ind]

        try:
            spec_group = enclosure_groups.get(species=spec)
            groups_formset.forms[group_count].initial.update(
                groups_formset.initial_extra[group_count]
            )
            group_form = groups_formset[group_count]
            group_count += 1
        except ObjectDoesNotExist:
            group_form = None
        formset_dict[spec.id]["group_form"] = group_form

        spec_anim_queryset = enclosure_animals.filter(species=spec)
        # creating an index into the animals_formset
        spec_anim_index = list(
            range(anim_total, spec_anim_queryset.count() + anim_total)
        )
        # this updates the animal formset with initial values
        [
            animals_formset[i].initial.update(animals_formset.initial_extra[i])
            for i in spec_anim_index
        ]
        formset_dict[spec.id]["animalformset_index"] = zip(
            spec_anim_queryset, [animals_formset[i] for i in spec_anim_index]
        )
        # updating total animals
        anim_total += spec_anim_queryset.count()

    return formset_dict, species_formset, groups_formset, animals_formset


def species_day_counts(enclosure_species, day=date.today()):
    day_counts = SpeciesCount.objects.filter(species__in=enclosure_species).filter(
        datecounted__gte=day, datecounted__lt=day + timedelta(days=1)
    )

    return day_counts


def get_init_spec_count_form(enclosure_species):
    # TODO: counts should default to maximum (across users) for the day
    # TODO: eliminate for loop

    # make one database query to get the species counts on a given day
    species_counts_today = species_day_counts(enclosure_species)

    # * note: this unpacks the queryset into a list and should be avoided
    init_spec = []
    for sp in enclosure_species:
        sp_count = 0
        sp_count_query = species_counts_today.filter(species=sp)
        if sp_count_query.count() > 0:
            # in case there is more than one this takes the max
            sp_count = sp_count_query.aggregate(Max("count"))["count__max"]
        init_spec.append({"species": sp, "count": sp_count})

    return init_spec


def groups_day_counts(groups, day=date.today()):
    groups_counts = GroupCount.objects.filter(group__in=groups).filter(
        datecounted__gte=day, datecounted__lt=day + timedelta(days=1)
    )

    return groups_counts


def get_init_group_count_form(enclosure_groups):

    # make one database query to get the species counts on a given day
    groups_counts_today = groups_day_counts(enclosure_groups)

    init_group = []
    for group in enclosure_groups:
        gp_count_query = groups_counts_today.filter(group=group)
        m_count = f_count = u_count = 0
        if gp_count_query.count() > 0:
            # in case there is more than one this takes the max
            m_count = gp_count_query.aggregate(Max("count_male"))["count_male__max"]
            f_count = gp_count_query.aggregate(Max("count_female"))["count_female__max"]
            u_count = gp_count_query.aggregate(Max("count_unknown"))[
                "count_unknown__max"
            ]
        init_group.append(
            {
                "group": group,
                "count_male": m_count,
                "count_female": f_count,
                "count_unknown": u_count,
            }
        )

    return init_group


def animal_day_conditions(animals, day=date.today()):
    # TODO: this could be a custom queryset on AnimalCount
    animals_conditions_today = AnimalCount.objects.filter(animal__in=animals).filter(
        datecounted__gte=day, datecounted__lt=day + timedelta(days=1)
    )

    return animals_conditions_today


def get_init_anim_count_form(enclosure_animals):
    # TODO: condition should default to median? condition (across users) for the day

    # make db query to get conditions for all the animals in enclosure
    animals_conditions_today = animal_day_conditions(enclosure_animals)

    init_anim = [{"animal": obj} for obj in enclosure_animals]

    anims_conds = []
    for anim in enclosure_animals:
        # * there can be more than one condition per animal
        try:
            cond = (
                animals_conditions_today.filter(animal=anim)
                .latest("datecounted")
                .condition
            )
        except ObjectDoesNotExist:
            cond = ""
        anims_conds.append(cond)

    [init.update({"condition": c}) for init, c in zip(init_anim, anims_conds)]

    return init_anim


@login_required
def count(request, enclosure_id):
    enclosure = get_object_or_404(Enclosure, pk=enclosure_id)

    enclosure_animals = enclosure.animals.all().order_by("species__common_name", "name")
    enclosure_groups = enclosure.groups.all().order_by("species__common_name")

    enclosure_species = enclosure.species().order_by("common_name")

    SpeciesCountFormset = inlineformset_factory(
        Enclosure,
        SpeciesCount,
        form=SpeciesCountForm,
        # formset=BaseSpeciesCountFormset,
        extra=enclosure_species.count(),
        max_num=enclosure_species.count(),
        can_order=False,
        can_delete=False,
    )

    GroupCountFormset = inlineformset_factory(
        Enclosure,
        GroupCount,
        form=GroupCountForm,
        # formset=BaseSpeciesCountFormset,
        extra=enclosure_groups.count(),
        max_num=enclosure_groups.count(),
        can_order=False,
        can_delete=False,
    )

    AnimalCountFormset = inlineformset_factory(
        Enclosure,
        AnimalCount,
        form=AnimalCountForm,
        # formset=BaseAnimalCountFormset,
        extra=enclosure_animals.count(),
        max_num=enclosure_animals.count(),
        can_order=False,
        can_delete=False,
    )

    # TODO: initial values aren't being passed into the formset correctly by default, figure out how to do it without manually editing each form
    init_spec = get_init_spec_count_form(enclosure_species)
    init_group = get_init_group_count_form(enclosure_groups)
    init_anim = get_init_anim_count_form(enclosure_animals)

    # if this is a POST request we need to process the form data
    if request.method == "POST":
        # create a form instance and populate it with data from the request:
        species_formset = SpeciesCountFormset(
            request.POST,
            instance=enclosure,
            initial=init_spec,
            prefix="species_formset",
        )

        groups_formset = GroupCountFormset(
            request.POST,
            instance=enclosure,
            initial=init_group,
            prefix="groups_formset",
        )

        # TODO: Test to make sure we are editing the correct animal counts
        animals_formset = AnimalCountFormset(
            request.POST,
            instance=enclosure,
            initial=init_anim,
            prefix="animals_formset",
        )

        # needed in the case the form wasn't submitted properly and we have to re-render the form
        # and for setting initial values
        formset_order, species_formset, groups_formset, animals_formset = get_formset_order(
            enclosure_species,
            enclosure_groups,
            enclosure_animals,
            species_formset,
            groups_formset,
            animals_formset,
        )

        # ! hack because empty permitted is occassionally set to False!
        for form in animals_formset:
            form.empty_permitted = True

        # check whether it's valid:
        if (
            species_formset.is_valid()
            and animals_formset.is_valid()
            and groups_formset.is_valid()
        ):

            def save_form_obj(form):
                # TODO: move this into model/(form?) and overwrite the save method
                # TODO: save should be update_or_create w/ user and date (so each user has MAX 1 count/day/spec)
                if form.has_changed():
                    obj = form.save(commit=False)
                    obj.user = request.user
                    # force insert because otherwise it always updated
                    obj.id = None
                    obj.save()

            # process the data in form.cleaned_data as required
            for form in species_formset:
                save_form_obj(form)

            for form in animals_formset:
                save_form_obj(form)

            for form in groups_formset:
                save_form_obj(form)

            return HttpResponseRedirect("/")

    # if a GET (or any other method) we'll create a blank form
    else:
        species_formset = SpeciesCountFormset(
            instance=enclosure, initial=init_spec, prefix="species_formset"
        )
        groups_formset = GroupCountFormset(
            instance=enclosure, initial=init_group, prefix="groups_formset"
        )
        animals_formset = AnimalCountFormset(
            instance=enclosure, initial=init_anim, prefix="animals_formset"
        )
        formset_order, species_formset, groups_formset, animals_formset = get_formset_order(
            enclosure_species,
            enclosure_groups,
            enclosure_animals,
            species_formset,
            groups_formset,
            animals_formset,
        )

    return render(
        request,
        "tally.html",
        {
            "enclosure": enclosure,
            "species_formset": species_formset,
            "groups_formset": groups_formset,
            "animals_formset": animals_formset,
            "formset_order": formset_order,
        },
    )
