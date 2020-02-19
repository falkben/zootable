import pandas as pd
from django.conf import settings
from django.utils import timezone


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
    dateday,
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
        formset_dict[spec.id]["prior_counts"] = spec.prior_counts(
            enclosure, ref_date=dateday
        )

        spec_groups = enclosure_groups.filter(species=spec)
        formset_dict[spec.id]["group_forms"] = []
        for spec_group in spec_groups:
            group_form = groups_formset[group_count]
            group_count += 1

            formset_dict[spec.id]["group_forms"].append(
                {
                    "group": spec_group,
                    "form": group_form,
                    "prior_counts": spec_group.prior_counts(ref_date=dateday),
                }
            )

        spec_anim_queryset = enclosure_animals.filter(species=spec)
        # creating an index into the animals_formset
        spec_anim_index = list(
            range(anim_total, spec_anim_queryset.count() + anim_total)
        )
        formset_dict[spec.id]["animalformset_index"] = zip(
            spec_anim_queryset,
            [animals_formset[i] for i in spec_anim_index],
            [anim.prior_conditions(ref_date=dateday) for anim in spec_anim_queryset],
        )
        # updating total animals
        anim_total += spec_anim_queryset.count()

    return formset_dict, species_formset, groups_formset, animals_formset


def get_init_spec_count_form(enclosure, enclosure_species, counts):

    # dict of counts to easily access
    if counts:
        counts_dict = {cc.species: cc.count for cc in counts}
    else:
        counts_dict = {}

    # * note: this unpacks the queryset into a list and should be avoided
    init_spec = []
    for sp in enclosure_species:
        count = counts_dict.get(sp, 0)  # default to 0 if not found
        init_spec.append({"species": sp, "count": count, "enclosure": enclosure})

    return init_spec


def get_init_group_count_form(enclosure_groups, counts):

    if counts:
        counts_dict = {cc.group: cc for cc in counts}
    else:
        counts_dict = {}

    init_group = []
    for group in enclosure_groups:
        count = counts_dict.get(group)
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


def get_init_anim_count_form(enclosure_animals, counts):
    # TODO: condition should default to median? condition (across users) for the day

    if counts:
        counts_dict = {cc.animal: cc for cc in counts}
    else:
        counts_dict = {}

    init_anim = [
        {
            "animal": anim,
            "condition": counts_dict.get(anim).condition
            if counts_dict.get(anim)
            else "",
            "comment": counts_dict.get(anim).comment if counts_dict.get(anim) else "",
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
                        field_name_constructor.format(f.name, "species__class_name"),
                        field_name_constructor.format(f.name, "species__order_name"),
                        field_name_constructor.format(f.name, "species__family_name"),
                        field_name_constructor.format(f.name, "species__genus_name"),
                        field_name_constructor.format(f.name, "species__species_name"),
                        field_name_constructor.format(f.name, "species__common_name"),
                    ]
                )
            elif f.name == "species":
                field_names.extend(
                    [
                        field_name_constructor.format(f.name, "class_name"),
                        field_name_constructor.format(f.name, "order_name"),
                        field_name_constructor.format(f.name, "family_name"),
                        field_name_constructor.format(f.name, "genus_name"),
                        field_name_constructor.format(f.name, "species_name"),
                        field_name_constructor.format(f.name, "common_name"),
                    ]
                )
        else:
            field_names.append(f.name)

    queryset_vals = qs.values(*field_names)
    df = pd.DataFrame(queryset_vals)

    return df


def clean_df(df):
    """cleans the counts dataframe for export to excel
    """

    if "id" in df.columns:
        df = df.drop(columns=["id"])

    # remove timezone from datetimes
    # convert times to app's timezone
    # get only time string
    if "datetimecounted" in df.columns:
        df["time_counted"] = (
            df["datetimecounted"]
            .dt.tz_convert(settings.TIME_ZONE)
            .dt.tz_localize(None)
            .dt.strftime("%H:%M:%S")
        )
    df = df.drop(columns=["datetimecounted"])

    # combining columns for species
    items = (
        "common_name",
        "class_name",
        "order_name",
        "family_name",
        "genus_name",
        "species_name",
    )
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

    # making col names prettier
    rename_cols = {
        "enclosure__name": "enclosure",
        "user__username": "user",
        "datecounted": "date_counted",
    }
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
        "class_name",
        "order_name",
        "family_name",
        "genus_name",
        "species_name",
        "common_name",
    ]
    [cols.remove(c) for c in cols_front]
    df = df[cols_front + cols]

    return df
