"""This script parses an xlsx file and enters it into the database
Callable:
python ingest_xlsx_data.py YOURFILE.xlsx
"""

import argparse
import os
import sys

sys.path.append("zootable")

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")
django.setup()

from zoo_checks.ingest import (
    read_xlsx_data,
    create_enclosures,
    create_species,
    find_animals_groups,
    create_animals,
    create_groups,
)


def main():
    parser = argparse.ArgumentParser(description="Parse csv file for animals")
    parser.add_argument("csvfile")
    args = parser.parse_args()

    df = read_xlsx_data(args.csvfile)
    create_enclosures(df)
    create_species(df)

    animals, groups = find_animals_groups(df)
    create_animals(animals)
    create_groups(groups)

    print(f"Processed {args.csvfile}")


if __name__ == "__main__":
    main()
