from django.urls import reverse
from zoo_checks.models import Enclosure
from zoo_checks.views import enclosure_counts_to_dict


def test_home(client, user_base):
    client.force_login(user_base)
    url = reverse("home")
    response = client.get(url)

    assert response.status_code == 200
    assert user_base.first_name in response.content.decode()
    assert (
        "No enclosures. Contact a manager to be added to a role"
        in response.content.decode()
    )


def test_home_counts(client, create_many_counts, user_base):

    num_enc = 7
    num_anim = 4
    num_species = 5

    create_many_counts(
        num_enc=num_enc, num_anim=num_anim, num_species=num_species,
    )

    client.force_login(user_base)
    url = reverse("home")
    response = client.get(url)

    assert response.status_code == 200
    assert "Individuals" in response.content.decode()


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
        all_counts_dict = enclosure_counts_to_dict(encl_q, animal_counts, group_counts)

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
