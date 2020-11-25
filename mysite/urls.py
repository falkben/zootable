"""mysite URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic.base import TemplateView

from zoo_checks import views

urlpatterns = [
    path("manage/", admin.site.urls, name="admin"),
    path("accounts/", include("allauth.urls")),
    path(
        "account_management/",
        TemplateView.as_view(template_name="account_management.html"),
        name="account_management",
    ),
    path("", views.home, name="home"),
    path("count/<slug:enclosure_slug>/", views.count, name="count"),
    path(
        "count/<slug:enclosure_slug>/<int:year>/<int:month>/<int:day>/",
        views.count,
        name="count",
    ),
    path(
        "tally_date_handler/<slug:enclosure_slug>",
        views.tally_date_handler,
        name="tally_date_handler",
    ),
    path(
        "edit_species_count/<slug:species_slug>/<slug:enclosure_slug>/<int:year>/<int:month>/<int:day>/",
        views.edit_species_count,
        name="edit_species_count",
    ),
    path(
        "edit_group_count/<group>/<int:year>/<int:month>/<int:day>/",
        views.edit_group_count,
        name="edit_group_count",
    ),
    path(
        "edit_animal_count/<animal>/<int:year>/<int:month>/<int:day>/",
        views.edit_animal_count,
        name="edit_animal_count",
    ),
    path("animal_counts/<animal>", views.animal_counts, name="animal_counts"),
    path("group_counts/<group>", views.group_counts, name="group_counts"),
    path(
        "species_counts/<slug:species_slug>/<slug:enclosure_slug>",
        views.species_counts,
        name="species_counts",
    ),
    path("upload/", views.ingest_form, name="ingest_form"),
    path("confirm_upload/", views.confirm_upload, name="confirm_upload"),
    path("export/", views.export, name="export"),
    path('animal_photo/', views.PhotoUploadView.as_view(), name='animal_photo'),
]


if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns

    # adding media photos
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
