from django.contrib import admin

from zoo_checks.models import Animal, AnimalCount, Exhibit, Group, Species, SpeciesCount

admin.site.register(Animal)
admin.site.register(AnimalCount)
admin.site.register(Group)
admin.site.register(Exhibit)
admin.site.register(Species)
admin.site.register(SpeciesCount)
