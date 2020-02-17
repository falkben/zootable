"""
script which identifies common permissions between users/enclosures 
prior to adding roles
"""


import os
import sys

sys.path.append("zootable")

import django  # noqa: E402
from django.db.models import Q  # noqa: E402

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")
django.setup()

from zoo_checks.models import Enclosure  # noqa: E402


enclosures = Enclosure.objects.all()

# iterate over enclosures
# extract "tuples" of users for each enclosure
# create a set of unique sets of users
shared_users_set = {
    # needs to be tuple to be put into a set (immutable)
    # sorted to create identical sequences
    tuple([u for u in enc.users.exclude(first_name="admin").order_by("id")])
    for enc in enclosures
}

shared_enclosures_set = set()
for users_group in shared_users_set:
    if not users_group:  # empty
        continue

    # ? this doesn't work in migrations, first user is not a user object but the username?
    query = Q()
    for user in users_group:
        query &= Q(users=user)

    # another way to write the same thing
    # from functools import reduce
    # import operator
    # query = reduce(operator.and_, (Q(users=user) for user in users_group))

    enclosure_group = tuple(
        [enc for enc in Enclosure.objects.exclude(~query).order_by("id")]
    )

    print(", ".join([u.first_name for u in users_group]))
    print(", ".join([e.name for e in enclosure_group]), "\n")
    shared_enclosures_set.add(enclosure_group)

