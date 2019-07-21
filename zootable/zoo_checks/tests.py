from django.test import TestCase

import pytest

from .ingest import read_xlsx_data


class IngestTestCase(TestCase):
    def setup(self):
        pass

    def test_read_xlsx_data(self):

        pytest.raises(TypeError, read_xlsx_data, "zootable/test_data/test_empty.xlsx")
