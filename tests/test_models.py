""" test models """


from zoo_checks.models import (
    Animal,
    Enclosure,
    Group,
    Species,
)


def test_animal_instance(animal_A: Animal) -> None:
    assert isinstance(animal_A, Animal)
    assert animal_A.name == "A_name"


def test_species_instance(species_base: Species):
    assert isinstance(species_base, Species)
    assert species_base.genus_name == "genus_base"


def test_enclosure_instance(enclosure_base: Enclosure):
    assert isinstance(enclosure_base, Enclosure)
    assert enclosure_base.name == "base"


def test_group_instance(group_B: Group):
    assert isinstance(group_B, Group)
    assert group_B.accession_number == "654321"


def test_accession_numbers_total(
    enclosure_base: Enclosure, animal_A: Animal, group_B: Group
):
    num = enclosure_base.accession_numbers_total()
    assert num == 2


# TODO:
# def test_accession_numbers_observed(
#     enclosure_base: Enclosure, animal_A: Animal, group_B: Group
# ):
#     ...
