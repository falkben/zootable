""" test models """

import string
from datetime import timedelta

import pytest
from django.utils.timezone import localtime

from tests.conftest import (
    animal_count_factory,
    animal_factory,
    group_count_factory,
    group_factory,
    species_count_factory,
)
from zoo_checks.models import Animal, AnimalCount, Enclosure, Group, GroupCount, Species


def test_animal_instance(animal_A):
    assert isinstance(animal_A, Animal)
    assert animal_A.name == "A_name"


def test_animal_count_instance(animal_count_A_BAR):
    assert isinstance(animal_count_A_BAR, AnimalCount)
    assert animal_count_A_BAR.condition == "BA"
    assert animal_count_A_BAR.datecounted == localtime().date()


def test_species_instance(species_base):
    assert isinstance(species_base, Species)
    assert species_base.genus_name == "genus_base"


def test_enclosure_instance(enclosure_base):
    assert isinstance(enclosure_base, Enclosure)
    assert enclosure_base.name == "base_enc"


def test_group_instance(group_B):
    assert isinstance(group_B, Group)
    assert group_B.accession_number == "654321"


def test_group_count_instance(group_B_count):
    assert isinstance(group_B_count, GroupCount)
    assert group_B_count.count_bar == 1
    assert group_B_count.datecounted == localtime().date()
    assert group_B_count.group.accession_number == "654321"


def test_accession_numbers_total(enclosure_base, animal_A, group_B):
    num = enclosure_base.accession_numbers_total()
    assert num == 2


def test_accession_numbers_observed(
    enclosure_base: Enclosure,
    animal_count_A_BAR,
    group_B_count,
    django_assert_num_queries,
):
    with django_assert_num_queries(2):
        num_observed = enclosure_base.accession_numbers_observed()
    assert num_observed == 2


def test_animal_counts_on_day(
    enclosure_base, animal_count_A_BAR, django_assert_num_queries,
):
    with django_assert_num_queries(1):
        num_counts = enclosure_base.animal_counts_on_day().count()

    assert num_counts == 1


def test_group_counts_on_day(
    enclosure_base, group_B_count, django_assert_num_queries,
):
    with django_assert_num_queries(1):
        num_counts = enclosure_base.group_counts_on_day().count()

    assert num_counts == 1


@pytest.mark.django_db
def test_counts_many_enclosures(species_base, user_base, django_assert_num_queries):
    # setup
    access_start = 100000
    num_enc = 7
    num_anim = 4
    num_groups = 5
    access_nums = iter(
        range(access_start, num_enc * num_anim * num_groups + access_start + 1)
    )
    spec_count_val = 42
    group_count_val = (6, 1, 2, 3)
    anim_count_cond = "BA"
    alph = string.ascii_lowercase

    counts, enc_list = [], []
    # create some test data
    for i in range(num_enc):
        enc_name = f"enc_{alph[i]}"
        enc = Enclosure.objects.create(name=enc_name)
        enc_list.append(enc)

        # create counts for the enc
        for k in range(num_anim):
            id = f"anim_{enc_name}_{alph[i]}"
            m_f = "MF"[k % 2]  # alternate
            anim = animal_factory(id, id, m_f, next(access_nums), enc, species_base)
            counts.append(animal_count_factory(anim_count_cond, anim, user_base, enc))

            # adding some counts on diff days
            for delta_day in (-3, -2, -1, 1, 2):
                animal_count_factory(
                    "NA",
                    anim,
                    user_base,
                    enc,
                    localtime() + timedelta(days=1) * delta_day,
                )

        for k in range(num_groups):
            id = f"id_{enc_name}_{alph[k]}"
            spec = Species.objects.create(
                common_name=f"common_{id}",
                class_name=f"class_base{id}",
                order_name=f"order_base{id}",
                family_name=f"family_{id}",
                genus_name=f"genus_{id}",
                species_name=f"species_{id}",
            )
            counts.append(species_count_factory(spec, user_base, enc, spec_count_val))

            # adding some counts on diff days
            for delta_day in (-3, -2, -1, 1, 2):
                species_count_factory(
                    spec,
                    user_base,
                    enc,
                    100,
                    localtime() + timedelta(days=1) * delta_day,
                )

            group = group_factory(spec, enc, next(access_nums), 10, 10, 10, 30)
            counts.append(group_count_factory(group, user_base, enc, *group_count_val))

            # adding some counts on diff days
            for delta_day in (-3, -2, -1, 1, 2):
                group_count_factory(
                    group,
                    user_base,
                    enc,
                    10,
                    10,
                    0,
                    0,
                    True,
                    localtime() + timedelta(days=1) * delta_day,
                )

    assert len(counts) == num_enc * (num_anim + num_groups * 2)

    with django_assert_num_queries(3):
        all_counts = Enclosure.all_counts(enc_list)

    # assertions
    for enc in enc_list:
        enc_dict = all_counts[enc.name]

        # species
        enc_spec_dict = enc_dict["species_counts"]
        assert len(enc_spec_dict) == num_groups
        for _, ct in enc_spec_dict.items():
            assert ct.count == spec_count_val
            assert ct.species in enc.species()
            assert ct.datecounted == localtime().date()

        # animals
        enc_anim_dict = enc_dict["animal_counts"]
        assert len(enc_anim_dict) == num_anim
        for _, ct in enc_anim_dict.items():
            assert ct.condition == anim_count_cond
            assert ct.animal in enc.animals.all()
            assert ct.animal.species == species_base
            assert ct.datecounted == localtime().date()

        enc_group_dict = enc_dict["group_counts"]
        for _, ct in enc_group_dict.items():
            assert (
                ct.count_total,
                ct.count_seen,
                ct.count_not_seen,
                ct.count_bar,
            ) == group_count_val
            assert ct.group in enc.groups.all()
            assert ct.group.species in enc.species()
            assert ct.datecounted == localtime().date()
