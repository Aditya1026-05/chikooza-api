from django.contrib import admin

from common.admin_mixins import PublicIdAdminMixin
from purchase.models import Purchase


@admin.register(Purchase)
class PurchaseAdmin(PublicIdAdminMixin, admin.ModelAdmin):
    list_display = (
        "date",
        "type",
        "flock",
        "user",
        "cost",
        "quantity",
        "item_name",
        "adjust_type",
        "public_id",
    )
    list_filter = ("type", "adjust_type", "date", "flock__farm")
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
