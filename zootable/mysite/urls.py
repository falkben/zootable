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
from django.contrib import admin
from django.urls import path, include
from django.views.generic.base import TemplateView

from zoo_checks import views

urlpatterns = [
    path("admin/", admin.site.urls, name="admin"),
    path("accounts/", include("allauth.urls")),
    path(
        "account_management/",
        TemplateView.as_view(template_name="account_management.html"),
        name="account_management",
    ),
    path("", views.home, name="home"),
    path("count/<enclosure_name>", views.count, name="count"),
    path(
        "edit_species_count/<species>/<enclosure>/<int:year>/<int:month>/<int:day>/",
        views.edit_species_count,
        name="edit_species_count",
    ),
    path(
        "edit_group_count/<int:group>/<int:year>/<int:month>/<int:day>/",
        views.edit_group_count,
        name="edit_group_count",
    ),
    path(
        "edit_animal_count/<int:animal>/<int:year>/<int:month>/<int:day>/",
        views.edit_animal_count,
        name="edit_animal_count",
    ),
    path("upload", views.ingest_form, name="ingest_form"),
    path("confirm_upload/", views.confirm_upload, name="confirm_upload"),
]