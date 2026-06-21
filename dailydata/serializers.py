import datetime

from rest_framework import serializers

from dailydata.models import (
    DailyData,
    DarknessTime,
    FeedAvailability,
    FlockVaccination,
    Vaccines,
    status_choices,
)
from sales.models import Sales


class UpdateDailyDataSerializer(serializers.ModelSerializer):
    """
    Class to validate the request data to update object of daily data.
    """

    mortality = serializers.IntegerField(required=False)
    feed_intake = serializers.IntegerField(required=False)
    average_bird_weight = serializers.IntegerField(required=False)
    flock_public_id = serializers.IntegerField(required=False)
    cooling = serializers.BooleanField(default=False)
    heating = serializers.BooleanField(default=False)
    seek = serializers.BooleanField(default=False)
    medicine = serializers.BooleanField(default=False)
    remarks = serializers.CharField(max_length=555, required=False)
    flock_vaccination = serializers.JSONField(required=False)
    darkness_time_public_id = serializers.IntegerField(required=False)
    feed_availability_public_id = serializers.IntegerField(required=False)

    class Meta:
        model = DailyData
        fields = [
            "mortality",
            "feed_intake",
            "average_bird_weight",
            "flock_public_id",
            "cooling",
            "heating",
            "seek",
            "medicine",
            "remarks",
            "flock_vaccination",
            "darkness_time_public_id",
            "feed_availability_public_id",
        ]


class CreateDailyDataSerializer(serializers.ModelSerializer):
    """
    Class to validate the request data to create object of daily data.
    """

    date = serializers.DateField()
    mortality = serializers.IntegerField()
    feed_intake = serializers.IntegerField()
    average_bird_weight = serializers.IntegerField(default=0)
    flock_public_id = serializers.IntegerField()
    cooling = serializers.BooleanField(default=False)
    heating = serializers.BooleanField(default=False)
    seek = serializers.BooleanField(default=False)
    medicine = serializers.BooleanField(default=False)
    remarks = serializers.CharField(max_length=555, required=False)
    flock_vaccination = serializers.JSONField(required=False)
    darkness_time_public_id = serializers.IntegerField()
    feed_availability_public_id = serializers.IntegerField()

    class Meta:
        model = DailyData
        fields = [
            "date",
            "mortality",
            "feed_intake",
            "average_bird_weight",
            "flock_public_id",
            "cooling",
            "heating",
            "seek",
            "medicine",
            "remarks",
            "flock_vaccination",
            "darkness_time_public_id",
            "feed_availability_public_id",
        ]


class CreateFlockVaccinationSerializer(serializers.ModelSerializer):
    """
    Class to validate incoming data to create flock vaccine object.
    """

    daily_data_public_id = serializers.IntegerField(source="dailydata.public_id")
    flock_public_id = serializers.IntegerField(source="flock.public_id")
    vaccine_public_id = serializers.IntegerField(source="vaccine.public_id")
    status = serializers.ChoiceField(choices=status_choices)

    class Meta:
        model = FlockVaccination
        fields = [
            "daily_data_public_id",
            "flock_public_id",
            "vaccine_public_id",
            "status",
        ]


class GetFlockVaccinationSerializer(serializers.ModelSerializer):
    flock_public_id = serializers.IntegerField(source="flock.public_id")
    daily_data_public_id = serializers.IntegerField(source="dailydata.public_id")
    vaccine_public_id = serializers.IntegerField(source="vaccine.public_id")
    vaccine_name = serializers.CharField(max_length=255, source="vaccine.name")

    class Meta:
        model = FlockVaccination
        fields = [
            "public_id",
            "flock_public_id",
            "daily_data_public_id",
            "vaccine_public_id",
            "vaccine_name",
            "status",
        ]


class GetVaccinesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vaccines
        exclude = ["id", "created_at", "updated_at"]


