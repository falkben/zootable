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

INPUT_EXAMPLE = "zootable/test_data/example.xlsx"
INPUT_EMPTY = "zootable/test_data/empty_data.xlsx"
INPUT_WRONG_COL = "zootable/test_data/wrong_column.xlsx"
INPUT_MALFORMED = "zootable/test_data/malformed.xlsx"
INPUT_ACCESSIONS_BAD = "zootable/test_data/too_many_digits_access_num.xlsx"


def test_read_xlsx_data():
    pytest.raises(TypeError, read_xlsx_data, INPUT_EMPTY)
    pytest.raises(TypeError, read_xlsx_data, INPUT_WRONG_COL)
    pytest.raises(XLRDError, read_xlsx_data, INPUT_MALFORMED)

    df = read_xlsx_data(INPUT_EXAMPLE)
    assert df.shape[0] == 5


def test_validate_input():

    df = read_xlsx_data(INPUT_ACCESSIONS_BAD)
    with pytest.raises(
        ValueError, match="Accession numbers should only have 6 characters"
    ):
        validate_input(df)

    df_simple_bad = pd.DataFrame({"Accession": "12345"}, index=[0])
    with pytest.raises(
        ValueError, match="Accession numbers should only have 6 characters"
    ):
        validate_input(df_simple_bad)

    df_simple_good = pd.DataFrame([{"Accession": "654321"}])
    df_validated = validate_input(df_simple_good)
    assert df_validated is not None
    assert df_validated.loc[0, "Accession"] == "654321"


@pytest.mark.django_db
def test_create_enclosures():

    encl_name = "example_enclosure"

    df = pd.DataFrame({"Enclosure": encl_name}, index=[0])
    create_enclosures(df)

    test_enclosure = Enclosure.objects.get(name=encl_name)

    assert test_enclosure is not None


@pytest.mark.django_db
def test_create_species():

    df = read_xlsx_data(INPUT_EXAMPLE)
    create_species(df)

    for common_name in df["Common"]:
        sp = Species.objects.get(common_name=common_name)
        assert sp is not None


@pytest.mark.django_db
def test_create_animals():
    df = read_xlsx_data(INPUT_EXAMPLE)

    # need to first create species, enclosures
    create_enclosures(df)
    create_species(df)

    create_animals(df)

    for acc_num in df["Accession"]:
        anim = Animal.objects.get(accession_number=acc_num)
        assert anim is not None


def test_find_animals_groups():
    pass


def test_create_groups():
    pass


def test_get_changesets():
    # test empty df -- raises an error

    # test df has all the same data as in database

    # test removes from enclosure as adds

    pass


def test_group_becomes_individuals():
    pass


def test_individual_becomes_group():
    pass
