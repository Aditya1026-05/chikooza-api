from django.contrib.auth import authenticate
from django.db import IntegrityError

import requests
from oauth2_provider.contrib.rest_framework import (
    OAuth2Authentication,
    TokenMatchesOASRequirements,
)
from oauth2_provider.models import AccessToken, Application
from rest_framework import status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from chikooza.settings import HOSTNAME
from common.base_models import Otp, Users
from common.constant import (
    ACCOUNT_DEACTIVATES,
    ALREADY_REGISTERED,
    ERROR,
    INVALID_CREDENTIALS,
    INVALID_OTP,
    INVALID_PASSWORD,
    MOBILE_NUMBER_ALREADY_EXISTS,
    MOBILE_NUMBER_NOT_VERIFIED,
    PERMISSION_NOT_ALLOWED,
    USER_DOES_NOT_EXIST,
    USERNAME_ALREADY_EXIST,
)
from common.utils import (
    build_otp_response_payload,
    check_user_existence_for_validation,
    create_token,
    get_detail,
    get_or_create_oauth_application,
    otp_delete_after_five_minutes,
    success_response,
    validate_url_value,
    validation_return_response,
)
from users.serializers import (
    ChangePasswordSerializer,
    ForgetPasswordSerializer,
    LoginSerializer,
    ProfileUserSerializer,
    ResetPasswordSerializer,
    SendOtpForUpdateMobileSerializer,
    SendOTPSerializer,
    SignUpSerializer,
    UpdateMobileSerializer,
    UpdateUserProfileSerializer,
    VerifyOTPSerializer,
)
from users.services import (
    ChangePasswordService,
    ForgetPasswordService,
    ResetPasswordServices,
    SendOTPServices,
    UpdateMobileService,
    UpdateUserProfileService,
    VerifyOtpService,
)
from users.utils import create_user


class SendOTPView(viewsets.ViewSet):
    """
    Class to send otp.
    """

    def create(self, request):
        serializer = SendOTPSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            try:
                data = {
                    "mobile_number": serializer.data["mobile_number"],
                    "username": serializer.data["username"],
                    "email": serializer.data["email"],
                }
                check_user_existence_for_validation(data)
                Otp.objects.get(
                    mobile_number=serializer.data["mobile_number"], is_verify=True
                )
                return Response(
                    {ERROR: MOBILE_NUMBER_ALREADY_EXISTS}, status.HTTP_400_BAD_REQUEST
                )
            except Otp.DoesNotExist:
                create_otp = SendOTPServices.execute(
                    {"mobile_number": serializer.data["mobile_number"]}
                )
                return get_detail(
                    "OTP created",
                    # U: OLD: {"otp": create_otp.otp, "mobile_number": create_otp.mobile_number}
                    # U: NEW: hide OTP in production responses, keep it visible for local MVP setup.
                    build_otp_response_payload(create_otp.otp, create_otp.mobile_number),
                    status.HTTP_201_CREATED,
                )


