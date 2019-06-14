from django.contrib import admin

from zoo_checks.models import (
    Animal,
    AnimalCount,
    Enclosure,
    Group,
    GroupCount,
    Species,
    SpeciesCount,
)

admin.site.register(Animal)
admin.site.register(AnimalCount)
admin.site.register(Group)
admin.site.register(GroupCount)
admin.site.register(Enclosure)
admin.site.register(Species)
admin.site.register(SpeciesCount)