class YesterdayDailyDataGetSerializer(serializers.ModelSerializer):
    flock_public_id = serializers.IntegerField(source="flock.public_id")
    flock_vaccination = serializers.SerializerMethodField()
    current_bird_count = serializers.SerializerMethodField()

    class Meta:
        model = DailyData
        fields = [
            "public_id",
            "date",
            "mortality",
            "total_mort",
            "feed_intake",
            "average_bird_weight",
            "flock_public_id",
            "cooling",
            "heating",
            "seek",
            "medicine",
            "remarks",
            "current_bird_count",
            "feed_stock",
            "total_feed",
            "average_feed",
            "fcr",
            "flock_vaccination",
            "total_fcr",
            "total_average_feed",
        ]

    def get_flock_vaccination(self, obj):
        flock_vaccine = FlockVaccination.objects.filter(dailydata=obj)
        return GetFlockVaccinationSerializer(flock_vaccine, many=True).data

    def get_current_bird_count(self, obj):
        lifting_count = 0
        if Sales.objects.filter(flock=obj.flock, date__gt=obj.date).exists():
            sales = Sales.objects.filter(flock=obj.flock, date__gt=obj.date)
            for sale in sales:
                lifting_count += sale.lifting_count
            current_bird_count = obj.current_bird_count - lifting_count
        else:
            current_bird_count = obj.current_bird_count
        return current_bird_count

class ListDailyDataSerializer(serializers.Serializer):
    flock_public_id = serializers.IntegerField(source="flock.public_id")
    date = serializers.DateField()

    class Meta:
        fields = ["date", "flock_public_id"]


class DailyDataGetSerializer(serializers.ModelSerializer):
    flock_public_id = serializers.IntegerField(source="flock.public_id")
    flock_vaccination = serializers.SerializerMethodField()
    flock_actual_birds = serializers.IntegerField(source="flock.actual_birds")
    darkness_time_public_id = serializers.IntegerField(
        source="darkness_time.public_id"
    )
    feed_availability_public_id = serializers.IntegerField(
        source="feed_availability.public_id"
    )

    class Meta:
        model = DailyData
        fields = [
            "public_id",
            "date",
            "mortality",
            "total_mort",
            "feed_intake",
            "average_bird_weight",
            "flock_actual_birds",
            "flock_public_id",
            "cooling",
            "heating",
            "seek",
            "medicine",
            "remarks",
            "current_bird_count",
            "feed_stock",
            "total_feed",
            "average_feed",
            "fcr",
            "flock_vaccination",
            "total_fcr",
            "total_average_feed",
            "darkness_time_public_id",
            "feed_availability_public_id",
        ]

    def get_flock_vaccination(self, obj):
        flock_vaccine = FlockVaccination.objects.filter(dailydata=obj)
        return GetFlockVaccinationSerializer(flock_vaccine, many=True).data

class DailyDataMortalitySerializer(serializers.Serializer):
    current_bird_count = serializers.IntegerField()
    actual_birds = serializers.IntegerField()

    class Meta:
        fields = ["current_bird_count", "actual_birds"]


class DailyDataAvgFeedSerializer(serializers.ModelSerializer):
    flock_public_id = serializers.IntegerField(source="flock.public_id")

    class Meta:
        model = DailyData
        fields = ["flock_public_id", "date", "current_bird_count", "feed_intake"]


class DailyDataFCRSerializer(serializers.ModelSerializer):
    flock_public_id = serializers.IntegerField(source="flock.public_id")

    class Meta:
        model = DailyData
        fields = ["flock_public_id", "average_feed", "date", "average_bird_weight"]


class GetDailyDataListSerializer(serializers.ModelSerializer):
    flock_public_id = serializers.IntegerField(source="flock.public_id")
    age = serializers.SerializerMethodField()
    class Meta:
        model = DailyData
        fields = ['date', 'public_id', 'flock_public_id', 'mortality', 'total_mort', 'current_bird_count', 'feed_stock',
                  'feed_intake', 'total_feed', 'average_bird_weight', 'average_feed', 'total_average_feed', 'fcr',
                  'total_fcr',
                  'cooling', 'heating', 'seek', 'medicine', 'remarks', 'status', 'age']

    def get_age(self, obj):
        today_date = datetime.datetime.today().date()
        age = today_date - obj.date
        return age.days


class GetDarknessTimeListSerializer(serializers.ModelSerializer):
    class Meta:
        model = DarknessTime
        fields = ['public_id', 'name']


class GetFeedAvailabilityListSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeedAvailability
        fields = ['public_id', 'name']