class VerifyOTPView(viewsets.ViewSet):
    """
    Class to verify otp.
    """

    @classmethod
    def create(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            if Otp.objects.filter(
                mobile_number=serializer.data["mobile_number"],
                otp=serializer.data["otp"],
            ).exists():
                # otp_delete_after_five_minutes(Otp.objects.get(mobile_number=serializer.data['mobile_number']))
                return get_detail(
                    "Mobile Number Verified.",
                    {"mobile_number": serializer.data["mobile_number"]},
                    status.HTTP_200_OK,
                )
            return Response({ERROR: INVALID_OTP}, status.HTTP_400_BAD_REQUEST)


class SignUpView(viewsets.ViewSet):
    """
    Class is used to register a user.
    """

    @classmethod
    def create(cls, request):
        try:
            serializer = SignUpSerializer(data=request.data)
            if serializer.is_valid(raise_exception=True):
                serializer_data = serializer.validated_data
                data = {"email": serializer_data["email"]}
                check_user_existence_for_validation(data)
                verified_otp = VerifyOtpService.execute(
                    {
                        "mobile_number": serializer_data["mobile_number"],
                        "otp": serializer_data["otp"],
                    }
                )
                if Otp.objects.filter(
                    mobile_number=serializer_data["mobile_number"]
                ).exists():
                    if verified_otp:
                        return create_user(serializer_data, True)
                    return Response({ERROR: INVALID_OTP}, status.HTTP_400_BAD_REQUEST)
                raise validation_return_response(
                    "mobile_number", MOBILE_NUMBER_NOT_VERIFIED
                )

        except IntegrityError:
            return validation_return_response("username", USERNAME_ALREADY_EXIST)


class LoginView(viewsets.ViewSet):
    """
    Class for login of a user.
    """

    @classmethod
    def create(cls, request):
        try:
            serializer = LoginSerializer(data=request.data)
            if serializer.is_valid(raise_exception=True):
                serializer_data = serializer.validated_data
                username = serializer_data.get("username")
                password = serializer_data.get("password")
                user = Users.objects.get(username=username)
                if user.is_active is True:
                    validate_user = authenticate(username=username, password=password)
                    if validate_user is None:
                        raise ValidationError(
                            {ERROR: INVALID_CREDENTIALS}, status.HTTP_400_BAD_REQUEST
                        )
                    # U: OLD: login assumed an old unhashed OAuth app secret already existed.
                    # U: NEW: create or rotate the user's OAuth app so Django OAuth Toolkit 3 works.
                    user_detail = get_or_create_oauth_application(user)
                    token = create_token(
                        user.username,
                        password,
                        user_detail.client_id,
                        user_detail.client_secret,
                    )
                    token["public_id"] = user.public_id
                    token["name"] = user.first_name
                    return get_detail("User Login", token, status.HTTP_200_OK)
                else:
                    return Response(
                        {ERROR: ACCOUNT_DEACTIVATES}, status.HTTP_406_NOT_ACCEPTABLE
                    )
        except Users.DoesNotExist:
            return Response({ERROR: INVALID_CREDENTIALS}, status.HTTP_404_NOT_FOUND)


class ProfileUserView(viewsets.ViewSet):
    """
    Class to get details of login user.
    """

    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenMatchesOASRequirements]

    required_alternate_scopes = {
        "GET": [["read"]],
        "POST": [["create"]],
        "PATCH": [["update"]],
        "PUT": [["update"]],
    }

    def create(cls, request):
        pass

    def retrieve(cls, request, pk):
        try:
            validate_url_value(pk, "usersPublicId")
            users = Users.objects.get(public_id=pk)
            if request.user.users.public_id == int(pk) or request.user.is_superuser:
                return get_detail(
                    "Profile", ProfileUserSerializer(users).data, status.HTTP_200_OK
                )
            return Response(
                {ERROR: PERMISSION_NOT_ALLOWED}, status.HTTP_400_BAD_REQUEST
            )
        except Users.DoesNotExist:
            return Response({ERROR: USER_DOES_NOT_EXIST}, status.HTTP_404_NOT_FOUND)

    @classmethod
    def partial_update(cls, request, pk):
        try:
            validate_url_value(pk, "usersPublicId")
            users = Users.objects.get(public_id=pk)
            if request.user.users.public_id == int(pk) or request.user.is_superuser:
                serializer = UpdateUserProfileSerializer(data=request.data)
                if serializer.is_valid(raise_exception=True):
                    serializer_data = serializer.validated_data
                    if (
                        Users.objects.exclude(email=users.email)
                        .filter(email=serializer_data.get("email"))
                        .exists()
                    ):
                        return Response(
                            {ERROR: ALREADY_REGISTERED}, status.HTTP_400_BAD_REQUEST
                        )

                    UpdateUserProfileService.execute(
                        {
                            "email": serializer_data.get("email"),
                            "mobile_number": serializer_data.get("mobile_number"),
                            "name": serializer_data.get("name"),
                            "users": users,
                        }
                    )
                    return success_response(
                        "Profile update successfully",
                        "profile",
                        "Profile update successfully",
                        200,
                    )
            return Response(
                {ERROR: PERMISSION_NOT_ALLOWED}, status.HTTP_400_BAD_REQUEST
            )
        except Users.DoesNotExist:
            return Response({ERROR: USER_DOES_NOT_EXIST}, status.HTTP_404_NOT_FOUND)


