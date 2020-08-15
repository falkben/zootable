"""
conftest.py is autodiscovered by pytest
https://docs.pytest.org/en/stable/fixture.html#conftest-py-sharing-fixture-functions
"""

import random
import string
from typing import Optional

import pytest
from django.utils.timezone import datetime, localtime, timedelta

from zoo_checks.models import (
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


@pytest.fixture
def user_base(db):
    return User.objects.create_user("base", first_name="base_first_name")


@pytest.fixture
def user_super(db):
    return User.objects.create_superuser("super", first_name="super_first_name")


@pytest.fixture
def role_base(db, user_base):
    role = Role.objects.create(name="role_base")
    role.users.add(user_base)
    role.save()
    return role


@pytest.fixture
def enclosure_factory(db, role_base):
    # closure
    def _enclosure_factory(name, role: Optional[Enclosure] = role_base):
        enc = Enclosure.objects.create(name=name)
        if role is not None:
            enc.roles.add(role)
            enc.save()
        return enc

    return _enclosure_factory


@pytest.fixture
def enclosure_base(db, enclosure_factory):
    return enclosure_factory("base_enc")


@pytest.fixture
def species_base(db):
    return Species.objects.create(
        common_name="common_base",
        class_name="class_base",
        order_name="order_base",
        family_name="family_base",
        genus_name="genus_base",
        species_name="species_base",
    )


def species_count_factory(
    species: Species,
    user: User,
    enclosure: Enclosure,
    count: int,
    datetimecounted: datetime = None,
) -> SpeciesCount:
    if datetimecounted is None:
        datetimecounted = localtime()
    return SpeciesCount.objects.create(
        datetimecounted=datetimecounted,
        datecounted=datetimecounted.date(),
        species=species,
        user=user,
        enclosure=enclosure,
        count=count,
    )


@pytest.fixture
def species_base_count(
    db, species_base, user_base, enclosure_base, datetimecounted=None
):
    if datetimecounted is None:
        datetimecounted = localtime()
    return species_count_factory(
        datetimecounted=datetimecounted,
        species=species_base,
        user=user_base,
        enclosure=enclosure_base,
        count=100,
    )


def animal_factory(
    name: str,
    identifier: str,
    sex: str,
    accession_number: str,
    enclosure: Enclosure,
    species: Species,
    active: bool = True,
) -> Animal:
    return Animal.objects.create(
        name=name,
        identifier=identifier,
        sex=sex,
        accession_number=accession_number,
        enclosure=enclosure,
        species=species,
        active=active,
    )


@pytest.fixture
def animal_A(db, species_base, enclosure_base):
    return animal_factory("A_name", "A_id", "M", "123456", enclosure_base, species_base)


@pytest.fixture
def animal_B_enc(db, species_base, enclosure_factory):
    # closure
    def _animal_B_enc(enclosure_name):

        enc = enclosure_factory(enclosure_name)
        return animal_factory("B_name", "B_id", "F", "111555", enc, species_base)

    return _animal_B_enc


def animal_count_factory(
    condition: str,
    animal: Animal,
    user: User,
    enclosure: Enclosure,
    datetimecounted: datetime = None,
    comment: str = "",
) -> AnimalCount:
    if datetimecounted is None:
        datetimecounted = localtime()
    return AnimalCount.objects.create(
        datetimecounted=datetimecounted,
        datecounted=datetimecounted.date(),
        condition=condition,
        comment=comment,
        animal=animal,
        user=user,
        enclosure=enclosure,
    )


@pytest.fixture
def animal_count_A_BAR(db, animal_A, user_base, enclosure_base, datetimecounted=None):
    if datetimecounted is None:
        datetimecounted = localtime()
    return animal_count_factory(
        "BA", animal_A, user_base, enclosure_base, datetimecounted
    )


def group_factory(
    species: Species,
    enclosure: Enclosure,
    accession_number: str,
    population_male: int,
    population_female: int,
    population_unknown: int,
    population_total: int,
    active: bool = True,
) -> Group:
    return Group.objects.create(
        species=species,
        enclosure=enclosure,
        accession_number=accession_number,
        population_male=population_male,
        population_female=population_female,
        population_unknown=population_unknown,
        population_total=population_total,
        active=active,
    )


@pytest.fixture
def group_B(db, enclosure_base, species_base):
    return group_factory(
        species=species_base,
        enclosure=enclosure_base,
        accession_number="654321",
        population_male=1,
        population_female=2,
        population_unknown=3,
        population_total=6,
    )


def group_count_factory(
    group: Group,
    user: User,
    enclosure: Enclosure,
    count_total: int,
    count_seen: int,
    count_not_seen: int,
    count_bar: int,
    needs_attn: bool = False,
    datetimecounted: datetime = None,
    comment: str = "",
) -> GroupCount:
    if datetimecounted is None:
        datetimecounted = localtime()
    return GroupCount.objects.create(
        group=group,
        datetimecounted=datetimecounted,
        datecounted=datetimecounted.date(),
        user=user,
        enclosure=enclosure,
        count_total=count_total,
        count_seen=count_seen,
        count_not_seen=count_not_seen,
        count_bar=count_bar,
        needs_attn=needs_attn,
        comment=comment,
    )


@pytest.fixture
def group_B_count(db, group_B, user_base, enclosure_base, datetimecounted=None):
    if datetimecounted is None:
        datetimecounted = localtime()
    return group_count_factory(
        group_B,
        user_base,
        enclosure_base,
        count_total=6,
        count_seen=3,
        count_not_seen=0,
        count_bar=1,
        needs_attn=False,
        comment="",
        datetimecounted=datetimecounted,
    )


@pytest.fixture
def create_many_counts(db, species_base, user_base, enclosure_factory):
    """
    sets up a large number of counts for testing
    returns the counts created as well as the enclosure
    """

    # closure
    def _create_many_counts(
        num_enc: int = 7, num_anim: int = 4, num_species: int = 5,
    ):
        access_start = 100000
        access_nums = iter(
            range(access_start, num_enc * num_anim * num_species + access_start + 1)
        )
        spec_count_val = 42
        group_count_val = (6, 1, 2, 3)
        anim_count_cond = "BA"
        alph = string.ascii_lowercase

        rand_alph_idx = random.sample(list(range(len(alph))), num_enc)

        s_cts, a_cts, g_cts, enc_list = [], [], [], []
        # create some test data
        for i in range(num_enc):
            enc_name = f"enc_{alph[rand_alph_idx[i]]}"
            enc = enclosure_factory(enc_name)
            enc_list.append(enc)

            # create counts for the enc
            for k in range(num_anim):
                id = f"anim_{enc_name}_{alph[i]}"
                m_f = "MF"[k % 2]  # alternate
                anim = animal_factory(id, id, m_f, next(access_nums), enc, species_base)
                a_cts.append(
                    animal_count_factory(anim_count_cond, anim, user_base, enc)
                )

                # adding some counts on diff days
                for delta_day in (-3, -2, -1, 1, 2):
                    animal_count_factory(
                        "NA",
                        anim,
                        user_base,
                        enc,
                        localtime() + timedelta(days=1) * delta_day,
                    )

            for k in range(num_species):
                id = f"id_{enc_name}_{alph[k]}"
                spec = Species.objects.create(
                    common_name=f"common_{id}",
                    class_name=f"class_base{id}",
                    order_name=f"order_base{id}",
                    family_name=f"family_{id}",
                    genus_name=f"genus_{id}",
                    species_name=f"species_{id}",
                )
                s_cts.append(
                    species_count_factory(spec, user_base, enc, spec_count_val)
                )

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
                g_cts.append(
                    group_count_factory(group, user_base, enc, *group_count_val)
                )

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

        return a_cts, s_cts, g_cts, enc_list

    return _create_many_counts
