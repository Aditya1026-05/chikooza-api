from django.contrib import admin

from common.admin_mixins import PublicIdAdminMixin
from farm.models import Country, Farm, State


@admin.register(State)
class StateAdmin(PublicIdAdminMixin, admin.ModelAdmin):
    list_display = ("name", "code", "country", "public_id")
    list_filter = ("country",)
    search_fields = ("name", "code", "country__name")
    ordering = ("name",)


@admin.register(Country)
class CountryAdmin(PublicIdAdminMixin, admin.ModelAdmin):
    list_display = ("name", "code", "isd_code", "public_id")
    search_fields = ("name", "code", "isd_code")
    ordering = ("name",)


@admin.register(Farm)
class FarmAdmin(PublicIdAdminMixin, admin.ModelAdmin):
    list_display = (
        "name",
        "user",
        "city",
        "district",
        "state",
        "shed_count",
        "status",
        "public_id",
    )
    list_filter = ("status", "country", "state", "district", "city")
    search_fields = (
        "name",
        "city",
        "district",
        "pin",
        "address",
        "user__username",
        "user__email",
        "user__mobile_number",
    )
    autocomplete_fields = ("user", "country", "state")
    list_select_related = ("user", "country", "state")
    ordering = ("name",)
    fieldsets = (
        (
            "Ownership",
            {
                "fields": (
                    "public_id",
                    "user",
                    "status",
                )
            },
        ),
        (
            "Farm Details",
            {
                "fields": (
                    "name",
                    "shed_count",
                    "address",
                    "city",
                    "district",
                    "pin",
                )
            },
        ),
        (
            "Location",
            {
                "fields": (
                    "country",
                    "state",
                    "lat_long",
                )
            },
        ),
        ("Audit", {"fields": ("created_at", "updated_at")}),
    )
