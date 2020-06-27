import pandas as pd
import pytest
from django.core.exceptions import ObjectDoesNotExist
from xlrd import XLRDError

from zoo_checks.ingest import (
    create_animals,
    create_enclosures,
    create_groups,
    create_species,
    find_animals_groups,
    get_changesets,
    ingest_changesets,
    read_xlsx_data,
    validate_input,
)
from zoo_checks.models import Animal, Enclosure, Group, Species

INPUT_EXAMPLE = "zootable/test_data/example.xlsx"
INPUT_EMPTY = "zootable/test_data/empty_data.xlsx"
INPUT_WRONG_COL = "zootable/test_data/wrong_column.xlsx"
INPUT_MALFORMED = "zootable/test_data/malformed.xlsx"
INPUT_ACCESSIONS_BAD = "zootable/test_data/too_many_digits_access_num.xlsx"
ONLY_GROUPS_EXAMPLE = "zootable/test_data/only_groups.xlsx"
ONLY_ANIMALS_EXAMPLE = "zootable/test_data/only_animals.xlsx"


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

    with pytest.raises(
        ValueError, match="Cannot create individuals. Not all have a pop. of 1"
    ):
        create_animals(df)

    animals, groups = find_animals_groups(df)
    create_animals(animals)

    for acc_num in animals["Accession"]:
        Animal.objects.get(accession_number=acc_num)

    for acc_num in groups["Accession"]:
        with pytest.raises(ObjectDoesNotExist):
            Animal.objects.get(accession_number=acc_num)


def test_find_animals_groups():
    cols = ["Population _Male", "Population _Female", "Population _Unknown"]
    nums = [[0, 1, 0], [1, 0, 1], [1, 0, 0], [0, 0, 1]]

    data = []
    for row in nums:
        data.append({c: n for c, n in zip(cols, row)})

    df = pd.DataFrame(data)
    animals, groups = find_animals_groups(df)

    assert animals.shape[0] == 3
    assert groups.shape[0] == 1


@pytest.mark.django_db
def test_create_groups():
    df = read_xlsx_data(INPUT_EXAMPLE)
    create_enclosures(df)
    create_species(df)

    with pytest.raises(
        ValueError, match="Cannot create groups. Not all have a pop. > 1"
    ):
        create_groups(df)

    animals, groups = find_animals_groups(df)
    create_groups(groups)

    for acc_num in groups["Accession"]:
        g = Group.objects.get(accession_number=acc_num)
        assert g.population_total > 1

    for acc_num in animals["Accession"]:
        with pytest.raises(ObjectDoesNotExist):
            Group.objects.get(accession_number=acc_num)


@pytest.mark.django_db
def test_get_changesets():
    # test empty df -- raises an error
    empty_df = pd.DataFrame([{}])
    with pytest.raises(KeyError):
        get_changesets(empty_df)

    # test that we get the changeset back as we think we should given the test data
    df = read_xlsx_data(INPUT_EXAMPLE)
    ch_s = get_changesets(df)

    assert ch_s["enclosures"] == ["enc1"]

    anim_add_accession = [
        ch_a["object_kwargs"]["Accession"]
        for ch_a in ch_s["animals"]
        if ch_a["action"] == "add"
    ]
    animals_acc = [
        "111111",
        "111113",
        "111114",
        "111115",
    ]
    assert sorted(anim_add_accession) == sorted(animals_acc)

    gp_add_accession = [
        ch_a["object_kwargs"]["Accession"]
        for ch_a in ch_s["groups"]
        if ch_a["action"] == "add"
    ]
    # only one group
    assert ["111112"] == gp_add_accession


@pytest.mark.django_db
def test_ingest_changesets():
    """ Test example ingest from df """

    df = read_xlsx_data(INPUT_EXAMPLE)
    ch_s = get_changesets(df)
    ingest_changesets(ch_s)

    accession_nums = df["Accession"]
    for accession_num in accession_nums:
        anim = Animal.objects.filter(accession_number=accession_num)
        groups = Group.objects.filter(accession_number=accession_num)
        assert len(anim) + len(groups) == 1

    df = read_xlsx_data(ONLY_GROUPS_EXAMPLE)
    ch_s = get_changesets(df)
    ingest_changesets(ch_s)

    accession_nums = df["Accession"]
    for accession_num in accession_nums:
        # this would raise an exception if it didn't find one
        Group.objects.get(accession_number=accession_num)

    df = read_xlsx_data(ONLY_ANIMALS_EXAMPLE)
    ch_s = get_changesets(df)
    ingest_changesets(ch_s)

    accession_nums = df["Accession"]
    for accession_num in accession_nums:
        # this would raise an exception if it didn't find one
        Animal.objects.get(accession_number=accession_num)


@pytest.mark.django_db
def test_group_becomes_individuals():
    """ Tests that when a group's numbers go to 1 it transforms into an "animal" from a "group"
    """
    df = read_xlsx_data(INPUT_EXAMPLE)
    create_enclosures(df)
    create_species(df)

    animals, groups = find_animals_groups(df)

    create_animals(animals)
    create_groups(groups)

    accession = "111112"
    gp = Group.objects.get(accession_number=accession)
    assert gp.population_total > 1

    # modify the df to have only one population
    df.at[df.index[df["Accession"] == accession], "Population _Female"] = 0
    df.at[df.index[df["Accession"] == accession], "Population _Unknown"] = 1

    # get_changesets on that dataframe
    changeset = get_changesets(df)

    # assert we are adding an individual
    animal_changes_accession = [
        ch_a["object_kwargs"]["Accession"]
        for ch_a in changeset["animals"]
        if ch_a["action"] == "add"
    ]
    assert accession in animal_changes_accession

    # assert we are removing the group
    group_changes_accession = [
        ch_a["object_kwargs"]["accession_number"]
        for ch_a in changeset["groups"]
        if ch_a["action"] == "del"
    ]
    assert accession in group_changes_accession


@pytest.mark.django_db
def test_individual_becomes_group():
    """ Tests that when an individual's numbers go > 1 it transforms into a "group" from an "animal"
    """
    df = read_xlsx_data(INPUT_EXAMPLE)
    create_enclosures(df)
    create_species(df)

    animals, groups = find_animals_groups(df)

    create_animals(animals)
    create_groups(groups)

    accession = "111111"

    # this would raise an not found exception if it was not present
    Animal.objects.get(accession_number=accession)

    # modify the df to have > one population
    df.at[df.index[df["Accession"] == accession], "Population _Female"] = 1
    df.at[df.index[df["Accession"] == accession], "Population _Unknown"] = 1

    # get_changesets on that dataframe
    changeset = get_changesets(df)

    # assert we are adding a group
    add_accession = [
        ch_a["object_kwargs"]["Accession"]
        for ch_a in changeset["groups"]
        if ch_a["action"] == "add"
    ]
    assert accession in add_accession

    # assert we are removing the animal
    del_accession = [
        ch_a["object_kwargs"]["accession_number"]
        for ch_a in changeset["animals"]
        if ch_a["action"] == "del"
    ]
    assert accession in del_accession
