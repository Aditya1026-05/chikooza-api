from django.contrib import admin

from common.admin_mixins import PublicIdAdminMixin
from sales.models import Sales


@admin.register(Sales)
class SalesAdmin(PublicIdAdminMixin, admin.ModelAdmin):
    list_display = (
        "date",
        "sales_type",
        "flock",
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
