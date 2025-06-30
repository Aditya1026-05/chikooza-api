import datetime

from oauth2_provider.contrib.rest_framework import (
    OAuth2Authentication,
    TokenMatchesOASRequirements,
)
from rest_framework import status, viewsets
from rest_framework.response import Response

from common.constant import (
    BREED_DOES_NOT_EXIST,
    ERROR,
    FARM_DOES_NOT_EXIST,
    FLOCK_DOES_NOT_EXIST,
    HATCHERY_DOES_NOT_EXIST,
    INTEGRATOR_DOES_NOT_EXIST,
)
from common.utils import (
    error_response,
    get_detail,
    list_response,
    success_response,
    validate_url_value, validation_return_response,
)
from farm.models import Farm
from flocks.models import Breed, Flock, Hatchery, Integrator
from flocks.serializers import (
    AddFlockSerializer,
    BreedListSerializer,
    GetFlockSerializer,
    IntegratorListSerializer,
    UpdateFlockSerializer, FlockSummarySerializer,
)
from flocks.services import AddFlockService, UpdateFlockService
from purchase.models import Purchase

#MV-23-6-25- 17-10 new imports
from flocks.utils import prepare_daily_data_response
from dailydata.models import DailyData
#MV-23-6-25- 17-10 change end

class FlockView(viewsets.ViewSet):
    """
    Class to work on flocks.
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
            serializer = AddFlockSerializer(data=request.data)
            if serializer.is_valid(raise_exception=True):
                serializer_data = serializer.validated_data
                today_date = datetime.date.today()
                hatch_date = serializer_data["hatch_date"]
                if hatch_date > today_date:
                    return error_response(
                        {ERROR: "Flock hatch date cannot be greater than today's date."},
                        status.HTTP_404_NOT_FOUND,
                    )
                else:
                    pass
                flock = AddFlockService.execute(
                    {"data": serializer_data, "user": request.user.users}
                )
            return get_detail(
                "Flock Created Successfully.",
                {"public_id": flock.public_id},
                status.HTTP_201_CREATED,
            )
        except Farm.DoesNotExist:
            return Response({ERROR: FARM_DOES_NOT_EXIST}, status.HTTP_404_NOT_FOUND)
        except Breed.DoesNotExist:
            return Response({ERROR: BREED_DOES_NOT_EXIST}, status.HTTP_404_NOT_FOUND)
        except Hatchery.DoesNotExist:
            return Response({ERROR: HATCHERY_DOES_NOT_EXIST}, status.HTTP_404_NOT_FOUND)
        except Integrator.DoesNotExist:
            return Response(
                {ERROR: INTEGRATOR_DOES_NOT_EXIST}, status.HTTP_404_NOT_FOUND
            )

    def retrieve(cls, request, pk):
        try:
            validate_url_value(pk, "farmPublicId")
            if Farm.objects.filter(user=request.user.users, public_id=pk).exists():
                farm = Farm.objects.get(public_id=pk)
                flocks = Flock.objects.filter(farm=farm)
                return list_response(
                    "Flocks List",
                    flocks.count(),
                    "flock_list",
                    GetFlockSerializer(flocks, many=True).data,
                    status.HTTP_200_OK,
                )

            return Response({ERROR: FARM_DOES_NOT_EXIST}, status.HTTP_404_NOT_FOUND)
        except Farm.DoesNotExist:
            return Response({ERROR: FARM_DOES_NOT_EXIST}, status.HTTP_404_NOT_FOUND)

    def partial_update(cls, request, pk):
        try:
            validate_url_value(pk, "flockPublicId")
            if Flock.objects.filter(public_id=pk).exists():
                flock = Flock.objects.get(public_id=pk)
                serializer = UpdateFlockSerializer(data=request.data)
                if serializer.is_valid(raise_exception=True):
                    serializer_data = serializer.validated_data
                    today_date = datetime.date.today()
                    hatch_date = serializer_data["hatch_date"]
                    if hatch_date > today_date:
                        return error_response(
                            {ERROR: "Flock hatch date cannot be greater than today's date."},
                            status.HTTP_404_NOT_FOUND,
                        )
                    else:
                        pass
                    UpdateFlockService.execute(
                        {"data": serializer_data, "flock": flock}
                    )
                    return success_response(
                        "Flock update successfully",
                        "Flock",
                        "Flock update successfully",
                        200,
                    )
            return Response({ERROR: FLOCK_DOES_NOT_EXIST}, status.HTTP_404_NOT_FOUND)
        except Flock.DoesNotExist:
            return Response({ERROR: FLOCK_DOES_NOT_EXIST}, status.HTTP_404_NOT_FOUND)
        except Integrator.DoesNotExist:
            return Response(
                {ERROR: INTEGRATOR_DOES_NOT_EXIST}, status.HTTP_404_NOT_FOUND
            )
        except Breed.DoesNotExist:
            return Response({ERROR: BREED_DOES_NOT_EXIST}, status.HTTP_404_NOT_FOUND)
        except Hatchery.DoesNotExist:
            return Response({ERROR: HATCHERY_DOES_NOT_EXIST}, status.HTTP_404_NOT_FOUND)


class BreedView(viewsets.ViewSet):
    """
    Class to create breed objects.
    """

    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenMatchesOASRequirements]

    required_alternate_scopes = {
        "GET": [["read"]],
        "POST": [["create"]],
        "PATCH": [["update"]],
        "PUT": [["update"]],
    }

    def list(cls, request):
        breeds = Breed.objects.all()
        return get_detail(
            "Breeds List",
            BreedListSerializer(breeds, many=True).data,
            status.HTTP_200_OK,
        )


class IntegratorView(viewsets.ViewSet):
    """
    Class to create integrator objects.
    """

    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenMatchesOASRequirements]

    required_alternate_scopes = {
        "GET": [["read"]],
        "POST": [["create"]],
        "PATCH": [["update"]],
        "PUT": [["update"]],
    }

    def list(cls, request):
        integrators = Integrator.objects.all()
        return get_detail(
            "Integrators List",
            IntegratorListSerializer(integrators, many=True).data,
            status.HTTP_200_OK,
        )


class FlockDetailView(viewsets.ViewSet):
    """
    Class to give details of flock.
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
    def retrieve(cls, request, pk):
        validate_url_value(pk, "flockPublicId")
        if Flock.objects.filter(user=request.user.users, public_id=pk).exists():
            flocks = Flock.objects.get(user=request.user.users, public_id=pk)

            return get_detail(
                "Flocks Detail", GetFlockSerializer(flocks).data, status.HTTP_200_OK
            )
        return error_response(FLOCK_DOES_NOT_EXIST, status.HTTP_404_NOT_FOUND)


