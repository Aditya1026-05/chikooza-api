import datetime
import logging
import random
import traceback

from django.contrib.auth.models import User

import pytz
import requests
from django.conf import settings
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

from chikooza.settings import HOSTNAME
from common.base_models import Users
from common.constant import (
    APP_RESULT,
    CUSTOMER_SIGN_UP_UNIQUE_EMAIL_ID_REQUIRED,
    ERROR,
    FORGOT_PASSWORD_SOCIAL_LOGIN_ERROR,
    INVALID_DATA,
    MESSAGE,
    MOBILE_NUMBER_ALREADY_EXISTS,
    PUBLIC_ID_LENGTH_VALIDATION,
    RECORD_NOT_FOUND,
    TOTAL_RECORDS,
)
from dailydata.models import DailyData
from flocks.models import Flock

logger = logging.getLogger(__name__)


class CustomTokenMatchesOASRequirement(BasePermission):
    """
    Class override for disable get permission on anonymous user.
    """

    def has_permission(self, request, view):
        # allow all GET requests
        if request.method == "GET":
            if request.headers.get("Authorization") and request.user.username == "":
                logger.info("Get authorized user for has_permission method.")
                return request.user and request.user.is_authenticated
            return True
        logger.info("Get authorized user for has_permission method.")
        return request.user and request.user.is_authenticated


def validate_pagination(request):
    """
    This function is created for validate limit and offset.
    """
    offset = request.GET.get("page")
    if offset:
        try:
            int(offset)
        except:
            logger.error(
                "Please pass integer value for size/page for validate_pagination method: %s",
                traceback.format_exc(),
            )
            raise ValidationError({ERROR: "Please pass integer value for size/page."})
    limit = request.GET.get("size")
    if limit:
        try:
            int(limit)
        except:
            logger.error(
                "Please pass integer value for size/page for validate_pagination method: %s",
                traceback.format_exc(),
            )
            raise ValidationError({ERROR: "Please pass integer value for size/page."})
    if offset is None:
        offset = 1
    if limit is None:
        limit = REST_FRAMEWORK.get("PAGE_SIZE")
    offset = (int(offset) - 1) * int(limit)
    limit = int(offset) + int(limit)
    logger.info("Getting limit and offset.")
    return limit, offset


def create_token(user, password, client_id, client_secret):
    """
    This function is used to create authenticate user token.
    """
    data = {
        "username": user,
        "password": password,
        "grant_type": "password",
        "client_id": client_id,
        
#MV-16-6-25- 17-10 comment hardcoded 
         "client_secret":"abc123",
       # "client_secret": client_secret
#MV-16-6-25- 17-10 change end

    }
#MV-16-6-25- 17-10 added headers
    headers = {'Content-type': 'application/x-www-form-urlencoded'}
    token = requests.post(HOSTNAME + "o/token/", data=data , headers=headers)
#MV-16-6-25- 17-10 comment hardcoded 
    logger.info("Successfully get access_token, expires_in and token_type.")
    return {
        "access_token": token.json().get("access_token"),
        "expires_in": token.json().get("expires_in"),
        "token_type": token.json().get("token_type"),
    }
    
    


def check_email_validate(email):
    try:
        User.objects.get(email=email)
        logger.error(
            "Email is already exist for check_email_validate method: %s",
            traceback.format_exc(),
        )
        return error_response(
            CUSTOMER_SIGN_UP_UNIQUE_EMAIL_ID_REQUIRED, status.HTTP_400_BAD_REQUEST
        )

    except User.MultipleObjectsReturned:
        return validation_return_response(
            CUSTOMER_SIGN_UP_UNIQUE_EMAIL_ID_REQUIRED, status.HTTP_400_BAD_REQUEST
        )
    except User.DoesNotExist:
        pass


def check_user_existence(data):
    try:
        data = data.popitem()
        user = Users.objects.get(**{data[0]: data[1]})
        if user.social_type:
            logger.error(
                "Forgot password social login error for check_user_existence method: %s",
                traceback.format_exc(),
            )
            raise validation_return_response(
                field=data[0], message=FORGOT_PASSWORD_SOCIAL_LOGIN_ERROR
            )
        logger.info("User get successfully for check_user_existence method.")
        return user

    except Users.DoesNotExist:
        logger.error(
            "User does not exist for check_user_existence method: %s",
            traceback.format_exc(),
        )
        raise validation_return_response(
            field=data[0],
            message=INVALID_DATA.format(
                "Email id" if data[0] == "username" else "mobile number"
            ),
        )


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


def does_not_exist_return_response(field, message, status_code):
    logger.error(
        "Does not exists for does_not_exist_return_response method: %s",
        traceback.format_exc(),
    )
    return Response(
        {MESSAGE: message, APP_RESULT: {field: message, "status": status_code}},
        status=status_code,
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
    logger.error(
        "Get error response in error_response method: %s", traceback.format_exc()
    )
    return Response({"status": status_code, MESSAGE: message}, status=status_code)


def check_update_email_validate(email, public_id):
    try:
        em = Users.objects.get(email=email)
        if em.public_id == public_id:
            return True
        logger.error(
            "Email is already exist for check_email_validate method: %s",
            traceback.format_exc(),
        )
        return error_response(
            CUSTOMER_SIGN_UP_UNIQUE_EMAIL_ID_REQUIRED, status.HTTP_400_BAD_REQUEST
        )
    except Users.DoesNotExist:
        return True


def send_otp(mobile_number):
    # U: OLD: random.randint(100000, 999999) was discarded and every OTP was 123456.
    # U: NEW: keep local MVP testing easy, but do not force a fixed OTP in production.
    fixed_otp = getattr(settings, "CHIKOOZA_FIXED_OTP", None)
    if fixed_otp:
        return int(fixed_otp)
    if settings.DEBUG:
        return 123456
    return random.randint(100000, 999999)


def otp_delete_after_five_minutes(otp_object):
    if otp_object.created_at < datetime.datetime.now(
        pytz.timezone("UTC")
    ) - datetime.timedelta(minutes=5):
        otp_object.delete()
        return True
    else:
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


def check_update_mobile_number(mobile_number, user):
    try:
        users = Users.objects.get(mobile_number=mobile_number, user_type="customer")
        if user.email == users.email:
            pass
        else:
            validation_return_response(ERROR, MOBILE_NUMBER_ALREADY_EXISTS)
    except Users.DoesNotExist:
        pass


def check_user_existence_for_validation(data):
    result = []
    for key, value in data.items():
        if Users.objects.filter(**{key: value}).exists():
            result.append(key)
    if len(result) != 0:
        raise validation_return_response(ERROR, f'{", ".join(result)} already exists.')
    else:
        pass


def check_flock_existence_for_validation(data):
    result = []
    for key, value in data.items():
        if Flock.objects.filter(**{key: value}).exists():
            result.append(key)
    if len(result) != 0:
        raise validation_return_response(ERROR, f'{", ".join(result)} already exists.')
    else:
        pass


def check_dailydata_existence_for_validation(date, flock_id):
    if DailyData.objects.filter(date=date, flock__public_id=flock_id).exists():
        raise validation_return_response(ERROR, "Daily Data Already Exist")


def daterange(start_date, end_date):
    for n in range(0, int((end_date - start_date).days) + 1, 7):
        yield start_date + datetime.timedelta(n)
