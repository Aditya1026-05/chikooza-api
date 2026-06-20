from unittest.mock import patch

from django.http import HttpResponse
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework import status

from common.base_models import PublicId, Users
from common.constant import APP_RESULT, ERROR, MESSAGE
from common.middleware import AuthenticationErrorMessage
from common.utils import (
    build_otp_response_payload,
    error_response,
    get_or_create_oauth_application,
    send_otp,
)


class SendOtpTests(SimpleTestCase):
    @override_settings(CHIKOOZA_FIXED_OTP="654321", DEBUG=True)
    def test_uses_configured_fixed_otp(self):
        self.assertEqual(send_otp("9999999999"), 654321)

    @override_settings(CHIKOOZA_FIXED_OTP=None, DEBUG=True)
    def test_keeps_local_debug_otp_for_mvp_testing(self):
        self.assertEqual(send_otp("9999999999"), 123456)

    @override_settings(CHIKOOZA_FIXED_OTP=None, DEBUG=False)
    def test_uses_random_otp_outside_debug(self):
        with patch("common.utils.random.randint", return_value=987654) as randint:
            otp = send_otp("9999999999")

        self.assertEqual(otp, 987654)
        randint.assert_called_once_with(100000, 999999)


class OtpResponsePayloadTests(SimpleTestCase):
    @override_settings(CHIKOOZA_FIXED_OTP=None, DEBUG=False)
    def test_hides_otp_in_production_payload(self):
        payload = build_otp_response_payload(123456, "9999999999")

        self.assertEqual(payload, {"mobile_number": "9999999999"})

    @override_settings(CHIKOOZA_FIXED_OTP=None, DEBUG=True)
    def test_includes_otp_for_debug_payload(self):
        payload = build_otp_response_payload(123456, "9999999999")

        self.assertEqual(payload, {"mobile_number": "9999999999", "otp": 123456})

    @override_settings(CHIKOOZA_FIXED_OTP="123456", DEBUG=False)
    def test_includes_otp_for_explicit_fixed_otp_payload(self):
        payload = build_otp_response_payload(123456, "9999999999")

        self.assertEqual(payload, {"mobile_number": "9999999999", "otp": 123456})


class AuthenticationErrorMiddlewareTests(SimpleTestCase):
    def test_handles_plain_http_response_without_drf_data(self):
        middleware = AuthenticationErrorMessage(
            lambda request: HttpResponse('{"error": "invalid_client"}', status=401)
        )
        response = middleware(object())

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response["content-type"], "application/json")
        self.assertIn(b"invalid_client", response.content)


class ApiErrorResponseTests(SimpleTestCase):
    def test_error_response_exposes_readable_message_and_structured_details(self):
        response = error_response(
            {ERROR: "Flock Does Not exist."},
            status.HTTP_404_NOT_FOUND,
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data[MESSAGE], "Flock Does Not exist.")
        self.assertEqual(response.data[ERROR], "Flock Does Not exist.")
        self.assertEqual(response.data[APP_RESULT], {ERROR: "Flock Does Not exist."})


class OAuthApplicationTests(TestCase):
    def test_creates_unhashed_server_owned_secret_for_password_grant(self):
        user = Users.objects.create_user(
            username="oauth-helper",
            email="oauth-helper@example.com",
            mobile_number=9092052099,
            password="TestPass123",
            public_id=PublicId.create_public_id(),
        )

        application = get_or_create_oauth_application(user)

        self.assertFalse(application.hash_client_secret)
        self.assertEqual(application.authorization_grant_type, application.GRANT_PASSWORD)
        self.assertTrue(application.client_secret)
