import datetime

# Create your views here.
from oauth2_provider.contrib.rest_framework import (
    OAuth2Authentication,
    TokenMatchesOASRequirements,
)
from rest_framework import status, viewsets
from rest_framework.response import Response

from common.constant import (
    DAILY_DATA_DOES_NOT_EXIST,
    ERROR,
    FLOCK_DOES_NOT_EXIST,
    FLOCK_VACCINATION_DELETE,
    FLOCK_VACCINATION_DOES_NOT_EXIST,
    PURCHASE_DOES_NOT_EXIST,
    VACCINES_DOES_NOT_EXIST, DARKNESS_TIME_DOES_NOT_EXIST, FEED_AVAILABILITY_DOES_NOT_EXIST,
)
from common.utils import (
    check_dailydata_existence_for_validation,
    delete_response,
    error_response,
    get_detail,
    list_response,
    success_response,
)
from dailydata.models import DailyData, FlockVaccination, Vaccines, DarknessTime, FeedAvailability
from dailydata.serializers import (
    CreateDailyDataSerializer,
    CreateFlockVaccinationSerializer,
    DailyDataAvgFeedSerializer,
    DailyDataFCRSerializer,
    DailyDataGetSerializer,
    DailyDataMortalitySerializer,
    GetFlockVaccinationSerializer,
    GetVaccinesSerializer,
    ListDailyDataSerializer,
    UpdateDailyDataSerializer,
    YesterdayDailyDataGetSerializer, GetDailyDataListSerializer, GetDarknessTimeListSerializer,
    GetFeedAvailabilityListSerializer,
)
from dailydata.services import (
    CreateDailyDataService,
    CreateFlockVaccinationService,
    UpdateDailyDataService,
)
from flocks.models import Flock
from flocks.serializers import GetDailyDataDetailSerializer
from purchase.models import Purchase
from sales.models import Sales
from users.utils import render_to_pdf
from flocks.utils import prepare_daily_data_response


