from django.contrib import admin
from django.utils.html import format_html

from common.admin_mixins import AdminWorkflowLinkMixin, PublicIdAdminMixin
from dailydata.models import DailyData
from flocks.models import Breed, Flock, Hatchery, Integrator
from purchase.models import Purchase
from sales.models import Sales


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
class FlockAdmin(AdminWorkflowLinkMixin, PublicIdAdminMixin, admin.ModelAdmin):
    list_display = (
        "name",
        "farm_link",
        "farmer",
        "breed",
        "hatch_date",
        "flock_size",
        "actual_birds",
        "operation_records",
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
    list_per_page = 25
    readonly_fields = PublicIdAdminMixin.readonly_fields + ("operation_records",)
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

    @admin.display(description="Farm")
    def farm_link(self, obj):
        return self.admin_change_link(obj.farm, obj.farm.name)

    @admin.display(description="Farmer")
    def farmer(self, obj):
        return self.admin_change_link(obj.user, obj.user.username)

    @admin.display(description="Records")
    def operation_records(self, obj):
        daily_count = DailyData.objects.filter(flock=obj).count()
        purchase_count = Purchase.objects.filter(flock=obj).count()
        sale_count = Sales.objects.filter(flock=obj).count()
        return format_html(
            "{} · {} · {}",
            self.admin_changelist_link(DailyData, f"{daily_count} daily", {"flock__id__exact": obj.pk}),
            self.admin_changelist_link(Purchase, f"{purchase_count} purchases", {"flock__id__exact": obj.pk}),
            self.admin_changelist_link(Sales, f"{sale_count} sales", {"flock__id__exact": obj.pk}),
        )
