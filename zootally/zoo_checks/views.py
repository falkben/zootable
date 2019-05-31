from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from django.shortcuts import render

from .forms import AnimalCountForm, SpeciesExhibitCountForm
from .models import Animal, Exhibit, Species


def create_combined_form(exhibits):
    form_list = []
    for exhibit in exhibits:
        for spec in exhibit.species.all():
            form_list.append(SpeciesExhibitCountForm(instance=spec))

        for anim in exhibit.animals.all():
            form_list.append(AnimalCountForm(instance=anim))
    return form_list


def count(request):
    exhibits = Exhibit.objects.filter(user=request.user)

    # if this is a POST request we need to process the form data
    if request.method == "POST":
        # create a form instance and populate it with data from the request:
        for form in form_list:
            # need to figure out whether it's an AnimalCountForm or a SpeciesCountForm
            form = AnimalCountForm(request.POST)
            # check whether it's valid:
            if form.is_valid():
                # process the data in form.cleaned_data as required
                # ...
                pass

        # if all forms were valid...
        # redirect to a new URL:
        return HttpResponseRedirect("/view_counts/")

    # if a GET (or any other method) we'll create a blank form
    else:
        form_list = create_combined_form(exhibits)

    return render(
        request, "tally.html", context={"form_list": form_list, "exhibits": exhibits}
    )


def view_counts(request):
    # a view of entered data

    pass
