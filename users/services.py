from service_objects import services

from common.base_models import EmailOtp, Otp, PublicId, Users, UsersForgotPassword
from common.utils import deliver_email_otp, otp_delete_after_five_minutes, send_otp


class SendOTPServices(services.Service):
    """
    Service class to create OTP model object.
    """

    def process(self):
        Otp.objects.filter(mobile_number=self.data.get("mobile_number")).delete()
        create_otp = Otp.objects.create(
            public_id=PublicId.create_public_id(),
            mobile_number=self.data.get("mobile_number"),
            otp=send_otp(self.data.get("mobile_number")),
        )
        return create_otp


class SendEmailOTPServices(services.Service):
    """
    Service class to create email OTP model object.
    """

    def process(self):
        email = self.data.get("email")
        EmailOtp.objects.filter(email=email).delete()
        create_otp = EmailOtp.objects.create(
            public_id=PublicId.create_public_id(),
            email=email,
            otp=send_otp(email),
        )
        deliver_email_otp(email, create_otp.otp)
        return create_otp


class VerifyOtpService(services.Service):
    """
    Service class is used to verify otp.
    """

    def process(self):
        try:
            otp = Otp.objects.get(
                mobile_number=self.data.get("mobile_number"), otp=self.data.get("otp")
            )
            otp.is_verify = True
            otp.save()
            return otp
        except Otp.DoesNotExist:
            return None


class VerifyEmailOtpService(services.Service):
    """
    Service class is used to verify email otp.
    """

    def process(self):
        try:
            otp = EmailOtp.objects.get(
                email=self.data.get("email"), otp=self.data.get("otp")
            )
            otp.is_verify = True
            otp.save()
            return otp
        except EmailOtp.DoesNotExist:
            return None


class UpdateUserProfileService(services.Service):
    """
    Service class to partially update user profile.
    """

    def process(self):
        users = self.data.get("users")
        if self.data.get("email"):
            users.email = self.data.get("email")
            users.save()
        if self.data.get("mobile_number"):
            users.mobile_number = self.data.get("mobile_number")
            users.save()
        if self.data.get("name"):
            users.first_name = self.data.get("name")
            users.save()

        return users


class ResetPasswordServices(services.Service):
    def process(self):
        mobile_number = self.data.get("mobile_number")
        otp = send_otp(mobile_number)
        UsersForgotPassword.objects.filter(users=self.data.get("users")).delete()
        create_otp = UsersForgotPassword.objects.create(
            public_id=PublicId.create_public_id(), users=self.data.get("users"), otp=otp
        )
        otp_delete_after_five_minutes(
            UsersForgotPassword.objects.filter(otp=otp).last()
        )
        return create_otp


class ForgetPasswordService(services.Service):
    """
    Class is to write business logic for forget password view.
    """

    def process(self):
        mobile_number = self.data.get("mobile_number")
        users = Users.objects.get(mobile_number=mobile_number)
        otp_verified = UsersForgotPassword.objects.filter(users=users).last()
        if otp_verified.otp == self.data.get("otp"):
            users.set_password(self.data.get("new_password"))
            users.save()
            return True
        else:
            return False


class UpdateMobileService(services.Service):
    """
    Class to update mobile no.
    """

    def process(self):
        users = self.data.get("users")
        if self.data.get("mobile_number"):
            users.mobile_number = self.data.get("mobile_number")
            users.save()
        return users


class ChangePasswordService(services.Service):
    """
    Class for business logic to change password.
    """

    def process(self):
        users = self.data.get("users")
        new_password = self.data.get("new_password")
        users.set_password(new_password)
        users.save()