class ResetPasswordView(viewsets.ViewSet):
    """
    Class is used to send otp for forget password.
    """

    def create(self, request):
        try:
            serializer = ResetPasswordSerializer(data=request.data)
            if serializer.is_valid(raise_exception=True):
                serializer_data = serializer.validated_data
                mobile_number = serializer_data.get("mobile_number")
                username = serializer_data.get("username")
                users = Users.objects.get(
                    mobile_number=mobile_number, username=username
                )
                if Users.objects.filter(
                    mobile_number=mobile_number, username=username
                ).exists():
                    create_otp = ResetPasswordServices.execute(
                        {
                            "mobile_number": serializer.data["mobile_number"],
                            "users": users,
                        }
                    )
                    return get_detail(
                        "OTP created to reset password",
                        # U: OLD: {"otp": create_otp.otp, "mobile_number": serializer.data["mobile_number"]}
                        # U: NEW: hide OTP in production responses, keep it visible for local MVP setup.
                        build_otp_response_payload(
                            create_otp.otp,
                            serializer.data["mobile_number"],
                        ),
                        status.HTTP_201_CREATED,
                    )
        except Users.DoesNotExist:
            return Response({ERROR: USER_DOES_NOT_EXIST}, status.HTTP_404_NOT_FOUND)


class ForgetPasswordView(viewsets.ViewSet):
    """
    Class to create new password for the users.
    """

    def create(self, request):
        try:
            serializer = ForgetPasswordSerializer(data=request.data)
            if serializer.is_valid(raise_exception=True):
                serializer_data = serializer.validated_data
                if Users.objects.filter(
                    mobile_number=serializer_data["mobile_number"],
                    username=serializer_data["username"],
                ).exists():
                    value = ForgetPasswordService.execute(serializer_data)
                    if value is True:
                        return get_detail(
                            "Password changed successfully.",
                            {"password": "Password changed"},
                            status.HTTP_201_CREATED,
                        )
                    else:
                        return Response(
                            {ERROR: INVALID_OTP}, status.HTTP_400_BAD_REQUEST
                        )
            return Response({ERROR: USER_DOES_NOT_EXIST}, status.HTTP_404_NOT_FOUND)
        except Users.DoesNotExist:
            return Response({ERROR: USER_DOES_NOT_EXIST}, status.HTTP_404_NOT_FOUND)


class SendOtpForUpdateMobileView(viewsets.ViewSet):
    """
    Class is used to send otp while changing mobile number.
    """

    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenMatchesOASRequirements]

    required_alternate_scopes = {
        "GET": [["read"]],
        "POST": [["create"]],
        "PATCH": [["update"]],
        "PUT": [["update"]],
    }

    @classmethod
    def create(cls, request):
        """
         This class method is used to send otp on business_user mobile number..
        :param request:
        :return:
        """
        serializer = SendOtpForUpdateMobileSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer_data = serializer.validated_data
            if (
                Users.objects.exclude(mobile_number=request.user.users.mobile_number)
                .filter(mobile_number=serializer_data.get("mobile_number"))
                .exists()
            ):
                return Response(
                    {ERROR: MOBILE_NUMBER_ALREADY_EXISTS}, status.HTTP_400_BAD_REQUEST
                )
            create_otp = SendOTPServices.execute(
                {"mobile_number": serializer.data["mobile_number"]}
            )
            return get_detail(
                "OTP created to update mobile_number",
                # U: OLD: {"otp": create_otp.otp, "mobile_number": create_otp.mobile_number}
                # U: NEW: hide OTP in production responses, keep it visible for local MVP setup.
                build_otp_response_payload(create_otp.otp, create_otp.mobile_number),
                status.HTTP_201_CREATED,
            )


