import os
import sys

sys.path.append("zootable")

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")
django.setup()

from zoo_checks.models import AnimalCount, GroupCount, SpeciesCount
from django.utils import timezone
from zoo_checks.helpers import today_time

all_animal_counts = AnimalCount.objects.filter(
    datetimecounted__lt=today_time() - timezone.timedelta(days=60)
).order_by("animal__id", "-datetimecounted", "-id")

uniq_animal_counts = (
    AnimalCount.objects.filter(
        datetimecounted__lt=today_time() - timezone.timedelta(days=60)
    )
    .order_by("animal__id", "-datecounted", "-datetimecounted", "-id", "animal")
    .distinct("animal__id", "datecounted")
)

for animal_count in uniq_animal_counts:
    # print(animal_count)
    dup_counts = all_animal_counts.filter(
        animal=animal_count.animal,
        enclosure=animal_count.enclosure,
        datecounted=animal_count.datecounted,
    )

    for dup_count in dup_counts[1:]:
        dup_count.delete()
