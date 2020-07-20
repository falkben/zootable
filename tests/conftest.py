"""
conftest.py is autodiscovered by pytest
https://docs.pytest.org/en/stable/fixture.html#conftest-py-sharing-fixture-functions
"""

import pytest
from django.utils.timezone import datetime, localtime

from zoo_checks.models import (
    Animal,
    AnimalCount,
    Enclosure,
    Group,
    GroupCount,
    Species,
    SpeciesCount,
    User,
)


@pytest.fixture
def user_base(db):
    return User.objects.create_user("base")


@pytest.fixture
def enclosure_base(db):
    return Enclosure.objects.create(name="base")


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


@pytest.fixture
def species_base_count(
    db, species_base, user_base, enclosure_base, datetimecounted=None
):
    if datetimecounted is None:
        datetimecounted = localtime()
    return SpeciesCount.objects.create(
        datetimecounted=datetimecounted,
        datecounted=datetimecounted.date(),
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


def animal_count_factory(
    datetimecounted: datetime,
    condition: str,
    animal: Animal,
    user: User,
    enclosure: Enclosure,
    comment: str = "",
) -> AnimalCount:
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
        datetimecounted, "BA", animal_A, user_base, enclosure_base
    )


@pytest.fixture
def group_B(db, enclosure_base, species_base):
    return Group.objects.create(
        active=True,
        accession_number="654321",
        population_male=1,
        population_female=2,
        population_unknown=3,
        population_total=6,
        species=species_base,
        enclosure=enclosure_base,
    )


def group_count_factory(
    datetimecounted: datetime,
    group: Group,
    user: User,
    enclosure: Enclosure,
    count_total: int,
    count_seen: int,
    count_not_seen: int,
    count_bar: int,
    needs_attn: bool,
    comment: str = "",
) -> GroupCount:
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
        datetimecounted,
        group_B,
        user_base,
        enclosure_base,
        count_total=6,
        count_seen=3,
        count_not_seen=0,
        count_bar=1,
        needs_attn=False,
        comment="",
    )
