from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from zoo_checks.models import (
    Animal,
    AnimalCount,
    Enclosure,
    Group,
    GroupCount,
    Role,
    Species,
    SpeciesCount,
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


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    filter_horizontal = ("users", "enclosures")
    # these can be function names
    # it uses what is defined in models.py which isn't what we want unless you give a "unique" name
    list_display = ("name", "get_enclosures", "get_users")

    def get_queryset(self, request):
        qs = super(RoleAdmin, self).get_queryset(request)
        return qs.prefetch_related("users", "enclosures")

    def get_users(self, obj):
        return ", ".join(f"{a.first_name} {a.last_name}" for a in obj.users.all())

    def get_enclosures(self, obj):
        return ", ".join(a.name for a in obj.enclosures.all())

    get_users.short_description = "users"
    get_enclosures.short_description = "enclosures"


@admin.register(Animal)
class AnimalAdmin(admin.ModelAdmin):
    list_display = (
        "accession_number",
        "name",
        "identifier",
        "species",
        "sex",
        "enclosure",
        "active",
    )
    list_filter = (
        "sex",
        "enclosure",
        "active",
    )


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = (
        "accession_number",
        "species",
        "population_male",
        "population_female",
        "population_unknown",
        "population_total",
        "enclosure",
        "active",
    )
    list_filter = (
        "enclosure",
        "active",
    )


class AnimalInline(admin.TabularInline):
    model = Animal

    fields = (
        "accession_number",
        "name",
        "identifier",
        "sex",
        "species",
        "active",
    )

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class GroupInline(admin.TabularInline):
    model = Group
    fields = (
        "accession_number",
        "species",
        "population_male",
        "population_female",
        "population_unknown",
        "population_total",
        "active",
    )

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Enclosure)
class EnclosureAdmin(admin.ModelAdmin):
    list_display = ("name", "animals", "groups")
    inlines = (AnimalInline, GroupInline)

    def get_queryset(self, request):
        qs = super(EnclosureAdmin, self).get_queryset(request)
        return qs.prefetch_related("animals", "groups")

    def animals(self, obj):
        return ", ".join(a.accession_number for a in obj.animals.all())

    def groups(self, obj):
        return ", ".join(g.accession_number for g in obj.groups.all())


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


admin.site.register(Species)
