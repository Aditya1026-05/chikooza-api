# Create your views here.
from oauth2_provider.contrib.rest_framework import (
    OAuth2Authentication,
    TokenMatchesOASRequirements,
)
from rest_framework import status, viewsets
from rest_framework.response import Response

from common.constant import (
    COUNTRY_DOES_NOT_EXIST,
    ERROR,
    FARM_DOES_NOT_EXIST,
    PERMISSION_NOT_ALLOWED,
    STATE_DOES_NOT_EXIST,
)
from common.utils import get_detail, success_response, validate_url_value
from farm.models import Country, Farm, State
from farm.serializers import (
    AddFarmSerializer,
    FarmGetSerializer,
    FarmListSerializer,
    GetCountrySerializer,
    GetStateSerializer,
    UpdateFarmSerializer,
)
from farm.services import AddFarmService, UpdateFarmService


class FarmView(viewsets.ViewSet):
    """
    Class is used for farm.
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
        try:
            serializer = AddFarmSerializer(data=request.data)
            if serializer.is_valid(raise_exception=True):
                serializer_data = serializer.validated_data
                farm_object = AddFarmService.execute(
                    {"data": serializer_data, "user": request.user.users}
                )
            return get_detail(
                "Farm created",
                {"public_id": farm_object.public_id},
                status.HTTP_201_CREATED,
            )
        except State.DoesNotExist:
            return Response({ERROR: STATE_DOES_NOT_EXIST}, status.HTTP_404_NOT_FOUND)
        except Country.DoesNotExist:
            return Response({ERROR: COUNTRY_DOES_NOT_EXIST}, status.HTTP_404_NOT_FOUND)

    def retrieve(cls, request, pk):
        try:
            validate_url_value(pk, "farmPublicId")
            farm = Farm.objects.get(public_id=pk)
            if request.user.users == farm.user or request.user.is_superuser:
                return get_detail(
                    "Farm details", FarmGetSerializer(farm).data, status.HTTP_200_OK
                )
            return Response(
                {ERROR: PERMISSION_NOT_ALLOWED}, status.HTTP_400_BAD_REQUEST
            )
        except Farm.DoesNotExist:
            return Response({ERROR: FARM_DOES_NOT_EXIST}, status.HTTP_404_NOT_FOUND)

    def list(cls, request):
        try:
            farm = Farm.objects.filter(user=request.user.users)
            return get_detail(
                "Farms List of login user.",
                FarmListSerializer(farm, many=True).data,
                status.HTTP_200_OK,
            )

        except Farm.DoesNotExist:
            return Response({ERROR: FARM_DOES_NOT_EXIST}, status.HTTP_404_NOT_FOUND)

    def partial_update(cls, request, pk):
        try:
            validate_url_value(pk, "farmPublicId")
            farm = Farm.objects.get(public_id=pk)
            if request.user.users == farm.user or request.user.is_superuser:
                serializer = UpdateFarmSerializer(data=request.data)
                if serializer.is_valid(raise_exception=True):
                    serializer_data = serializer.validated_data
                    UpdateFarmService.execute({"data": serializer_data, "farm": farm})
                    return success_response(
                        "Profile update successfully",
                        "profile",
                        "Profile update successfully",
                        200,
                    )
        except Farm.DoesNotExist:
            return Response({ERROR: FARM_DOES_NOT_EXIST}, status.HTTP_404_NOT_FOUND)


class StateView(viewsets.ViewSet):
    """
    Class is used to get list of states.
    """

    def list(cls, request):
        state = State.objects.all()
        return get_detail(
            "State List", GetStateSerializer(state, many=True).data, status.HTTP_200_OK
        )


class CountryView(viewsets.ViewSet):
    """
    Class is used to get list of country.
    """

    def list(cls, request):
        country = Country.objects.all()
        return get_detail(
            "Country List",
            GetCountrySerializer(country, many=True).data,
            status.HTTP_200_OK,
        )
