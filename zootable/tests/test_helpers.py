import pandas as pd
from django_mock_queries.query import MockModel, MockSet
from django.utils import timezone
import pytest

from zoo_checks.helpers import qs_to_df, clean_df


def test_qs_to_df():
    test_data = [
        {"mock_name": "john", "email": "john@gmail.com"},
        {"mock_name": "jeff", "email": "jeff@hotmail.com"},
        {"mock_name": "bill", "email": "bill@gmail.com"},
    ]
    test_df = pd.DataFrame(test_data)

    qs = MockSet(
        MockModel(test_data[0]), MockModel(test_data[1]), MockModel(test_data[2])
    )
    df = qs_to_df(qs)

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
