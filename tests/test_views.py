import datetime
from random import randint

from django.test import SimpleTestCase
from django.urls import reverse
from django.utils import timezone

from zoo_checks.ingest import TRACKS_REQ_COLS
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
    resp = client.get(url)

    assert resp.status_code == 200
    assert resp.context["selected_role"] is None
    assert user_base.first_name in resp.content.decode()
    assert (
        "No enclosures. Contact a manager to be added to a role"
        in resp.content.decode()
    )


def test_home_counts(client, create_many_counts, user_base):

    num_enc = 7
    num_anim = 4
    num_species = 5

    create_many_counts(
        num_enc=num_enc,
        num_anim=num_anim,
        num_species=num_species,
    )

    client.force_login(user_base)
    url = reverse("home")
    resp = client.get(url)

    assert resp.status_code == 200
    assert list(resp.context["roles"]) == list(user_base.roles.all())
    assert resp.context["selected_role"] is None
    assert "Individuals" in resp.content.decode()


def test_count(
    client, user_base, enclosure_base, animal_A, animal_count_A_BAR, group_B
):
    client.force_login(user_base)

    # GET

    resp = client.get(f"/count/{enclosure_base.slug}/")
    assert resp.context["enclosure"] == enclosure_base
    assert resp.context["conditions"] == AnimalCount.CONDITIONS

    # untested context:
    # "dateday": dateday,
    # "species_formset": species_formset,
    # "groups_formset": groups_formset,
    # "animals_formset": animals_formset,
    # "formset_order": formset_order,
    # "dateform": dateform,
    # "conditions": AnimalCount.CONDITIONS,

    # test a different date

    # create some counts

    # todo:
    # POST


def test_tally_date_handler(client, enclosure_base, user_base):
    client.force_login(user_base)

    yesterday = datetime.date.today() - datetime.timedelta(days=1)
    tomorrow = datetime.date.today() + datetime.timedelta(days=1)

    resp = client.post(f"/tally_date_handler/{enclosure_base.slug}")
    assert resp.status_code == 302
    SimpleTestCase().assertRedirects(resp, f"/count/{enclosure_base.slug}/")

    resp = client.get(f"/tally_date_handler/{enclosure_base.slug}")
    assert resp.status_code == 302
    SimpleTestCase().assertRedirects(resp, f"/count/{enclosure_base.slug}/")

    resp = client.post(
        f"/tally_date_handler/{enclosure_base.slug}",
        {"tally_date": yesterday.strftime("%m/%d/%Y")},
    )
    assert resp.status_code == 302
    SimpleTestCase().assertRedirects(
        resp,
        (
            "/count/"
            f"{enclosure_base.slug}/{yesterday.year}/{yesterday.month}/{yesterday.day}/"
        ),
    )

    resp = client.post(
        f"/tally_date_handler/{enclosure_base.slug}",
        {"tally_date": "not_a_date"},
    )
    assert resp.status_code == 302
    # normally this is in resp.context but context is None since we're doing a redirect
    messages = list(resp.wsgi_request._messages)
    assert messages[0].message == "Error in date entered"
    SimpleTestCase().assertRedirects(resp, f"/count/{enclosure_base.slug}/")

    resp = client.post(
        f"/tally_date_handler/{enclosure_base.slug}",
        {"tally_date": tomorrow.strftime("%m/%d/%Y")},
    )
    assert resp.status_code == 302
    messages = list(resp.wsgi_request._messages)
    assert messages[0].message == "Error in date entered"
    SimpleTestCase().assertRedirects(resp, f"/count/{enclosure_base.slug}/")


