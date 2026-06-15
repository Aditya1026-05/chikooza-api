import uuid

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models


class CreateUpdateDate(models.Model):
    class Meta:
        abstract = True

    # Save date and time of add and update.
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)


class UniqueIds(models.Model):
    class Meta:
        abstract = True

    id = models.BigAutoField(primary_key=True, unique=True)
    #  public id to share with the the in url,
    #  Used for REST routes and public displays
    public_id = models.BigIntegerField(editable=False, unique=True)


class PublicId:
    # method for generating public id
    @staticmethod
    def create_public_id():
        public_id = uuid.uuid4().int >> 75
        return public_id


class BaseModel(CreateUpdateDate, UniqueIds):
    """
    Create model for inheriting purpose only.
    """

    class Meta:
        abstract = True

    pass


class Otp(BaseModel):
    """
    Model for store customer otp.
    """

    class Meta:
        db_table = "otp"

    otp = models.IntegerField()
    mobile_number = models.CharField(max_length=15, null=True)
    is_verify = models.BooleanField(default=False)


class EmailOtp(BaseModel):
    """
    Model for storing email verification OTP.
    """

    class Meta:
        db_table = "email_otp"

    otp = models.IntegerField()
    email = models.EmailField(max_length=255)
    is_verify = models.BooleanField(default=False)


class UsersForgotPassword(BaseModel):
    """
    Model for storing customer OTP.
    """

    class Meta:
        db_table = "customer_forgot_password"

    users = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="user_forgot_password"
    )
    otp = models.IntegerField()
    attempt = models.IntegerField(null=True)
    otp_verify = models.BooleanField(default=False)


class Users(User, BaseModel):
    """
    Model for store users detail's.
    """

    class Meta:
        db_table = "users"

    APPROVAL_PENDING = "pending"
    APPROVAL_APPROVED = "approved"
    APPROVAL_REJECTED = "rejected"
    APPROVAL_STATUS_CHOICES = (
        (APPROVAL_PENDING, "Pending"),
        (APPROVAL_APPROVED, "Approved"),
        (APPROVAL_REJECTED, "Rejected"),
    )

    mobile_number = models.CharField(max_length=15)
    is_email_verified = models.BooleanField(default=False)
    is_phone_verified = models.BooleanField(default=False)
    approval_status = models.CharField(
        max_length=20,
        choices=APPROVAL_STATUS_CHOICES,
        default=APPROVAL_PENDING,
    )
    approval_note = models.TextField(blank=True)
    approval_reviewed_at = models.DateTimeField(null=True, blank=True)
    approval_reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_farmer_accounts",
    )


class RegistrationApprovalPolicy(BaseModel):
    """
    Admin-controlled policy for deciding whether new farmer accounts auto-activate.
    """

    class Meta:
        db_table = "registration_approval_policy"
        verbose_name = "registration approval policy"
        verbose_name_plural = "registration approval policy"

    MODE_AUTO = "auto"
    MODE_MANUAL = "manual"
    MODE_CHOICES = (
        (MODE_AUTO, "Auto approve"),
        (MODE_MANUAL, "Manual review"),
    )

    name = models.CharField(max_length=100, default="Default policy", unique=True)
    mode = models.CharField(max_length=20, choices=MODE_CHOICES, default=MODE_AUTO)
    require_email_verified = models.BooleanField(default=True)
    require_phone_verified = models.BooleanField(default=True)
    allowed_email_domains = models.TextField(
        blank=True,
        help_text="Optional comma-separated allow-list, for example gmail.com,outlook.com.",
    )
    blocked_email_domains = models.TextField(
        blank=True,
        help_text="Optional comma-separated block-list, for example mailinator.com.",
    )
    is_enabled = models.BooleanField(default=True)

    @classmethod
    def get_default(cls):
        policy, _ = cls.objects.get_or_create(
            name="Default policy",
            defaults={
                "public_id": PublicId.create_public_id(),
                "mode": cls.MODE_AUTO,
                "require_email_verified": True,
                "require_phone_verified": True,
                "is_enabled": True,
            },
        )
        return policy

    @staticmethod
    def _domain_list(value):
        return {item.strip().lower() for item in value.split(",") if item.strip()}

    def should_auto_approve(self, email, phone_verified, email_verified):
        if not self.is_enabled or self.mode != self.MODE_AUTO:
            return False
        if self.require_phone_verified and not phone_verified:
            return False
        if self.require_email_verified and not email_verified:
            return False

        email_domain = (email or "").split("@")[-1].lower()
        allowed_domains = self._domain_list(self.allowed_email_domains)
        blocked_domains = self._domain_list(self.blocked_email_domains)

        if blocked_domains and email_domain in blocked_domains:
            return False
        if allowed_domains and email_domain not in allowed_domains:
            return False
        return True

    def __str__(self):
        return f"{self.name} ({self.mode})"


class Address(BaseModel):
    """
    Model for storing user address details.
    """

    class Meta:
        db_table = "address"

    users = models.ForeignKey(
        Users, on_delete=models.CASCADE, related_name="users_address"
    )

    latitude = models.FloatField()
    longitude = models.FloatField()
    address_land_mark = models.CharField(max_length=255)
    city = models.CharField(max_length=255, null=True)
    state = models.CharField(max_length=255, null=True)
    country = models.CharField(max_length=255, null=True)
    pin_code = models.IntegerField(null=True)
