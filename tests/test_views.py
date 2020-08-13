from django.urls import reverse
from zoo_checks.models import AnimalCount, Enclosure
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


def test_enclosure_counts_to_dict(create_many_counts, django_assert_num_queries):
    """
    Tests the dictionary creation from list of counts
    Tests the structure of the dict
    """
    num_enc = 7
    num_anim = 4
    num_species = num_groups = 5

    _, _, _, enc_list = create_many_counts(
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

        keys = {
            "animal_count_total",
            "animal_conditions",
            "group_counts",
            "group_count_total",
            "total_animals",
            "total_groups",
        }
        assert set(enc_dict.keys()) == keys

        assert enc_dict["animal_count_total"] == num_anim
        assert enc_dict["total_animals"] == num_anim

        # (1+3) Seen/BAR from input to group_count_factory
        assert enc_dict["group_count_total"] == num_groups * (1 + 3)

        # pop total = 30
        assert enc_dict["total_groups"] == num_groups * 30

        assert list(enc_dict["animal_conditions"].keys()) == [
            c[1] for c in AnimalCount.CONDITIONS
        ]
        assert all(
            [
                all([isinstance(c, AnimalCount) for c in c_l])
                for c_l in enc_dict["animal_conditions"].values()
            ]
        )

        assert list(enc_dict["group_counts"].keys()) == ["Seen", "BAR", "Needs Attn"]
        # These values come from the factory inputs to create group_counts
        assert enc_dict["group_counts"]["Seen"] == num_groups
        assert enc_dict["group_counts"]["BAR"] == num_groups * 3
        assert enc_dict["group_counts"]["Needs Attn"] == 0
