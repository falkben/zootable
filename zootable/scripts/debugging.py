"""to be run from root directory
"""

import os
import sys

sys.path.append("zootable")

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")
django.setup()

from django.db.models.functions import Cast
from django.db.models.fields import DateField
from zoo_checks.models import AnimalCount, Enclosure

enclosures = Enclosure.objects.filter(name="Australia")

animal_counts = (
    AnimalCount.objects.filter(enclosure__in=enclosures)
    .annotate(dateonlycounted=Cast("datecounted", DateField()))
    .order_by("dateonlycounted")
    .distinct("dateonlycounted")
)


print(animal_counts)

for c in animal_counts:
    print(c.id, c, "\\", c.datecounted, "\\", c.dateonlycounted)
