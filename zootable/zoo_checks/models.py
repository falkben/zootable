from itertools import chain

from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.utils import timezone
from django_extensions.db.fields import AutoSlugField

from .helpers import today_time


class Enclosure(models.Model):
    name = models.CharField(max_length=50, unique=True)

    slug = AutoSlugField(null=True, default=None, populate_from="name", unique=True)

    users = models.ManyToManyField(User)

    def __str__(self):
        return self.name

    def species(self):
        """Combines exhibit's animals' species and groups' species together 
        into a distinct queryset of species
        """
        animals = (
            self.animals.all()
            .filter(active=True)
            .order_by("species__common_name", "name")
        )
        groups = self.groups.all().filter(active=True).order_by("species__common_name")
        animal_species = Species.objects.filter(animal__in=animals)
        group_species = Species.objects.filter(group__in=groups)

        return (animal_species | group_species).distinct()

    class Meta:
        ordering = ["name"]


class Species(models.Model):
    common_name = models.CharField(max_length=50, unique=True)
    species_name = models.CharField(max_length=50)
    genus_name = models.CharField(max_length=50)
    class_name = models.CharField(max_length=50)
    order_name = models.CharField(max_length=50)
    family_name = models.CharField(max_length=50)

    slug = AutoSlugField(
        null=True,
        default=None,
        populate_from=["common_name", "species_name"],
        unique=True,
    )

    def __str__(self):
        return ", ".join((self.genus_name, self.species_name))

    class Meta:
        ordering = ["common_name"]
        verbose_name_plural = "species"

    def get_count_day(self, enclosure, day=None):
        if day is None:
            day = today_time()
        try:
            count = self.counts.filter(
                datetimecounted__gte=day,
                datetimecounted__lt=day + timezone.timedelta(days=1),
                enclosure=enclosure,
            ).latest("datetimecounted", "id")
        except ObjectDoesNotExist:
            count = None

        return count

    def current_count(self, enclosure):
        count = self.get_count_day(enclosure)

        if count is None:
            count = {"count": 0, "day": today_time()}
        else:
            count = {"count": count.count, "day": today_time()}
        return count

    def prior_counts(self, enclosure, prior_days=3):
        counts = [0] * prior_days
        for p in range(prior_days):
            day = today_time() - timezone.timedelta(days=p + 1)
            count = self.get_count_day(enclosure, day)
            if count is None:
                count = {"count": 0, "day": day}
            else:
                count = {"count": count.count, "day": day}
            counts[p] = count

        return counts


class AnimalSet(models.Model):
    active = models.BooleanField(default=True)
    accession_number = models.PositiveIntegerField(unique=True)

    species = models.ForeignKey(Species, on_delete=models.CASCADE)

    class Meta:
        abstract = True

    def to_dict(self, fields=None, exclude=None):
        opts = self._meta
        data = {}
        for f in chain(opts.concrete_fields, opts.private_fields, opts.many_to_many):
            if not getattr(f, "editable", False):
                continue
            if fields and f.name not in fields:
                continue
            if exclude and f.name in exclude:
                continue

            # the change from model_to_dict(obj):
            if f.is_relation:
                data[f.name] = str(
                    f.related_model.objects.get(pk=f.value_from_object(self))
                )
            else:
                data[f.name] = f.value_from_object(self)

        return data


class Animal(AnimalSet):
    """An AnimalSet of 1
    """

    SEX = [("M", "Male"), ("F", "Female"), ("U", "Unknown")]

    name = models.CharField(max_length=40)
    identifier = models.CharField(max_length=40)
    sex = models.CharField(max_length=1, choices=SEX, default="U")

    slug = AutoSlugField(
        null=True, default=None, populate_from=["accession_number"], unique=True
    )

    enclosure = models.ForeignKey(
        Enclosure, on_delete=models.SET_NULL, related_name="animals", null=True
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return "|".join(
            (self.name, self.identifier, self.sex, str(self.accession_number))
        )

    def count_on_day(self, day=None):
        if day is None:
            day = today_time()
        try:
            count = self.conditions.filter(
                datetimecounted__gte=day,
                datetimecounted__lt=day + timezone.timedelta(days=1),
            ).latest("datetimecounted", "id")
        except ObjectDoesNotExist:
            count = None

        return count

    def condition_on_day(self, day=None):
        if day is None:
            day = today_time()
        count = self.count_on_day(day)
        return count

    @property
    def current_condition(self):
        count = self.condition_on_day()
        if count is not None:
            return count.condition
        else:
            return ""

    def prior_conditions(self, prior_days=3):
        """Given a set of animals, returns their counts from the prior N days
        """
        conds = [""] * prior_days
        for p in range(prior_days):
            day = today_time() - timezone.timedelta(days=p + 1)
            count = self.count_on_day(day)
            conds[p] = {"count": count, "day": day}

        return conds


class Group(AnimalSet):
    """Same as an animal, just represents a group of them w/ no identifier
    """

    population_male = models.PositiveSmallIntegerField(default=0)
    population_female = models.PositiveSmallIntegerField(default=0)
    population_unknown = models.PositiveSmallIntegerField(default=0)

    slug = AutoSlugField(
        null=True, default=None, populate_from="accession_number", unique=True
    )

    enclosure = models.ForeignKey(
        Enclosure, on_delete=models.SET_NULL, related_name="groups", null=True
    )

    class Meta:
        ordering = ["species__common_name"]

    def __str__(self):
        return "|".join((self.species.common_name, str(self.accession_number)))

    def get_count_day(self, day=None):
        if day is None:
            day = today_time()
        try:
            count = self.counts.filter(
                datetimecounted__gte=day,
                datetimecounted__lt=day + timezone.timedelta(days=1),
            ).latest("datetimecounted", "id")

            return count
        except ObjectDoesNotExist:
            return None

    def current_count(self):
        return self.get_count_day()

    def prior_counts(self, prior_days=3):
        counts = [0] * prior_days
        for p in range(prior_days):
            day = today_time() - timezone.timedelta(days=p + 1)
            counts[p] = {"count": self.get_count_day(day), "day": day}

        return counts


class Count(models.Model):
    datetimecounted = models.DateTimeField(default=timezone.now)
    datecounted = models.DateField(default=timezone.localdate)

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    enclosure = models.ForeignKey(Enclosure, on_delete=models.SET_NULL, null=True)

    class Meta:
        abstract = True
        ordering = ["datetimecounted"]


class AnimalCount(Count):
    SEEN = "SE"
    NEEDSATTENTION = "NA"
    # bright active responsive (the best)
    BAR = "BA"
    NOT_SEEN = "NS"

    CONDITIONS = [(SEEN, "Seen"), (NEEDSATTENTION, "Attn"), (NOT_SEEN, "Not Seen")]

    STAFF_CONDITIONS = [(BAR, "BAR")] + CONDITIONS

    condition = models.CharField(max_length=2, choices=STAFF_CONDITIONS, null=True)

    animal = models.ForeignKey(
        Animal, on_delete=models.CASCADE, related_name="conditions"
    )

    def __str__(self):
        return "|".join(
            (
                str(self.animal.accession_number),
                self.animal.name,
                self.user.username,
                timezone.localtime(self.datetimecounted).strftime("%Y-%m-%d"),
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
                timezone.localtime(self.datetimecounted).strftime("%Y-%m-%d"),
                ".".join(
                    (
                        str(self.count_male),
                        str(self.count_female),
                        str(self.count_unknown),
                    )
                ),
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
                timezone.localtime(self.datetimecounted).strftime("%Y-%m-%d"),
                str(self.count),
            )
        )
