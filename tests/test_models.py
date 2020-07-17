""" test models """

from datetime import date, datetime

import pytest

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
def create_animal_factory(
    db,
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
        enclosure=enclosure,
        active=active,
        accession_number=accession_number,
        species=species,
    )


@pytest.fixture
def animal_A(db, create_animal_factory, enclosure, species, active=True) -> Animal:
    return create_animal_factory(
        "A", "A animal", "M", "543210", enclosure, species, active
    )


@pytest.fixture
def animal_B(db, create_animal_factory, enclosure, species, active=True) -> Animal:
    return create_animal_factory(
        "B", "B animal", "F", "012345", enclosure, species, active
    )


@pytest.fixture
def animal_count_factory(db, animal: Animal, user: User, enclosure: Enclosure):
    def create_animal_count(
        condition: str, datetimecounted: datetime, datecounted: date, comment: str = "",
    ):
        animal_count = AnimalCount.objects.create(
            condition=condition,
            comment=comment,
            datetimecounted=datetimecounted,
            datecounted=datecounted,
            user=user,
            animal=animal,
            enclosure=enclosure,
        )
        return animal_count

    return create_animal_count


def test_should_create_animal(animal_A: Animal) -> None:
    enclosure = create_enclosure("name")
    species = create_species("lkjlkj")
    assert isinstance(animal_A, Animal, enclosure, species)


# pytest fixtures for creating models


# create some test data
# users
# species
# animals
# groups
# animal counts
# group counts
# species counts


# test Enclosure counts_on_day
