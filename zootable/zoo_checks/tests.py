import pytest
from xlrd import XLRDError

from .ingest import read_xlsx_data


def test_read_xlsx_data():
    pytest.raises(TypeError, read_xlsx_data, "zootable/test_data/empty_data.xlsx")
    pytest.raises(TypeError, read_xlsx_data, "zootable/test_data/wrong_column.xlsx")
    pytest.raises(XLRDError, read_xlsx_data, "zootable/test_data/malformed.xlsx")

    df = read_xlsx_data("zootable/test_data/example.xlsx")
    assert df.shape[0] == 2
