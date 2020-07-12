"""to be run from root directory
"""

import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")
django.setup()

from django.db.models.functions import Cast
from django.db.models.fields import DateField
from zoo_checks.models import AnimalCount, Enclosure, GroupCount, SpeciesCount
from django.db.models.functions import TruncDate
from django.utils import timezone
from zoo_checks.helpers import today_time

enclosures = Enclosure.objects.filter(name__in=["Australia", "Barramundi (ARG 1A)"])
tzinfo = "America/New York"
num_days = 1

animal_counts = (
    AnimalCount.objects.filter(
        enclosure__in=enclosures,
        datetimecounted__lte=timezone.localtime(),
        datetimecounted__gt=today_time() - timezone.timedelta(num_days),
    )
    .annotate(dateonlycounted=TruncDate("datetimecounted", tzinfo=tzinfo))
    .order_by("dateonlycounted", "animal_id")
    .distinct("dateonlycounted", "animal_id")
)
group_counts = (
    GroupCount.objects.filter(
        enclosure__in=enclosures,
        datetimecounted__lte=timezone.localtime(),
        datetimecounted__gt=today_time() - timezone.timedelta(num_days),
    )
    .annotate(dateonlycounted=TruncDate("datetimecounted", tzinfo=tzinfo))
    .order_by("dateonlycounted", "group_id")
    .distinct("dateonlycounted", "group_id")
)
species_counts = (
    SpeciesCount.objects.filter(
        enclosure__in=enclosures,
        datetimecounted__lte=timezone.localtime(),
        datetimecounted__gt=today_time() - timezone.timedelta(num_days),
    )
    .annotate(dateonlycounted=TruncDate("datetimecounted", tzinfo=tzinfo))
    .order_by("dateonlycounted", "species_id")
    .distinct("dateonlycounted", "species_id")
)

animal_dict = animal_counts.values()[0]
group_dict = group_counts.values()[0]
species_dict = species_counts.values()[0]

print(animal_dict)
print(animal_dict.keys())

print(group_dict)
print(group_dict.keys())

print(species_dict)
print(species_dict.keys())
