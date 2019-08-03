import pytest
from xlrd import XLRDError

from .ingest import (
    read_xlsx_data,
    create_enclosures,
    create_species,
    find_animals_groups,
    create_animals,
    create_groups,
    get_changesets,
)


def test_read_xlsx_data():
    pytest.raises(TypeError, read_xlsx_data, "zootable/test_data/empty_data.xlsx")
    pytest.raises(TypeError, read_xlsx_data, "zootable/test_data/wrong_column.xlsx")
    pytest.raises(XLRDError, read_xlsx_data, "zootable/test_data/malformed.xlsx")

    df = read_xlsx_data("zootable/test_data/example.xlsx")
    assert df.shape[0] == 4


def test_create_enclosures():
    pass


def test_create_species():
    pass


def test_find_animals_groups():
    pass


def test_create_animals():
    pass


def test_create_groups():
    pass


def test_get_changesets():
    # test empty df -- raises an error

    # test df has all the same data as in database

    # test removes from enclosure as adds

    pass
