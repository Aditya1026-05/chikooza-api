from django.contrib import admin
from django.utils import timezone

from common.admin_mixins import PublicIdAdminMixin
from common.base_models import (
    EmailOtp,
    Otp,
    RegistrationApprovalPolicy,
    Users,
    UsersForgotPassword,
)


@admin.register(Users)
class UsersAdmin(PublicIdAdminMixin, admin.ModelAdmin):
    list_display = (
        "username",
        "email",
        "mobile_number",
        "is_email_verified",
        "is_phone_verified",
        "approval_status",
        "is_active",
        "is_staff",
        "is_superuser",
        "date_joined",
        "public_id",
    )
    list_filter = (
        "approval_status",
        "is_email_verified",
        "is_phone_verified",
        "is_active",
        "is_staff",
        "is_superuser",
        "date_joined",
    )
    search_fields = ("username", "email", "first_name", "last_name", "mobile_number")
    ordering = ("-date_joined",)
    readonly_fields = (
        "public_id",
        "created_at",
        "updated_at",
        "last_login",
        "date_joined",
        "approval_reviewed_at",
    )
    actions = ("approve_farmer_accounts", "reject_farmer_accounts")

    @admin.action(description="Approve selected farmer accounts")
    def approve_farmer_accounts(self, request, queryset):
        queryset.update(
            approval_status=Users.APPROVAL_APPROVED,
            approval_note="Approved from admin.",
            approval_reviewed_at=timezone.now(),
            approval_reviewed_by_id=request.user.id,
            is_active=True,
        )

    @admin.action(description="Reject selected farmer accounts")
    def reject_farmer_accounts(self, request, queryset):
        queryset.update(
            approval_status=Users.APPROVAL_REJECTED,
            approval_note="Rejected from admin.",
            approval_reviewed_at=timezone.now(),
            approval_reviewed_by_id=request.user.id,
            is_active=False,
        )


@admin.register(Otp)
class OtpAdmin(PublicIdAdminMixin, admin.ModelAdmin):
    list_display = ("mobile_number", "otp", "is_verify", "created_at", "public_id")
    list_filter = ("is_verify", "created_at")
    search_fields = ("mobile_number", "otp")
    ordering = ("-created_at",)


@admin.register(EmailOtp)
class EmailOtpAdmin(PublicIdAdminMixin, admin.ModelAdmin):
    list_display = ("email", "otp", "is_verify", "created_at", "public_id")
    list_filter = ("is_verify", "created_at")
    search_fields = ("email", "otp")
    ordering = ("-created_at",)


@admin.register(RegistrationApprovalPolicy)
class RegistrationApprovalPolicyAdmin(PublicIdAdminMixin, admin.ModelAdmin):
    list_display = (
        "name",
        "mode",
        "require_email_verified",
        "require_phone_verified",
        "is_enabled",
        "updated_at",
    )
    list_filter = ("mode", "is_enabled", "require_email_verified", "require_phone_verified")
    readonly_fields = ("public_id", "created_at", "updated_at")
    fieldsets = (
        (
            "Approval mode",
            {
                "fields": (
                    "name",
                    "mode",
                    "is_enabled",
                    "require_email_verified",
                    "require_phone_verified",
                )
            },
        ),
        (
            "Auto approval filters",
            {
                "fields": ("allowed_email_domains", "blocked_email_domains"),
                "description": (
                    "Leave allow-list empty to allow all verified emails. Block-list "
                    "always prevents auto approval."
                ),
            },
        ),
        ("System", {"fields": ("public_id", "created_at", "updated_at")}),
    )

    def has_add_permission(self, request):
        return not RegistrationApprovalPolicy.objects.exists()


@admin.register(UsersForgotPassword)
class UsersForgotPasswordAdmin(PublicIdAdminMixin, admin.ModelAdmin):
    list_display = ("users", "otp", "attempt", "otp_verify", "created_at", "public_id")
    list_filter = ("otp_verify", "created_at")
    search_fields = ("users__username", "users__email", "otp")
    autocomplete_fields = ("users",)
    list_select_related = ("users",)
    ordering = ("-created_at",)
