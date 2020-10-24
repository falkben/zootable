from operator import itemgetter
import re

import pandas as pd
from django.core.exceptions import ObjectDoesNotExist

from zoo_checks.models import Animal, Enclosure, Group, Species

TRACKS_REQ_COLS = [
    "Enclosure",
    "Accession",
    "Common",
    "Class",
    "Order",
    "Family",
    "GSS",
    "Species",
    "Sex",
    "Identifiers",  # * contains both name and identifier for an animal
    "Population _Male",
    "Population _Female",
    "Population _Unknown",
]


def validate(df):
    """xlsx file needs certain columns, can't be empty"""

    df_col_names = list(df.columns)

    # ensure # of rows > 0
    if not df.shape[0] > 0:
        raise TypeError("No data found in file")

    if not all([col in df_col_names for col in TRACKS_REQ_COLS]):
        raise TypeError("Not all columns found in file")

    df["Accession"] = df["Accession"].apply(str)

    return df[TRACKS_REQ_COLS]


def read_xlsx_data(datafile):
    """Reads a xlsx datafile and returns a pandas dataframe"""
    try:
        df = pd.read_excel(datafile)
        df = validate(df)
    except Exception as e:
        raise e
    return df


def get_enclosures(df):
    return set(df["Enclosure"])


def create_enclosures(df):
    """Given data in a pandas dataframe, create any missing enclosures"""
    enclosures = get_enclosures(df)
    for enclosure in enclosures:
        create_enclosure_name(enclosure)


def create_enclosure_name(enclosure_name):
    encl, _ = Enclosure.objects.get_or_create(name=enclosure_name)


def create_species(df):
    """Create any species that exist in the pandas dataframe but not in the database"""
    df_species = df.drop_duplicates(
        subset=["Common", "GSS", "Species", "Class", "Order", "Family"]
    )
    for _, row in df_species.iterrows():
        common_name = row["Common"]
        genus_name = row["GSS"]
        species_name = row["Species"]
        class_name = row["Class"]
        order_name = row["Order"]
        family_name = row["Family"]
        Species.objects.update_or_create(
            common_name=common_name,
            defaults={
                "genus_name": genus_name,
                "species_name": species_name,
                "class_name": class_name,
                "order_name": order_name,
                "family_name": family_name,
            },
        )


def get_animal_identifier(identifiers):
    """Returns any identifiers joined into a single string, comma separated
    Name and identifier stored in the same col. and can be any order
    """
    if pd.isna(identifiers):
        return ""
    # finds any sections of text following "Tag/Band:" optionally followed by a comma
    tag_band = r"Tag/Band:([\w\s\d#]*)[,]?"
    mm = re.findall(tag_band, identifiers)
    tag = ",".join(mm)
    return tag


def get_sex(row):
    # start with sex being unknown
    sex = "U"
    # use sex column as primary
    if not pd.isna(row["Sex"]):
        # sets sex to either M/F/U
        sex = row["Sex"]
    # use population values as secondary if available
    else:
        if row["Population _Male"] == 1:
            sex = "M"
        if row["Population _Female"] == 1:
            sex = "F"
    return sex


def get_group_attributes(row):
    active, accession_number, species, enclosure = get_animal_set_info(row)
    population_male = row["Population _Male"]
    population_female = row["Population _Female"]
    population_unknown = row["Population _Unknown"]

    # todo: we need to make sure we grab _all_ the attributes
    # something like Model._meta.get_fields()

    attributes = {
        "accession_number": accession_number,
        "active": active,
        "enclosure": enclosure,
        "species": species,
        "population_male": population_male,
        "population_female": population_female,
        "population_unknown": population_unknown,
        "population_total": population_male + population_female + population_unknown,
    }

    return attributes


