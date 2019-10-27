from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist

from django.conf import settings

import pandas as pd


def today_time():
    return timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)


def prior_days(days=3):
    p_days = []
    for p in range(days):
        day = today_time() - timezone.timedelta(days=p + 1)
        p_days.append({"year": day.year, "month": day.month, "day": day.day})

    return p_days


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
        formset_dict[spec.id]["species"] = spec

        # NOTE: We could avoid the following when there's group's for that species since they are hidden
        formset_dict[spec.id]["formset"] = species_formset[ind]
        formset_dict[spec.id]["prior_counts"] = spec.prior_counts(enclosure)

        spec_groups = enclosure_groups.filter(species=spec)
        formset_dict[spec.id]["group_forms"] = []
        for spec_group in spec_groups:
            group_form = groups_formset[group_count]
            group_count += 1

            formset_dict[spec.id]["group_forms"].append(
                {"group": spec_group, "form": group_form}
            )

        spec_anim_queryset = enclosure_animals.filter(species=spec)
        # creating an index into the animals_formset
        spec_anim_index = list(
            range(anim_total, spec_anim_queryset.count() + anim_total)
        )
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
        init_spec.append(
            {
                "species": sp,
                "count": sp.current_count(enclosure)["count"],
                "enclosure": enclosure,
            }
        )

    return init_spec


def get_init_group_count_form(enclosure_groups):
    init_group = []
    for group in enclosure_groups:
        count = group.current_count()
        init_group.append(
            {
                "group": group,
                "count_male": 0 if count is None else count.count_male,
                "count_female": 0 if count is None else count.count_female,
                "count_unknown": 0 if count is None else count.count_unknown,
                "enclosure": group.enclosure,
            }
        )

    return init_group


def get_init_anim_count_form(enclosure_animals):
    # TODO: condition should default to median? condition (across users) for the day

    # make db query to get conditions for all the animals in enclosure
    init_anim = [
        {
            "animal": anim,
            "condition": anim.current_condition,
            "enclosure": anim.enclosure,
        }
        for anim in enclosure_animals
    ]

    return init_anim


def qs_to_df(qs, fields):
    """Takes a queryset and outputs a dataframe
    """

    field_names = []
    field_name_constructor = "{}__{}"
    for f in fields:
        if f.is_relation:
            if f.name == "enclosure":
                field_names.append(field_name_constructor.format(f.name, "name"))
            elif f.name == "user":
                field_names.append(field_name_constructor.format(f.name, "username"))
            elif f.name in ("animal", "group"):
                field_names.extend(
                    [
                        field_name_constructor.format(f.name, "accession_number"),
                        field_name_constructor.format(f.name, "species__genus_name"),
                        field_name_constructor.format(f.name, "species__species_name"),
                        field_name_constructor.format(f.name, "species__common_name"),
                    ]
                )
            elif f.name == "species":
                field_names.extend(
                    [
                        field_name_constructor.format(f.name, "genus_name"),
                        field_name_constructor.format(f.name, "species_name"),
                        field_name_constructor.format(f.name, "common_name"),
                    ]
                )
        else:
            field_names.append(f.name)

    queryset_vals = list(qs.values(*field_names, "dateonlycounted"))
    df = pd.DataFrame(queryset_vals)

    return df


def clean_df(df):
    """cleans the counts dataframe for export to excel
    """

    # remove dateonlycounted
    if "dateonlycounted" in df.columns:
        df = df.drop(columns=["dateonlycounted"])

    if "id" in df.columns:
        df = df.drop(columns=["id"])

    # remove timezones from datetimes (for excel) but still display datetime for the app's timezone
    if "datetimecounted" in df.columns:
        df["datetimecounted"] = df["datetimecounted"].dt.tz_convert(settings.TIME_ZONE)
        df["datetimecounted"] = df["datetimecounted"].dt.tz_localize(None)

    # combining columns for species
    items = ("common_name", "genus_name", "species_name")
    for item in items:
        cols = [
            f"species__{item}",
            f"animal__species__{item}",
            f"group__species__{item}",
        ]
        cols = [c for c in cols if c in df.columns]
        df[f"{item}"] = df[cols].apply(
            lambda row: "".join(row.dropna().astype(str)), axis=1
        )
        df = df.drop(columns=cols)

    # combining accession_number
    cols = [f"animal__accession_number", f"group__accession_number"]
    cols = [c for c in cols if c in df.columns]
    df["accession_number"] = df[cols].apply(
        lambda row: "".join(row.dropna().astype(int).astype(str)), axis=1
    )
    df = df.drop(columns=cols)

    # split the datetime into separate columns
    df["date_counted"] = df["datetimecounted"].dt.date
    df["time_counted"] = df["datetimecounted"].dt.strftime("%H:%M:%S")
    df = df.drop(columns=["datetimecounted"])

    # making col names prettier
    rename_cols = {"enclosure__name": "enclosure", "user__username": "user"}
    df = df.rename(columns=rename_cols)

    # sorting the values
    df = df.sort_values(
        by=["enclosure", "date_counted", "time_counted", "species_name"]
    )

    # sorting the columns
    cols = df.columns.to_list()
    cols_front = [
        "enclosure",
        "date_counted",
        "time_counted",
        "genus_name",
        "species_name",
        "common_name",
    ]
    [cols.remove(c) for c in cols_front]
    df = df[cols_front + cols]

    return df
