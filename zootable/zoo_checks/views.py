from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import ObjectDoesNotExist
from django.forms import inlineformset_factory
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import AnimalCountForm, GroupCountForm, SpeciesCountForm, UploadFileForm
from .ingest import handle_ingest
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


def set_formset_order(
    enclosure,
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
        formset_dict[spec.id]["prior_counts"] = spec.prior_counts(enclosure)

        try:
            spec_group = enclosure_groups.get(species=spec)
            groups_formset.forms[group_count].initial.update(
                groups_formset.initial_extra[group_count]
            )
            group_form = groups_formset[group_count]
            # ! hack: figure out how to override the form init function?
            group_count_types = "male", "female", "unknown"
            for gctype in group_count_types:
                group_form.fields[f"count_{gctype}"].widget.attrs.update(
                    {"max": eval(f"spec_group.population_{gctype}")}
                )
            group_count += 1
        except ObjectDoesNotExist:
            group_form = None
            spec_group = None
        formset_dict[spec.id]["group_form"] = group_form
        formset_dict[spec.id]["group"] = spec_group

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


def get_init_spec_count_form(enclosure, enclosure_species):
    # TODO: counts should default to maximum (across users) for the day
    # TODO: eliminate for loop

    # * note: this unpacks the queryset into a list and should be avoided
    init_spec = []
    for sp in enclosure_species:
        init_spec.append({"species": sp, "count": sp.current_count(enclosure)["count"]})

    return init_spec


def get_init_group_count_form(enclosure_groups):
    init_group = []
    for group in enclosure_groups:
        group_count = group.current_count()
        init_group.append(
            {
                "group": group,
                "count_male": group_count["m_count"],
                "count_female": group_count["f_count"],
                "count_unknown": group_count["u_count"],
            }
        )

    return init_group


def get_init_anim_count_form(enclosure_animals):
    # TODO: condition should default to median? condition (across users) for the day

    # make db query to get conditions for all the animals in enclosure
    init_anim = [
        {"animal": anim, "condition": anim.current_condition}
        for anim in enclosure_animals
    ]

    return init_anim


@login_required
def count(request, enclosure_name):
    enclosure = get_object_or_404(Enclosure, name=enclosure_name)

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
    init_spec = get_init_spec_count_form(enclosure, enclosure_species)
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
            form_kwargs={"is_staff": request.user.is_staff},
        )

        # needed in the case the form wasn't submitted properly and we have to re-render the form
        # and for setting initial values
        formset_order, species_formset, groups_formset, animals_formset = set_formset_order(
            enclosure,
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
                    obj.datecounted = timezone.now()
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
            instance=enclosure,
            initial=init_anim,
            prefix="animals_formset",
            form_kwargs={"is_staff": request.user.is_staff},
        )
        formset_order, species_formset, groups_formset, animals_formset = set_formset_order(
            enclosure,
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


@login_required
def edit_species_count(request, species, enclosure, year, month, day):
    species = get_object_or_404(Species, common_name=species)
    enclosure = get_object_or_404(Enclosure, name=enclosure)

    dateday = timezone.make_aware(timezone.datetime(year, month, day))

    count = species.get_count_day(enclosure, day=dateday)
    init_form = {
        "count": 0 if count is None else count.count,
        "species": species,
        "enclosure": enclosure,
    }

    if request.method == "POST":
        form = SpeciesCountForm(request.POST, init_form)
        if form.is_valid():
            # save the data
            if form.has_changed():
                obj = form.save(commit=False)
                obj.user = request.user
                # force insert because otherwise it always updated
                obj.id = None
                obj.datecounted = (
                    dateday + timezone.timedelta(days=1) - timezone.timedelta(seconds=1)
                )
                obj.save()
            return redirect("count", enclosure_name=enclosure.name)
    else:
        form = SpeciesCountForm(initial=init_form)

    return render(
        request,
        "edit_species_count.html",
        {
            "form": form,
            "count": count,
            "species": species,
            "enclosure": enclosure,
            "dateday": dateday,
        },
    )


@login_required
def edit_group_count(request, group, year, month, day):
    group = get_object_or_404(Group, accession_number=group)
    enclosure = group.enclosure

    dateday = timezone.make_aware(timezone.datetime(year, month, day))
    count = group.get_count_day(day=dateday)
    init_form = {
        "count_male": 0 if count is None else count["m_count"],
        "count_female": 0 if count is None else count["f_count"],
        "count_unknown": 0 if count is None else count["u_count"],
        "group": group,
        "enclosure": enclosure,
    }

    if request.method == "POST":
        form = GroupCountForm(request.POST, initial=init_form)
        if form.is_valid():
            # save the data
            if form.has_changed():
                obj = form.save(commit=False)
                obj.user = request.user
                # force insert because otherwise it always updated
                obj.id = None
                obj.datecounted = (
                    dateday + timezone.timedelta(days=1) - timezone.timedelta(seconds=1)
                )
                obj.save()
            return redirect("count", enclosure_name=enclosure.name)
    else:
        form = GroupCountForm(initial=init_form)

    return render(
        request,
        "edit_group_count.html",
        {
            "form": form,
            "count": count,
            "group": group,
            "enclosure": enclosure,
            "dateday": dateday,
        },
    )


@login_required
def edit_animal_count(request, animal, year, month, day):
    animal = get_object_or_404(Animal, accession_number=animal)
    enclosure = animal.enclosure

    dateday = timezone.make_aware(timezone.datetime(year, month, day))
    count = animal.count_on_day(day=dateday)
    init_form = {
        "condition": "" if count is None else count["condition"],
        "animal": animal,
        "enclosure": enclosure,
    }

    if request.method == "POST":
        form = AnimalCountForm(
            request.POST, initial=init_form, is_staff=request.user.is_staff
        )
        if form.is_valid():
            # save the data
            if form.has_changed():
                obj = form.save(commit=False)
                obj.user = request.user
                # force insert because otherwise it always updated
                obj.id = None
                obj.datecounted = (
                    dateday + timezone.timedelta(days=1) - timezone.timedelta(seconds=1)
                )
                obj.save()
            return redirect("count", enclosure_name=enclosure.name)
    else:
        form = AnimalCountForm(initial=init_form, is_staff=request.user.is_staff)

    return render(
        request,
        "edit_animal_count.html",
        {
            "form": form,
            "count": count,
            "animal": animal,
            "enclosure": enclosure,
            "dateday": dateday,
        },
    )


@user_passes_test(lambda u: u.is_superuser, redirect_field_name=None)
def ingest_form(request):
    if request.method == "POST":
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            # where we compute changes
            changesets = handle_ingest(request.FILES["file"])
            request.session["changesets"] = changesets
            request.session["upload_file"] = str(request.FILES["file"])

            # TODO: if no changesets, then we notify and redirect back to home

            # redirect to a confirmation page
            return redirect("confirm_upload")

    else:
        form = UploadFileForm()
        del request.session["changesets"]
        del request.session["upload_file"]

    return render(request, "upload_form.html", {"form": form})


@user_passes_test(lambda u: u.is_superuser, redirect_field_name=None)
def confirm_upload(request):
    changesets = request.session.get("changesets")
    upload_file = request.session.get("upload_file")

    return render(
        request,
        "confirm_upload.html",
        {"changesets": changesets, "upload_file": upload_file},
    )

