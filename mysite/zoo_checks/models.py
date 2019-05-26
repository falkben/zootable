from django.db import models
from django.contrib.auth.models import User


class Exhibit(models.Model):
    name = models.CharField(max_length=60)

    user = models.ManyToManyField(User)


class Species(models.Model):
    name = models.CharField(max_length=80)

    exhibits = models.ManyToManyField(Exhibit)


class Animal(models.Model):
    name = models.CharField(max_length=40)
    accession_number = models.PositiveIntegerField()
    identifier = models.CharField(max_length=40)

    species = models.ForeignKey(Species, on_delete=models.CASCADE)
    exhibit = models.ForeignKey(Exhibit, on_delete=models.CASCADE)


class Count(models.Model):
    count_val = models.PositiveSmallIntegerField(default=0)
    count_date = models.DateTimeField()

    user = models.ManyToManyField(User)

    class Meta:
        abstract = True


class AnimalCount(Count):
    animal = models.ForeignKey(Animal, on_delete=models.CASCADE)


class SpeciesExhibitCount(Count):
    species = models.ForeignKey(Species, on_delete=models.CASCADE)
    exhibit = models.ForeignKey(Exhibit, on_delete=models.CASCADE)
