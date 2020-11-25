import logging
import os

import pandas as pd
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import Paginator
from django.db.models import Count, Prefetch, Q
from django.forms import formset_factory
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.generic import View
from PIL import Image

from zoo_checks.custom_storage import MediaStorage
from zoo_checks.ingest import TRACKS_REQ_COLS

from .forms import (
    AnimalCountForm,
    ExportForm,
    GroupCountForm,
    SpeciesCountForm,
    TallyDateForm,
    UploadFileForm,
)
from .helpers import (
    clean_df,
    get_init_anim_count_form,
    get_init_group_count_form,
    get_init_spec_count_form,
    qs_to_df,
    set_formset_order,
    today_time,
)
from .ingest import handle_upload, ingest_changesets
from .models import (
    Animal,
    AnimalCount,
    Enclosure,
    Group,
    GroupCount,
    Role,
    Species,
    SpeciesCount,
    User,
)

baselogger = logging.getLogger("zootable")
LOGGER = baselogger.getChild(__name__)

""" helpers that need models """


def get_accessible_enclosures(user: User):
    # superuser sees all enclosures
    if not user.is_superuser:
        enclosures = Enclosure.objects.filter(roles__in=user.roles.all()).distinct()
    else:
        enclosures = Enclosure.objects.all()

    return enclosures


def redirect_if_not_permitted(request: HttpRequest, enclosure: Enclosure) -> bool:
    """
    Returns
    -------

    True if user does not belong to enclosure or if not superuser

    False if user belongs to enclosure or is superuser
    """
    if request.user.is_superuser or request.user.roles.filter(enclosures=enclosure):
        return False

    messages.error(
        request, f"You do not have permissions to access enclosure {enclosure.name}"
    )
    LOGGER.error(
        (
            "Insufficient permissions to access enclosure"
            f" {enclosure.name}, user: {request.user.username}"
        )
    )
    return True


def enclosure_counts_to_dict(enclosures, animal_counts, group_counts) -> dict:
    """
    repackage enclosure counts into dict for template render
    dict order of enclosures is same as list/query order
    not using defaultdict(list) because django templates have difficulty with them
    """

    def create_counts_dict(enclosures, counts) -> dict:
        """Takes a list/queryset of counts and enclosures

        Returns a dictionary

        - keys: enclosures
        - values: list of counts belonging to the enclosure

        We do this (once) in order to be able to iterate over counts for each enclosure
        """
        counts_dict = {}
        for enc in enclosures:
            counts_dict[enc] = []
        [counts_dict[c.enclosure].append(c) for c in counts]
        return counts_dict

    def separate_conditions(counts) -> dict:
        """
        Arguments: Animal counts

        Returns: dictionary

        - keys: condition names
        - values: list of counts
        """
        cond_dict = {}
        for cond in AnimalCount.CONDITIONS:
            cond_dict[cond[1]] = []  # init to empty list
        [cond_dict[c.get_condition_display()].append(c) for c in counts]
        return cond_dict

    def separate_group_count_attributes(counts) -> dict:
        """
        Arguments: Group counts (typically w/in an enclosure)

        Returns: dictionary

        - keys: Seen, BAR, Needs Attn
        - values: sum of group counts within each key
        """
        count_dict = {}
        count_dict["Seen"] = sum([c.count_seen for c in counts])
        count_dict["BAR"] = sum([c.count_bar for c in counts])
        count_dict["Needs Attn"] = sum([c.needs_attn for c in counts])
        return count_dict

    enc_anim_ct_dict = create_counts_dict(enclosures, animal_counts)
    enc_group_ct_dict = create_counts_dict(enclosures, group_counts)
    counts_dict = {}
    for enc in enclosures:
        enc_anim_counts_sum = sum(
            [
                c.condition in [o_c[0] for o_c in AnimalCount.OBSERVED_CONDITIONS]
                for c in enc_anim_ct_dict[enc]
            ]
        )
        enc_group_counts_sum = sum(
            [c.count_seen + c.count_bar for c in enc_group_ct_dict[enc]]
        )
        total_groups = sum([g.population_total for g in enc.groups.all()])

        counts_dict[enc] = {
            "animal_count_total": enc_anim_counts_sum,
            "animal_conditions": separate_conditions(enc_anim_ct_dict[enc]),
            "group_counts": separate_group_count_attributes(enc_group_ct_dict[enc]),
            "group_count_total": enc_group_counts_sum,
            "total_animals": enc.animals.count(),
            "total_groups": total_groups,
        }

    return counts_dict