def create_groups(df):
    """Creates groups"""

    # we sometimes don't have any to add
    if len(df.index) == 0:
        return None

    pop_sum = df[["Population _Male", "Population _Female", "Population _Unknown"]].sum(
        axis=1
    )
    try:
        assert all(pop_sum > 1)
    except AssertionError:
        raise ValueError("Cannot create groups. Not all have a pop. > 1")

    # col names for groups:
    # active, accession_number, species, population_male, population_female,
    # population_unknown, enclosure, population_total
    for _, row in df.iterrows():
        attributes = get_group_attributes(row)

        # * This overrides anything in the database for this accession number
        Group.objects.update_or_create(
            accession_number=attributes.pop("accession_number"), defaults=attributes
        )


def get_animal_attributes(row):
    # zootable animal col names:
    # name, active, accession, species, identifier, enclosure, sex

    # todo: we need to always make sure we grab _all_ the attributes

    active, accession_number, species, enclosure = get_animal_set_info(row)
    identifier = get_animal_identifier(row["Identifiers"])
    name = get_animal_name(row["Identifiers"])
    sex = get_sex(row)

    attributes = {
        "accession_number": accession_number,
        "name": name,
        "identifier": identifier,
        "active": active,
        "sex": sex,
        "enclosure": enclosure,
        "species": species,
    }

    return attributes


def create_animals(df):
    """Creates animals (individuals)"""

    # we sometimes don't have any to add
    if len(df.index) == 0:
        return None

    pop_sum = df[["Population _Male", "Population _Female", "Population _Unknown"]].sum(
        axis=1
    )
    try:
        assert all(pop_sum == 1)
    except AssertionError:
        raise ValueError("Cannot create individuals. Not all have a pop. of 1")

    for _, row in df.iterrows():
        attributes = get_animal_attributes(row)

        # * This overrides anything in the database for this accession number
        Animal.objects.update_or_create(
            accession_number=attributes.pop("accession_number"), defaults=attributes
        )


def change_obj_active_state(model, accession_number, active_state):
    """Marks an animal/group active/inactive"""
    obj = model.objects.get(accession_number=accession_number)
    obj.active = active_state
    obj.save()


def get_animal_name(identifiers):
    """Returns the name of the animal, if mult. comma separated
    Name and identifier stored in same
    """
    if pd.isna(identifiers):
        return ""
    # finds any sections of text following "Internal House Name:"
    intern_name = r"Internal House Name:([\w|\s\d#]*)[,]?"
    mm = re.findall(intern_name, identifiers)
    name = ",".join(mm)
    return name


def get_species_obj(row):
    # common names are unique
    return Species.objects.get(common_name=row["Common"])


def get_enclosure_obj(row):
    """Returns an Enclosure object from database given its name"""
    return Enclosure.objects.get(name=row["Enclosure"])


def get_animal_set_info(row):
    """returns data common to all animal_sets"""
    active = True
    accession_number = row["Accession"]
    species = get_species_obj(row)
    enclosure = get_enclosure_obj(row)
    return active, accession_number, species, enclosure


def find_animals_groups(df):
    """given a dataframe, return animals and groups dataframes based on population of
    each row (> 1 == group)"""
    pop_sums = df[
        ["Population _Male", "Population _Female", "Population _Unknown"]
    ].sum(axis=1)
    groups = df[pop_sums > 1]
    animals = df[pop_sums == 1]
    return animals, groups


def create_changeset_action(action, **kwargs):
    changeset = {"action": action}
    changeset.update(kwargs)
    return changeset


def get_objs_to_delete(df, modeltype, enclosure_names):
    changesets = []

    # * mark for delete any anim/grps that get switched from one type to the other
    upload_accession_numbers = set(df["Accession"])

    enclosure_objects = Enclosure.objects.filter(name__in=enclosure_names)

    # "active" animals/groups in included enclosures that aren't in uploaded accession
    # nums need to be deleted
    objs_to_delete = modeltype.objects.filter(
        active=True, enclosure__in=enclosure_objects
    ).exclude(accession_number__in=upload_accession_numbers)

    for obj in objs_to_delete:
        obj_attrs = obj.to_dict()
        obj_attrs.pop("id")
        changesets.append(
            create_changeset_action(
                "del", object_kwargs=obj_attrs, enclosure=obj.enclosure.name
            )
        )

    changesets.sort(key=itemgetter("enclosure"))

    return changesets


