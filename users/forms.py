from django import forms
from django.contrib.auth.forms import (
    AdminPasswordChangeForm,
    UserChangeForm,
    UserCreationForm,
)
from django.core.exceptions import ValidationError
from django.utils import timezone
from oauth2_provider.models import AccessToken, RefreshToken

from common.base_models import Users


class FarmerAccountValidationMixin:
    """Shared identity checks for farmer account forms in Django admin."""

    email = forms.EmailField(required=True, label="Email address")
    mobile_number = forms.RegexField(
        regex=r"^[0-9]{10,12}$",
        required=True,
        label="Mobile number",
        error_messages={"invalid": "Enter a mobile number containing 10 to 12 digits."},
    )

    def _other_users(self):
        queryset = Users.objects.all()
        if self.instance and self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        return queryset

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if self._other_users().filter(email__iexact=email).exists():
            raise ValidationError("A farmer with this email address already exists.")
        return email

    def clean_mobile_number(self):
        mobile_number = self.cleaned_data["mobile_number"].strip()
        if self._other_users().filter(mobile_number=mobile_number).exists():
            raise ValidationError("A farmer with this mobile number already exists.")
        return mobile_number


class FarmerCreationForm(FarmerAccountValidationMixin, UserCreationForm):
    """Create a login-ready farmer without exposing privilege controls."""

    class Meta(UserCreationForm.Meta):
        model = Users
        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "mobile_number",
        )

    def save(self, commit=True):
        farmer = super().save(commit=False)
        farmer.is_staff = False
        farmer.is_superuser = False
        farmer.is_active = True
        farmer.is_email_verified = True
        farmer.is_phone_verified = True
        farmer.approval_status = Users.APPROVAL_APPROVED
        farmer.approval_note = "Registered and approved by an administrator."
        farmer.approval_reviewed_at = timezone.now()
        if commit:
            farmer.save()
        return farmer


class FarmerChangeForm(FarmerAccountValidationMixin, UserChangeForm):
    """Edit farmer details while keeping the encoded password read-only."""

    class Meta(UserChangeForm.Meta):
        model = Users
        fields = "__all__"

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if self._other_users().filter(username__iexact=username).exists():
            raise ValidationError("A user with that username already exists.")
        return username

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("approval_status") == Users.APPROVAL_APPROVED:
            missing_verification = not cleaned_data.get(
                "is_email_verified"
            ) or not cleaned_data.get("is_phone_verified")
            if missing_verification:
                raise ValidationError(
                    "Approve a farmer only after both email and phone are verified."
                )
        return cleaned_data


class FarmerAdminPasswordChangeForm(AdminPasswordChangeForm):
    """Reset a farmer password and revoke existing API access tokens."""

    def save(self, commit=True):
        farmer = super().save(commit=commit)
        if commit:
            RefreshToken.objects.filter(user=farmer).delete()
            AccessToken.objects.filter(user=farmer).delete()
        return farmer
