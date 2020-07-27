from django.urls import reverse


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
    assert "<h3>Enclosures</h3>" in response.content.decode()