def get_modeltype_changeset(df, modeltype):
    """Generic way to get list of changesets
    Iterate over every object
    For each object, determine if any of its attributes changed
    Record changes as a changeset for that object
    """

    add_update_changesets = []

    for _, row in df.iterrows():
        try:
            # if this doesn't fail, an entry exists for that modeltype
            modeltype.objects.get(accession_number=row["Accession"])

            # * this is not necessarily an update if there's been no change
            # TODO: separate type added if nothing changed
            add_update_changesets.append(
                create_changeset_action(
                    "update", object_kwargs=row.to_dict(), enclosure=row["Enclosure"]
                )
            )
        except ObjectDoesNotExist:
            # an addition for this modeltype
            add_update_changesets.append(
                create_changeset_action(
                    "add", object_kwargs=row.to_dict(), enclosure=row["Enclosure"]
                )
            )

            # todo: check to see if it's a deletion of the other model type here?

    add_update_changesets.sort(key=itemgetter("enclosure"))

    return add_update_changesets


def get_changesets(df):
    # get set of enclosures the user loaded; that data is expected to be complete
    enclosures_uploaded = get_enclosures(df)

    animals, groups = find_animals_groups(df)

    del_anim_changesets = get_objs_to_delete(animals, Animal, enclosures_uploaded)
    del_group_changesets = get_objs_to_delete(groups, Group, enclosures_uploaded)

    animal_changeset = get_modeltype_changeset(animals, Animal)
    group_changeset = get_modeltype_changeset(groups, Group)

    changesets = {
        "animals": animal_changeset + del_anim_changesets,
        "groups": group_changeset + del_group_changesets,
        "enclosures": list(enclosures_uploaded),
    }

    return changesets


def validate_input(df):
    # check that all accession numbers are of 6 digit length
    digit_list = df["Accession"]
    digits = list(map(lambda a: len(str(a)), digit_list))
    if any(d != 6 for d in digits):
        raise ValueError("Accession numbers should only have 6 characters")

    return df


def handle_upload(f):
    """Input: an xlsx file containing data to ingest
    Returns: changeset
    """
    df = read_xlsx_data(f)

    df_validated = validate_input(df)

    changeset = get_changesets(df_validated)

    return changeset


def ingest_changesets(changesets):
    # create new enclosures
    for enc_name in changesets.get("enclosures"):
        create_enclosure_name(enc_name)

    # create new species
    anim_add_dict = [
        value["object_kwargs"]
        for value in changesets.get("animals")
        if value["action"] in ("add", "update")
    ]
    grp_add_dict = [
        value["object_kwargs"]
        for value in changesets.get("groups")
        if value["action"] in ("add", "update")
    ]

    add_dict = anim_add_dict + grp_add_dict
    add_df = pd.DataFrame(add_dict)
    create_species(add_df)

    # create new animals
    anim_add_df = pd.DataFrame(anim_add_dict)
    create_animals(anim_add_df)

    # create new groups
    grp_add_df = pd.DataFrame(grp_add_dict)
    create_groups(grp_add_df)

    # make inactive animals
    inactive_animals = [
        value["object_kwargs"]
        for value in changesets.get("animals")
        if value["action"] == "del"
    ]
    for obj in inactive_animals:
        change_obj_active_state(Animal, obj["accession_number"], False)

    # make inactive groups
    inactive_groups = [
        value["object_kwargs"]
        for value in changesets.get("groups")
        if value["action"] == "del"
    ]
    for obj in inactive_groups:
        change_obj_active_state(Group, obj["accession_number"], False)
