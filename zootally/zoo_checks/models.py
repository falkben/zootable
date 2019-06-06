from django.db import models
from django.contrib.auth.models import User


class Exhibit(models.Model):
    name = models.CharField(max_length=60)

    user = models.ManyToManyField(User)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]


class Species(models.Model):
    common_name = models.CharField(max_length=80)
    latin_name = models.CharField(max_length=80)

    exhibits = models.ManyToManyField(Exhibit, related_name="species")

    def __str__(self):
        return self.common_name

    class Meta:
        ordering = ["common_name"]


class Animal(models.Model):
    name = models.CharField(max_length=40)
    accession_number = models.PositiveIntegerField(unique=True)
    identifier = models.CharField(max_length=40)

    species = models.ForeignKey(Species, on_delete=models.CASCADE)
    exhibit = models.ForeignKey(
        Exhibit, on_delete=models.CASCADE, related_name="animals"
    )

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]


class Count(models.Model):
    datecounted = models.DateField(auto_now=True)

    users = models.ManyToManyField(User)

    class Meta:
        abstract = True
        ordering = ["datecounted"]


class AnimalCount(Count):
    SEEN = "SE"
    NEEDSATTENTION = "NA"
    BAR = "BA"
    MISSING = "MI"

    CONDITIONS = [
        ("", ""),
        (SEEN, "seen"),
        (NEEDSATTENTION, "Needs Attention"),
        (BAR, "BAR (Sr. Avic.)"),
        (MISSING, "Missing (Avic. only)"),
    ]

    condition = models.CharField(
        max_length=2, choices=CONDITIONS, default="", blank=True
    )

    animal = models.ForeignKey(Animal, on_delete=models.CASCADE)
    exhibit = models.ForeignKey(Exhibit, on_delete=models.CASCADE)


class SpeciesCount(Count):
    count = models.PositiveSmallIntegerField(default=0)

    species = models.ForeignKey(Species, on_delete=models.CASCADE)
    exhibit = models.ForeignKey(Exhibit, on_delete=models.CASCADE)
