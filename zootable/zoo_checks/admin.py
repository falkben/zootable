from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from zoo_checks.models import (
    Animal,
    AnimalCount,
    Enclosure,
    Group,
    GroupCount,
    Species,
    SpeciesCount,
    Role,
    User,
)


@admin.register(AnimalCount)
class AnimalCountAdmin(admin.ModelAdmin):
    readonly_fields = ("datetimecounted", "datecounted")


@admin.register(GroupCount)
class GroupCountAdmin(admin.ModelAdmin):
    readonly_fields = ("datetimecounted", "datecounted")


@admin.register(SpeciesCount)
class SpeciesCountAdmin(admin.ModelAdmin):
    readonly_fields = ("datetimecounted", "datecounted")


@admin.register(Enclosure)
class EnclosureAdmin(admin.ModelAdmin):
    filter_horizontal = ("users",)


# Unregister the provided model admin
admin.site.unregister(User)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """This is primarily to limit permissions on the user page
    We really only want to allow staff to be able to add users to groups
    This is copied from: 
    https://realpython.com/manage-users-in-django-admin/#prevent-non-superusers-from-editing-their-own-permissions
    """

    readonly_fields = [
        "date_joined",
    ]

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        is_superuser = request.user.is_superuser
        disabled_fields = set()  # type: Set[str]

        if not is_superuser:
            disabled_fields = {"username", "is_superuser", "user_permissions"}

        # Prevent non-superusers from editing their own permissions
        if not is_superuser and obj is not None and obj == request.user:
            disabled_fields = {
                "is_staff",
                "is_superuser",
                "groups",
                "user_permissions",
            }

        for f in disabled_fields:
            if f in form.base_fields:
                form.base_fields[f].disabled = True

        return form


admin.site.register(Animal)
admin.site.register(Group)
admin.site.register(Species)
admin.site.register(Role)
