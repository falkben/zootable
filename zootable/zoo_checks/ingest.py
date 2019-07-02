import re
import pandas as pd

from zoo_checks.models import Animal, Enclosure, Group, Species, User


def read_xlsx_data(datafile):
    """Reads a xlsx datafile and returns a pandas dataframe
    """
    return pd.read_excel(datafile)


def get_enclosure_changeset(df):
    """Outputs list of dictionaries
    Each dictionary is an enclosure to add or remove
    containing name of enclosure and action to take
    """
    upload_enclosures = set(df["Enclosure"])

    db_enclosures = list(Enclosure.objects.all())
    db_enclosure_names = set([enc.name for enc in db_enclosures])

    add_enclosures = upload_enclosures - db_enclosure_names
    rem_enclosures = db_enclosure_names - upload_enclosures

    changeset = []

    def create_changeset_action(enc, action):
        return {"name": enc, "action": action}

    for add_enc in add_enclosures:
        changeset.append(create_changeset_action(add_enc, "add"))
    for rem_enc in rem_enclosures:
        changeset.append(create_changeset_action(rem_enc, "rem"))

    return changeset


def get_species_changeset(df):
    pass


def get_animal_changeset(df):
    pass


def get_group_changeset(df):
    pass


def get_changesets(df):
    enclosure_changeset = get_enclosure_changeset(df)

    # get_species_changeset(df)
    # get_animal_changeset(df)
    # get_group_changeset(df)

    changesets = {"enclosure": enclosure_changeset}

    return changesets


def handle_ingest(f):
    """Input: an xlsx file containing data to ingest
    Returns: changeset
    """
    df = read_xlsx_data(f)

    changeset = get_changesets(df)

    return changeset