def get_selected_role(request: HttpRequest):
    # user requests view all
    if request.GET.get("view_all", False):
        request.session.pop("selected_role", None)
        return

    # might have a default selected role in session
    # or might be requesting a selected role
    else:
        # default selected role, gets cleared if you log out
        default_role = request.session.get("selected_role", None)

        # get role query param (default_role if not found)
        role_name = request.GET.get("role", default_role)

        if role_name is not None:
            try:
                request.session["selected_role"] = role_name
                return Role.objects.get(slug=role_name)
            except ObjectDoesNotExist:
                # role probably changed or bad query
                messages.info(request, "Selected role not found")
                request.session.pop("selected_role", None)
                LOGGER.info(f"role not found and removed from session: {role_name}")
                return
        else:
            return


""" views """


@login_required
# TODO: logins may not be sufficient - user a part of a group?
# TODO: add pagination
def home(request: HttpRequest):
    enclosures_query = get_accessible_enclosures(request.user)

    # only show enclosures that have active animals/groups
    query = Q(animals__active=True) | Q(groups__active=True)

    selected_role = get_selected_role(request)
    if selected_role is not None:
        query = query & Q(roles=selected_role)

    # prefetching in order to build up the info displayed for each enclosure
    groups_prefetch = Prefetch("groups", queryset=Group.objects.filter(active=True))
    animals_prefetch = Prefetch("animals", queryset=Animal.objects.filter(active=True))

    enclosures_query = (
        enclosures_query.prefetch_related(groups_prefetch, animals_prefetch)
        .filter(query)
        .distinct()
    )

    paginator = Paginator(enclosures_query, 10)
    page = request.GET.get("page", 1)
    enclosures = paginator.get_page(page)
    page_range = range(
        max(int(page) - 5, 1), min(int(page) + 5, paginator.num_pages) + 1
    )

    roles = request.user.roles.all()

    cts = Enclosure.all_counts(enclosures)
    enclosure_cts_dict = enclosure_counts_to_dict(enclosures, *cts)

    return render(
        request,
        "home.html",
        {
            "enclosures": enclosures,
            "cts_dict": enclosure_cts_dict,
            "page_range": page_range,
            "roles": roles,
            "selected_role": selected_role,
        },
    )


