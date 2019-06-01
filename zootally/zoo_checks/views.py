from datetime import datetime

from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from django.shortcuts import render

from .forms import AnimalCountForm, SpeciesExhibitCountForm
from .models import Animal, Exhibit, Species, AnimalCount, SpeciesExhibitCount


def create_combined_form(exhibits):
    # TODO: counts should default to maximum (across users) for the day
    # TODO: condition should default to median condition (across users) for the day

    form_dict = {}

    count_kwargs = {"datetime": datetime.now()}

    for exhibit in exhibits:
        form_dict[exhibit] = {}
        for spec in exhibit.species.all():
            spec_count = SpeciesExhibitCount(
                species=spec, exhibit=exhibit, **count_kwargs
            )
            form_dict[exhibit][spec] = {}

            form_dict[exhibit][spec][spec] = SpeciesExhibitCountForm(
                instance=spec_count
            )

            anim_spec_exhib = Animal.objects.filter(exhibit=exhibit, species=spec)
            for anim in anim_spec_exhib:
                anim_count = AnimalCount(animal=anim, **count_kwargs)
                form_dict[exhibit][spec][anim] = AnimalCountForm(instance=anim_count)

    return form_dict


def count(request):
    exhibits = Exhibit.objects.filter(user=request.user)

    # if this is a POST request we need to process the form data
    if request.method == "POST":
        # create a form instance and populate it with data from the request:
        for form in form_dict:
            # need to figure out whether it's an AnimalCountForm or a SpeciesCountForm
            form = AnimalCountForm(request.POST)
            # check whether it's valid:
            if form.is_valid():
                # TODO: add current user to the list of users on this count object

                # process the data in form.cleaned_data as required
                # ...
                pass

        # if all forms were valid...
        # redirect to a new URL:
        return HttpResponseRedirect("/view_counts/")

    # if a GET (or any other method) we'll create a blank form
    else:
        form_dict = create_combined_form(exhibits)

    return render(
        request, "tally.html", context={"form_dict": form_dict, "exhibits": exhibits}
    )


def view_counts(request):
    # a view of entered data

    pass
