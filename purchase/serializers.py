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
    cost = serializers.IntegerField()
    remarks = serializers.CharField(max_length=255)

    def __init__(self, *args, **kwargs):
        super(AddPurchaseSerializer, self).__init__(*args, **kwargs)
        if kwargs.get("data").get("type") == "Feed":
            self.fields["company_name"] = serializers.CharField(
                max_length=255, allow_null=True
            )
            self.fields["item_name"] = serializers.CharField(
                max_length=255, allow_null=True
            )
            self.fields["unit"] = serializers.IntegerField(allow_null=True)
            self.fields["size"] = serializers.IntegerField(allow_null=True)
            self.fields["item_type"] = serializers.ChoiceField(
                choices=item_type_choice, allow_null=True
            )
        elif kwargs.get("data").get("type") in ["Medicine", "Vaccination", "Equipment"]:
            self.fields["quantity"] = serializers.IntegerField(allow_null=True)
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
    cost = serializers.IntegerField(required=False)
    quantity = serializers.IntegerField(required=False, allow_null=True)
    company_id = serializers.IntegerField(required=False, allow_null=True)
    company_name = serializers.CharField(
        max_length=255, required=False, allow_null=True
    )
    item_name = serializers.CharField(max_length=255, required=False, allow_null=True)
    item_type = serializers.ChoiceField(
        choices=item_type_choice, required=False, allow_null=True
    )
    unit = serializers.IntegerField(required=False, allow_null=True)
    size = serializers.IntegerField(required=False, allow_null=True)
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
