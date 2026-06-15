from django.urls import include, path

from rest_framework.routers import DefaultRouter

from users.views import (
    ChangePasswordView,
    ForgetPasswordView,
    LoginView,
    LogoutView,
    ProfileUserView,
    ResetPasswordView,
    SendOtpForUpdateMobileView,
    SendOTPView,
    SignUpView,
    UpdateMobileNoView,
    VerifyEmailOTPView,
    VerifyOTPView,
)

router = DefaultRouter()
router.register(r"signUp", SignUpView, basename="sign_up")
router.register(r"login", LoginView, basename="login")
router.register(r"sendOtp", SendOTPView, basename="send_otp")
router.register(r"verifyOtp", VerifyOTPView, basename="verify_otp")
router.register(r"verifyEmailOtp", VerifyEmailOTPView, basename="verify_email_otp")
router.register(r"profile", ProfileUserView, basename="profile_view")
router.register(r"resetPassword", ResetPasswordView, basename="reset_password")
router.register(r"forgetPassword", ForgetPasswordView, basename="forget_password")
router.register(
    r"sendOtpForUpdateMobile",
    SendOtpForUpdateMobileView,
    basename="send_otp_for_update_mobile",
)
router.register(r"updateMobile", UpdateMobileNoView, basename="update_mobile_no")
router.register(r"changePassword", ChangePasswordView, basename="change_password")
router.register(r"logout", LogoutView, basename="logout")

urlpatterns = [path("", include(router.urls))]
