import uuid

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

    mobile_number = models.CharField(max_length=15)


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
