"""This script parses a tracks file and enters it into the database
"""

# TODO: add genus for species

import sys
import os
import django
import re

sys.path.append("zootally")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")
django.setup()

# TODO: argparse so can call from command line

import pandas as pd


from zoo_checks.models import Animal, Exhibit, Species


DATAFILE = "zootally/tracks_data/Australia.Exhibit.Bird.Inventory.xlsx"


def get_species_obj(row):
    common_name = row["Common"]
    latin_name = row["Species"]
    return Species.objects.get(common_name=common_name, latin_name=latin_name)


def get_exhibit_obj(row):
    return Exhibit.objects.get(name=row["Enclosure"])


df = pd.read_excel(DATAFILE)

# exhibits
exhibits = set(df["Enclosure"])
# print(exhibits)
for exhibit in exhibits:
    if not Exhibit.objects.filter(name=exhibit).exists():
        Exhibit(name=exhibit).save()

# species
df_species = df.drop_duplicates(subset=["Common", "Species"])
# print(species)
for index, row in df_species.iterrows():
    common_name = row["Common"]
    latin_name = row["Species"]
    exhibit = get_exhibit_obj(row)
    existing_sp = Species.objects.filter(common_name=common_name, latin_name=latin_name)
    if not existing_sp.exists():
        sp = Species(common_name=common_name, latin_name=latin_name)
        sp.save()
    else:
        sp = Species.objects.get(common_name=common_name, latin_name=latin_name)
    if exhibit not in sp.exhibits.all():
        sp.exhibits.add(exhibit)


# animals
for index, row in df.iterrows():
    # name, active, accession, species, identifier, exhibit, sex

    # name and identifier stored in the same col. and can be any order
    tag_band = r"Tag/Band:([\w\s\d#]+)[,]?"
    mm = re.findall(tag_band, row["Identifiers"])
    identifier = ""
    if len(mm) > 0:
        identifier = ",".join(mm)

    intern_name = r"Internal House Name:([\w|\s]*)"
    mm = re.findall(intern_name, row["Identifiers"])
    if len(mm):
        name = ",".join(mm)

    # re_exp = f"{intern_name},{tag_band}|{tag_band},{intern_name}"
    # groups = re.match(re_exp, row["Identifiers"])
    # if groups is None or len(groups.groups()) < 4:
    # print("all ids not found")clear
    # name = groups[1] or groups[4]
    # identifier = groups[2] or groups[3]
    active = True
    accession_number = row["Accession"]
    species = get_species_obj(row)
    exhibit = get_exhibit_obj(row)
    sex = row["Sex"]
    if sex == "":
        sex = "U"

    if Animal.objects.filter(accession_number=accession_number).exists():
        # * This overrides anything in the database for this accession number
        anim = Animal.objects.get(accession_number=accession_number)
        anim.name = name
        anim.identifier = identifier
        anim.active = active
        anim.sex = sex
        anim.exhibit = exhibit
        anim.species = species
    else:
        anim = Animal(
            name=name,
            identifier=identifier,
            active=active,
            accession_number=accession_number,
            sex=sex,
            exhibit=exhibit,
            species=species,
        )
    anim.save()

