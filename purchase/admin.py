from django.contrib import admin

from common.admin_filters import (
    FlockFarmWorkflowFilter,
    FlockFarmerWorkflowFilter,
    FlockWorkflowFilter,
)
from common.admin_mixins import AdminWorkflowLinkMixin, PublicIdAdminMixin
from purchase.models import Purchase


@admin.register(Purchase)
class PurchaseAdmin(AdminWorkflowLinkMixin, PublicIdAdminMixin, admin.ModelAdmin):
    list_display = (
        "date",
        "type",
        "flock_link",
        "farm",
        "farmer",
        "cost",
        "quantity",
        "item_name",
        "adjust_type",
        "public_id",
    )
    list_filter = (
        FlockFarmerWorkflowFilter,
        FlockFarmWorkflowFilter,
        FlockWorkflowFilter,
        "type",
        "adjust_type",
        "date",
    )
    search_fields = (
        "item_name",
        "company_name",
        "remarks",
        "flock__name",
        "flock__farm__name",
        "user__username",
        "user__email",
    )
    autocomplete_fields = ("flock", "user")
    list_select_related = ("flock", "flock__farm", "user")
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
