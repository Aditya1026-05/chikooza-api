from common.base_models import PublicId


class PublicIdAdminMixin:
    readonly_fields = ("public_id", "created_at", "updated_at")

    def save_model(self, request, obj, form, change):
        if hasattr(obj, "public_id") and not obj.public_id:
            obj.public_id = PublicId.create_public_id()
        super().save_model(request, obj, form, change)
