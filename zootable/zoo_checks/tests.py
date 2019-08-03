import pytest
from xlrd import XLRDError

from .ingest import read_xlsx_data


def test_read_xlsx_data():
    pytest.raises(TypeError, read_xlsx_data, "zootable/test_data/empty_data.xlsx")
    pytest.raises(TypeError, read_xlsx_data, "zootable/test_data/wrong_column.xlsx")
    pytest.raises(XLRDError, read_xlsx_data, "zootable/test_data/malformed.xlsx")

    df = read_xlsx_data("zootable/test_data/example.xlsx")
    assert df.shape[0] == 2


def test_get_changesets():
    # test empty df -- raises an error

    # test df has all the same data as in database

    # test removes from enclosure as adds

    pass
