from urllib.parse import urlencode

from django.urls import reverse
from django.utils.html import format_html

from common.base_models import PublicId


class PublicIdAdminMixin:
    readonly_fields = ("public_id", "created_at", "updated_at")

    def save_model(self, request, obj, form, change):
        if hasattr(obj, "public_id") and not obj.public_id:
            obj.public_id = PublicId.create_public_id()
        super().save_model(request, obj, form, change)


class AdminWorkflowLinkMixin:
    """Small helpers for building workflow links inside Django admin lists."""

    def admin_change_link(self, obj, label=None):
        if not obj:
            return "-"

        opts = obj._meta
        url = reverse(
            f"admin:{opts.app_label}_{opts.model_name}_change",
            args=(obj.pk,),
        )
        return format_html('<a href="{}">{}</a>', url, label or str(obj))

    def admin_changelist_url(self, model, params=None):
        opts = model._meta
        url = reverse(f"admin:{opts.app_label}_{opts.model_name}_changelist")
        if params:
            url = f"{url}?{urlencode(params)}"
        return url

    def admin_changelist_link(self, model, label, params=None):
        return format_html(
            '<a href="{}">{}</a>',
            self.admin_changelist_url(model, params=params),
            label,
        )
