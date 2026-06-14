from django.contrib import admin

from common.admin_mixins import PublicIdAdminMixin
from common.base_models import Otp, Users, UsersForgotPassword


@admin.register(Users)
class UsersAdmin(PublicIdAdminMixin, admin.ModelAdmin):
    list_display = (
        "username",
        "email",
        "mobile_number",
        "is_active",
        "is_staff",
        "is_superuser",
        "date_joined",
        "public_id",
    )
    list_filter = ("is_active", "is_staff", "is_superuser", "date_joined")
    search_fields = ("username", "email", "first_name", "last_name", "mobile_number")
    ordering = ("-date_joined",)
    readonly_fields = (
        "public_id",
        "created_at",
        "updated_at",
        "last_login",
        "date_joined",
    )


@admin.register(Otp)
class OtpAdmin(PublicIdAdminMixin, admin.ModelAdmin):
    list_display = ("mobile_number", "otp", "is_verify", "created_at", "public_id")
    list_filter = ("is_verify", "created_at")
    search_fields = ("mobile_number", "otp")
    ordering = ("-created_at",)


@admin.register(UsersForgotPassword)
class UsersForgotPasswordAdmin(PublicIdAdminMixin, admin.ModelAdmin):
    list_display = ("users", "otp", "attempt", "otp_verify", "created_at", "public_id")
    list_filter = ("otp_verify", "created_at")
    search_fields = ("users__username", "users__email", "otp")
    autocomplete_fields = ("users",)
    list_select_related = ("users",)
    ordering = ("-created_at",)
