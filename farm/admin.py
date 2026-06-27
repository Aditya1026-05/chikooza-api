from django.contrib import admin
from django.utils.html import format_html

from common.admin_filters import FarmerWorkflowFilter
from common.admin_mixins import AdminWorkflowLinkMixin, PublicIdAdminMixin
from dailydata.models import DailyData
from farm.models import Country, Farm, State
from flocks.models import Flock


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
class FarmAdmin(AdminWorkflowLinkMixin, PublicIdAdminMixin, admin.ModelAdmin):
    list_display = (
        "name",
        "farmer",
        "city",
        "district",
        "state",
        "shed_count",
        "flock_records",
        "status",
        "public_id",
    )
    list_filter = (FarmerWorkflowFilter, "status", "country", "state", "district", "city")
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
    list_per_page = 25
    readonly_fields = PublicIdAdminMixin.readonly_fields + ("flock_records",)
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

    @admin.display(description="Farmer")
    def farmer(self, obj):
        return self.admin_change_link(obj.user, obj.user.username)

    @admin.display(description="Records")
    def flock_records(self, obj):
        flock_count = Flock.objects.filter(farm=obj).count()
        daily_count = DailyData.objects.filter(flock__farm=obj).count()
        return format_html(
            "{} · {}",
            self.admin_changelist_link(Flock, f"{flock_count} flocks", {"farm__id__exact": obj.pk}),
            self.admin_changelist_link(
                DailyData,
                f"{daily_count} daily entries",
                {"flock__farm__id__exact": obj.pk},
            ),
        )
