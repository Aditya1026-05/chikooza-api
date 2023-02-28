from rest_framework import serializers

from farm.models import Country, Farm, State


class AddFarmSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=30)
    address = serializers.CharField(max_length=255)
    city = serializers.CharField(max_length=255)
    state_public_id = serializers.IntegerField()
    country_public_id = serializers.IntegerField()
    pin = serializers.CharField(max_length=20)
    lat_long = serializers.CharField(max_length=50, required=False, allow_null=True,
                                     allow_blank=True)
    shed_count = serializers.IntegerField()
    status = serializers.BooleanField(default=1)

    class Meta:
        model = Farm
        fields = [
            "name",
            "address",
            "city",
            "state_public_id",
            "country_public_id",
            "pin",
            "lat_long",
            "shed_count",
            "status",
        ]


class FarmGetSerializer(serializers.ModelSerializer):
    state_name = serializers.CharField(max_length=255, source="state.name")
    country_name = serializers.CharField(max_length=255, source="country.name")
    state_public_id = serializers.CharField(max_length=255, source="state.public_id")
    country_public_id = serializers.CharField(
        max_length=255, source="country.public_id"
    )

    class Meta:
        model = Farm
        fields = [
            "public_id",
            "name",
            "address",
            "city",
            "state_name",
            "country_name",
            "pin",
            "lat_long",
            "shed_count",
            "status",
            "state_public_id",
            "country_public_id",
        ]


class FarmListSerializer(serializers.ModelSerializer):
    state_name = serializers.CharField(max_length=255, source="state.name")
    country_name = serializers.CharField(max_length=255, source="country.name")
    state_public_id = serializers.CharField(max_length=255, source="state.public_id")
    country_public_id = serializers.CharField(
        max_length=255, source="country.public_id"
    )

    class Meta:
        model = Farm
        fields = [
            "id",
            "public_id",
            "name",
            "address",
            "city",
            "state_name",
            "country_name",
            "pin",
            "lat_long",
            "shed_count",
            "status",
            "state_public_id",
            "country_public_id",
        ]


class UpdateFarmSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=30, required=False)
    address = serializers.CharField(max_length=255, required=False)
    city = serializers.CharField(max_length=255, required=False)
    pin = serializers.CharField(max_length=20, required=False)
    lat_long = serializers.CharField(max_length=50, required=False, allow_blank=True,
                                     allow_null=True)
    shed_count = serializers.IntegerField(required=False)
    state_public_id = serializers.CharField(max_length=255, required=False)
    country_public_id = serializers.CharField(max_length=255, required=False)

    class Meta:
        fields = [
            "name",
            "address",
            "city",
            "state_public_id",
            "country_public_id",
            "pin",
            "lat_long",
            "shed_count",
            "status",
        ]


class GetStateSerializer(serializers.ModelSerializer):
    class Meta:
        model = State
        fields = ["public_id", "name"]


class GetCountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ["public_id", "name"]
