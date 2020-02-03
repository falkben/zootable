"""tiny script to check the num of digits/characters in all accession numbers
"""

import os
import sys

sys.path.append("zootable")

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")
django.setup()

from zoo_checks.models import Animal, Group


def num_digits(digit_list):
    len_a = list(map(lambda a: len(str(a)), digit_list))
    min_a = min(len_a)
    max_a = max(len_a)
    print(f"min: {min_a}, max: {max_a}")


animal_accession_nums = Animal.objects.all().values_list("accession_number", flat=True)
num_digits(animal_accession_nums)

group_accession_nums = Animal.objects.all().values_list("accession_number", flat=True)
num_digits(group_accession_nums)
