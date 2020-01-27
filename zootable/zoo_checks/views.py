from datetime import datetime

import pandas as pd
import pytz
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Count, F
from django.forms import formset_factory
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

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
    redirect_if_not_permitted,
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
    Species,
    SpeciesCount,
)


""" helpers that need models """


def get_accessible_enclosures(request):
    # superuser sees all enclosures
    if not request.user.is_superuser:
        enclosures = Enclosure.objects.filter(users=request.user)
    else:
        enclosures = Enclosure.objects.all()

    return enclosures


""" views """


@login_required
# TODO: logins may not be sufficient - user a part of a group?
# TODO: add pagination
def home(request):
    enclosures_query = get_accessible_enclosures(request)

    paginator = Paginator(enclosures_query, 20)
    page = request.GET.get("page", 1)
    enclosures = paginator.get_page(page)
    page_range = range(
        max(int(page) - 5, 1), min(int(page) + 5, paginator.num_pages) + 1
    )

    return render(
        request, "home.html", {"enclosures": enclosures, "page_range": page_range}
    )


@login_required
def count(request, enclosure_slug, year=None, month=None, day=None):
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

    enclosure_animals = enclosure.animals.filter(active=True).order_by(
        "species__common_name", "name", "accession_number"
    )
    enclosure_groups = enclosure.groups.filter(active=True).order_by(
        "species__common_name", "accession_number"
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
            request.POST, initial=init_anim, prefix="animals_formset",
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

                    # if we're setting a count for a different day than today, set the date/datetime
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

    # if a GET (or any other method) we'll create a blank form
    else:
        species_formset = SpeciesCountFormset(
            initial=init_spec, prefix="species_formset"
        )
        groups_formset = GroupCountFormset(initial=init_group, prefix="groups_formset")
        animals_formset = AnimalCountFormset(
            initial=init_anim, prefix="animals_formset",
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
        },
    )


@login_required
def tally_date_handler(request, enclosure_slug):
    """ Called from tally page to change date tally
    """

    # if it's a POST: pull out the date from the cleaned data then send it to "count"
    if request.method == "POST":
        form = TallyDateForm(request.POST)
        if form.is_valid():
            tzinfo = pytz.timezone(settings.TIME_ZONE)

            target_date = datetime.combine(
                form.cleaned_data["tally_date"], datetime.min.time(), tzinfo=tzinfo
            )
            return redirect(
                "count",
                enclosure_slug=enclosure_slug,
                year=target_date.year,
                month=target_date.month,
                day=target_date.day,
            )
        else:
            messages.error(request, "Error in date entered")

    # if it's a GET: just redirect back to count method
    return redirect("count", enclosure_slug=enclosure_slug)