class DailyDataView(viewsets.ViewSet):
    """
    Class to create daily data object.
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
        try:
            serializer = CreateDailyDataSerializer(data=request.data)
            if serializer.is_valid(raise_exception=True):
                serializer_data = serializer.validated_data
                check_dailydata_existence_for_validation(
                    serializer_data["date"], serializer_data["flock_public_id"]
                )
                daily_data = CreateDailyDataService.execute(
                    {"data": serializer_data, "user": request.user.users}
                )
                return get_detail(
                    "Daily Data Created",
                    {"public_id": daily_data.public_id},
                    status.HTTP_201_CREATED,
                )
        except Flock.DoesNotExist:
            return Response({ERROR: FLOCK_DOES_NOT_EXIST}, status.HTTP_404_NOT_FOUND)
        except Purchase.DoesNotExist:
            return Response({ERROR: PURCHASE_DOES_NOT_EXIST}, status.HTTP_404_NOT_FOUND)
        except DarknessTime.DoesNotExist:
            return Response({ERROR: DARKNESS_TIME_DOES_NOT_EXIST}, status.HTTP_404_NOT_FOUND)
        except FeedAvailability.DoesNotExist:
            return Response({ERROR: FEED_AVAILABILITY_DOES_NOT_EXIST}, status.HTTP_404_NOT_FOUND)

    @classmethod
    def list(cls, request):
        try:
            serializer = ListDailyDataSerializer(data=request.GET)
            if serializer.is_valid(raise_exception=True):
                serializer_data = serializer.validated_data
                flock_public_id = serializer_data["flock"].get("public_id")
                flock = Flock.objects.get(public_id=flock_public_id)
                flock_date = flock.hatch_date
                date = serializer_data["date"]
                number_of_days = (date - flock_date).days
                yesterday = date - datetime.timedelta(days=1)
                
                if DailyData.objects.filter(flock__public_id=flock_public_id, date=yesterday).exists():
                    yesterday_daily_data = DailyData.objects.get(
                        flock__public_id=flock_public_id, date=yesterday
                    )
                    yesterday_daily_data_result = YesterdayDailyDataGetSerializer(yesterday_daily_data).data
                    # Add calculated values
                    yesterday_calculated = prepare_daily_data_response(yesterday_daily_data, flock)
                    yesterday_daily_data_result.update(yesterday_calculated)
                else:
                    yesterday_daily_data_result = {}
                    
                if DailyData.objects.filter(flock__public_id=flock_public_id, date=date).exists():
                    dailydata = DailyData.objects.get(
                        flock__public_id=flock_public_id, date=date
                    )
                    result = DailyDataGetSerializer(dailydata).data
                    # Add calculated values
                    today_calculated = prepare_daily_data_response(dailydata, flock)
                    result.update(today_calculated)
                else:
                    result = {}
                return get_detail(
                    "Daily data details",
                    {
                        "daily_data": result,
                        "number_of_days": number_of_days,
                        "yesterday_daily_data": yesterday_daily_data_result,
                    },
                    status.HTTP_200_OK,
                )
        except Flock.DoesNotExist:
            return Response({ERROR: FLOCK_DOES_NOT_EXIST}, status.HTTP_404_NOT_FOUND)
        
    @classmethod
    def partial_update(cls, request, pk):
        try:
            dailydata = DailyData.objects.get(public_id=pk)
            serializer = UpdateDailyDataSerializer(data=request.data)
            if serializer.is_valid(raise_exception=True):
                serializer_data = serializer.validated_data
                UpdateDailyDataService.execute(
                    {"data": serializer_data, "daily_data": dailydata}
                )
                return success_response(
                    "Daily Data update successfully",
                    "daily_data",
                    "Daily Data update successfully",
                    200,
                )
        except DailyData.DoesNotExist:
            return Response(
                {ERROR: DAILY_DATA_DOES_NOT_EXIST}, status.HTTP_404_NOT_FOUND
            )


class FlockVaccinationView(viewsets.ViewSet):
    """
    Class to create vaccine objects for daily data.
    """

    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenMatchesOASRequirements]

    required_alternate_scopes = {
        "GET": [["read"]],
        "POST": [["create"]],
        "PATCH": [["update"]],
        "PUT": [["update"]],
        "DELETE": [["delete"]],
    }

    @classmethod
    def create(cls, request):
        try:
            serializer = CreateFlockVaccinationSerializer(data=request.data)
            if serializer.is_valid(raise_exception=True):
                serializer_data = serializer.validated_data
                flock_vaccination = CreateFlockVaccinationService.execute(
                    {"data": serializer_data}
                )
                return get_detail(
                    "Flock Vaccination Created",
                    {"public_id": flock_vaccination.public_id},
                    status.HTTP_201_CREATED,
                )
        except Flock.DoesNotExist:
            return error_response(
                {ERROR: FLOCK_DOES_NOT_EXIST}, status.HTTP_404_NOT_FOUND
            )

        except DailyData.DoesNotExist:
            return error_response(
                {ERROR: DAILY_DATA_DOES_NOT_EXIST}, status.HTTP_404_NOT_FOUND
            )

        except Vaccines.DoesNotExist:
            return error_response(
                {ERROR: VACCINES_DOES_NOT_EXIST}, status.HTTP_404_NOT_FOUND
            )

    @classmethod
    def list(cls, request):
        flock_vaccination = FlockVaccination.objects.all()
        return list_response(
            "Flock Vaccination List",
            flock_vaccination.count(),
            "flock_vaccination_list",
            GetFlockVaccinationSerializer(flock_vaccination, many=True).data,
            status.HTTP_200_OK,
        )

    @classmethod
    def retrieve(cls, request, pk):
        try:
            flock_vaccination = FlockVaccination.objects.get(public_id=pk)
            return get_detail(
                "Flock Vaccination Detail",
                GetFlockVaccinationSerializer(flock_vaccination).data,
                status.HTTP_200_OK,
            )
        except FlockVaccination.DoesNotExist:
            return error_response(
                {ERROR: FLOCK_VACCINATION_DOES_NOT_EXIST}, status.HTTP_404_NOT_FOUND
            )

    @classmethod
    def delete(cls, request, pk):
        try:
            flock_vaccination = FlockVaccination.objects.get(public_id=pk)
            flock_vaccination.delete()
            return delete_response(FLOCK_VACCINATION_DELETE, status.HTTP_200_OK)
        except FlockVaccination.DoesNotExist:
            return error_response(
                {ERROR: FLOCK_VACCINATION_DOES_NOT_EXIST}, status.HTTP_404_NOT_FOUND
            )


class VaccinesView(viewsets.ViewSet):
    """
    Class for vaccines objects.
    """

    @classmethod
    def list(cls, request):
        vaccine = Vaccines.objects.all()
        return list_response(
            "Vaccines List",
            vaccine.count(),
            "vaccines_list",
            GetVaccinesSerializer(vaccine, many=True).data,
            status.HTTP_200_OK,
        )


class DailyDataDetailView(viewsets.ViewSet):
    """
    Class to give detail of daily data.
    """

    @classmethod
    def list(cls, request):
        try:
            daily_data = DailyData.objects.filter(
                flock__public_id=request.GET.get("flock_public_id")
            )
            result_data = []

            for entry in daily_data:
                flock = entry.flock
                enriched = prepare_daily_data_response(entry, flock)
                
                base_data = GetDailyDataListSerializer(entry).data
                
                base_data.update({
                    "bird_count": enriched["bird_count"],
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
                
                result_data.append(base_data)
            return list_response(
                "Daily Data List.",
                daily_data.count(),
                "daily_data_list",
                result_data,
                status.HTTP_200_OK,
            )
        except DailyData.DoesNotExist:
            return error_response(
                {ERROR: DAILY_DATA_DOES_NOT_EXIST}, status.HTTP_404_NOT_FOUND
            )


class DailyDataMortalityView(viewsets.ViewSet):
    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenMatchesOASRequirements]

    required_alternate_scopes = {
        "GET": [["read"]],
        "POST": [["create"]],
        "PATCH": [["update"]],
        "PUT": [["update"]],
        "DELETE": [["delete"]],
    }

    @classmethod
    def list(cls, request):
        serializer = DailyDataMortalitySerializer(data=request.GET)
        if serializer.is_valid(raise_exception=True):
            serializer_data = serializer.validated_data
            current_bird_count = serializer_data["current_bird_count"]
            actual_birds = serializer_data["actual_birds"]
            total_mortality_value = actual_birds - current_bird_count
            total_mortality_percentage = (total_mortality_value * 100) / actual_birds
            return get_detail(
                "Total Mortality",
                {
                    "total_mort_value": total_mortality_value,
                    "total_mort_percent": round(total_mortality_percentage, 2),
                },
                status.HTTP_200_OK,
            )


class DailyDataAverageFeedBirdsView(viewsets.ViewSet):
    """
    Class to create average feed/birds details of daily data.
    """

    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenMatchesOASRequirements]

    required_alternate_scopes = {
        "GET": [["read"]],
        "POST": [["create"]],
        "PATCH": [["update"]],
        "PUT": [["update"]],
        "DELETE": [["delete"]],
    }

    def list(cls, request):
        try:
            serializer = DailyDataAvgFeedSerializer(data=request.GET)
            if serializer.is_valid(raise_exception=True):
                serializer_data = serializer.validated_data
                feed_intake = serializer_data["feed_intake"]
                flock = Flock.objects.get(
                    public_id=serializer.validated_data["flock"].get("public_id")
                )
                date = serializer_data["date"]
                current_bird_count = serializer_data["current_bird_count"]
                yesterday = date - datetime.timedelta(days=1)
                if DailyData.objects.filter(date=yesterday, flock=flock).exists():
                    yesterday_daily_data = DailyData.objects.get(
                        date=yesterday, flock=flock
                    )
                    yesterday_avg_feed = yesterday_daily_data.average_feed
                else:
                    yesterday_avg_feed = 0
                average_feed = (feed_intake * 1000) / current_bird_count
                total_average_feed = yesterday_avg_feed + average_feed
                return get_detail(
                    "Average Feed Per Bird",
                    {
                        "avg_feed_per_bird": round(average_feed, 2),
                        "total_feed_per_bird": round(total_average_feed, 2),
                    },
                    status.HTTP_200_OK,
                )
        except Flock.DoesNotExist:
            return error_response(
                {ERROR: FLOCK_DOES_NOT_EXIST}, status.HTTP_404_NOT_FOUND
            )


class DailyDataFCRView(viewsets.ViewSet):
    """
    Class to create fcr details of daily data.
    """

    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenMatchesOASRequirements]

    required_alternate_scopes = {
        "GET": [["read"]],
        "POST": [["create"]],
        "PATCH": [["update"]],
        "PUT": [["update"]],
        "DELETE": [["delete"]],
    }

    @classmethod
    def list(cls, request):
        try:
            serializer = DailyDataFCRSerializer(data=request.GET)
            if serializer.is_valid(raise_exception=True):
                serializer_data = serializer.validated_data
                flock = Flock.objects.get(
                    public_id=serializer_data["flock"].get("public_id")
                )
                average_feed = serializer_data["average_feed"]
                date = serializer_data["date"]
                yesterday = date - datetime.timedelta(days=1)
                if DailyData.objects.filter(date=yesterday, flock=flock).exists():
                    yesterday_daily_data = DailyData.objects.get(
                        date=yesterday, flock=flock
                    )
                    avg_feed = yesterday_daily_data.total_average_feed
                else:
                    avg_feed = 0
                average_bird_weight = serializer_data["average_bird_weight"]
                total_average_feed = avg_feed + average_feed
                fcr = (
                    total_average_feed / (average_bird_weight - flock.chick_weight)
                    if (average_bird_weight - flock.chick_weight)
                    else 0
                )
                total_fcr = (
                    total_average_feed / average_bird_weight
                    if average_bird_weight
                    else 0
                )
                if fcr <= 0:
                    fcr = 0
                else:
                    fcr = fcr
                return get_detail(
                    "FCR",
                    {
                        "fcr": round(fcr, 2),
                        "total_fcr": round(total_fcr, 2),
                    },
                    status.HTTP_200_OK,
                )
        except Flock.DoesNotExist:
            return error_response(
                {ERROR: FLOCK_DOES_NOT_EXIST}, status.HTTP_404_NOT_FOUND
            )


class DailyDataLastDateView(viewsets.ViewSet):
    """
    Class to give last date of daily data.
    """

    def retrieve(self, request, pk):
        try:
            count = 0
            flock = Flock.objects.get(public_id=pk)
            daily_data = DailyData.objects.filter(flock=flock).latest("date")
            sales = Sales.objects.filter(flock=flock, date__gt=daily_data.date)
            for sale in sales:
                count += sale.lifting_count
            return get_detail(
                "Last date of daily data",
                {
                    "last_date": daily_data.date,
                    "current_bird_count": daily_data.current_bird_count - count

                },
                status.HTTP_200_OK,
            )
        except Flock.DoesNotExist:
            return error_response(
                {ERROR: FLOCK_DOES_NOT_EXIST}, status.HTTP_404_NOT_FOUND
            )
        except DailyData.DoesNotExist:
            return error_response(
                {ERROR: DAILY_DATA_DOES_NOT_EXIST}, status.HTTP_404_NOT_FOUND
            )


class DailyDataListView(viewsets.ViewSet):
    """
    List of all daily data of particular flock.
    """
    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenMatchesOASRequirements]

    required_alternate_scopes = {
        "GET": [["read"]],
        "POST": [["create"]],
        "PATCH": [["update"]],
        "PUT": [["update"]],
        "DELETE": [["delete"]],
    }

    @classmethod
    def list(cls, request):
        try:
            daily_data = DailyData.objects.filter(
            flock__public_id=request.GET.get("flock_public_id")
            )
            result_data = []

            for entry in daily_data:
                flock = entry.flock
                enriched = prepare_daily_data_response(entry, flock)
                
                # Get the original serialized data
                base_data = GetDailyDataListSerializer(entry).data
                
                # Update only the fields from enrichment that should overwrite/augment base
                base_data.update({
                    "bird_count": enriched["bird_count"],
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
                
                result_data.append(base_data)

            
            return list_response(
                "Daily Data List.",
                daily_data.count(),
                "daily_data_list",
                result_data,
                status.HTTP_200_OK,
            )
        except DailyData.DoesNotExist:
            return error_response(
                {ERROR: DAILY_DATA_DOES_NOT_EXIST}, status.HTTP_404_NOT_FOUND
            )


class DarknessTimeView(viewsets.ViewSet):
    """
    List of all darkness time.
    """

    @classmethod
    def list(cls, request):
        try:
            darkness_time = DarknessTime.objects.all()
            return list_response(
                "DarknessTime List",
                darkness_time.count(),
                "darkness_time_list",
                GetDarknessTimeListSerializer(darkness_time, many=True).data,
                status.HTTP_200_OK,
            )
        except DarknessTime.DoesNotExist:
            return error_response(
                {ERROR: DARKNESS_TIME_DOES_NOT_EXIST}, status.HTTP_404_NOT_FOUND
            )


class FeedAvailabilityView(viewsets.ViewSet):
    """
    List of all feed availability.
    """

    @classmethod
    def list(cls, request):
        try:
            feed_availability = FeedAvailability.objects.all()
            return list_response(
                "FeedAvailability List",
                feed_availability.count(),
                "feed_availability_list",
                GetFeedAvailabilityListSerializer(feed_availability, many=True).data,
                status.HTTP_200_OK,
            )
        except FeedAvailability.DoesNotExist:
            return error_response(
                {ERROR: FEED_AVAILABILITY_DOES_NOT_EXIST}, status.HTTP_404_NOT_FOUND
            )


class PDFView(viewsets.ViewSet):
    @classmethod
    def list(cls, request):
        template_name = "dailydata.html"
        daily_data = DailyData.objects.filter(
                flock__public_id=request.GET.get("flock_public_id")
            )
        
        result_data = []

        for entry in daily_data:
            flock = entry.flock
            enriched = prepare_daily_data_response(entry, flock)
                
            # Get the original serialized data
            base_data = GetDailyDataListSerializer(entry).data
                
            # Update only the fields from enrichment that should overwrite/augment base
            base_data.update({
                "bird_count": enriched["bird_count"],
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
                
            result_data.append(base_data)

        return render_to_pdf(
            template_name,
            {
                "record": result_data,
            },
        )