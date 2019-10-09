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


@admin.register(AnimalCount)
class AnimalCountAdmin(admin.ModelAdmin):
    readonly_fields = ("datetimecounted", "datecounted")


@admin.register(GroupCount)
class GroupCountAdmin(admin.ModelAdmin):
    readonly_fields = ("datetimecounted", "datecounted")


@admin.register(SpeciesCount)
class SpeciesCountAdmin(admin.ModelAdmin):
    readonly_fields = ("datetimecounted", "datecounted")


admin.site.register(Animal)
admin.site.register(Group)
admin.site.register(Enclosure)
admin.site.register(Species)
