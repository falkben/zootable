from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist


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

        try:
            spec_group = enclosure_groups.get(species=spec)
            group_form = groups_formset[group_count]
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