@login_required
def count(request: HttpRequest, enclosure_slug, year=None, month=None, day=None):
    enclosure = get_object_or_404(Enclosure, slug=enclosure_slug)

    if redirect_if_not_permitted(request, enclosure):
        return redirect("home")

    if None in [year, month, day]:
        dateday = today_time()
    else:
        dateday = timezone.make_aware(timezone.datetime(year, month, day))

    if dateday.date() == today_time().date():
        count_today = True
    else:
        count_today = False

    enclosure_animals = (
        enclosure.animals.filter(active=True)
        .order_by("species__common_name", "name", "accession_number")
        .select_related("species")
    )
    enclosure_groups = (
        enclosure.groups.filter(active=True)
        .order_by("species__common_name", "accession_number")
        .select_related("species")
    )

    enclosure_species = enclosure.species().order_by("common_name")

    SpeciesCountFormset = formset_factory(SpeciesCountForm, extra=0)

    GroupCountFormset = formset_factory(GroupCountForm, extra=0)

    AnimalCountFormset = formset_factory(AnimalCountForm, extra=0)

    species_counts_on_day = SpeciesCount.counts_on_day(
        enclosure_species, enclosure, day=dateday
    )
    init_spec = get_init_spec_count_form(
        enclosure, enclosure_species, species_counts_on_day
    )

    group_counts_on_day = GroupCount.counts_on_day(enclosure_groups, day=dateday)
    init_group = get_init_group_count_form(enclosure_groups, group_counts_on_day)

    animal_counts_on_day = AnimalCount.counts_on_day(enclosure_animals, day=dateday)
    init_anim = get_init_anim_count_form(enclosure_animals, animal_counts_on_day)

    # if this is a POST request we need to process the form data
    if request.method == "POST":
        # create a form instance and populate it with data from the request:
        species_formset = SpeciesCountFormset(
            request.POST, initial=init_spec, prefix="species_formset"
        )

        groups_formset = GroupCountFormset(
            request.POST, initial=init_group, prefix="groups_formset"
        )

        # TODO: Test to make sure we are editing the correct animal counts
        animals_formset = AnimalCountFormset(
            request.POST,
            initial=init_anim,
            prefix="animals_formset",
        )

        # check whether it's valid:
        if (
            species_formset.is_valid()
            and animals_formset.is_valid()
            and groups_formset.is_valid()
        ):

            def save_form_in_formset(form):
                # TODO: move this into model/(form?) and overwrite the save method
                if form.has_changed():
                    instance = form.save(commit=False)
                    instance.user = request.user

                    # if setting count for a diff day than today, set the date/datetime
                    if not count_today:
                        instance.datetimecounted = (
                            dateday
                            + timezone.timedelta(days=1)
                            - timezone.timedelta(seconds=1)
                        )
                        instance.datecounted = dateday.date()

                    instance.update_or_create_from_form()

            # process the data in form.cleaned_data as required
            for formset in (species_formset, animals_formset, groups_formset):
                for form in formset:
                    save_form_in_formset(form)

            messages.success(request, "Saved")
            LOGGER.info("Saved counts")
            return redirect(
                "count",
                enclosure_slug=enclosure.slug,
                year=dateday.year,
                month=dateday.month,
                day=dateday.day,
            )

        else:
            (
                formset_order,
                species_formset,
                groups_formset,
                animals_formset,
            ) = set_formset_order(
                enclosure,
                enclosure_species,
                enclosure_groups,
                enclosure_animals,
                species_formset,
                groups_formset,
                animals_formset,
                dateday,
            )

            messages.error(request, "There was an error processing the form")
            LOGGER.error("Error in processing the form")

    # if a GET (or any other method) we'll create a blank form
    else:
        species_formset = SpeciesCountFormset(
            initial=init_spec, prefix="species_formset"
        )
        groups_formset = GroupCountFormset(initial=init_group, prefix="groups_formset")
        animals_formset = AnimalCountFormset(
            initial=init_anim,
            prefix="animals_formset",
        )
        (
            formset_order,
            species_formset,
            groups_formset,
            animals_formset,
        ) = set_formset_order(
            enclosure,
            enclosure_species,
            enclosure_groups,
            enclosure_animals,
            species_formset,
            groups_formset,
            animals_formset,
            dateday,
        )

    dateform = TallyDateForm()
    return render(
        request,
        "tally.html",
        {
            "dateday": dateday,
            "enclosure": enclosure,
            "species_formset": species_formset,
            "groups_formset": groups_formset,
            "animals_formset": animals_formset,
            "formset_order": formset_order,
            "dateform": dateform,
            "conditions": AnimalCount.CONDITIONS,
        },
    )


