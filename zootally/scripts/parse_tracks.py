"""This script parses a tracks file and enters it into the database
"""

import os
import re
import sys

sys.path.append("zootally")

import django
import pandas as pd

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")
django.setup()

from zoo_checks.models import Animal, Enclosure, Group, Species, User

# TODO: argparse so can call from command line


# DATAFILE = "zootally/tracks_data/Australia.Exhibit.Bird.Inventory.xlsx"
DATAFILE = "zootally/tracks_data/BTR.Inventory.xlsx"


def get_species_obj(row):
    common_name = row["Common"]
    species_name = row["Species"]
    genus_name = row["GSS"]
    return Species.objects.get(
        common_name=common_name, genus_name=genus_name, species_name=species_name
    )


def get_enclosure_obj(row):
    """Returns an Enclosure object from database given its name
    """
    return Enclosure.objects.get(name=row["Enclosure"])


def read_tracks(datafile):
    """Reads a tracks datafile and returns a pandas dataframe
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
    df_species = df.drop_duplicates(subset=["Common", "GSS", "Species"])
    for index, row in df_species.iterrows():
        common_name = row["Common"]
        genus_name = row["GSS"]
        species_name = row["Species"]
        Species.objects.get_or_create(
            common_name=common_name, genus_name=genus_name, species_name=species_name
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
        group = Group.objects.update_or_create(
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
        anim = Animal.objects.update_or_create(
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


def main():
    df = read_tracks(DATAFILE)
    create_enclosures(df)
    create_species(df)

    animals, groups = find_animals_groups(df)
    create_animals(animals)
    create_groups(groups)

    print(f"Processed, {DATAFILE}")


if __name__ == "__main__":
    main()
