from datetime import datetime

import pandas as pd
import pytz
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.forms import formset_factory
from django.http import HttpResponse
from django.db.models import F
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import (
    AnimalCountForm,
    ExportForm,
    GroupCountForm,
    SpeciesCountForm,
    UploadFileForm,
)
from .helpers import (
    clean_df,
    get_init_anim_count_form,
    get_init_group_count_form,
    get_init_spec_count_form,
    qs_to_df,
    set_formset_order,
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


@login_required
# TODO: logins may not be sufficient - user a part of a group?
def home(request):
    enclosures = Enclosure.objects.filter(users=request.user)

    return render(request, "home.html", {"enclosures": enclosures})


@login_required
def count(request, enclosure_slug):
    enclosure = get_object_or_404(Enclosure, slug=enclosure_slug)

    # if the user cannot edit the enclosure, redirect to home
    if request.user not in enclosure.users.all():
        return redirect("home")

    enclosure_animals = (
        enclosure.animals.all()
        .filter(active=True)
        .order_by("species__common_name", "name")
    )
    enclosure_groups = (
        enclosure.groups.all().filter(active=True).order_by("species__common_name")
    )

    enclosure_species = enclosure.species().order_by("common_name")

    SpeciesCountFormset = formset_factory(SpeciesCountForm, extra=0)

    GroupCountFormset = formset_factory(GroupCountForm, extra=0)

    AnimalCountFormset = formset_factory(AnimalCountForm, extra=0)

    init_spec = get_init_spec_count_form(enclosure, enclosure_species)
    init_group = get_init_group_count_form(enclosure_groups)
    init_anim = get_init_anim_count_form(enclosure_animals)

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
            form_kwargs={"is_staff": request.user.is_staff},
        )

        # check whether it's valid:
        if (
            species_formset.is_valid()
            and animals_formset.is_valid()
            and groups_formset.is_valid()
        ):

            def save_form_in_formset(form):
                # TODO: move this into model/(form?) and overwrite the save method
                # TODO: save should be update_or_create w/ user and date (so each user has MAX 1 count/day/spec)
                if form.has_changed():
                    instance = form.save(commit=False)
                    instance.user = request.user
                    instance.update_or_create_from_form()

            # process the data in form.cleaned_data as required
            for formset in (species_formset, animals_formset, groups_formset):
                for form in formset:
                    save_form_in_formset(form)

            messages.success(request, "Saved")
            return redirect("count", enclosure_slug=enclosure.slug)

        else:
            formset_order, species_formset, groups_formset, animals_formset = set_formset_order(
                enclosure,
                enclosure_species,
                enclosure_groups,
                enclosure_animals,
                species_formset,
                groups_formset,
                animals_formset,
            )

            messages.error(request, "There was an error processing the form")

    # if a GET (or any other method) we'll create a blank form
    else:
        species_formset = SpeciesCountFormset(
            initial=init_spec, prefix="species_formset"
        )
        groups_formset = GroupCountFormset(initial=init_group, prefix="groups_formset")
        animals_formset = AnimalCountFormset(
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
def edit_species_count(request, species_slug, enclosure_slug, year, month, day):
    species = get_object_or_404(Species, slug=species_slug)
    enclosure = get_object_or_404(Enclosure, slug=enclosure_slug)

    # if the user cannot edit the enclosure, redirect to home
    if request.user not in enclosure.users.all():
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
                obj.datetimecounted = (
                    dateday + timezone.timedelta(days=1) - timezone.timedelta(seconds=1)
                )
                obj.datecounted = dateday
                obj.save()
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

    # if the user cannot edit the enclosure, redirect to home
    if request.user not in enclosure.users.all():
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
                obj.datetimecounted = (
                    dateday + timezone.timedelta(days=1) - timezone.timedelta(seconds=1)
                )
                obj.datecounted = dateday
                obj.save()
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
    animal = get_object_or_404(Animal, accession_number=animal)
    enclosure = animal.enclosure

    # if the user cannot edit the enclosure, redirect to home
    if request.user not in enclosure.users.all():
        return redirect("home")

    animal_counts_query = AnimalCount.objects.filter(animal=animal).order_by(
        "-datetimecounted", "-id"
    )

    paginator = Paginator(animal_counts_query, 10)
    page = request.GET.get("page")
    animal_counts_records = paginator.get_page(page)

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
            "animal": animal,
            "enclosure": enclosure,
            "animal_counts": animal_counts_records,
            "chart_data": chart_data,
            "chart_labels": chart_labels,
        },
    )


