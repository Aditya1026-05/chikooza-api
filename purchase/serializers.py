from rest_framework import serializers

from dailydata.models import DailyData
from purchase.models import Purchase, feed_type_choice

item_type_choice = ((100, "Pre Starter"), (101, "Starter"), (102, "Finisher"))


class AddPurchaseSerializer(serializers.Serializer):
    """
    Class to validate the data for purchase.
    """

    flock_public_id = serializers.IntegerField()
    type = serializers.ChoiceField(choices=feed_type_choice)
    date = serializers.DateField()
    cost = serializers.IntegerField(min_value=1)
    remarks = serializers.CharField(max_length=255)

    def __init__(self, *args, **kwargs):
        super(AddPurchaseSerializer, self).__init__(*args, **kwargs)
        initial_data = kwargs.get("data") or {}
        if initial_data.get("type") == "Feed":
            self.fields["company_name"] = serializers.CharField(
                max_length=255, allow_null=True
            )
            self.fields["item_name"] = serializers.CharField(
                max_length=255, allow_null=True
            )
            # Feed stock can increase only from positive bag count and bag size.
            self.fields["unit"] = serializers.IntegerField(min_value=1)
            self.fields["size"] = serializers.IntegerField(min_value=1)
            self.fields["item_type"] = serializers.ChoiceField(
                choices=item_type_choice, allow_null=True
            )
        elif initial_data.get("type") in ["Medicine", "Vaccination", "Equipment"]:
            self.fields["quantity"] = serializers.IntegerField(min_value=1)
            self.fields["company_name"] = serializers.CharField(
                max_length=255, allow_null=True
            )
            self.fields["item_name"] = serializers.CharField(
                max_length=255, allow_null=True
            )


class GetPurchaseSerializer(serializers.ModelSerializer):
    """
    Class to return the detail of purchase object.
    """

    flock_public_id = serializers.IntegerField(source="flock.public_id")

    class Meta:
        model = Purchase
        fields = [
            "public_id",
            "flock_public_id",
            "type",
            "date",
            "cost",
            "quantity",
            "company_id",
            "company_name",
            "item_name",
            "item_type",
            "unit",
            "size",
            "remarks",
        ]


class UpdatePurchaseSerializer(serializers.ModelSerializer):
    """
    Class to validate request date to update purchase object.
    """

    date = serializers.DateField(required=False)
    cost = serializers.IntegerField(required=False, min_value=1)
    quantity = serializers.IntegerField(required=False, min_value=1)
    company_id = serializers.IntegerField(required=False, allow_null=True)
    company_name = serializers.CharField(
        max_length=255, required=False, allow_null=True
    )
    item_name = serializers.CharField(max_length=255, required=False, allow_null=True)
    item_type = serializers.ChoiceField(
        choices=item_type_choice, required=False, allow_null=True
    )
    unit = serializers.IntegerField(required=False, min_value=1)
    size = serializers.IntegerField(required=False, min_value=1)
    remarks = serializers.CharField(max_length=255, required=False, allow_null=True)

    class Meta:
        model = Purchase
        fields = [
            "date",
            "cost",
            "quantity",
            "company_id",
            "company_name",
            "item_name",
            "item_type",
            "unit",
            "size",
            "remarks",
        ]


class QuantitySerializer(serializers.ModelSerializer):
    flock_public_id = serializers.IntegerField(source="flock.public_id")

    class Meta:
        model = DailyData
        fields = ["date", "flock_public_id"]
