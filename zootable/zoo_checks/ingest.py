import re
import pandas as pd

from zoo_checks.models import Animal, Enclosure, Group, Species, User


def read_xlsx_data(datafile):
    """Reads a xlsx datafile and returns a pandas dataframe
    """
    return pd.read_excel(datafile)


def create_changeset_action(action, **kwargs):
    changeset = {"action": action}
    changeset.update(kwargs)
    return changeset


def get_enclosure_changeset(df):
    """Outputs list of dictionaries
    Each dictionary is an enclosure to add or remove
    containing name of enclosure and action to take
    """
    # returns a set of enclosure names
    upload_enclosures = set(df["Enclosure"])

    # enclosure names are a unique field
    db_enclosure_names = set(Enclosure.objects.values_list("name", flat=True))

    add_enclosures = upload_enclosures - db_enclosure_names
    rem_enclosures = db_enclosure_names - upload_enclosures

    changeset = []

    for add_enc in add_enclosures:
        changeset.append(create_changeset_action("add", name=add_enc))
    for rem_enc in rem_enclosures:
        changeset.append(create_changeset_action("rem", name=rem_enc))

    return changeset


def get_species_changeset(df):
    """Outputs list of dictionaries
    Each dictionary is an species to add or remove
    """

    # returns dataframe with species specific data
    df_species = df.drop_duplicates(
        subset=["Common", "GSS", "Species", "Class", "Order", "Family"]
    )
    upload_obj_names = set(df_species["Common"])

    db_obj_names = set(Species.objects.values_list("common_name", flat=True))

    add_objs = upload_obj_names - db_obj_names
    rem_objs = db_obj_names - upload_obj_names

    changeset = []

    for obj_name in add_objs:
        spec_row = df_species.loc[df_species["Common"] == obj_name]
        changeset.append(
            create_changeset_action(
                "add",
                common_name=spec_row["Common"].values[0],
                species_name=spec_row["Species"].values[0],
                genus_name=spec_row["GSS"].values[0],
                class_name=spec_row["Class"].values[0],
                order_name=spec_row["Order"].values[0],
                family_name=spec_row["Family"].values[0],
            )
        )
    for obj_name in rem_objs:
        spec_data = Species.objects.get(common_name=obj_name)
        changeset.append(
            create_changeset_action(
                "rem",
                common_name=spec_data.common_name,
                species_name=spec_data.species_name,
                genus_name=spec_data.genus_name,
                class_name=spec_data.class_name,
                order_name=spec_data.order_name,
                family_name=spec_data.family_name,
            )
        )

    return changeset


def get_animal_changeset(df):
    pass


def get_group_changeset(df):
    pass


def get_changesets(df):
    enclosure_changeset = get_enclosure_changeset(df)

    species_changeset = get_species_changeset(df)

    # animal_changeset = get_animal_changeset(df)
    # group_changeset = get_group_changeset(df)

    changesets = {"enclosure": enclosure_changeset, "species": species_changeset}

    return changesets


def handle_ingest(f):
    """Input: an xlsx file containing data to ingest
    Returns: changeset
    """
    df = read_xlsx_data(f)

    changeset = get_changesets(df)

    return changeset
