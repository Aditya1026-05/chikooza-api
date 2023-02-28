import datetime

from django.db.models.functions import ExtractDay
from django.shortcuts import render
from oauth2_provider.contrib.rest_framework import OAuth2Authentication, TokenMatchesOASRequirements
from rest_framework import viewsets, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from common.constant import ERROR, FLOCK_DOES_NOT_EXIST, LIFTING_COUNT_NOT_VALID, SALES_DOES_NOT_EXIST, \
    DAILY_DATA_DOES_NOT_EXIST
from common.utils import get_detail, error_response, validate_url_value, list_response, success_response, daterange, \
    validation_return_response
from dailydata.models import DailyData
from flocks.models import Flock
from sales.models import Sales
from sales.serializers import AddSalesSerializer, GetSalesSerializer, GetSalesListSerializer, UpdateSalesSerializer
from sales.services import AddSalesService, UpdateSalesService


# Create your views here.
class SalesView(viewsets.ViewSet):
    """
    Class to perform crud operations for sales.
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
        Class to create sale object.
        """
        try:
            serializer = AddSalesSerializer(data=request.data)
            if serializer.is_valid(raise_exception=True):
                serializer_data = serializer.validated_data
                validate_url_value(serializer_data.get('flock')['public_id'], 'FLOCK_ID')
                flock = Flock.objects.get(public_id=serializer_data.get('flock')['public_id'])
                if DailyData.objects.filter(flock=flock).exists():
                    daily_data = DailyData.objects.filter(flock=flock).last()
                    data = daily_data.current_bird_count
                else:
                    data = flock.actual_birds
                if data < serializer_data.get('lifting_count'):
                    return error_response({ERROR: LIFTING_COUNT_NOT_VALID}, status.HTTP_404_NOT_FOUND
                                          )
                sales = AddSalesService.execute(
                    {"data": serializer_data, "flock": flock}
                )
            return get_detail(
                "Sales Created Successfully.",
                {"public_id": sales.public_id},
                status.HTTP_201_CREATED,
            )
        except Flock.DoesNotExist:
            return Response({ERROR: FLOCK_DOES_NOT_EXIST}, status.HTTP_404_NOT_FOUND)

    @classmethod
    def retrieve(cls, request, pk):
        try:
            sales = Sales.objects.get(public_id=pk)
            return get_detail(
                "Sales Detail",
                GetSalesSerializer(sales).data,
                status.HTTP_200_OK,
            )
        except Sales.DoesNotExist:
            return error_response(
                {ERROR: SALES_DOES_NOT_EXIST}, status.HTTP_404_NOT_FOUND
            )

    @classmethod
    def list(cls, request):
        try:
            serializer = GetSalesListSerializer(data=request.GET)
            if serializer.is_valid(raise_exception=True):
                serializer_data = serializer.validated_data
                sales = Sales.objects.filter(
                    flock__public_id=serializer_data.get('flock')['public_id']
                )
                return list_response(
                    "Sales List.",
                    sales.count(),
                    "sales_list",
                    GetSalesSerializer(sales, many=True).data,
                    status.HTTP_200_OK,
                )
        except Flock.DoesNotExist:
            return error_response(
                {ERROR: FLOCK_DOES_NOT_EXIST}, status.HTTP_404_NOT_FOUND
            )

    @classmethod
    def partial_update(cls, request, pk):
        try:
            sales = Sales.objects.get(public_id=pk)
            serializer = UpdateSalesSerializer(data=request.data)
            if serializer.is_valid(raise_exception=True):
                serializer_data = serializer.validated_data
                UpdateSalesService.execute(
                    {"data": serializer_data, "sales": sales}
                )
                return success_response(
                    "Sales update successfully",
                    "sales",
                    "Sales update successfully",
                    200,
                )
        except Sales.DoesNotExist:
            return Response(
                {ERROR: SALES_DOES_NOT_EXIST}, status.HTTP_404_NOT_FOUND
            )


class AgeView(viewsets.ViewSet):
    def retrieve(cls, request, pk):
        today_date = datetime.datetime.today().date()
        age = today_date - datetime.datetime.strptime(pk, "%Y-%m-%d").date()
        return get_detail(
            "Age Till Today.",
            age.days,
            status.HTTP_200_OK,
        )


class GraphView(viewsets.ViewSet):
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
            if pk == '1':
                flocks = Flock.objects.filter(user=request.user)
                for res in flocks:
                    if DailyData.objects.filter(flock=res).count() > 5:
                        flock = res
            else:
                flock = Flock.objects.get(public_id=pk)
            week_no = []
            mortality = []
            current_bird_count = []
            date = []
            fcr = []
            weight = []
            daily_datas = DailyData.objects.filter(flock=flock)

            if daily_datas.count() <=1:
                raise validation_return_response(ERROR, 'Please Enter more daily data to see the progress.')
            start_date = daily_datas.first().date
            end_date = daily_datas.last().date
            for dt in daterange(start_date, end_date):
                daily_data_weekly = DailyData.objects.get(flock=flock, date=dt)
                if daily_data_weekly.average_bird_weight == 0:
                    if DailyData.objects.filter(flock=flock, date__lte=dt).exclude(average_bird_weight=0).exists():
                        dd = DailyData.objects.filter(flock=flock, date__lte=dt).exclude(average_bird_weight=0).latest(
                            'updated_at')
                        weight.append(dd.average_bird_weight)
                    else:
                        weight.append(0)
                else:
                    weight.append(daily_data_weekly.average_bird_weight)
                fcr.append(daily_data_weekly.fcr)
                week_no.append(len(fcr))
            for daily_data in daily_datas:
                mortality.append(daily_data.mortality)
                current_bird_count.append(daily_data.current_bird_count)
                date.append((daily_data.date))

            return get_detail(
                "Graph Details",
                {'mortality': mortality,
                 'current_bird_count': current_bird_count,
                 'date': date,
                 'fcr': fcr,
                 'average_weight': weight,
                 'week': week_no},
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
