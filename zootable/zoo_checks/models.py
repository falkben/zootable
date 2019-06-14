from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.utils import timezone

from .helpers import today_time


class Enclosure(models.Model):
    name = models.CharField(max_length=50, unique=True)

    users = models.ManyToManyField(User)

    def __str__(self):
        return self.name

    def species(self):
        """Combines exhibit's animals' species and groups' species together 
        into a distinct queryset of species
        """
        animals = self.animals.all().order_by("species__common_name", "name")
        groups = self.groups.all().order_by("species__common_name")
        animal_species = Species.objects.filter(animal__in=animals)
        group_species = Species.objects.filter(group__in=groups)

        return (animal_species | group_species).distinct()

    class Meta:
        ordering = ["name"]


class Species(models.Model):
    common_name = models.CharField(max_length=80)
    species_name = models.CharField(max_length=80)
    genus_name = models.CharField(max_length=80)

    def __str__(self):
        return ", ".join((self.genus_name, self.species_name))

    class Meta:
        ordering = ["common_name"]

    def get_count_day(self, day=today_time()):
        count = 0
        day_counts = self.counts.filter(
            datecounted__gte=day, datecounted__lt=day + timezone.timedelta(days=1)
        )
        if day_counts.exists():
            # in case there is more than one this takes the max
            count = day_counts.aggregate(models.Max("count"))["count__max"]

        return count

    @property
    def current_count(self):

        return self.get_count_day()

    @property
    def prior_counts(self, prior_days=3):
        counts = [0] * prior_days
        for p in range(prior_days):
            day = today_time() - timezone.timedelta(days=p + 1)
            counts[p] = self.get_count_day(day)

        return counts


class AnimalSet(models.Model):
    active = models.BooleanField(default=True)
    accession_number = models.PositiveIntegerField(unique=True)

    species = models.ForeignKey(Species, on_delete=models.CASCADE)

    class Meta:
        abstract = True


class Animal(AnimalSet):
    """An AnimalSet of 1
    """

    SEX = [("M", "Male"), ("F", "Female"), ("U", "Unknown")]

    name = models.CharField(max_length=40)
    identifier = models.CharField(max_length=40)
    sex = models.CharField(max_length=1, choices=SEX, default="U")

    enclosure = models.ForeignKey(
        Enclosure, on_delete=models.SET_NULL, related_name="animals", null=True
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return "|".join(
            (self.name, self.identifier, self.sex, str(self.accession_number))
        )

    @property
    def current_condition(self):
        try:
            cond = self.conditions.latest("datecounted").condition
        except ObjectDoesNotExist:
            cond = ""
        return cond

    @property
    def prior_conditions(self, prior_days=3):
        """Given a set of animals, returns their counts from the prior N days
        """
        conds = [""] * prior_days
        for p in range(prior_days):
            day = today_time() - timezone.timedelta(days=p + 1)
            try:
                conds[p] = (
                    self.conditions.filter(
                        datecounted__gte=day,
                        datecounted__lt=day + timezone.timedelta(days=1),
                    )
                    .latest("datecounted")
                    .condition
                )
            except ObjectDoesNotExist:
                pass

        return conds


class Group(AnimalSet):
    """Same as an animal, just represents a group of them w/ no identifier
    """

    population_male = models.PositiveSmallIntegerField(default=0)
    population_female = models.PositiveSmallIntegerField(default=0)
    population_unknown = models.PositiveSmallIntegerField(default=0)

    enclosure = models.ForeignKey(
        Enclosure, on_delete=models.SET_NULL, related_name="groups", null=True
    )

    class Meta:
        ordering = ["species__common_name"]

    def __str__(self):
        return "|".join((self.species.common_name, self.accession_number))

    def get_count_day(self, day=today_time()):
        m_count = f_count = u_count = 0

        day_counts = self.counts.filter(
            datecounted__gte=day, datecounted__lt=day + timezone.timedelta(days=1)
        )
        if day_counts.exists():
            # in case there is more than one this takes the max
            m_count = day_counts.aggregate(models.Max("count_male"))["count_male__max"]
            f_count = day_counts.aggregate(models.Max("count_female"))[
                "count_female__max"
            ]
            u_count = day_counts.aggregate(models.Max("count_unknown"))[
                "count_unknown__max"
            ]

        return m_count, f_count, u_count

    @property
    def current_count(self):
        m_count, f_count, u_count = self.get_count_day()
        return m_count, f_count, u_count

    @property
    def prior_counts(self, prior_days=3):
        counts = [0] * prior_days
        for p in range(prior_days):
            day = today_time() - timezone.timedelta(days=p + 1)
            counts[p] = self.get_count_day(day)

        return counts


class Count(models.Model):
    datecounted = models.DateTimeField(auto_now=True)

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    enclosure = models.ForeignKey(Enclosure, on_delete=models.SET_NULL, null=True)

    class Meta:
        abstract = True
        ordering = ["datecounted"]


class AnimalCount(Count):
    SEEN = "SE"
    NEEDSATTENTION = "NA"
    # bright active responsive (the best)
    BAR = "BA"

    CONDITIONS = [(BAR, "BAR"), (SEEN, "Seen"), (NEEDSATTENTION, "Attn")]

    condition = models.CharField(max_length=2, choices=CONDITIONS)

    animal = models.ForeignKey(
        Animal, on_delete=models.CASCADE, related_name="conditions"
    )

    def __str__(self):
        return "|".join(
            (
                self.animal.name,
                self.user.username,
                self.datecounted.strftime("%Y-%m-%d"),
                self.condition,
            )
        )


class GroupCount(Count):
    count_male = models.PositiveSmallIntegerField(default=0)
    count_female = models.PositiveSmallIntegerField(default=0)
    count_unknown = models.PositiveSmallIntegerField(default=0)

    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="counts")

    def __str__(self):
        return "|".join(
            (
                self.group.species.common_name,
                self.user.username,
                self.datecounted.strftime("%Y-%m-%d"),
                str(self.count),
            )
        )


class SpeciesCount(Count):
    count = models.PositiveSmallIntegerField(default=0)

    species = models.ForeignKey(
        Species, on_delete=models.CASCADE, related_name="counts"
    )

    def __str__(self):
        return "|".join(
            (
                self.species.common_name,
                self.user.username,
                self.datecounted.strftime("%Y-%m-%d"),
                str(self.count),
            )
        )
