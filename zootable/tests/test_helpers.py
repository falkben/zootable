import pandas as pd
from django_mock_queries.query import MockModel, MockSet, MockField
from django.utils import timezone
import pytest

from zoo_checks.helpers import qs_to_df, clean_df


class MockFieldIsRelation(MockField):
    def __init__(self, *args, **kwargs):
        self.is_relation = kwargs.pop("is_relation", False)
        super().__init__(*args, **kwargs)


def test_qs_to_df():
    test_data = [
        {"mock_name": "john", "email": "john@gmail.com", "dateonlycounted": None},
        {"mock_name": "jeff", "email": "jeff@hotmail.com", "dateonlycounted": None},
        {"mock_name": "bill", "email": "bill@gmail.com", "dateonlycounted": None},
    ]
    test_df = pd.DataFrame(test_data)

    qs = MockSet(
        MockModel(test_data[0]), MockModel(test_data[1]), MockModel(test_data[2])
    )
    df = qs_to_df(qs, [MockFieldIsRelation("mock_name"), MockFieldIsRelation("email")])

    assert pd.DataFrame.equals(df, test_df)


def test_clean_df():
    timestamp = timezone.localtime()
    test_data = [
        {"mock_name": "john", "email": "john@gmail.com", "datecounted": timestamp}
    ]
    test_df = pd.DataFrame(test_data)

    df_clean = clean_df(test_df)

    assert df_clean.loc[0]["datecounted"].to_pydatetime() == timestamp.replace(
        tzinfo=None
    )
