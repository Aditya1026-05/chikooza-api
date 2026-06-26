from django.test import TestCase, override_settings
from unittest.mock import patch
from rest_framework import status
from rest_framework.test import APIRequestFactory

from common.base_models import EmailOtp, Otp, RegistrationApprovalPolicy, Users
from users.views import LoginView, SendOTPView, SignUpView


@override_settings(CHIKOOZA_FIXED_OTP="123456", DEBUG=True)
class UserVerificationApprovalTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.password = "safePass123"
        self.payload = {
            "mobile_number": "9998887776",
            "name": "Demo Farmer",
            "email": "demo@example.com",
            "username": "demo@example.com",
            "password": self.password,
            "confirm_password": self.password,
        }

    def _send_otp(self, payload=None):
        view = SendOTPView.as_view({"post": "create"})
        request = self.factory.post("/users/sendOtp/", payload or self.payload, format="json")
        return view(request)

    def _signup(self, payload=None):
        view = SignUpView.as_view({"post": "create"})
        data = {
            **(payload or self.payload),
            "otp": 123456,
            "email_otp": 123456,
        }
        request = self.factory.post("/users/signUp/", data, format="json")
        return view(request)

    def test_send_otp_creates_phone_and_email_otps(self):
        response = self._send_otp()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Otp.objects.filter(mobile_number="9998887776").exists())
        self.assertTrue(EmailOtp.objects.filter(email="demo@example.com").exists())
        self.assertEqual(response.data["results"]["otp"], 123456)
        self.assertEqual(response.data["results"]["email_otp"], 123456)

    def test_signup_auto_approves_verified_farmer_by_default(self):
        self._send_otp()

        response = self._signup()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = Users.objects.get(username="demo@example.com")
        self.assertTrue(user.is_phone_verified)
        self.assertTrue(user.is_email_verified)
        self.assertEqual(user.approval_status, Users.APPROVAL_APPROVED)
        self.assertTrue(user.is_active)

    def test_signup_waits_for_admin_when_policy_is_manual(self):
        policy = RegistrationApprovalPolicy.get_default()
        policy.mode = RegistrationApprovalPolicy.MODE_MANUAL
        policy.save()
        self._send_otp()

        response = self._signup()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = Users.objects.get(username="demo@example.com")
        self.assertEqual(user.approval_status, Users.APPROVAL_PENDING)
        self.assertFalse(user.is_active)

    def test_pending_manual_user_cannot_login(self):
        policy = RegistrationApprovalPolicy.get_default()
        policy.mode = RegistrationApprovalPolicy.MODE_MANUAL
        policy.save()
        self._send_otp()
        self._signup()
        view = LoginView.as_view({"post": "create"})
        request = self.factory.post(
            "/users/login/",
            {"username": "demo@example.com", "password": self.password},
            format="json",
        )

        response = view(request)

        self.assertEqual(response.status_code, status.HTTP_406_NOT_ACCEPTABLE)
        self.assertIn("approval", response.data["error"].lower())

    def test_login_accepts_email_when_username_is_different(self):
        user = Users.objects.create_user(
            username="demo_farmer",
            email="demo@example.com",
            password=self.password,
            mobile_number="9998887776",
            public_id=123456789,
            is_phone_verified=True,
            is_email_verified=True,
            approval_status=Users.APPROVAL_APPROVED,
            is_active=True,
        )
        view = LoginView.as_view({"post": "create"})
        request = self.factory.post(
            "/users/login/",
            {"username": user.email, "password": self.password},
            format="json",
        )

        with patch(
            "users.views.create_token",
            return_value={
                "access_token": "test-token",
                "expires_in": 3600,
                "token_type": "Bearer",
            },
        ):
            response = view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"]["public_id"], user.public_id)
