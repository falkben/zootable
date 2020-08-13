""" test models """


import pytest
from django.utils.timezone import localtime
from zoo_checks.models import Animal, AnimalCount, Enclosure, Group, GroupCount, Species


def test_animal_instance(animal_A):
    assert isinstance(animal_A, Animal)
    assert animal_A.name == "A_name"


def test_animal_count_instance(animal_count_A_BAR):
    assert isinstance(animal_count_A_BAR, AnimalCount)
    assert animal_count_A_BAR.condition == "BA"
    assert animal_count_A_BAR.datecounted == localtime().date()


def test_species_instance(species_base):
    assert isinstance(species_base, Species)
    assert species_base.genus_name == "genus_base"


def test_enclosure_instance(enclosure_base):
    assert isinstance(enclosure_base, Enclosure)
    assert enclosure_base.name == "base_enc"


def test_group_instance(group_B):
    assert isinstance(group_B, Group)
    assert group_B.accession_number == "654321"


def test_group_count_instance(group_B_count):
    assert isinstance(group_B_count, GroupCount)
    assert group_B_count.count_bar == 1
    assert group_B_count.datecounted == localtime().date()
    assert group_B_count.group.accession_number == "654321"


def test_accession_numbers_total(enclosure_base, animal_A, group_B):
    num = enclosure_base.accession_numbers_total()
    assert num == 2


def test_accession_numbers_observed(
    enclosure_base: Enclosure,
    animal_count_A_BAR,
    group_B_count,
    django_assert_num_queries,
):
    with django_assert_num_queries(2):
        num_observed = enclosure_base.accession_numbers_observed()
    assert num_observed == 2


def test_animal_counts_on_day(
    enclosure_base, animal_count_A_BAR, django_assert_num_queries,
):
    with django_assert_num_queries(1):
        num_counts = enclosure_base.animal_counts_on_day().count()

    assert num_counts == 1


def test_group_counts_on_day(
    enclosure_base, group_B_count, django_assert_num_queries,
):
    with django_assert_num_queries(1):
        num_counts = enclosure_base.group_counts_on_day().count()

    assert num_counts == 1


@pytest.mark.django_db
def test_enclosure_all_counts(create_many_counts, user_base, django_assert_num_queries):
    """
    Tests that we can pull out correct counts
    tests the content of the counts
    """
    num_enc = 7
    num_anim = 4
    num_species = num_groups = 5

    a_cts, s_cts, g_cts, enc_list = create_many_counts(
        num_enc=num_enc, num_anim=num_anim, num_species=num_species,
    )
    counts = a_cts + s_cts + g_cts

    assert len(counts) == num_enc * (num_anim + num_groups * 2)

    with django_assert_num_queries(3):
        counts_tuple = Enclosure.all_counts(enc_list)
        species_counts, animal_counts, group_counts = (list(ct) for ct in counts_tuple)

    # assert counts
    assert len(species_counts) == num_species * num_enc
    assert len(group_counts) == num_groups * num_enc
    assert len(animal_counts) == num_anim * num_enc

    # the counts from db are ordered
    # counts from all_counts are by creation order
    assert set(species_counts) == set(s_cts)
    assert set(group_counts) == set(g_cts)
    assert set(animal_counts) == set(a_cts)

    assert all(c.user == user_base for c in species_counts)
    assert all(c.count == 42 for c in species_counts)

    assert all(c.user == user_base for c in animal_counts)
    assert all(c.condition == "BA" for c in animal_counts)

    assert all(c.user == user_base for c in group_counts)
    assert all(c.count_total == 6 for c in group_counts)


def test_enclosure_counts_to_dict(
    create_many_counts, species_base, django_assert_num_queries
):
    """
    Tests the dictionary creation from list of counts
    Tests the structure of the dict
    """
    num_enc = 7
    num_anim = 4
    num_species = num_groups = 5

    a_cts, s_cts, g_cts, enc_list = create_many_counts(
        num_enc=num_enc, num_anim=num_anim, num_species=num_species,
    )

    # create a query similar to how we build it in the view
    encl_q = Enclosure.objects.filter(name__in=enc_list).prefetch_related(
        "animals", "groups"
    )
    with django_assert_num_queries(5):
        # 3 for enclosures, groups, animals (w/ prefetch related)
        # 2 for animal_counts and group_counts

        animal_counts, group_counts = Enclosure.all_counts(encl_q)
        all_counts_dict = Enclosure.enclosure_counts_to_dict(
            encl_q, animal_counts, group_counts
        )

    # assert dict keys present in original query
    assert list(encl_q) == list(all_counts_dict.keys())

    # assert dict structure
    for enc in enc_list:
        enc_dict = all_counts_dict[enc]

        # todo
        # animal_count_total
        # animal_conditions
        # group_counts
        # group_count_total
        # total_animals
        # total_groups
