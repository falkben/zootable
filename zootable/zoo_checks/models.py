from itertools import chain

from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.utils import timezone
from django_extensions.db.fields import AutoSlugField

from .helpers import today_time


class Enclosure(models.Model):
    name = models.CharField(max_length=100, unique=True)

    slug = AutoSlugField(null=True, default=None, populate_from="name", unique=True)

    users = models.ManyToManyField(User)

    def __str__(self):
        return self.name

    def species(self):
        """Combines exhibit's animals' species and groups' species together 
        into a distinct queryset of species
        """
        animals = self.animals.filter(active=True).order_by(
            "species__common_name", "name"
        )
        groups = self.groups.filter(active=True).order_by("species__common_name")
        animal_species = Species.objects.filter(animal__in=animals)
        group_species = Species.objects.filter(group__in=groups)

        return (animal_species | group_species).distinct()

    def accession_numbers(self):
        animals = self.animals.filter(active=True)
        groups = self.groups.filter(active=True)

        return animals, groups

    def accession_numbers_observed(self, day=None):
        if day is None:
            day = today_time()

        animals, groups = self.accession_numbers()

        # we don't care if we are getting the correct counts on the day
        # just the number of disctinct counts
        animal_counts = (
            AnimalCount.objects.filter(
                animal__in=animals,
                datetimecounted__gte=day,
                datetimecounted__lt=day + timezone.timedelta(days=1),
            )
            .order_by("animal__accession_number", "-datetimecounted")
            .distinct("animal__accession_number")
        )
        group_counts = (
            GroupCount.objects.filter(
                group__in=groups,
                datetimecounted__gte=day,
                datetimecounted__lt=day + timezone.timedelta(days=1),
            )
            .order_by("group__accession_number", "-datetimecounted")
            .distinct("group__accession_number")
        )

        return animal_counts.count() + group_counts.count()

    def accession_numbers_total(self):
        animals, groups = self.accession_numbers()

        return animals.count() + groups.count()

    class Meta:
        ordering = ["name"]


class Species(models.Model):
    common_name = models.CharField(max_length=100, unique=True)
    species_name = models.CharField(max_length=100)
    genus_name = models.CharField(max_length=100)
    class_name = models.CharField(max_length=100)
    order_name = models.CharField(max_length=100)
    family_name = models.CharField(max_length=100)

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

    def prior_counts(self, enclosure, prior_days=3, ref_date=None):
        """get all the prior counts returned in a list using a single query"""

        if ref_date is None:
            ref_date = today_time()

        # we get the min and max days to search over
        min_day = ref_date - timezone.timedelta(days=prior_days)
        max_day = ref_date

        # perform the query, returning only the latest counts, and distinct on dates
        # need to sort by id because edited counts have the same date/datetimes
        counts_q = (
            self.counts.filter(
                datetimecounted__gte=min_day,
                datetimecounted__lt=max_day,
                enclosure=enclosure,
            )
            .order_by("-datecounted", "-datetimecounted", "-id")
            .distinct("datecounted")
        )

        # create the dict to index into
        if counts_q:
            counts_dict = {q.datecounted: q.count for q in counts_q}
        else:
            counts_dict = {}

        # iterate over the days and return
        counts = [0] * prior_days
        for p in range(prior_days):
            daytime = ref_date - timezone.timedelta(days=p + 1)
            day = ref_date.date() - timezone.timedelta(days=p + 1)
            day_count = counts_dict.get(day)

            counts[p] = (
                {"count": day_count, "day": daytime}
                if day_count
                else {"count": 0, "day": daytime}
            )

        return counts