def test_edit_species_count(
    client,
    user_base,
    species_base,
    enclosure_base,
    enclosure_factory,
    species_base_count,
):
    client.force_login(user_base)

    # todo: timezone ...?
    yesterday_time = datetime.datetime.now() - datetime.timedelta(days=1)
    yesterday = yesterday_time.date()

    enc_not_permit = enclosure_factory("not_permit", None)

    # not permitted
    resp = client.get(
        (
            "/edit_species_count/"
            f"{species_base.slug}/{enc_not_permit.name}"
            f"/{yesterday.year}/{yesterday.month}/{yesterday.day}/"
        )
    )
    assert resp.status_code == 302
    SimpleTestCase().assertRedirects(resp, "/")

    count = species_base_count(yesterday_time)

    # GET
    resp = client.get(
        (
            "/edit_species_count/"
            f"{species_base.slug}/{enclosure_base.name}/"
            f"{yesterday.year}/{yesterday.month}/{yesterday.day}/"
        )
    )
    assert resp.status_code == 200
    assert resp.context["species"] == species_base
    assert resp.context["enclosure"] == enclosure_base
    assert resp.context["dateday"].year == yesterday.year
    assert resp.context["dateday"].month == yesterday.month
    assert resp.context["dateday"].day == yesterday.day
    assert resp.context["count"] == count
    # todo: form context

    # POST
    post_data = {
        "count": randint(1, 400),
        "species": species_base.id,
        "enclosure": enclosure_base.id,
    }
    resp = client.post(
        (
            "/edit_species_count/"
            f"{species_base.slug}/{enclosure_base.name}/"
            f"{yesterday.year}/{yesterday.month}/{yesterday.day}/"
        ),
        data=post_data,
        follow=True,
    )
    assert resp.status_code == 200
    assert resp.redirect_chain == [(f"/count/{enclosure_base.slug}/", 302)]
    assert species_base.counts.latest("datetimecounted").count == post_data["count"]


def test_edit_group_count(
    client,
    user_base,
    group_B,
    group_factory,
    enclosure_base,
    enclosure_factory,
    group_B_count_datetime_factory,
):
    client.force_login(user_base)

    # todo: timezone ...?
    yesterday_time = datetime.datetime.now() - datetime.timedelta(days=1)
    yesterday = yesterday_time.date()

    enc_not_permit = enclosure_factory("not_permit", None)
    group_not_permit = group_factory("abc123", 5, 4, 3, 12, enclosure=enc_not_permit)

    # not permitted
    resp = client.get(
        (
            "/edit_group_count/"
            f"{group_not_permit.accession_number}/"
            f"{yesterday.year}/{yesterday.month}/{yesterday.day}/"
        )
    )
    assert resp.status_code == 302
    SimpleTestCase().assertRedirects(resp, "/")

    count = group_B_count_datetime_factory(yesterday_time)

    # GET
    resp = client.get(
        (
            "/edit_group_count/"
            f"{group_B.accession_number}/"
            f"{yesterday.year}/{yesterday.month}/{yesterday.day}/"
        )
    )
    assert resp.status_code == 200
    assert resp.context["count"] == count
    assert resp.context["group"] == group_B
    assert resp.context["enclosure"] == enclosure_base
    assert resp.context["dateday"].year == yesterday.year
    assert resp.context["dateday"].month == yesterday.month
    assert resp.context["dateday"].day == yesterday.day
    # todo: form context

    # POST
    count_bar = randint(1, 400)
    count_seen = count_bar + randint(5, 25)
    count_total = count_bar + count_seen
    post_data = {
        "count_seen": count_seen,
        "enclosure": enclosure_base.id,
        "count_bar": count_bar,
        "comment": "this is a randomly generated count",
        "group": group_B.id,
        "count_total": count_total,
        "needs_attn": False,
    }
    resp = client.post(
        (
            "/edit_group_count/"
            f"{group_B.accession_number}/"
            f"{yesterday.year}/{yesterday.month}/{yesterday.day}/"
        ),
        data=post_data,
        follow=True,
    )
    assert resp.status_code == 200
    assert resp.redirect_chain == [(f"/count/{enclosure_base.slug}/", 302)]

    latest_count = group_B.counts.latest("datetimecounted")
    assert latest_count.count_seen == post_data["count_seen"]
    assert latest_count.count_bar == post_data["count_bar"]


