import pytest
from xlrd import XLRDError
import pandas as pd


from zoo_checks.models import Enclosure, Species, Animal
from zoo_checks.ingest import (
    read_xlsx_data,
    create_enclosures,
    create_species,
    create_animals,
    validate_input,
    # find_animals_groups,
    # create_groups,
    # get_changesets,
)


def test_read_xlsx_data():
    pytest.raises(TypeError, read_xlsx_data, "zootable/test_data/empty_data.xlsx")
    pytest.raises(TypeError, read_xlsx_data, "zootable/test_data/wrong_column.xlsx")
    pytest.raises(XLRDError, read_xlsx_data, "zootable/test_data/malformed.xlsx")

    df = read_xlsx_data("zootable/test_data/example.xlsx")
    assert df.shape[0] == 5


@pytest.mark.django_db
def test_create_enclosures():

    encl_name = "example_enclosure"

    df = pd.DataFrame({"Enclosure": encl_name}, index=[0])
    create_enclosures(df)

    test_enclosure = Enclosure.objects.get(name=encl_name)

    assert test_enclosure is not None


@pytest.mark.django_db
def test_create_species():

    df = read_xlsx_data("zootable/test_data/example.xlsx")
    create_species(df)

    for common_name in df["Common"]:
        sp = Species.objects.get(common_name=common_name)
        assert sp is not None


@pytest.mark.django_db
def test_create_animals():
    df = read_xlsx_data("zootable/test_data/example.xlsx")

    # need to first create species, enclosures
    create_enclosures(df)
    create_species(df)

    df_validated = validate_input(df)
    create_animals(df_validated)

    for acc_num in df_validated["Accession"]:
        anim = Animal.objects.get(accession_number=acc_num)
        assert anim is not None


def test_validate_input():
    pass


def test_find_animals_groups():
    pass


def test_create_groups():
    pass


def test_get_changesets():
    # test empty df -- raises an error

    # test df has all the same data as in database

    # test removes from enclosure as adds

    pass
