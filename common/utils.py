import datetime
import logging
import random
import sys
import traceback
from secrets import token_urlsafe

from django.core.exceptions import ImproperlyConfigured

import requests
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from common.base_models import Users
from common.constant import (
    APP_RESULT,
    ERROR,
    MESSAGE,
    MOBILE_NUMBER_ALREADY_EXISTS,
    PUBLIC_ID_LENGTH_VALIDATION,
    RECORD_NOT_FOUND,
    TOTAL_RECORDS,
)
from dailydata.models import DailyData
from oauth2_provider.models import Application

logger = logging.getLogger(__name__)


def create_token(user, password, client_id, client_secret):
    """
    This function is used to create authenticate user token.
    """
    if not client_secret:
        raise ImproperlyConfigured("OAuth application client_secret is missing.")

    data = {
        "username": user,
        "password": password,
        "grant_type": "password",
        "client_id": client_id,
        "client_secret": client_secret,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    token = requests.post(
        settings.HOSTNAME + "o/token/", data=data, headers=headers, timeout=10
    )
    try:
        token_data = token.json()
    except ValueError as exc:
        logger.error(
            "OAuth token endpoint returned non-JSON response: %s", token.text[:300]
        )
        raise ImproperlyConfigured(
            "OAuth token endpoint returned an invalid response."
        ) from exc

    if token.status_code >= 400:
        logger.error("OAuth token endpoint failed: %s", token_data)
        raise ValidationError(
            {
                ERROR: token_data.get("error_description")
                or token_data.get("error")
                or "Token creation failed."
            }
        )

    logger.info("Successfully get access_token, expires_in and token_type.")
    return {
        "access_token": token_data.get("access_token"),
        "expires_in": token_data.get("expires_in"),
        "token_type": token_data.get("token_type"),
    }


def get_or_create_oauth_application(user):
    """
    Return a password-grant OAuth application whose secret is usable server-side.
    """
    application = Application.objects.filter(user=user).first()
    secret_needs_rotation = not application or application.hash_client_secret

    if application is None:
        application = Application(user=user)

    if secret_needs_rotation:
        # The password-grant flow needs a server-readable client secret.
        application.client_secret = token_urlsafe(48)
        application.hash_client_secret = False

    application.authorization_grant_type = Application.GRANT_PASSWORD
    application.client_type = Application.CLIENT_CONFIDENTIAL
    application.name = application.name or "user"
    application.redirect_uris = settings.HOSTNAME
    application.save()
    return application


def validation_return_response(field, message):
    logger.error(
        "Validation error for validation_return_response method: %s",
        traceback.format_exc(),
    )
    raise ValidationError(
        {
            MESSAGE: message,
            APP_RESULT: {field: [message]},
            "status": status.HTTP_400_BAD_REQUEST,
        }
    )


def success_response(success_msg, key, msg, status_code):
    logger.info("Success details.")
    return Response(
        {"status": status_code, MESSAGE: success_msg, APP_RESULT: {key: msg}},
        status=status_code,
    )


def list_response(message, count, list_name, result, status_code):
    logger.info("Get list for list_response method.")
    return Response(
        {
            "status": status_code or status.HTTP_200_OK,
            MESSAGE: message,
            APP_RESULT: {TOTAL_RECORDS: count, list_name: result},
        }
    )


def get_detail(message, result, status_code):
    logger.info("Getting details successfully for get_detail method.")
    return Response(
        {"status": status_code, MESSAGE: message, APP_RESULT: result},
        status=status_code,
    )


def delete_response(message, status_code):
    logger.info("Delete method successfully")
    return Response({"status": status_code, MESSAGE: message}, status=status_code)


def error_response(message, status_code):
    """Return a consistent API error while preserving structured field details."""
    readable_message = message
    if isinstance(message, dict):
        readable_message = (
            message.get(ERROR)
            or message.get(MESSAGE)
            or next(iter(message.values()), RECORD_NOT_FOUND)
        )
    if status_code >= 500:
        logger.error(
            "API error response %s: %s",
            status_code,
            readable_message,
            exc_info=bool(sys.exc_info()[0]),
        )
    else:
        logger.info("API error response %s: %s", status_code, readable_message)
    return Response(
        {
            "status": status_code,
            MESSAGE: readable_message,
            ERROR: readable_message,
            APP_RESULT: message if isinstance(message, dict) else {},
        },
        status=status_code,
    )


def send_otp(mobile_number):
    """Generate the configured development OTP or a random production OTP."""
    fixed_otp = getattr(settings, "CHIKOOZA_FIXED_OTP", None)
    if fixed_otp:
        return int(fixed_otp)
    if settings.DEBUG:
        return 123456
    return random.randint(100000, 999999)


def build_otp_response_payload(otp, mobile_number):
    payload = {"mobile_number": mobile_number}
    # OTP values are visible only during local or explicit fixed-OTP testing.
    if settings.DEBUG or getattr(settings, "CHIKOOZA_FIXED_OTP", None):
        payload["otp"] = otp
    return payload


def build_email_otp_response_payload(otp, email):
    payload = {"email": email}
    # Email OTPs follow the same local-testing visibility rule as phone OTPs.
    if settings.DEBUG or getattr(settings, "CHIKOOZA_FIXED_OTP", None):
        payload["email_otp"] = otp
    return payload


def deliver_email_otp(email, otp):
    """
    Send email OTP when delivery is enabled. Local/dev keeps the OTP in the API
    response so setup is possible without SMTP credentials.
    """
    if not getattr(settings, "CHIKOOZA_EMAIL_OTP_DELIVERY_ENABLED", False):
        return False
    send_mail(
        "Verify your Chikooza email",
        f"Your Chikooza email verification OTP is {otp}.",
        getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@chikooza.local"),
        [email],
        fail_silently=False,
    )
    return True


def otp_delete_after_five_minutes(otp_object):
    """Delete and report OTP records older than five minutes."""
    expiry_cutoff = timezone.now() - datetime.timedelta(minutes=5)
    if otp_object.created_at < expiry_cutoff:
        otp_object.delete()
        return True
    return False


def validate_url_value(public_id, key_name):
    """
    This function is created to validate ids.
    :param public_id:
    :param key_name:
    :raise ValidationError
    """
    try:
        if public_id is not None:
            int(public_id)
            if public_id == "0" or public_id == 0:
                raise validation_return_response(
                    field=MESSAGE, message=RECORD_NOT_FOUND
                )
            elif len(str(public_id)) > PUBLIC_ID_LENGTH_VALIDATION:
                raise validation_return_response(
                    field=MESSAGE, message=RECORD_NOT_FOUND
                )
    except ValueError:
        raise validation_return_response(field=MESSAGE, message=RECORD_NOT_FOUND)


def mobile_number_validation(mobile_number):
    try:
        Users.objects.get(mobile_number=mobile_number)
        logger.error(
            "You are already registered user please go for login.",
            traceback.format_exc(),
        )
        raise validation_return_response("mobile_number", MOBILE_NUMBER_ALREADY_EXISTS)
    except Users.MultipleObjectsReturned:
        logger.error(
            "Mobile number is already exist for mobile_number_validation method: %s",
            traceback.format_exc(),
        )
        raise validation_return_response("mobile_number", MOBILE_NUMBER_ALREADY_EXISTS)
    except Users.DoesNotExist:
        pass


def check_user_existence_for_validation(data):
    result = []
    for key, value in data.items():
        if Users.objects.filter(**{key: value}).exists():
            result.append(key)
    if result:
        raise validation_return_response(ERROR, f'{", ".join(result)} already exists.')


def check_dailydata_existence_for_validation(date, flock_id):
    if DailyData.objects.filter(date=date, flock__public_id=flock_id).exists():
        raise validation_return_response(ERROR, "Daily Data Already Exist")


def daterange(start_date, end_date):
    for n in range(0, int((end_date - start_date).days) + 1, 7):
        yield start_date + datetime.timedelta(n)