@login_required
def group_counts(request, group):
    group = get_object_or_404(Group, accession_number=group)
    enclosure = group.enclosure

    # if the user cannot edit the enclosure, redirect to home
    if request.user not in enclosure.users.all():
        return redirect("home")

    group_counts_query = GroupCount.objects.filter(group=group).order_by(
        "-datetimecounted", "-id"
    )

    paginator = Paginator(group_counts_query, 10)
    page = request.GET.get("page")
    group_counts_records = paginator.get_page(page)

    # db counts the sums
    query_data = (
        group_counts_query.annotate(
            sum=F("count_male") + F("count_female") + F("count_unknown")
        )
        .values("sum")
        .order_by("sum")
        .annotate(num=Count("sum"))
    )
    chart_labels = sorted(set(query_data.values_list("sum", flat=True)))
    chart_data = [query_data.get(sum=s)["num"] for s in chart_labels]

    return render(
        request,
        "group_counts.html",
        {
            "group": group,
            "enclosure": enclosure,
            "group_counts": group_counts_records,
            "chart_data": chart_data,
            "chart_labels": chart_labels,
        },
    )


@login_required
def edit_animal_count(request, animal, year, month, day):
    animal = get_object_or_404(Animal, accession_number=animal)
    enclosure = animal.enclosure

    # if the user cannot edit the enclosure, redirect to home
    if request.user not in enclosure.users.all():
        return redirect("home")

    dateday = timezone.make_aware(timezone.datetime(year, month, day))
    count = animal.count_on_day(day=dateday)
    init_form = {
        "condition": "" if count is None else count.condition,
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
                obj.datetimecounted = (
                    dateday + timezone.timedelta(days=1) - timezone.timedelta(seconds=1)
                )
                obj.datecounted = dateday
                obj.save()
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


@user_passes_test(lambda u: u.is_superuser, redirect_field_name=None)
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


@user_passes_test(lambda u: u.is_superuser, redirect_field_name=None)
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
    enclosures = Enclosure.objects.filter(users=request.user)

    if request.method == "POST":
        form = ExportForm(request.POST)
        if form.is_valid():
            enclosures = form.cleaned_data["selected_enclosures"]

            tzinfo = pytz.timezone(settings.TIME_ZONE)

            start_date = datetime.combine(
                form.cleaned_data["start_date"], datetime.min.time(), tzinfo=tzinfo
            )
            end_date = datetime.combine(
                form.cleaned_data["end_date"], datetime.min.time(), tzinfo=tzinfo
            ) + timezone.timedelta(days=1)

            animal_counts = (
                AnimalCount.objects.filter(
                    enclosure__in=enclosures,
                    datetimecounted__gte=start_date,
                    datetimecounted__lt=end_date,
                )
                .annotate(dateonlycounted=TruncDate("datetimecounted", tzinfo=tzinfo))
                .order_by("dateonlycounted", "animal_id")
                .distinct("dateonlycounted", "animal_id")
            )
            group_counts = (
                GroupCount.objects.filter(
                    enclosure__in=enclosures,
                    datetimecounted__gte=start_date,
                    datetimecounted__lt=end_date,
                )
                .annotate(dateonlycounted=TruncDate("datetimecounted", tzinfo=tzinfo))
                .order_by("dateonlycounted", "group_id")
                .distinct("dateonlycounted", "group_id")
            )
            species_counts = (
                SpeciesCount.objects.filter(
                    enclosure__in=enclosures,
                    datetimecounted__gte=start_date,
                    datetimecounted__lt=end_date,
                )
                .annotate(dateonlycounted=TruncDate("datetimecounted", tzinfo=tzinfo))
                .order_by("dateonlycounted", "species_id")
                .distinct("dateonlycounted", "species_id")
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

            enclosure_names = (enc.slug for enc in enclosures)
            response[
                "Content-Disposition"
            ] = f'attachment; filename="zootable_export_{"_".join(enclosure_names)}_{start_date.strftime("%Y%m%d")}_{(end_date- timezone.timedelta(days=1)).strftime("%Y%m%d")}.xlsx"'

            # create xlsx object and put it into the response using pandas
            with pd.ExcelWriter(response, engine="xlsxwriter") as writer:
                df_merge_clean.to_excel(writer, sheet_name="Sheet1", index=False)

            # TODO: (Fancy) redirect to home and have javascript serve the xlsx file from that page
            # send it to the user
            return response

    else:
        form = ExportForm(initial={"num_days": 7})
        form["selected_enclosures"].queryset = Enclosure.objects.filter(
            users=request.user
        )

    return render(request, "export.html", {"enclosures": enclosures, "form": form})