def test_edit_animal_count(
    client,
    user_base,
    enclosure_factory,
    animal_factory,
    animal_A,
    enclosure_base,
    animal_count_A_BAR_datetime_factory,
):
    client.force_login(user_base)

    # todo: timezone ...?
    yesterday_time = datetime.datetime.now() - datetime.timedelta(days=1)
    yesterday = yesterday_time.date()

    enc_not_permit = enclosure_factory("not_permit", None)

    anim_not_permit = animal_factory(
        name="kermitthefrog",
        identifier="green",
        sex="m",
        accession_number="abc123",
        enclosure=enc_not_permit,
    )

    # not permitted
    resp = client.get(
        (
            "/edit_animal_count/"
            f"{anim_not_permit.accession_number}/"
            f"{yesterday.year}/{yesterday.month}/{yesterday.day}/"
        )
    )
    assert resp.status_code == 302
    SimpleTestCase().assertRedirects(resp, "/")

    count = animal_count_A_BAR_datetime_factory(yesterday_time)

    # GET
    resp = client.get(
        (
            "/edit_animal_count/"
            f"{animal_A.accession_number}/"
            f"{yesterday.year}/{yesterday.month}/{yesterday.day}/"
        )
    )
    assert resp.status_code == 200
    assert resp.context["count"] == count
    assert resp.context["animal"] == animal_A
    assert resp.context["enclosure"] == enclosure_base
    assert resp.context["dateday"].year == yesterday.year
    assert resp.context["dateday"].month == yesterday.month
    assert resp.context["dateday"].day == yesterday.day
    # todo: form context

    # POST
    post_data = {
        "condition": "NA",
        "comment": "this is a test count",
        "animal": animal_A.id,
        "enclosure": enclosure_base.id,
    }
    resp = client.post(
        (
            "/edit_animal_count/"
            f"{animal_A.accession_number}/"
            f"{yesterday.year}/{yesterday.month}/{yesterday.day}/"
        ),
        data=post_data,
        follow=True,
    )
    assert resp.status_code == 200
    assert resp.redirect_chain == [(f"/count/{enclosure_base.slug}/", 302)]

    latest_count = animal_A.conditions.latest("datetimecounted")
    assert latest_count.condition == "NA"
    assert latest_count.comment == "this is a test count"
    assert latest_count.enclosure == enclosure_base


def test_animal_counts(
    client,
    animal_A,
    animal_count_factory,
    user_base,
    user_factory,
    enclosure_base,
):

    num_counts = 100

    rando_user = user_factory("rando")
    client.force_login(rando_user)
    url = reverse("animal_counts", args=[animal_A.accession_number])
    resp = client.get(url)
    assert resp.status_code == 302
    messages = list(resp.wsgi_request._messages)
    assert (
        messages[0].message
        == f"You do not have permissions to access enclosure {animal_A.enclosure}"
    )

    counts = []
    for d in range(num_counts):
        counts.append(
            animal_count_factory(
                "BA",
                timezone.localtime() - datetime.timedelta(days=d),
                comment=f"test count on day {d}",
            )
        )

    # test some counts w/ context
    client.force_login(user_base)
    url = reverse("animal_counts", args=[animal_A.accession_number])
    resp = client.get(url)
    assert resp.status_code == 200
    assert resp.context["animal"] == animal_A
    assert resp.context["enclosure"] == enclosure_base
    assert list(resp.context["animal_counts"]) == counts[:10]
    assert resp.context["page_range"][0] == 1
    assert resp.context["page_range"][-1] == 1 + 5
    # chart_data
    # chart_labels

    # test pagination
    url = "{}{}".format(
        reverse("animal_counts", args=[animal_A.accession_number]), f"?page={2}"
    )
    resp = client.get(url)
    assert resp.status_code == 200
    assert list(resp.context["animal_counts"]) == counts[10:20]
    assert resp.context["page_range"][0] == 1
    assert resp.context["page_range"][-1] == 2 + 5


def test_group_counts(
    client,
    group_B,
    group_B_count_datetime_factory,
    user_base,
    user_factory,
    enclosure_base,
):
    num_counts = 120

    # test perms
    rando_user = user_factory("rando")
    client.force_login(rando_user)
    url = reverse("group_counts", args=[group_B.accession_number])
    resp = client.get(url)
    assert resp.status_code == 302  # redirect to home
    messages = list(resp.wsgi_request._messages)
    assert (
        messages[0].message
        == f"You do not have permissions to access enclosure {group_B.enclosure}"
    )

    counts = []
    for d in range(num_counts):
        counts.append(
            group_B_count_datetime_factory(
                timezone.localtime() - datetime.timedelta(days=d)
            )
        )

    # test some counts w/ context
    client.force_login(user_base)
    url = reverse("group_counts", args=[group_B.accession_number])
    resp = client.get(url)
    assert resp.status_code == 200
    assert resp.context["group"] == group_B
    assert resp.context["enclosure"] == enclosure_base
    assert list(resp.context["counts"]) == counts[:10]
    assert resp.context["page_range"][0] == 1
    assert resp.context["page_range"][-1] == 1 + 5

    # test pagination
    url = "{}{}".format(
        reverse("group_counts", args=[group_B.accession_number]), f"?page={2}"
    )
    resp = client.get(url)
    assert resp.status_code == 200
    assert list(resp.context["counts"]) == counts[10:20]
    assert resp.context["page_range"][0] == 1
    assert resp.context["page_range"][-1] == 2 + 5


