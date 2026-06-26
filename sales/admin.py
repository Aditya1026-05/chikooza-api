from django.contrib import admin

from common.admin_mixins import AdminWorkflowLinkMixin, PublicIdAdminMixin
from sales.models import Sales


@admin.register(Sales)
class SalesAdmin(AdminWorkflowLinkMixin, PublicIdAdminMixin, admin.ModelAdmin):
    list_display = (
        "date",
        "sales_type",
        "flock_link",
        "farm",
        "farmer",
        "lifting_count",
        "total_weight",
        "rate_per_kg",
        "cost",
        "buyer",
        "public_id",
    )
    list_filter = ("sales_type", "date", "flock__farm")
    search_fields = (
        "buyer",
        "buyer_phone_no",
        "buyer_email",
        "vehicle_no",
        "remarks",
        "flock__name",
        "flock__farm__name",
    )
    autocomplete_fields = ("flock",)
    list_select_related = ("flock", "flock__farm")
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
        return self.admin_change_link(obj.flock.user, obj.flock.user.username)