class UpdateMobileNoView(viewsets.ViewSet):
    """
    Class is used to receive otp while changing mobile number.
    """

    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenMatchesOASRequirements]

    required_alternate_scopes = {
        "GET": [["read"]],
        "POST": [["create"]],
        "PATCH": [["update"]],
        "PUT": [["update"]],
    }

    @classmethod
    def partial_update(cls, request, pk):
        try:
            validate_url_value(pk, "usersPublicId")
            users = Users.objects.get(public_id=pk)
            if request.user.users.public_id == int(pk) or request.user.is_superuser:
                serializer = UpdateMobileSerializer(data=request.data)
                if serializer.is_valid(raise_exception=True):
                    serializer_data = serializer.validated_data
                    if Otp.objects.filter(
                        mobile_number=serializer.data["mobile_number"]
                    ).exists():
                        otp = Otp.objects.get(
                            mobile_number=serializer.data["mobile_number"]
                        )
                        if otp.otp == serializer_data["otp"]:
                            otp_delete_after_five_minutes(
                                Otp.objects.get(
                                    mobile_number=serializer.data["mobile_number"]
                                )
                            )
                            UpdateMobileService.execute(
                                {
                                    "mobile_number": serializer_data.get(
                                        "mobile_number"
                                    ),
                                    "users": users,
                                }
                            )
                            return success_response(
                                "Profile update successfully",
                                "profile",
                                "Profile update successfully",
                                200,
                            )
                        return Response(
                            {ERROR: INVALID_OTP}, status.HTTP_400_BAD_REQUEST
                        )
                    raise validation_return_response(
                        "mobile_number", MOBILE_NUMBER_NOT_VERIFIED
                    )
            return Response(
                {ERROR: PERMISSION_NOT_ALLOWED}, status.HTTP_400_BAD_REQUEST
            )
        except Users.DoesNotExist:
            return Response({ERROR: USER_DOES_NOT_EXIST}, status.HTTP_404_NOT_FOUND)


class ChangePasswordView(viewsets.ViewSet):
    """
    Class is used to change the password of login user.
    """

    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenMatchesOASRequirements]

    required_alternate_scopes = {
        "GET": [["read"]],
        "POST": [["create"]],
        "PATCH": [["update"]],
        "PUT": [["update"]],
    }

    @classmethod
    def create(cls, request):
        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer_data = serializer.validated_data
            current_password = serializer_data["current_password"]
            if request.user.check_password(serializer_data["current_password"]):
                ChangePasswordService.execute(
                    {
                        "password": serializer_data["current_password"],
                        "new_password": serializer_data["new_password"],
                        "users": request.user,
                    }
                )
                return success_response(
                    "Password changed successfully",
                    "password changed",
                    "Password changed successfully",
                    200,
                )
            return Response(
                {ERROR: INVALID_PASSWORD.format(current_password)},
                status.HTTP_400_BAD_REQUEST,
            )


class LogoutView(viewsets.ViewSet):
    """
    Class is used for logout view.
    """

    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenMatchesOASRequirements]

    required_alternate_scopes = {"GET": [["read"]]}

    def list(cls, request):
        user = request.user
        token = request._auth.token
        access_token = AccessToken.objects.get(token=token)
        user_detail = Application.objects.filter(user_id=user.id)
        data = {
            "token": access_token.token,
            "client_id": user_detail.first().client_id,
            "client_secret": user_detail.first().client_secret,
        }
        requests.post(HOSTNAME + "o/revoke_token/", data=data)
        return success_response("Logout", "Logout", "Logout successfully", 200)
