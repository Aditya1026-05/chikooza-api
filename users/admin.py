from datetime import timedelta
from secrets import token_urlsafe
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
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
from users.forms import (
    FarmerAdminPasswordChangeForm,
    FarmerChangeForm,
    FarmerCreationForm,
)


@admin.register(Users)
class UsersAdmin(AdminWorkflowLinkMixin, PublicIdAdminMixin, UserAdmin):
    form = FarmerChangeForm
    add_form = FarmerCreationForm
    change_password_form = FarmerAdminPasswordChangeForm
    list_display = (
        "username",
        "email",
        "mobile_number",
        "approval_badge",
        "verification_status",
        "is_active",
        "is_staff",
        "product_records",
        "password_action",
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
    readonly_fields = (
        "public_id",
        "created_at",
        "updated_at",
        "last_login",
        "date_joined",
        "approval_reviewed_at",
        "approval_reviewed_by",
        "product_records",
        "password_action",
        "dashboard_action",
    )
    actions = ("approve_farmer_accounts", "reject_farmer_accounts")
    add_fieldsets = (
        (
            "Register farmer",
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "password1",
                    "password2",
                    "first_name",
                    "last_name",
                    "email",
                    "mobile_number",
                ),
                "description": (
                    "Admin-registered farmers are verified, approved, and active "
                    "immediately. They cannot receive staff privileges from this form."
                ),
            },
        ),
    )
    fieldsets = (
        (
            "Admin inspection",
            {
                "fields": (
                    "password_action",
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
                "<path:object_id>/reset-password/",
                self.admin_site.admin_view(self.reset_farmer_password),
                name="common_users_reset_password",
            ),
            path(
                "<path:object_id>/open-dashboard/",
                self.admin_site.admin_view(self.open_dashboard_as_farmer),
                name="common_users_open_dashboard",
            ),
        ]
        return custom_urls + urls

    def save_model(self, request, obj, form, change):
        if not change:
            obj.is_staff = False
            obj.is_superuser = False
            obj.is_active = True
            obj.is_email_verified = True
            obj.is_phone_verified = True
            obj.approval_status = Users.APPROVAL_APPROVED
            obj.approval_note = "Registered and approved by an administrator."
            obj.approval_reviewed_at = timezone.now()
            obj.approval_reviewed_by = request.user
        else:
            previous = Users.objects.get(pk=obj.pk)
            if obj.approval_status != previous.approval_status:
                obj.is_active = obj.approval_status == Users.APPROVAL_APPROVED
                obj.approval_reviewed_at = timezone.now()
                obj.approval_reviewed_by = request.user
        super().save_model(request, obj, form, change)

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if obj is None or request.user.is_superuser:
            return fieldsets
        return tuple(
            fieldset for fieldset in fieldsets if fieldset[0] != "Admin permissions"
        )

    def has_change_permission(self, request, obj=None):
        if (
            obj is not None
            and (obj.is_staff or obj.is_superuser)
            and not request.user.is_superuser
        ):
            return False
        return super().has_change_permission(request, obj)

    @staticmethod
    def _is_farmer_account(user):
        return not user.is_staff and not user.is_superuser

    def reset_farmer_password(self, request, object_id):
        farmer = get_object_or_404(Users, pk=object_id)
        if not self._is_farmer_account(farmer):
            raise PermissionDenied
        return self.user_change_password(request, str(farmer.pk))

    def _can_open_farmer_dashboard(self, request):
        return request.user.is_superuser or request.user.has_perm("common.change_users")

    def open_dashboard_as_farmer(self, request, object_id):
        if not self._can_open_farmer_dashboard(request):
            raise PermissionDenied

        farmer = get_object_or_404(Users, pk=object_id)
        if (
            not self._is_farmer_account(farmer)
            or not farmer.is_active
            or farmer.approval_status != Users.APPROVAL_APPROVED
        ):
            raise PermissionDenied
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
            "{} · {} · {} · {} · {}",
            self.admin_changelist_link(
                Farm, f"{farm_count} farms", {"user__id__exact": obj.pk}
            ),
            self.admin_changelist_link(
                Flock, f"{flock_count} flocks", {"user__id__exact": obj.pk}
            ),
            self.admin_changelist_link(
                DailyData, f"{daily_count} daily", {"user__id__exact": obj.pk}
            ),
            self.admin_changelist_link(
                Purchase, f"{purchase_count} purchases", {"user__id__exact": obj.pk}
            ),
            self.admin_changelist_link(
                Sales, f"{sale_count} sales", {"flock__user__id__exact": obj.pk}
            ),
        )

    @admin.display(description="Dashboard")
    def dashboard_action(self, obj):
        if not obj or not obj.pk:
            return "-"
        if (
            not self._is_farmer_account(obj)
            or not obj.is_active
            or obj.approval_status != Users.APPROVAL_APPROVED
        ):
            return "-"
        url = reverse("admin:common_users_open_dashboard", args=(obj.pk,))
        return format_html(
            '<a class="btn btn-sm btn-success" href="{}" target="_blank" rel="noopener">Open dashboard</a>',
            url,
        )

    @admin.display(description="Password")
    def password_action(self, obj):
        if not obj or not obj.pk or not self._is_farmer_account(obj):
            return "-"
        url = reverse("admin:common_users_reset_password", args=(obj.pk,))
        return format_html(
            '<a class="btn btn-sm btn-outline-primary" href="{}">Reset password</a>',
            url,
        )

    @admin.action(description="Approve selected farmer accounts")
    def approve_farmer_accounts(self, request, queryset):
        selected_count = queryset.count()
        eligible_farmers = list(
            queryset.filter(
                approval_status=Users.APPROVAL_PENDING,
                is_staff=False,
                is_superuser=False,
                is_email_verified=True,
                is_phone_verified=True,
            )
        )
        reviewed_at = timezone.now()
        for farmer in eligible_farmers:
            farmer.approval_status = Users.APPROVAL_APPROVED
            farmer.approval_note = "Approved by an administrator."
            farmer.approval_reviewed_at = reviewed_at
            farmer.approval_reviewed_by = request.user
            farmer.is_active = True
            farmer.save(
                update_fields=(
                    "approval_status",
                    "approval_note",
                    "approval_reviewed_at",
                    "approval_reviewed_by",
                    "is_active",
                    "updated_at",
                )
            )
            self.log_change(request, farmer, "Approved farmer registration.")

        approved_count = len(eligible_farmers)
        self.message_user(
            request,
            f"Approved {approved_count} farmer registration(s).",
            level=messages.SUCCESS,
        )
        skipped_count = selected_count - approved_count
        if skipped_count:
            self.message_user(
                request,
                (
                    f"Skipped {skipped_count} account(s). Only pending, verified "
                    "farmer registrations can be approved."
                ),
                level=messages.WARNING,
            )

    @admin.action(description="Reject selected farmer accounts")
    def reject_farmer_accounts(self, request, queryset):
        selected_count = queryset.count()
        eligible_farmers = list(
            queryset.filter(
                approval_status=Users.APPROVAL_PENDING,
                is_staff=False,
                is_superuser=False,
            )
        )
        reviewed_at = timezone.now()
        for farmer in eligible_farmers:
            farmer.approval_status = Users.APPROVAL_REJECTED
            farmer.approval_note = "Rejected by an administrator."
            farmer.approval_reviewed_at = reviewed_at
            farmer.approval_reviewed_by = request.user
            farmer.is_active = False
            farmer.save(
                update_fields=(
                    "approval_status",
                    "approval_note",
                    "approval_reviewed_at",
                    "approval_reviewed_by",
                    "is_active",
                    "updated_at",
                )
            )
            self.log_change(request, farmer, "Rejected farmer registration.")

        rejected_count = len(eligible_farmers)
        self.message_user(
            request,
            f"Rejected {rejected_count} farmer registration(s).",
            level=messages.SUCCESS,
        )
        skipped_count = selected_count - rejected_count
        if skipped_count:
            self.message_user(
                request,
                f"Skipped {skipped_count} account(s) that were not pending farmers.",
                level=messages.WARNING,
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
    list_filter = (
        "mode",
        "is_enabled",
        "require_email_verified",
        "require_phone_verified",
    )
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
