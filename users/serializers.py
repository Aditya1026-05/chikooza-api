from django.core.validators import RegexValidator

from rest_framework import serializers

from common.base_models import Users


class SignUpSerializer(serializers.Serializer):
    phone_message = "Enter a valid phone number."
    phone_regex = RegexValidator(regex="^[0-9]{10,12}$", message=phone_message)
    mobile_number = serializers.IntegerField(required=True, validators=[phone_regex])
    name = serializers.CharField(min_length=3, max_length=255)
    email = serializers.EmailField(max_length=255)
    username = serializers.CharField(min_length=3, max_length=255)
    password = serializers.CharField(min_length=5, max_length=30)
    confirm_password = serializers.CharField(min_length=5, max_length=30)
    otp = serializers.IntegerField()
    email_otp = serializers.IntegerField()

    class Meta:
        fields = [
            "mobile_number",
            "name",
            "email",
            "username",
            "password",
            "confirm_password",
            "otp",
            "email_otp",
        ]

    def validate(self, data):
        """
        Check password and confirm_password are same or not.
        """
        if not data.get("password") or not data.get("confirm_password"):
            raise serializers.ValidationError(
                "Please enter a password and " "confirm it."
            )
        if data.get("password") != data.get("confirm_password"):
            raise serializers.ValidationError("Those passwords don't match.")
        return data


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=255)
    password = serializers.CharField(max_length=30)

    class Meta:
        abstract = True


class SendOTPSerializer(serializers.Serializer):
    phone_message = "Enter a valid phone number."
    phone_regex = RegexValidator(regex="^[0-9]{10,12}$", message=phone_message)
    mobile_number = serializers.IntegerField(required=True, validators=[phone_regex])
    name = serializers.CharField(min_length=3, max_length=255)
    email = serializers.EmailField(max_length=255)
    username = serializers.CharField(min_length=3, max_length=255)
    password = serializers.CharField(min_length=5, max_length=30)
    confirm_password = serializers.CharField(min_length=5, max_length=30)

    def validate(self, data):
        """
        Check password and confirm_password are same or not.
        """
        if not data.get("password") or not data.get("confirm_password"):
            raise serializers.ValidationError(
                "Please enter a password and " "confirm it."
            )
        if data.get("password") != data.get("confirm_password"):
            raise serializers.ValidationError("Those passwords don't match.")
        return data

    class Meta:
        fields = "__all__"


class VerifyOTPSerializer(serializers.Serializer):
    phone_message = "Enter a valid phone number."
    phone_regex = RegexValidator(regex="^[0-9]{10,12}$", message=phone_message)
    mobile_number = serializers.IntegerField(validators=[phone_regex])
    otp = serializers.IntegerField()

    class Meta:
        fields = "__all__"


class VerifyEmailOTPSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=255)
    email_otp = serializers.IntegerField()

    class Meta:
        fields = "__all__"


class ProfileUserSerializer(serializers.ModelSerializer):
    name = serializers.CharField(max_length=255, source="first_name")

    class Meta:
        model = Users
        fields = ["public_id", "email", "username", "name", "mobile_number"]


class UpdateUserProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=False)
    name = serializers.CharField(required=False, max_length=255)

    class Meta:
        model = Users
        fields = ["email", "name"]


class ResetPasswordSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=255)
    phone_message = "Enter a valid phone number."
    phone_regex = RegexValidator(regex="^[0-9]{10,12}$", message=phone_message)
    mobile_number = serializers.IntegerField(validators=[phone_regex])

    class Meta:
        fields = ["username", "mobile_number"]


class ForgetPasswordSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=255)
    phone_message = "Enter a valid phone number."
    phone_regex = RegexValidator(regex="^[0-9]{10,12}$", message=phone_message)
    mobile_number = serializers.IntegerField(validators=[phone_regex])
    otp = serializers.IntegerField()
    new_password = serializers.CharField(max_length=30)
    confirm_new_password = serializers.CharField(max_length=30)

    def validate(self, data):
        """
        Check password and confirm_password are same or not.
        """
        if not data.get("new_password") or not data.get("confirm_new_password"):
            raise serializers.ValidationError(
                "Please enter a password and " "confirm it."
            )
        if data.get("new_password") != data.get("confirm_new_password"):
            raise serializers.ValidationError("Those passwords don't match.")
        return data

    class Meta:
        fields = [
            "username",
            "mobile_number",
            "otp",
            "new_password",
            "confirm_new_password",
        ]


class UpdateMobileSerializer(serializers.Serializer):
    phone_message = "Enter a valid phone number."
    phone_regex = RegexValidator(regex="^[0-9]{10,12}$", message=phone_message)
    mobile_number = serializers.IntegerField(validators=[phone_regex])
    otp = serializers.IntegerField()

    class Meta:
        fields = "__all__"


class SendOtpForUpdateMobileSerializer(serializers.Serializer):
    phone_message = "Enter a valid phone number."
    phone_regex = RegexValidator(regex="^[0-9]{10,12}$", message=phone_message)
    mobile_number = serializers.IntegerField(validators=[phone_regex])

    class Meta:
        fields = "__all__"


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(max_length=30)
    new_password = serializers.CharField(max_length=30)
    confirm_new_password = serializers.CharField(max_length=30)

    class Meta:
        fields = "__all__"

    def validate(self, data):
        """
        Check password and confirm_password are same or not.
        """
        if not data.get("new_password") or not data.get("confirm_new_password"):
            raise serializers.ValidationError(
                "Please enter a password and " "confirm it."
            )
        if data.get("new_password") != data.get("confirm_new_password"):
            raise serializers.ValidationError("Those passwords don't match.")
        return data
