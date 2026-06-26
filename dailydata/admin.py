from django.contrib import admin

from common.admin_mixins import AdminWorkflowLinkMixin, PublicIdAdminMixin
from dailydata.models import (
    DailyData,
    DarknessTime,
    FeedAvailability,
    FlockVaccination,
    Vaccines,
)


@admin.register(DarknessTime)
class DarknessTimeAdmin(PublicIdAdminMixin, admin.ModelAdmin):
    list_display = ("name", "public_id")
    search_fields = ("name",)
    ordering = ("name",)


@admin.register(FeedAvailability)
class FeedAvailabilityAdmin(PublicIdAdminMixin, admin.ModelAdmin):
    list_display = ("name", "public_id")
    search_fields = ("name",)
    ordering = ("name",)


@admin.register(Vaccines)
class VaccinesAdmin(PublicIdAdminMixin, admin.ModelAdmin):
    list_display = ("name", "full_name", "company_id", "status", "public_id")
    list_filter = ("status",)
    search_fields = ("name", "full_name", "description", "company_id")
    ordering = ("name",)


@admin.register(DailyData)
class DailyDataAdmin(AdminWorkflowLinkMixin, PublicIdAdminMixin, admin.ModelAdmin):
    list_display = (
        "date",
        "flock_link",
        "farm",
        "farmer",
        "current_bird_count",
        "mortality",
        "total_mort",
        "feed_intake",
        "feed_stock",
        "average_bird_weight",
        "fcr",
        "status",
        "public_id",
    )
    list_filter = (
        "status",
        "date",
        "flock__farm",
        "cooling",
        "heating",
        "seek",
        "medicine",
        "darkness_time",
        "feed_availability",
    )
    search_fields = (
        "flock__name",
        "flock__farm__name",
        "user__username",
        "user__email",
        "remarks",
    )
    autocomplete_fields = ("flock", "user", "darkness_time", "feed_availability")
    list_select_related = (
        "flock",
        "flock__farm",
        "user",
        "darkness_time",
        "feed_availability",
    )
    date_hierarchy = "date"
    ordering = ("-date", "-created_at")
    list_per_page = 25

    @admin.display(description="Flock")
    def flock_link(self, obj):
        return self.admin_change_link(obj.flock, obj.flock.name)

    @admin.display(description="Farm")
    def farm(self, obj):
        return self.admin_change_link(obj.flock.farm, obj.flock.farm.name)

    @admin.display(description="Farmer")
    def farmer(self, obj):
        return self.admin_change_link(obj.user, obj.user.username)


@admin.register(FlockVaccination)
class FlockVaccinationAdmin(AdminWorkflowLinkMixin, PublicIdAdminMixin, admin.ModelAdmin):
    list_display = ("daily_data", "flock_link", "vaccine", "status", "public_id")
    list_filter = ("status", "vaccine", "flock__farm")
    search_fields = (
        "flock__name",
        "flock__farm__name",
        "vaccine__name",
        "vaccine__full_name",
    )
    autocomplete_fields = ("dailydata", "flock", "vaccine")
    list_select_related = ("dailydata", "flock", "vaccine")

    @admin.display(description="Daily data")
    def daily_data(self, obj):
        return self.admin_change_link(obj.dailydata, obj.dailydata.date)

    @admin.display(description="Flock")
    def flock_link(self, obj):
        return self.admin_change_link(obj.flock, obj.flock.name)
