"""
conftest.py is autodiscovered by pytest
https://docs.pytest.org/en/stable/fixture.html#conftest-py-sharing-fixture-functions
"""

import random
import string
from typing import Optional

import pytest
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpResponse
from django.utils.timezone import datetime, localtime, timedelta

from zoo_checks.models import (
    Animal,
    AnimalCount,
    Enclosure,
    Group,
    GroupCount,
    Role,
    Species,
    SpeciesCount,
    User,
)


@pytest.fixture
def rf_get_factory(rf, user_base):
    """request factory factory
    adds session and messages "middleware" to the request object

    Remember that when using RequestFactory, the request does not pass
    through middleware. If your view expects fields such as request.user
    to be set, you need to set them explicitly.
    """

    def _rf_get_factory(url: str, user: Optional[User] = user_base):
        request = rf.get(url)

        if user is not None:
            request.user = user

        # adding session
        middleware = SessionMiddleware(lambda req: HttpResponse())
        middleware.process_request(request)
        request.session.save()

        # adding messages
        messages = FallbackStorage(request)
        setattr(request, "_messages", messages)

        return request

    return _rf_get_factory


@pytest.fixture
def user_factory(db):
    def _user_factory(name: str, first_name: str = ""):
        return User.objects.create_user(name, first_name=first_name)

    return _user_factory


@pytest.fixture
def user_base(user_factory):
    return user_factory("base", first_name="base_first_name")


@pytest.fixture
def user_super(db):
    return User.objects.create_superuser("super", first_name="super_first_name")


@pytest.fixture
def role_base(user_base):
    role = Role.objects.create(name="role_base")
    role.users.add(user_base)
    role.save()
    return role


@pytest.fixture
def enclosure_factory(role_base):
    # closure
    def _enclosure_factory(name, role: Optional[Enclosure] = role_base):
        enc = Enclosure.objects.create(name=name)
        if role is not None:
            enc.roles.add(role)
            enc.save()
        return enc

    return _enclosure_factory


@pytest.fixture
def enclosure_base(enclosure_factory):
    return enclosure_factory("base_enc")


@pytest.fixture
def species_factory(db):
    def _species_factory(
        common_name="common_base",
        class_name="class_base",
        order_name="order_base",
        family_name="family_base",
        genus_name="genus_base",
        species_name="species_base",
    ):
        return Species.objects.create(
            common_name=common_name,
            class_name=class_name,
            order_name=order_name,
            family_name=family_name,
            genus_name=genus_name,
            species_name=species_name,
        )

    return _species_factory


@pytest.fixture
def species_base(species_factory):
    return species_factory()


@pytest.fixture
def species_count_factory(species_base, enclosure_base, user_base):
    def _species_count_factory(
        count: int,
        user: User = user_base,
        enclosure: Enclosure = enclosure_base,
        species: Species = species_base,
        datetimecounted: datetime = None,
    ) -> SpeciesCount:
        if datetimecounted is None:
            datetimecounted = localtime()
        return SpeciesCount.objects.create(
            datetimecounted=datetimecounted,
            datecounted=datetimecounted.date(),
            species=species,
            user=user,
            enclosure=enclosure,
            count=count,
        )

    return _species_count_factory


@pytest.fixture
def species_base_count(species_count_factory):

    # closure
    def _species_base_count(datetimecounted=None):
        if datetimecounted is None:
            datetimecounted = localtime()
        return species_count_factory(
            count=100,
            datetimecounted=datetimecounted,
        )

    return _species_base_count


@pytest.fixture
def animal_factory(enclosure_base, species_base):
    def _animal_factory(
        name: str,
        identifier: str,
        sex: str,
        accession_number: str,
        active: bool = True,
        enclosure=enclosure_base,
        species=species_base,
    ) -> Animal:
        return Animal.objects.create(
            name=name,
            identifier=identifier,
            sex=sex,
            accession_number=accession_number,
            enclosure=enclosure,
            species=species,
            active=active,
        )

    return _animal_factory


@pytest.fixture
def animal_A(animal_factory):
    return animal_factory("A_name", "A_id", "M", "123456")


@pytest.fixture
def animal_B_enc(enclosure_factory, animal_factory):
    # closure
    def _animal_B_enc(enclosure_name):

        enc = enclosure_factory(enclosure_name)
        return animal_factory("B_name", "B_id", "F", "111555", enclosure=enc)

    return _animal_B_enc


@pytest.fixture
def animal_count_factory(animal_A, user_base, enclosure_base):
    def _animal_count_factory(
        condition: str,
        datetimecounted: datetime = None,
        comment: str = "",
        animal: Animal = animal_A,
        user: User = user_base,
        enclosure: Enclosure = enclosure_base,
    ) -> AnimalCount:
        if datetimecounted is None:
            datetimecounted = localtime()
        return AnimalCount.objects.create(
            datetimecounted=datetimecounted,
            datecounted=datetimecounted.date(),
            condition=condition,
            comment=comment,
            animal=animal,
            user=user,
            enclosure=enclosure,
        )

    return _animal_count_factory


@pytest.fixture
def animal_count_A_BAR_datetime_factory(animal_count_factory):
    def _animal_count_A_BAR(datetimecounted=None) -> AnimalCount:
        if datetimecounted is None:
            datetimecounted = localtime()
        return animal_count_factory("BA", datetimecounted)

    return _animal_count_A_BAR