@login_required
def edit_species_count(request, species_slug, enclosure_slug, year, month, day):
    species = get_object_or_404(Species, slug=species_slug)
    enclosure = get_object_or_404(Enclosure, slug=enclosure_slug)

    if redirect_if_not_permitted(request, enclosure):
        return redirect("home")

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
def edit_group_count(request, group, year, month, day):
    group = get_object_or_404(Group, accession_number=group)
    enclosure = group.enclosure

    if redirect_if_not_permitted(request, enclosure):
        return redirect("home")

    dateday = timezone.make_aware(timezone.datetime(year, month, day))
    count = group.get_count_day(day=dateday)
    init_form = {
        "count_male": 0 if count is None else count.count_male,
        "count_female": 0 if count is None else count.count_female,
        "count_unknown": 0 if count is None else count.count_unknown,
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
def animal_counts(request, animal):
    animal_obj = get_object_or_404(Animal, accession_number=animal)
    enclosure = animal_obj.enclosure

    if redirect_if_not_permitted(request, enclosure):
        return redirect("home")

    animal_counts_query = AnimalCount.objects.filter(animal=animal_obj).order_by(
        "-datetimecounted", "-id"
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
    for cond_slug, _ in AnimalCount.STAFF_CONDITIONS:
        if cond_slug in cond_slugs:
            chart_data.append(query_data.get(condition=cond_slug)["num"])
        else:
            chart_data.append(0)
    # gets the full name of the condition (from second item in tuple)
    chart_labels = [c[1] for c in AnimalCount.STAFF_CONDITIONS]

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
def group_counts(request, group):
    group = get_object_or_404(Group, accession_number=group)
    enclosure = group.enclosure

    if redirect_if_not_permitted(request, enclosure):
        return redirect("home")

    group_counts_query = GroupCount.objects.filter(group=group).order_by(
        "-datetimecounted", "-id"
    )

    paginator = Paginator(group_counts_query, 10)
    page = request.GET.get("page", 1)
    group_counts_records = paginator.get_page(page)
    page_range = range(
        max(int(page) - 5, 1), min(int(page) + 5, paginator.num_pages) + 1
    )

    # db creates sum column
    query_data = group_counts_query.annotate(
        sum=F("count_male") + F("count_female") + F("count_unknown")
    )

    chart_labels_line = [
        d.strftime("%m-%d-%Y")
        for d in list(query_data.values_list("datecounted", flat=True)[:100])
    ]
    chart_data_line_total = list(query_data.values_list("sum", flat=True)[:100])
    chart_data_line_male = list(query_data.values_list("count_male", flat=True)[:100])
    chart_data_line_female = list(
        query_data.values_list("count_female", flat=True)[:100]
    )
    chart_data_line_unknown = list(
        query_data.values_list("count_unknown", flat=True)[:100]
    )

    # for the pie chart (last 100)
    sum_counts = list(query_data.values_list("sum", flat=True)[:100])
    chart_labels_pie = sorted(set(sum_counts))
    chart_data_pie = [sum_counts.count(s) for s in chart_labels_pie]

    return render(
        request,
        "group_counts.html",
        {
            "group": group,
            "enclosure": enclosure,
            "counts": group_counts_records,
            "chart_data_line_male": chart_data_line_male,
            "chart_data_line_female": chart_data_line_female,
            "chart_data_line_unknown": chart_data_line_unknown,
            "chart_data_line_total": chart_data_line_total,
            "chart_labels_line": chart_labels_line,
            "chart_data_pie": chart_data_pie,
            "chart_labels_pie": chart_labels_pie,
            "page_range": page_range,
        },
    )


@login_required
def species_counts(request, species_slug, enclosure_slug):
    obj = get_object_or_404(Species, slug=species_slug)
    enclosure = get_object_or_404(Enclosure, slug=enclosure_slug)

    if redirect_if_not_permitted(request, enclosure):
        return redirect("home")

    counts_query = SpeciesCount.objects.filter(
        species=obj, enclosure=enclosure
    ).order_by("-datetimecounted", "-id")

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
def edit_animal_count(request, animal, year, month, day):
    animal = get_object_or_404(Animal, accession_number=animal)
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


@user_passes_test(lambda u: u.is_staff, redirect_field_name=None)
def ingest_form(request):
    if request.method == "POST":
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            # where we compute changes
            try:
                changesets = handle_upload(request.FILES["file"])
            except Exception as e:
                messages.error(request, e)
                return redirect("ingest_form")

            request.session["changesets"] = changesets
            request.session["upload_file"] = str(request.FILES["file"])

            # redirect to a confirmation page
            return redirect("confirm_upload")

    else:
        form = UploadFileForm()
        request.session.pop("changesets", None)
        request.session.pop("upload_file", None)

    return render(request, "upload_form.html", {"form": form})


@user_passes_test(lambda u: u.is_staff, redirect_field_name=None)
def confirm_upload(request):
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
            return redirect("ingest_form")

        # clearing the changesets
        request.session.pop("changesets", None)
        request.session.pop("upload_file", None)

        messages.success(request, "Saved")

        return redirect("home")

    return render(
        request,
        "confirm_upload.html",
        {"changesets": changesets, "upload_file": upload_file},
    )


@login_required
def export(request):
    accessible_enclosures = get_accessible_enclosures(request)

    if request.method == "POST":
        form = ExportForm(request.POST)
        if form.is_valid():
            selected_enclosures = form.cleaned_data["selected_enclosures"]
            # limit to only accessible enclosures
            # TODO: test to check we cannot export data we aren't allowed to access
            enclosures = accessible_enclosures & selected_enclosures

            start_date = form.cleaned_data["start_date"]
            end_date = form.cleaned_data["end_date"]

            # TODO: these could be abstracted to a function that returns this for any model
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
                messages.error(request, "No data in range")
                return redirect("export")

            df_merge_clean = clean_df(df_merge)

            # create response object to save the data into
            response = HttpResponse(
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            enclosure_names = "_".join((enc.slug for enc in enclosures))
            start_date_str = start_date.strftime("%Y%m%d")
            end_date_str = end_date.strftime("%Y%m%d")
            response[
                "Content-Disposition"
            ] = f'attachment; filename="zootable_export_{enclosure_names}_{start_date_str}_{end_date_str}.xlsx"'

            # create xlsx object and put it into the response using pandas
            with pd.ExcelWriter(response, engine="xlsxwriter") as writer:
                df_merge_clean.to_excel(writer, sheet_name="Sheet1", index=False)

            # TODO: (Fancy) redirect to home and have javascript serve the xlsx file from that page
            # send it to the user
            return response

    else:
        form = ExportForm(initial={"num_days": 7})
        form.fields["selected_enclosures"].queryset = accessible_enclosures

    return render(request, "export.html", {"form": form})
