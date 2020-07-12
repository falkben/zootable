import pandas as pd
import pytest
from django.utils import timezone

from zoo_checks.helpers import clean_df, qs_to_df
from zoo_checks.models import Animal, Enclosure, Group, Species, GroupCount


@pytest.mark.django_db
def test_qs_to_df():
    """ Tests the conversion of a queryset to a dataframe
    """

    # pattern:
    # testdata: dict
    # create test dataframe from dict
    # create a record in the database from dict
    # get the record as a queryset using that dict as the filter
    # convert the queryset to a dataframe
    # assert all items in original dict are present in created dataframe

    enc_data = {"name": "test_enclosure"}
    enc = Enclosure(**enc_data)
    enc.save()

    sp_data = {
        "common_name": "test_common_name",
        "class_name": "test_class_name",
        "order_name": "test_order_name",
        "family_name": "test_family_name",
        "genus_name": "test_genus_name",
        "species_name": "test_species_name",
    }
    sp = Species(**sp_data)
    sp.save()

    anim_data = {
        "accession_number": "abcdef",
        "name": "test_name",
        "identifier": "test_identifier",
    }
    anim_foreign = {
        "species": sp,
        "enclosure": enc,
    }
    animal = Animal(**{**anim_data, **anim_foreign})
    animal.save()

    group_data = {
        "accession_number": "fedcba",
        "population_female": 10,
    }
    group_foreign = {
        "species": sp,
        "enclosure": enc,
    }
    group = Group(**{**group_data, **group_foreign})
    group.save()

    gp_count_data = {
        "count_bar": 10,
        "count_seen": 100,
    }
    gp_count_foreign = {
        "group": group,
    }
    gp_count = GroupCount(**{**gp_count_data, **gp_count_foreign})
    gp_count.save()

    def _check_dataframe(dict_data, model):
        df_test = pd.DataFrame([dict_data])

        qs = model.objects.filter(**dict_data)
        df_from_qs = qs_to_df(qs, model._meta.fields)

        for k, v in dict_data.items():
            assert df_test.iloc[0][k] == df_from_qs.iloc[0][k] == v

    _check_dataframe(sp_data, Species)
    _check_dataframe(anim_data, Animal)
    _check_dataframe(group_data, Group)
    _check_dataframe(gp_count_data, GroupCount)


def test_clean_df():
    timestamp = timezone.localtime()
    test_data = [
        {
            "id": 1637,
            "datetimecounted": timestamp,
            "user__username": 4,
            "enclosure__name": "encl_test_name",
            "condition": "SE",
            "datecounted": timestamp.date(),
        }
    ]
    test_df = pd.DataFrame(test_data)
    df_clean = clean_df(test_df)

    assert df_clean.loc[0]["date_counted"] == timestamp.replace(tzinfo=None).date()
    assert df_clean.loc[0]["time_counted"] == timestamp.replace(
        tzinfo=None
    ).time().strftime("%H:%M:%S")