class AnimalSet(models.Model):
    """ Anything with an accession number """

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

    name = models.CharField(max_length=100)
    identifier = models.CharField(max_length=200)
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

    def prior_conditions(self, prior_days=3, ref_date=None):
        """Given a set of animals, returns their counts from the prior N days
        """

        if ref_date is None:
            ref_date = today_time()

        # we get the min and max days to search over
        min_day = ref_date - timezone.timedelta(days=prior_days)
        max_day = ref_date

        # perform the query, returning only the latest counts, and distinct on dates
        # need to sort by id because edited counts have the same date/datetimes
        counts_q = (
            self.conditions.filter(
                datetimecounted__gte=min_day, datetimecounted__lt=max_day
            )
            .order_by("-datecounted", "-datetimecounted", "-id")
            .distinct("datecounted")
        )

        # create the dict to index into
        if counts_q:
            counts_dict = {q.datecounted: q for q in counts_q}
        else:
            counts_dict = {}

        conds = [""] * prior_days
        for p in range(prior_days):
            daytime = ref_date - timezone.timedelta(days=p + 1)
            day = ref_date.date() - timezone.timedelta(days=p + 1)

            count = counts_dict.get(day)
            conds[p] = {"count": count, "day": daytime}

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

    def prior_counts(self, prior_days=3, ref_date=None):
        """Prior counts using a single query"""

        if ref_date is None:
            ref_date = today_time()

        # we get the min and max days to search over
        min_day = ref_date - timezone.timedelta(days=prior_days)
        max_day = ref_date

        # perform the query, returning only the latest counts, and distinct on dates
        # need to sort by id because edited counts have the same date/datetimes
        counts_q = (
            self.counts.filter(
                datetimecounted__gte=min_day, datetimecounted__lt=max_day
            )
            .order_by("-datecounted", "-datetimecounted", "-id")
            .distinct("datecounted")
        )

        # create the dict to index into
        if counts_q:
            counts_dict = {q.datecounted: q for q in counts_q}
        else:
            counts_dict = {}

        counts = [0] * prior_days
        for p in range(prior_days):
            daytime = ref_date - timezone.timedelta(days=p + 1)
            day = ref_date.date() - timezone.timedelta(days=p + 1)

            counts[p] = {"count": counts_dict.get(day), "day": daytime}

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

    # NOTE: everyone can do BAR now
    condition = models.CharField(max_length=2, choices=STAFF_CONDITIONS, null=True)

    comment = models.TextField(blank=True, default="")

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

    @classmethod
    def counts_on_day(cls, animals, day=None):
        """Returns counts on a given day from a list of animals
        """
        if day is None:
            day = today_time()

        return (
            cls.objects.filter(
                animal__in=animals,
                datetimecounted__gte=day,
                datetimecounted__lt=day + timezone.timedelta(days=1),
            )
            .order_by("animal__accession_number", "-datetimecounted")
            .distinct("animal__accession_number")
        )

    def update_or_create_from_form(self):
        # we want the identifier to be:
        # user, datecounted, animal, enclosure?
        AnimalCount.objects.update_or_create(
            user=self.user,
            datecounted=self.datecounted,
            animal=self.animal,
            enclosure=self.enclosure,
            # The update_or_create method tries to fetch an object from database based on the given kwargs.
            # If a match is found, it updates the fields passed in the defaults dictionary.
            defaults={
                "datetimecounted": self.datetimecounted,
                "condition": self.condition,
                "comment": self.comment,
            },
        )


class GroupCount(Count):
    count_male = models.PositiveSmallIntegerField(default=0)
    count_female = models.PositiveSmallIntegerField(default=0)
    count_unknown = models.PositiveSmallIntegerField(default=0)

    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="counts")

    @property
    def total(self):
        return self.count_male + self.count_female + self.count_unknown

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

    @classmethod
    def counts_on_day(cls, groups, day=None):
        """Returns counts on a given day from a list of groups
        """
        if day is None:
            day = today_time()

        return (
            cls.objects.filter(
                group__in=groups,
                datetimecounted__gte=day,
                datetimecounted__lt=day + timezone.timedelta(days=1),
            )
            .order_by("group__accession_number", "-datetimecounted")
            .distinct("group__accession_number")
        )

    def update_or_create_from_form(self):
        # we want the identifier to be:
        # user, datecounted, group, enclosure?
        GroupCount.objects.update_or_create(
            user=self.user,
            datecounted=self.datecounted,
            group=self.group,
            enclosure=self.enclosure,
            defaults={
                "datetimecounted": self.datetimecounted,
                "count_male": self.count_male,
                "count_female": self.count_female,
                "count_unknown": self.count_unknown,
            },
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

    @classmethod
    def counts_on_day(cls, species, enclosure, day=None):
        """Returns the counts on a given day from a list of species for an enclosure
        """
        if day is None:
            day = today_time()

        return (
            cls.objects.filter(
                species__in=species,
                enclosure=enclosure,
                datetimecounted__gte=day,
                datetimecounted__lt=day + timezone.timedelta(days=1),
            )
            .order_by("species__common_name", "-datetimecounted")
            .distinct("species__common_name")
        )

    def update_or_create_from_form(self):
        # we want the identifier to be:
        # user, datecounted, group, enclosure?
        SpeciesCount.objects.update_or_create(
            user=self.user,
            datecounted=self.datecounted,
            species=self.species,
            enclosure=self.enclosure,
            defaults={"datetimecounted": self.datetimecounted, "count": self.count},
        )

