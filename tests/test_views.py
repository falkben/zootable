from django.urls import reverse

from zoo_checks.models import AnimalCount, Enclosure
from zoo_checks.views import (
    enclosure_counts_to_dict,
    get_accessible_enclosures,
    get_selected_role,
    redirect_if_not_permitted,
)


def test_home(client, user_base):
    client.force_login(user_base)
    url = reverse("home")
    response = client.get(url)

    assert response.status_code == 200
    assert response.context["selected_role"] is None
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
    assert list(response.context["roles"]) == list(user_base.roles.all())
    assert response.context["selected_role"] is None
    assert "Individuals" in response.content.decode()


def test_get_accessible_enclosures(
    user_base, enclosure_base, enclosure_factory, user_super
):
    enclosures = get_accessible_enclosures(user_base)
    assert list(enclosures) == [enclosure_base]

    # create a bunch of enclosures, but don't assign to role
    enc_set = {enclosure_base}
    for i in range(10):
        enc_set.add(enclosure_factory(str(i), role=None))

    # super user should get all the enclosures
    enclosures_super = get_accessible_enclosures(user_super)
    assert set(enclosures_super) == enc_set

    # regular user should still have the same single enclosure
    enclosures = get_accessible_enclosures(user_base)
    assert list(enclosures) == [enclosure_base]


def test_redirect_if_not_permitted(
    rf_get_factory, enclosure_factory, enclosure_base, user_super
):
    request = rf_get_factory("/count/")
    forbidden_enc = enclosure_factory("forbidden_enc", role=None)

    # test if user doesn't have role that includes enclosure (True)
    assert redirect_if_not_permitted(request, forbidden_enc)

    # test if user has role that includes enclosure (False)
    assert not redirect_if_not_permitted(request, enclosure_base)

    # test if user is superuser (False)
    request.user = user_super
    assert not redirect_if_not_permitted(request, enclosure_base)
    assert not redirect_if_not_permitted(request, forbidden_enc)


def test_selected_role(rf_get_factory, role_base):

    # test view all query param returns None and clears session
    request = rf_get_factory("/home/?view_all=true")
    request.session["selected_role"] = "role_base"
    selected_role = get_selected_role(request)
    assert selected_role is None
    assert request.session.get("selected_role") is None

    # test role in session & no query params returns session role
    request = rf_get_factory("/home/")
    request.session["selected_role"] = "role_base"
    selected_role = get_selected_role(request)
    assert selected_role == role_base
    assert request.session.get("selected_role") == "role_base"

    # test role query param returns role and sets session
    request = rf_get_factory("/home/?role=role_base")
    selected_role = get_selected_role(request)
    assert selected_role == role_base
    assert request.session.get("selected_role") == "role_base"

    # test role query param and different session query param returns query param role and sets session
    request = rf_get_factory("/home/?role=role_base")
    request.session["selected_role"] = "diff_role"
    selected_role = get_selected_role(request)
    assert selected_role == role_base
    assert request.session.get("selected_role") == "role_base"

    # test absence of all of these return None
    request = rf_get_factory("/home/")
    selected_role = get_selected_role(request)
    assert selected_role is None


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