@login_required
def tally_date_handler(request: HttpRequest, enclosure_slug):
    """Called from tally page to change date tally"""

    # if it's a POST: pull out the date from the cleaned data then send it to "count"
    if request.method == "POST":
        form = TallyDateForm(request.POST)
        if form.is_valid():
            target_date = form.cleaned_data["tally_date"]

            return redirect(
                "count",
                enclosure_slug=enclosure_slug,
                year=target_date.year,
                month=target_date.month,
                day=target_date.day,
            )
        else:
            messages.error(request, "Error in date entered")
            LOGGER.error("Error in date entered")

    # if it's a GET: just redirect back to count method
    return redirect("count", enclosure_slug=enclosure_slug)


@login_required
def edit_species_count(
    request: HttpRequest, species_slug, enclosure_slug, year, month, day
):
    species = get_object_or_404(Species, slug=species_slug)
    enclosure = get_object_or_404(Enclosure, slug=enclosure_slug)

    if redirect_if_not_permitted(request, enclosure):
        return redirect("home")

    dateday = timezone.make_aware(timezone.datetime(year, month, day))

    count = species.count_on_day(enclosure, day=dateday)
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
                if dateday.date() == timezone.localdate():
                    obj.datetimecounted = timezone.localtime()
                else:
                    obj.datetimecounted = (
                        dateday
                        + timezone.timedelta(days=1)
                        - timezone.timedelta(seconds=1)
                    )
                obj.datecounted = dateday
                obj.update_or_create_from_form()
            return redirect("count", enclosure_slug=enclosure.slug)
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
def edit_group_count(request: HttpRequest, group, year, month, day):
    group = get_object_or_404(
        Group.objects.select_related("enclosure", "species"), accession_number=group
    )
    enclosure = group.enclosure

    if redirect_if_not_permitted(request, enclosure):
        return redirect("home")

    dateday = timezone.make_aware(timezone.datetime(year, month, day))
    count = group.count_on_day(day=dateday)
    init_form = {
        "count_seen": 0 if count is None else count.count_seen,
        "count_bar": 0 if count is None else count.count_bar,
        "comment": "" if count is None else count.comment,
        "count_total": group.population_total,
        "group": group,
        "enclosure": enclosure,
        "needs_attn": False if count is None else count.needs_attn,
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
                if dateday.date() == timezone.localdate():
                    obj.datetimecounted = timezone.localtime()
                else:
                    obj.datetimecounted = (
                        dateday
                        + timezone.timedelta(days=1)
                        - timezone.timedelta(seconds=1)
                    )
                obj.datecounted = dateday
                obj.update_or_create_from_form()
            return redirect("count", enclosure_slug=enclosure.slug)
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
def animal_counts(request: HttpRequest, animal):
    animal_obj = get_object_or_404(
        Animal.objects.select_related("enclosure", "species"), accession_number=animal
    )
    enclosure = animal_obj.enclosure

    if redirect_if_not_permitted(request, enclosure):
        return redirect("home")

    animal_counts_query = (
        AnimalCount.objects.filter(animal=animal_obj)
        .select_related("user")
        .order_by("-datetimecounted", "-id")
    )

    paginator = Paginator(animal_counts_query, 10)
    page = request.GET.get("page", 1)
    animal_counts_records = paginator.get_page(page)
    page_range = range(
        max(int(page) - 5, 1), min(int(page) + 5, paginator.num_pages) + 1
    )

    # db counts each condition type
    query_data = (
        animal_counts_query.values("condition")
        .order_by("condition")
        .annotate(num=Count("condition"))
    )

    # generating the data and labels
    cond_slugs = [count["condition"] for count in query_data]
    chart_data = []
    for cond_slug, _ in AnimalCount.CONDITIONS:
        if cond_slug in cond_slugs:
            chart_data.append(query_data.get(condition=cond_slug)["num"])
        else:
            chart_data.append(0)
    # gets the full name of the condition (from second item in tuple)
    chart_labels = [c[1] for c in AnimalCount.CONDITIONS]

    return render(
        request,
        "animal_counts.html",
        {
            "animal": animal_obj,
            "enclosure": enclosure,
            "animal_counts": animal_counts_records,
            "chart_data": chart_data,
            "chart_labels": chart_labels,
            "page_range": page_range,
        },
    )


@login_required
def group_counts(request: HttpRequest, group):
    group = get_object_or_404(
        Group.objects.select_related("enclosure", "species"), accession_number=group
    )
    enclosure = group.enclosure

    if redirect_if_not_permitted(request, enclosure):
        return redirect("home")

    group_counts_query = (
        GroupCount.objects.filter(group=group)
        .select_related("user")
        .order_by("-datetimecounted", "-id")
    )

    paginator = Paginator(group_counts_query, 10)
    page = request.GET.get("page", 1)
    group_counts_records = paginator.get_page(page)
    page_range = range(
        max(int(page) - 5, 1), min(int(page) + 5, paginator.num_pages) + 1
    )

    chart_labels_line = [
        d.strftime("%m-%d-%Y")
        for d in list(group_counts_query.values_list("datecounted", flat=True)[:100])
    ]
    chart_data_line_total = list(
        group_counts_query.values_list("count_total", flat=True)[:100]
    )

    chart_data_line_seen = list(
        group_counts_query.values_list("count_seen", flat=True)[:100]
    )
    chart_data_line_bar = list(
        group_counts_query.values_list("count_bar", flat=True)[:100]
    )

    # for the pie chart (last 100)
    sum_counts = chart_data_line_seen
    chart_labels_pie = sorted(set(sum_counts))
    chart_data_pie = [sum_counts.count(s) for s in chart_labels_pie]

    return render(
        request,
        "group_counts.html",
        {
            "group": group,
            "enclosure": enclosure,
            "counts": group_counts_records,
            "chart_data_line_total": chart_data_line_total,
            "chart_data_line_seen": chart_data_line_seen,
            "chart_data_line_bar": chart_data_line_bar,
            "chart_labels_line": chart_labels_line,
            "chart_data_pie": chart_data_pie,
            "chart_labels_pie": chart_labels_pie,
            "page_range": page_range,
        },
    )


@login_required
def species_counts(request: HttpRequest, species_slug, enclosure_slug):
    obj = get_object_or_404(Species, slug=species_slug)
    enclosure = get_object_or_404(Enclosure, slug=enclosure_slug)

    if redirect_if_not_permitted(request, enclosure):
        return redirect("home")

    counts_query = (
        SpeciesCount.objects.filter(species=obj, enclosure=enclosure)
        .select_related("user")
        .order_by("-datetimecounted", "-id")
    )

    paginator = Paginator(counts_query, 10)
    page = request.GET.get("page", 1)
    counts_records = paginator.get_page(page)
    page_range = range(
        max(int(page) - 5, 1), min(int(page) + 5, paginator.num_pages) + 1
    )

    chart_labels_line = [
        d.strftime("%m-%d-%Y")
        for d in list(
            counts_query.values_list("datecounted", flat=True).order_by(
                "datetimecounted"
            )[:100]
        )
    ]
    chart_data_line_total = list(
        counts_query.values_list("count", flat=True).order_by("datetimecounted")[:100]
    )

    # for the pie chart (last 100)
    sum_counts = list(counts_query.values_list("count", flat=True)[:100])
    chart_labels_pie = sorted(set(sum_counts))
    chart_data_pie = [sum_counts.count(s) for s in chart_labels_pie]

    return render(
        request,
        "species_counts.html",
        {
            "obj": obj,
            "enclosure": enclosure,
            "counts": counts_records,
            "chart_data_line_total": chart_data_line_total,
            "chart_labels_line": chart_labels_line,
            "chart_data_pie": chart_data_pie,
            "chart_labels_pie": chart_labels_pie,
            "page_range": page_range,
        },
    )


@login_required
def edit_animal_count(request: HttpRequest, animal, year, month, day):
    animal = get_object_or_404(
        Animal.objects.select_related("enclosure", "species"), accession_number=animal
    )
    enclosure = animal.enclosure

    if redirect_if_not_permitted(request, enclosure):
        return redirect("home")

    dateday = timezone.make_aware(timezone.datetime(year, month, day))
    count = animal.count_on_day(day=dateday)
    init_form = {
        "condition": "" if count is None else count.condition,
        "comment": "" if count is None else count.comment,
        "animal": animal,
        "enclosure": enclosure,
    }

    if request.method == "POST":
        form = AnimalCountForm(request.POST, initial=init_form)
        if form.is_valid():
            # save the data
            if form.has_changed():
                obj = form.save(commit=False)
                obj.user = request.user
                # force insert because otherwise it always updated
                obj.id = None
                if dateday.date() == timezone.localdate():
                    obj.datetimecounted = timezone.localtime()
                else:
                    obj.datetimecounted = (
                        dateday
                        + timezone.timedelta(days=1)
                        - timezone.timedelta(seconds=1)
                    )
                obj.datecounted = dateday
                obj.update_or_create_from_form()
            return redirect("count", enclosure_slug=enclosure.slug)
    else:
        form = AnimalCountForm(initial=init_form)

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


@user_passes_test(lambda u: u.is_staff, redirect_field_name=None)
def ingest_form(request: HttpRequest):
    """ For for submitting excel files for ingest """
    if request.method == "POST":
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            # where we compute changes
            try:
                changesets = handle_upload(request.FILES["file"])
            except Exception as e:
                messages.error(request, e)
                LOGGER.error("Error during data ingest")
                return redirect("ingest_form")

            request.session["changesets"] = changesets
            request.session["upload_file"] = str(request.FILES["file"])

            # redirect to a confirmation page
            return redirect("confirm_upload")

    else:
        form = UploadFileForm()
        request.session.pop("changesets", None)
        request.session.pop("upload_file", None)

    return render(
        request, "upload_form.html", {"form": form, "req_cols": TRACKS_REQ_COLS}
    )


@user_passes_test(lambda u: u.is_staff, redirect_field_name=None)
def confirm_upload(request: HttpRequest):
    """ after ingest form submit, show confirmation page before writing to db """
    changesets = request.session.get("changesets")
    upload_file = request.session.get("upload_file")

    if upload_file is None or changesets is None:
        return redirect("ingest_form")

    # TODO: create a form w/ checkboxes for each change
    if request.method == "POST":
        # user clicked submit button on confirm_upload

        # call functions in ingest.py to save the changes
        try:
            ingest_changesets(changesets)
        except Exception as e:
            messages.error(request, e)
            LOGGER.error("error during data upload")
            return redirect("ingest_form")

        # clearing the changesets
        request.session.pop("changesets", None)
        request.session.pop("upload_file", None)

        messages.success(request, "Saved")
        LOGGER.info("Uploaded data")

        return redirect("home")

    return render(
        request,
        "confirm_upload.html",
        {"changesets": changesets, "upload_file": upload_file},
    )


@login_required
def export(request: HttpRequest):
    """ export counts to excel for user download w/ time range """
    accessible_enclosures = get_accessible_enclosures(request.user)

    if request.method == "POST":
        form = ExportForm(request.POST)
        # initialize the selected enclosures queryset
        form.fields["selected_enclosures"].queryset = accessible_enclosures
        if form.is_valid():
            selected_enclosures = form.cleaned_data["selected_enclosures"]
            # limit to only accessible enclosures
            # TODO: test to check we cannot export data we aren't allowed to access
            enclosures = accessible_enclosures & selected_enclosures

            start_date = form.cleaned_data["start_date"]
            end_date = form.cleaned_data["end_date"]

            # TODO: abstract to a function that returns this for any model?
            animal_counts = (
                AnimalCount.objects.filter(
                    enclosure__in=enclosures,
                    datecounted__gte=start_date,
                    datecounted__lte=end_date,
                )
                .order_by("datecounted", "animal_id", "datetimecounted")
                .distinct("datecounted", "animal_id")
            )
            group_counts = (
                GroupCount.objects.filter(
                    enclosure__in=enclosures,
                    datecounted__gte=start_date,
                    datecounted__lte=end_date,
                )
                .order_by("datecounted", "group_id", "datetimecounted")
                .distinct("datecounted", "group_id")
            )
            species_counts = (
                SpeciesCount.objects.filter(
                    enclosure__in=enclosures,
                    datecounted__gte=start_date,
                    datecounted__lte=end_date,
                )
                .order_by("datecounted", "species_id", "datetimecounted")
                .distinct("datecounted", "species_id")
            )

            # convert to pandas dataframe
            animal_counts_df = qs_to_df(animal_counts, AnimalCount._meta.fields)
            group_counts_df = qs_to_df(group_counts, GroupCount._meta.fields)
            species_counts_df = qs_to_df(species_counts, SpeciesCount._meta.fields)

            # merge the dfs together
            df_merge = pd.concat(
                [animal_counts_df, group_counts_df, species_counts_df],
                ignore_index=True,
                sort=False,
            )

            if df_merge.empty:
                form.add_error(None, "No data in range")
                extra = {
                    "enclosures": list(enclosures.values("id", "name")),
                    "start_date": start_date.strftime("%m/%d/%Y"),
                    "end_date": end_date.strftime("%m/%d/%Y"),
                }
                LOGGER.error(f"no data to export for enclosures", extra=extra)
                return render(request, "export.html", {"form": form})

            df_merge_clean = clean_df(df_merge)

            # create response object to save the data into
            response = HttpResponse(
                content_type=(
                    "application/vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet"
                )
            )

            enclosure_names = "_".join((enc.slug for enc in enclosures))
            start_date_str = start_date.strftime("%Y%m%d")
            end_date_str = end_date.strftime("%Y%m%d")
            response["Content-Disposition"] = (
                "attachment; "
                'filename="zootable_export_'
                f'{enclosure_names}_{start_date_str}_{end_date_str}.xlsx"'
            )

            # create xlsx object and put it into the response using pandas
            with pd.ExcelWriter(response, engine="xlsxwriter") as writer:
                df_merge_clean.to_excel(writer, sheet_name="Sheet1", index=False)

            # TODO: redirect to home w/ javascript serve xlsx file from that page
            # send it to the user
            return response

    else:
        form = ExportForm()
        # initialize the selected enclosures queryset to only ones accessible
        form.fields["selected_enclosures"].queryset = accessible_enclosures

    return render(request, "export.html", {"form": form})


class PhotoUploadView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        file_obj = request.FILES.get("file", "")

        try:
            Image.open(file_obj)
        except Exception:
            # return error message about attempt at image load
            return JsonResponse(
                {
                    "message": "Error opening image"
                },
                status=400,
            )

        # do your validation here e.g. file size/type check


        # organize a path for the file in bucket
        file_directory_within_bucket = "user_upload_files/{username}".format(
            username=request.user
        )

        # synthesize a full file path; note that we included the filename
        file_path_within_bucket = os.path.join(
            file_directory_within_bucket, file_obj.name
        )

        media_storage = MediaStorage()

        if not media_storage.exists(
            file_path_within_bucket
        ):  # avoid overwriting existing file
            media_storage.save(file_path_within_bucket, file_obj)
            file_url = media_storage.url(file_path_within_bucket)

            return JsonResponse(
                {
                    "message": "OK",
                    "fileUrl": file_url,
                }
            )
        else:
            return JsonResponse(
                {
                    "message": "Error: file {filename} already exists at {file_directory} in bucket {bucket_name}".format(
                        filename=file_obj.name,
                        file_directory=file_directory_within_bucket,
                        bucket_name=media_storage.bucket_name,
                    ),
                },
                status=400,
            )