class FlockSummaryView(viewsets.ViewSet):
    """
       Class to give details of flock.
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
    def retrieve(cls, request, pk):
        try:
            validate_url_value(pk, "flockPublicId")
            flock = Flock.objects.get(public_id=pk)
            # return get_detail(Add commentMore actions
            #     "Flock Summary",
            #     FlockSummarySerializer(flock).data,
            #     status.HTTP_200_OK,
            # )
        # except Flock.DoesNotExist:Add commentMore actions
        #     return Response({ERROR: FLOCK_DOES_NOT_EXIST}, status.HTTP_404_NOT_FOUND)
            
#MV-23-6-25- 17-10 update response
            base_data = FlockSummarySerializer(flock).data
            
            latest_daily_data = DailyData.objects.filter(flock=flock).order_by('-date').first()
            
            if latest_daily_data:
                enriched = prepare_daily_data_response(latest_daily_data, flock)
                base_data.update({
                    "birds_count": enriched["bird_count"],
                    "total_feed_purchased": enriched["total_feed_purchased"],
                    "total_feed_consumed": enriched["total_feed_consumed"],
                    "feed_stock": enriched["feed_stock"],
                    "average_feed_per_bird": enriched["average_feed_per_bird"],
                    "total_average_feed": enriched["total_average_feed"],
                    "total_mortality_percentage": enriched["total_mortality_percentage"],
                    "cum_mort": enriched["cum_mort"],
                    "fcr": enriched["fcr"],
                    "total_fcr": enriched["total_fcr"],
                    "remarks": enriched["remarks"],
                })
            
            return Response({
                "success": True,
                "results": base_data
            }, status=status.HTTP_200_OK)
            
        except Flock.DoesNotExist:
            return Response({
                "success": False,
                "error": FLOCK_DOES_NOT_EXIST
            }, status=status.HTTP_404_NOT_FOUND)
#MV-23-6-25- 17-10 change end