def test_species_counts(
    client, species_count_factory, species_base, user_base, user_factory, enclosure_base
):
    num_counts = 30

    # test perms
    rando_user = user_factory("rando")
    client.force_login(rando_user)
    url = reverse("species_counts", args=[species_base.slug, enclosure_base.slug])
    # should redirect to home
    resp = client.get(url)
    assert resp.status_code == 302
    messages = list(resp.wsgi_request._messages)
    assert (
        messages[0].message
        == f"You do not have permissions to access enclosure {enclosure_base}"
    )

    # create some counts
    counts = []
    for d in range(num_counts):
        counts.append(
            species_count_factory(
                50, datetimecounted=timezone.localtime() - datetime.timedelta(days=d)
            )
        )

    # test some counts w/ context
    client.force_login(user_base)
    url = reverse("species_counts", args=[species_base.slug, enclosure_base.slug])
    resp = client.get(url)
    assert resp.status_code == 200
    assert resp.context["obj"] == species_base
    assert resp.context["enclosure"] == enclosure_base
    assert list(resp.context["counts"]) == counts[:10]
    assert resp.context["page_range"][0] == 1
    assert resp.context["page_range"][-1] == 3
    # "chart_data_line_total"
    # "chart_labels_line"
    # "chart_data_pie"
    # "chart_labels_pie"


def test_ingest_form(client, user_base, user_super):
    client.force_login(user_base)

    url = reverse("ingest_form")
    resp = client.get(url)
    assert resp.status_code == 302
    SimpleTestCase().assertRedirects(resp, "/accounts/login/", target_status_code=302)

    client.force_login(user_super)
    resp = client.get(url)
    assert resp.status_code == 200
    assert resp.context["req_cols"] == TRACKS_REQ_COLS

    # todo: test session data manipulation (changesets/upload_file)

    # TODO: POST


def test_confirm_upload():
    # /confirm_upload

    # changesets and upload_file in session

    # test GET

    # test POST (writes changes to db)
    pass


def test_export(client, user_base, enclosure_base, user_factory, caplog):

    # GET

    # user w/ no enclosures empty list of enclosures
    rando_user = user_factory("rando")
    client.force_login(rando_user)
    resp = client.get("/export/")
    assert resp.status_code == 200
    assert list(resp.context["form"].fields["selected_enclosures"].queryset) == list(
        Enclosure.objects.none()
    )

    # user_base has enclosure_base in list of options
    client.force_login(user_base)
    resp = client.get("/export/")
    assert resp.status_code == 200
    assert enclosure_base.name in resp.content.decode()
    assert (
        resp.context["form"].fields["selected_enclosures"].queryset[0] == enclosure_base
    )

    # POST
    # still with user_base logged in
    yesterday = datetime.date.today() - datetime.timedelta(days=1)
    yesterday

    caplog.clear()
    # w/ no counts
    resp = client.post(
        "/export/",
        {
            "start_date": yesterday.strftime("%m/%d/%Y"),
            "end_date": datetime.date.today().strftime("%m/%d/%Y"),
            "selected_enclosures": enclosure_base.id,
        },
    )
    assert resp.status_code == 200
    record = caplog.records[0]

    assert record.message == "no data to export for enclosures"
    assert record.enclosures[0]["name"] == enclosure_base.name
    assert record.start_date == yesterday.strftime("%m/%d/%Y")
    assert record.end_date == datetime.date.today().strftime("%m/%d/%Y")

    # create some counts
    # assert 201 status code
    # load in excel data, convert to dataframe and check the counts


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

    # test role query param and diff session query param returns query param role and
    # sets session
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
        num_enc=num_enc,
        num_anim=num_anim,
        num_species=num_species,
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
