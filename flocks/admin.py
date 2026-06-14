from django.contrib import admin

from common.admin_mixins import PublicIdAdminMixin
from flocks.models import Breed, Flock, Hatchery, Integrator


@admin.register(Breed)
class BreedAdmin(PublicIdAdminMixin, admin.ModelAdmin):
    list_display = ("name", "code", "line", "public_id")
    search_fields = ("name", "code", "line")
    ordering = ("name",)


@admin.register(Hatchery)
class HatcheryAdmin(PublicIdAdminMixin, admin.ModelAdmin):
    list_display = ("name", "city", "state", "phone", "email", "public_id")
    list_filter = ("country", "state", "city")
    search_fields = (
        "name",
        "nickname",
        "city",
        "pin",
        "email",
        "phone",
        "phone2",
        "contact",
    )
    autocomplete_fields = ("country", "state")
    list_select_related = ("country", "state")
    ordering = ("name",)


@admin.register(Integrator)
class IntegratorAdmin(PublicIdAdminMixin, admin.ModelAdmin):
    list_display = ("name", "city", "state", "phone", "email", "public_id")
    list_filter = ("country", "state", "city")
    search_fields = (
        "name",
        "nickname",
        "city",
        "pin",
        "email",
        "phone",
        "phone2",
        "contact",
    )
    autocomplete_fields = ("country", "state")
    list_select_related = ("country", "state")
    ordering = ("name",)


@admin.register(Flock)
class FlockAdmin(PublicIdAdminMixin, admin.ModelAdmin):
    list_display = (
        "name",
        "farm",
        "user",
        "breed",
        "hatch_date",
        "flock_size",
        "actual_birds",
        "status",
        "public_id",
    )
    list_filter = (
        "status",
        "integration",
        "ec_shed",
        "breed",
        "farm__state",
        "hatch_date",
    )
    search_fields = (
        "name",
        "farm__name",
        "user__username",
        "user__email",
        "breed__name",
        "hatchery_name",
    )
    autocomplete_fields = ("user", "farm", "breed", "hatchery", "integrator")
    list_select_related = ("user", "farm", "breed", "hatchery", "integrator")
    date_hierarchy = "hatch_date"
    ordering = ("-hatch_date", "name")
    fieldsets = (
        (
            "Ownership",
            {
                "fields": (
                    "public_id",
                    "user",
                    "farm",
                    "status",
                )
            },
        ),
        (
            "Flock Setup",
            {
                "fields": (
                    "name",
                    "hatch_date",
                    "flock_size",
                    "actual_birds",
                    "flock_bird",
                    "breed",
                    "chick_weight",
                    "chick_cost",
                )
            },
        ),
        (
            "Source",
            {
                "fields": (
                    "integration",
                    "integrator",
                    "hatchery",
                    "hatchery_name",
                    "hatchery_vaccine",
                )
            },
        ),
        (
            "Systems",
            {
                "fields": (
                    "feed_sys",
                    "drinking_sys",
                    "ec_shed",
                )
            },
        ),
        ("Audit", {"fields": ("created_at", "updated_at")}),
    )
