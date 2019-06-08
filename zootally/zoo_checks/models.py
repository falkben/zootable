from django.db import models
from django.contrib.auth.models import User


class Exhibit(models.Model):
    name = models.CharField(max_length=50, unique=True)

    user = models.ManyToManyField(User)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]


class Species(models.Model):
    # TODO: add genus name
    common_name = models.CharField(max_length=80)
    latin_name = models.CharField(max_length=80)

    def __str__(self):
        return self.common_name

    class Meta:
        ordering = ["common_name"]


class AnimalSet(models.Model):
    name = models.CharField(max_length=40)
    active = models.BooleanField(default=True)
    accession_number = models.PositiveIntegerField(unique=True)

    species = models.ForeignKey(Species, on_delete=models.CASCADE)

    class Meta:
        abstract = True
        ordering = ["name"]

    def __str__(self):
        return " | ".join((self.name, str(self.accession_number)))


class Animal(AnimalSet):
    """An AnimalSet of 1
    """

    SEX = [("M", "Male"), ("F", "Female"), ("U", "Unknown")]

    identifier = models.CharField(max_length=40)
    sex = models.CharField(max_length=1, choices=SEX, default="U")

    exhibit = models.ForeignKey(
        Exhibit, on_delete=models.SET_NULL, related_name="animals", null=True
    )


class Group(AnimalSet):
    """Same as an animal, just represents a group of them w/ no identifier
    """

    population_male = models.PositiveSmallIntegerField(default=0)
    population_female = models.PositiveSmallIntegerField(default=0)
    population_unknown = models.PositiveSmallIntegerField(default=0)

    exhibit = models.ForeignKey(
        Exhibit, on_delete=models.SET_NULL, related_name="groups", null=True
    )


class Count(models.Model):
    datecounted = models.DateField(auto_now=True)

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    exhibit = models.ForeignKey(Exhibit, on_delete=models.SET_NULL, null=True)

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

    def __str__(self):
        return "|".join((self.animal.name, str(self.datecounted), self.condition))


class GroupCount(Count):
    count_male = models.PositiveSmallIntegerField(default=0)
    count_female = models.PositiveSmallIntegerField(default=0)
    count_unknown = models.PositiveSmallIntegerField(default=0)

    group = models.ForeignKey(Group, on_delete=models.CASCADE)

    def __str__(self):
        return str(self.count)


class SpeciesCount(Count):
    count = models.PositiveSmallIntegerField(default=0)

    species = models.ForeignKey(Species, on_delete=models.CASCADE)

    def __str__(self):
        return "|".join(
            (self.species.common_name, str(self.datecounted), str(self.count))
        )
