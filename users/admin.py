from datetime import timedelta
from secrets import token_urlsafe
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import admin, messages
from django.contrib.auth.hashers import identify_hasher
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from oauth2_provider.models import AccessToken

from common.admin_mixins import AdminWorkflowLinkMixin, PublicIdAdminMixin
from common.base_models import (
    EmailOtp,
    Otp,
    RegistrationApprovalPolicy,
    Users,
    UsersForgotPassword,
)
from common.utils import get_or_create_oauth_application
from dailydata.models import DailyData
from farm.models import Farm
from flocks.models import Flock
from purchase.models import Purchase
from sales.models import Sales


@admin.register(Users)
class UsersAdmin(AdminWorkflowLinkMixin, PublicIdAdminMixin, admin.ModelAdmin):
    list_display = (
        "username",
        "email",
        "mobile_number",
        "approval_badge",
        "verification_status",
        "is_active",
        "is_staff",
        "product_records",
        "dashboard_action",
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
    list_per_page = 25
    filter_horizontal = ("groups", "user_permissions")
    raw_id_fields = ("approval_reviewed_by",)
    readonly_fields = (
        "public_id",
        "created_at",
        "updated_at",
        "last_login",
        "date_joined",
        "approval_reviewed_at",
        "product_records",
        "dashboard_action",
    )
    actions = ("approve_farmer_accounts", "reject_farmer_accounts")
    fieldsets = (
        (
            "Admin inspection",
            {
                "fields": (
                    "dashboard_action",
                    "product_records",
                )
            },
        ),
        (
            "Account",
            {
                "fields": (
                    "username",
                    "password",
                    "first_name",
                    "last_name",
                    "email",
                    "mobile_number",
                )
            },
        ),
        (
            "Review status",
            {
                "fields": (
                    "approval_status",
                    "approval_note",
                    "is_active",
                    "is_email_verified",
                    "is_phone_verified",
                    "approval_reviewed_at",
                    "approval_reviewed_by",
                )
            },
        ),
        (
            "Admin permissions",
            {
                "classes": ("collapse",),
                "fields": (
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (
            "Audit",
            {
                "classes": ("collapse",),
                "fields": (
                    "public_id",
                    "last_login",
                    "date_joined",
                    "created_at",
                    "updated_at",
                ),
            },
        ),
    )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<path:object_id>/open-dashboard/",
                self.admin_site.admin_view(self.open_dashboard_as_farmer),
                name="common_users_open_dashboard",
            )
        ]
        return custom_urls + urls

    def save_model(self, request, obj, form, change):
        password = form.cleaned_data.get("password")
        if password:
            try:
                identify_hasher(password)
            except ValueError:
                obj.set_password(password)
        super().save_model(request, obj, form, change)

    def _can_open_farmer_dashboard(self, request):
        return request.user.is_superuser or request.user.has_perm("common.change_users")

    def open_dashboard_as_farmer(self, request, object_id):
        if not self._can_open_farmer_dashboard(request):
            raise PermissionDenied

        farmer = get_object_or_404(Users, pk=object_id)
        application = get_or_create_oauth_application(farmer)
        AccessToken.objects.filter(
            user=farmer,
            application=application,
            expires__lt=timezone.now(),
        ).delete()
        token = AccessToken.objects.create(
            user=farmer,
            application=application,
            token=token_urlsafe(96),
            expires=timezone.now() + timedelta(minutes=45),
            scope="read create update delete groups",
        )
        display_name = farmer.first_name or farmer.username
        fragment = urlencode(
            {
                "token": token.token,
                "publicid": farmer.public_id,
                "name": display_name,
                "adminInspect": "1",
            }
        )
        messages.info(
            request,
            f"Opened farmer dashboard for {farmer.username}. The inspection token expires in 45 minutes.",
        )
        frontend_base = settings.CHIKOOZA_UI_BASE_URL.rstrip("/")
        return HttpResponseRedirect(f"{frontend_base}/admin-access#{fragment}")

    @admin.display(description="Review")
    def approval_badge(self, obj):
        badge_class = {
            Users.APPROVAL_APPROVED: "success",
            Users.APPROVAL_PENDING: "warning",
            Users.APPROVAL_REJECTED: "danger",
        }.get(obj.approval_status, "secondary")
        return format_html(
            '<span class="badge badge-{}">{}</span>',
            badge_class,
            obj.get_approval_status_display(),
        )

    @admin.display(description="Verified")
    def verification_status(self, obj):
        email = "Email" if obj.is_email_verified else "Email pending"
        phone = "Phone" if obj.is_phone_verified else "Phone pending"
        return f"{email} / {phone}"

    @admin.display(description="Product records")
    def product_records(self, obj):
        if not obj or not obj.pk:
            return "-"

        farm_count = Farm.objects.filter(user=obj).count()
        flock_count = Flock.objects.filter(user=obj).count()
        daily_count = DailyData.objects.filter(user=obj).count()
        purchase_count = Purchase.objects.filter(user=obj).count()
        sale_count = Sales.objects.filter(flock__user=obj).count()

        return format_html(
            '{} · {} · {} · {} · {}',
            self.admin_changelist_link(Farm, f"{farm_count} farms", {"user__id__exact": obj.pk}),
            self.admin_changelist_link(Flock, f"{flock_count} flocks", {"user__id__exact": obj.pk}),
            self.admin_changelist_link(DailyData, f"{daily_count} daily", {"user__id__exact": obj.pk}),
            self.admin_changelist_link(Purchase, f"{purchase_count} purchases", {"user__id__exact": obj.pk}),
            self.admin_changelist_link(Sales, f"{sale_count} sales", {"flock__user__id__exact": obj.pk}),
        )

    @admin.display(description="Dashboard")
    def dashboard_action(self, obj):
        if not obj or not obj.pk:
            return "-"
        if obj.is_staff or obj.is_superuser:
            return "-"
        url = reverse("admin:common_users_open_dashboard", args=(obj.pk,))
        return format_html(
            '<a class="btn btn-sm btn-success" href="{}" target="_blank" rel="noopener">Open dashboard</a>',
            url,
        )

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
