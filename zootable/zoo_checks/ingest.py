import re
import pandas as pd

from zoo_checks.models import Animal, Enclosure, Group, Species, User


def read_xlsx_data(datafile):
    """Reads a xlsx datafile and returns a pandas dataframe
    """
    return pd.read_excel(datafile)


def create_enclosures(df):
    """Given data in a pandas dataframe, create any missing enclosures
    """
    enclosures = set(df["Enclosure"])
    for enclosure in enclosures:
        encl, _ = Enclosure.objects.get_or_create(name=enclosure)
        encl.users.add(*list(User.objects.filter(is_superuser=True)))


def create_species(df):
    """Create any species that exist in the pandas dataframe but not in the database
    """
    df_species = df.drop_duplicates(
        subset=["Common", "GSS", "Species", "Class", "Order", "Family"]
    )
    for index, row in df_species.iterrows():
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


def create_groups(df):
    """Creates groups
    """
    # col names for groups:
    # active, accession_number, species, population_male, population_female, population_unknown, enclosure
    for index, row in df.iterrows():
        active, accession_number, species, enclosure = get_animal_set_info(row)
        population_male = row["Population _Male"]
        population_female = row["Population _Female"]
        population_unknown = row["Population _Unknown"]

        # * This overrides anything in the database for this accession number
        Group.objects.update_or_create(
            accession_number=accession_number,
            defaults={
                "active": active,
                "enclosure": enclosure,
                "species": species,
                "population_male": population_male,
                "population_female": population_female,
                "population_unknown": population_unknown,
            },
        )


def create_animals(df):
    """Creates animals (individuals)
    """
    for index, row in df.iterrows():
        # zootable animal col names:
        # name, active, accession, species, identifier, enclosure, sex
        active, accession_number, species, enclosure = get_animal_set_info(row)
        identifier = get_animal_identifier(row["Identifiers"])
        name = get_animal_name(row["Identifiers"])
        sex = get_sex(row)

        # * This overrides anything in the database for this accession number
        Animal.objects.update_or_create(
            accession_number=accession_number,
            defaults={
                "name": name,
                "identifier": identifier,
                "active": active,
                "sex": sex,
                "enclosure": enclosure,
                "species": species,
            },
        )


def create_changeset_action(action, **kwargs):
    changeset = {"action": action}
    changeset.update(kwargs)
    return changeset


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
    """Returns an Enclosure object from database given its name
    """
    return Enclosure.objects.get(name=row["Enclosure"])


def get_animal_set_info(row):
    """returns data common to all animal_sets
    """
    active = True
    accession_number = row["Accession"]
    species = get_species_obj(row)
    enclosure = get_enclosure_obj(row)
    return active, accession_number, species, enclosure


def find_animals_groups(df):
    """given a dataframe, return animals and groups dataframes based on population of each row (> 1 == group)
    """
    pop_sums = df[
        ["Population _Male", "Population _Female", "Population _Unknown"]
    ].sum(axis=1)
    groups = df[pop_sums > 1]
    animals = df[pop_sums == 1]
    return animals, groups


def get_animal_changeset(animals):
    """Iterate over every animal
    For each animal, determine if any of its attributes changed
    Record changes as a changeset for that animal
    """

    pass


def get_group_changeset(groups):
    """Iterate over every group
    For each animal, determine if any of its attributes changed
    Record changes as a changeset for that animal
    """
    pass


def get_changesets(df):
    animals, groups = find_animals_groups(df)
    animal_changeset = get_animal_changeset(animals)
    group_changeset = get_group_changeset(groups)

    changesets = {"animals": animal_changeset, "groups": group_changeset}

    return changesets


def handle_ingest(f):
    """Input: an xlsx file containing data to ingest
    Returns: changeset
    """
    df = read_xlsx_data(f)

    changeset = get_changesets(df)

    return changeset
