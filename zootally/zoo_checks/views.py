from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import render

from .models import Exhibit, Species, Animal


@login_required
def count(request):
    # make a form

    exhibits = Exhibit.objects.filter(user=request.user)

    return render(request, "tally.html", context={"exhibits": exhibits})


def view_counts(request):
    # a view of entered data

    pass