@pytest.fixture
def animal_count_A_BAR(animal_count_A_BAR_datetime_factory):
    return animal_count_A_BAR_datetime_factory()


@pytest.fixture
def group_factory(enclosure_base, species_base):
    def _group_factory(
        accession_number: str,
        population_male: int,
        population_female: int,
        population_unknown: int,
        population_total: int,
        enclosure: Enclosure = enclosure_base,
        species: Species = species_base,
        active: bool = True,
    ) -> Group:
        return Group.objects.create(
            species=species,
            enclosure=enclosure,
            accession_number=accession_number,
            population_male=population_male,
            population_female=population_female,
            population_unknown=population_unknown,
            population_total=population_total,
            active=active,
        )

    return _group_factory


@pytest.fixture
def group_B(group_factory):
    return group_factory(
        accession_number="654321",
        population_male=1,
        population_female=2,
        population_unknown=3,
        population_total=6,
    )


@pytest.fixture
def group_count_factory(group_B, user_base, enclosure_base):
    def _group_count_factory(
        count_total: int,
        count_seen: int,
        count_not_seen: int,
        count_bar: int,
        needs_attn: bool = False,
        datetimecounted: datetime = None,
        comment: str = "",
        group: Group = group_B,
        user: User = user_base,
        enclosure: Enclosure = enclosure_base,
    ) -> GroupCount:
        if datetimecounted is None:
            datetimecounted = localtime()
        return GroupCount.objects.create(
            group=group,
            datetimecounted=datetimecounted,
            datecounted=datetimecounted.date(),
            user=user,
            enclosure=enclosure,
            count_total=count_total,
            count_seen=count_seen,
            count_not_seen=count_not_seen,
            count_bar=count_bar,
            needs_attn=needs_attn,
            comment=comment,
        )

    return _group_count_factory


@pytest.fixture
def group_B_count_datetime_factory(group_count_factory):
    def _group_B_count(datetimecounted=None):
        if datetimecounted is None:
            datetimecounted = localtime()
        return group_count_factory(
            count_total=6,
            count_seen=3,
            count_not_seen=0,
            count_bar=1,
            needs_attn=False,
            comment="",
            datetimecounted=datetimecounted,
        )

    return _group_B_count


@pytest.fixture
def group_B_count(group_B_count_datetime_factory):
    return group_B_count_datetime_factory()


@pytest.fixture
def create_many_counts(
    enclosure_factory,
    group_factory,
    animal_count_factory,
    animal_factory,
    group_count_factory,
    species_count_factory,
):
    """
    sets up a large number of counts for testing
    returns the counts created as well as the enclosure
    """

    # closure
    def _create_many_counts(
        num_enc: int = 7,
        num_anim: int = 4,
        num_species: int = 5,
    ):
        access_start = 100000
        access_nums = iter(
            range(access_start, num_enc * num_anim * num_species + access_start + 1)
        )
        spec_count_val = 42
        group_count_val = (6, 1, 2, 3)
        anim_count_cond = "BA"
        alph = string.ascii_lowercase

        rand_alph_idx = random.sample(list(range(len(alph))), num_enc)

        s_cts, a_cts, g_cts, enc_list = [], [], [], []
        # create some test data
        for i in range(num_enc):
            enc_name = f"enc_{alph[rand_alph_idx[i]]}"
            enc = enclosure_factory(enc_name)
            enc_list.append(enc)

            # create counts for the enc
            for k in range(num_anim):
                id = f"anim_{enc_name}_{alph[i]}"
                m_f = "MF"[k % 2]  # alternate
                anim = animal_factory(id, id, m_f, next(access_nums), enclosure=enc)
                a_cts.append(
                    animal_count_factory(anim_count_cond, animal=anim, enclosure=enc)
                )

                # adding some counts on diff days
                for delta_day in (-3, -2, -1, 1, 2):
                    animal_count_factory(
                        "NA",
                        localtime() + timedelta(days=1) * delta_day,
                        animal=anim,
                        enclosure=enc,
                    )

            for k in range(num_species):
                id = f"id_{enc_name}_{alph[k]}"
                spec = Species.objects.create(
                    common_name=f"common_{id}",
                    class_name=f"class_base{id}",
                    order_name=f"order_base{id}",
                    family_name=f"family_{id}",
                    genus_name=f"genus_{id}",
                    species_name=f"species_{id}",
                )
                s_cts.append(
                    species_count_factory(spec_count_val, species=spec, enclosure=enc)
                )

                # adding some counts on diff days
                for delta_day in (-3, -2, -1, 1, 2):
                    species_count_factory(
                        100,
                        species=spec,
                        enclosure=enc,
                        datetimecounted=localtime() + timedelta(days=1) * delta_day,
                    )

                group = group_factory(
                    next(access_nums), 10, 10, 10, 30, species=spec, enclosure=enc
                )
                g_cts.append(
                    group_count_factory(*group_count_val, group=group, enclosure=enc)
                )

                # adding some counts on diff days
                for delta_day in (-3, -2, -1, 1, 2):
                    group_count_factory(
                        10,
                        10,
                        0,
                        0,
                        True,
                        localtime() + timedelta(days=1) * delta_day,
                        group=group,
                        enclosure=enc,
                    )

        return a_cts, s_cts, g_cts, enc_list

    return _create_many_counts
