from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from common.utils import send_otp


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
