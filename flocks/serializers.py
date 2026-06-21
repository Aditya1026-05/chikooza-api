import datetime

from django.db.models import Sum
from rest_framework import serializers, status
from rest_framework.exceptions import ValidationError

from dailydata.models import DailyData
from flocks.models import Breed, Flock, Integrator, sys_choices
from purchase.models import Purchase
from sales.models import Sales

boolean_choice = [(True, True), (False, False)]


class BaseSerializer(serializers.Serializer):
    def is_valid(self, raise_exception=False):
        assert not hasattr(self, "restore_object"), (
            "Serializer `%s.%s` has old-style version 2 `.restore_object()` "
            "that is no longer compatible with REST framework 3. "
            "Use the new-style `.create()` and `.update()` methods instead."
            % (self.__class__.__module__, self.__class__.__name__)
        )

        assert hasattr(self, "initial_data"), (
            "Cannot call `.is_valid()` as no `data=` keyword argument was "
            "passed when instantiating the serializer instance."
        )

        if not hasattr(self, "_validated_data"):
            try:
                self._validated_data = self.run_validation(self.initial_data)
            except ValidationError as exc:
                self._validated_data = {}
                self._errors = exc.detail
            else:
                self._errors = {}

        if self._errors and raise_exception:
            "Invalid parameters."
            for key, value in self.errors.items():
                if key == "non_field_errors" and self.data["mobile_or_email"]:
                    key = "country_code"
                elif key == "non_field_errors" and not self.data["mobile_or_email"]:
                    key = self.data["type"]
                f"{str(key.replace('_', ' '))} {str(value[0])}"
                break
            raise ValidationError(
                {
                    "message": "Validation Error",
                    "result": self.errors,
                    "status": status.HTTP_400_BAD_REQUEST,
                }
            )
        return not bool(self._errors)


class AddFlockSerializer(BaseSerializer):
    """
    Class to validate data for creating flock object.
    """

    farm_public_id = serializers.IntegerField()
    flock_name = serializers.CharField(max_length=255)
    integration = serializers.BooleanField()
    hatch_date = serializers.DateField()
    flock_size = serializers.IntegerField()
    actual_birds = serializers.IntegerField()
    breed_public_id = serializers.IntegerField()
    hatchery_public_id = serializers.IntegerField(required=False)
    hatchery_name = serializers.CharField(max_length=555)
    chick_weight = serializers.IntegerField()
    hatchery_vaccine = serializers.IntegerField(required=False)
    feed_sys = serializers.ChoiceField(choices=sys_choices)
    drinking_sys = serializers.ChoiceField(choices=sys_choices)
    ec_shed = serializers.BooleanField()

    def __init__(self, *args, **kwargs):
        super(AddFlockSerializer, self).__init__(*args, **kwargs)
        if kwargs.get("data").get("integration"):
            self.fields["integrator_public_id"] = serializers.IntegerField(
                allow_null=True
            )
        else:
            self.fields["chick_cost"] = serializers.IntegerField(allow_null=True)


class BreedListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Breed
        fields = ["name", "public_id"]


class GetFlockSerializer(serializers.ModelSerializer):
    flock_name = serializers.CharField(max_length=255, source="name")
    flock_public_id = serializers.CharField(max_length=255, source="public_id")
    chick_breed = serializers.CharField(max_length=255, source="breed.name")
    integrator_name = serializers.CharField(
        max_length=255, source="integrator.name", allow_null=True
    )
    integrator_public_id = serializers.IntegerField(
        source="integrator.public_id", allow_null=True
    )
    chick_breed_public_id = serializers.IntegerField(
        source="breed.public_id", allow_null=True
    )
    hatchery_name = serializers.CharField(max_length=555)
    farm_public_id = serializers.IntegerField(source="farm.public_id")
    farm_name = serializers.CharField(source="farm.name", max_length=255)
    age = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    address = serializers.CharField(max_length=255, source="farm.address")
    mobile_number = serializers.IntegerField(source="user.mobile_number")

    class Meta:
        model = Flock
        fields = [
            "farm_public_id",
            "farm_name",
            "flock_public_id",
            "flock_name",
            "hatch_date",
            "flock_size",
            "actual_birds",
            "chick_breed",
            "chick_breed_public_id",
            "hatchery_name",
            "integration",
            "integrator_name",
            "integrator_public_id",
            "chick_weight",
            "ec_shed",
            "feed_sys",
            "chick_cost",
            "drinking_sys",
            "age",
            "status",
            "address",
            "mobile_number",
            "flock_bird",
        ]

    def get_age(self, obj):
        date = datetime.datetime.today().date()
        age = date - obj.hatch_date
        return age.days

    def get_status(self, obj):
        sales = Sales.objects.filter(flock=obj)
        if sales.filter(sales_type="final_lifting").exists():
            return "sold"
        if sales.exists() and obj.actual_birds <= 0:
            return "sold"
        return "current"


class IntegratorListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Integrator
        fields = ["public_id", "name", "nickname"]


class UpdateFlockSerializer(serializers.Serializer):
    flock_name = serializers.CharField(max_length=255, required=False)
    hatch_date = serializers.DateField(required=False)
    flock_size = serializers.IntegerField(required=False)
    actual_birds = serializers.IntegerField(required=False)
    breed_public_id = serializers.IntegerField(required=False)
    hatchery = serializers.CharField(max_length=255, required=False)
    hatchery_name = serializers.CharField(max_length=255, required=False)
    integration = serializers.BooleanField(required=False)
    integrator_public_id = serializers.IntegerField(required=False)
    chick_weight = serializers.IntegerField(required=False)
    ec_shed = serializers.BooleanField(required=False)
    feed_sys = serializers.ChoiceField(choices=sys_choices, required=False)
    drinking_sys = serializers.ChoiceField(choices=sys_choices, required=False)

    def __init__(self, *args, **kwargs):
        super(UpdateFlockSerializer, self).__init__(*args, **kwargs)
        if kwargs.get("data").get("integration") is True:
            self.fields["integrator_public_id"] = serializers.IntegerField(
                allow_null=True
            )
        else:
            self.fields["chick_cost"] = serializers.IntegerField(allow_null=True)


class GetDailyDataDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyData
        fields = ["public_id", "date"]


class FlockSummarySerializer(serializers.Serializer):
    flock_name = serializers.CharField(max_length=255, source="name")
    flock_public_id = serializers.CharField(max_length=255, source="public_id")
    chick_breed = serializers.CharField(max_length=255, source="breed.name")
    integrator_name = serializers.CharField(
        max_length=255, source="integrator.name", allow_null=True
    )
    integrator_public_id = serializers.IntegerField(
        source="integrator.public_id", allow_null=True
    )
    chick_breed_public_id = serializers.IntegerField(
        source="breed.public_id", allow_null=True
    )

    sales_data = serializers.SerializerMethodField()

    hatchery_name = serializers.CharField(max_length=555)
    farm_public_id = serializers.IntegerField(source="farm.public_id")
    farm_name = serializers.CharField(source="farm.name", max_length=255)
    age = serializers.SerializerMethodField()
    address = serializers.CharField(max_length=255, source="farm.address")
    mobile_number = serializers.IntegerField(source="user.mobile_number")
    mortality = serializers.SerializerMethodField()
    total_mort = serializers.SerializerMethodField()
    hatch_date = serializers.DateField()
    feed_intake = serializers.SerializerMethodField()
    average_feed = serializers.SerializerMethodField()
    average_bird_weight = serializers.SerializerMethodField()
    fcr = serializers.SerializerMethodField()
    feed_stock = serializers.SerializerMethodField()
    total_feed = serializers.SerializerMethodField()
    total_feed_cost = serializers.SerializerMethodField()
    feed_cost_per_kg = serializers.SerializerMethodField()
    flock_size = serializers.IntegerField(required=False)
    actual_birds = serializers.IntegerField(required=False)
    chick_cost = serializers.IntegerField()
    chick_cost_per_kg = serializers.SerializerMethodField()
    vaccine = serializers.SerializerMethodField()
    medicine = serializers.SerializerMethodField()
    labour = serializers.SerializerMethodField()
    equipment = serializers.SerializerMethodField()

    other = serializers.SerializerMethodField()
    total_cost = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    birds_count = serializers.SerializerMethodField()
    sales_amount = serializers.SerializerMethodField()
    sales_total_weight = serializers.SerializerMethodField()
    sales_average_weight = serializers.SerializerMethodField()
    sales_rate_per_kg = serializers.SerializerMethodField()
    profit_loss = serializers.SerializerMethodField()
    penalties = serializers.SerializerMethodField()
    incentives = serializers.SerializerMethodField()
    other_taxes = serializers.SerializerMethodField()
    current_bird_count = serializers.SerializerMethodField()
    has_daily_data = serializers.SerializerMethodField()
    daily_data_count = serializers.SerializerMethodField()
    purchase_count = serializers.SerializerMethodField()
    sales_count = serializers.SerializerMethodField()

    class Meta:
        model = Flock
        fields = [
            "farm_public_id", "farm_name", "flock_public_id", "flock_name",
            "hatch_date", "flock_size", "actual_birds", "chick_breed",
            "chick_breed_public_id", "hatchery_name", "integration",
            "integrator_name", "integrator_public_id", "chick_weight",
            "ec_shed", "feed_sys", "chick_cost", "drinking_sys", "age",
            "address", "mobile_number", "mortality", "total_mort",
            "feed_intake", "average_feed", "average_bird_weight", "fcr",
            "feed_stock", "total_feed", "total_feed_cost", "feed_cost_per_kg",
            "chick_cost_per_kg", "vaccine", "medicine", "total_cost",
            "sales_total_weight", "other", "status", "birds_count",
            "sales_amount", "sales_average_weight", "sales_rate_per_kg",
            "profit_loss",
            "labour", "equipment", "sales_data", "penalties", "incentives",
            "other_taxes", "current_bird_count", "has_daily_data",
            "daily_data_count", "purchase_count", "sales_count",
        ]

    def _latest_daily_data(self, obj):
        return DailyData.objects.filter(flock=obj).order_by("date").last()

    def _sum_purchase(self, obj, purchase_type, field="cost"):
        return (
            Purchase.objects.filter(flock=obj, type=purchase_type)
            .aggregate(total=Sum(field))
            .get("total")
            or 0
        )

    def _purchase_count(self, obj):
        return Purchase.objects.filter(flock=obj).count()

    def _sales_count(self, obj):
        return Sales.objects.filter(flock=obj).count()

    def get_age(self, obj):
        date = datetime.datetime.today().date()
        age = date - obj.hatch_date
        return age.days

    def get_total_feed(self, obj):
        return self._sum_purchase(obj, "Feed", "quantity")

    def get_medicine(self, obj):
        return self._sum_purchase(obj, "Medicine")

    def get_vaccine(self, obj):
        return self._sum_purchase(obj, "Vaccination")

    def get_current_bird_count(self, obj):
        daily_data = self._latest_daily_data(obj)
        if not daily_data:
            return obj.actual_birds

        lifting_count = 0
        if Sales.objects.filter(
            flock=daily_data.flock, date__gt=daily_data.date
        ).exists():
            sales = Sales.objects.filter(
                flock=daily_data.flock, date__gt=daily_data.date
            )
            for sale in sales:
                lifting_count += sale.lifting_count
            current_bird_count = daily_data.current_bird_count - lifting_count
        else:
            current_bird_count = daily_data.current_bird_count
        return current_bird_count

    def get_other(self, obj):
        return self._sum_purchase(obj, "Other")

    def get_labour(self, obj):
        return self._sum_purchase(obj, "Labour")

    def get_equipment(self, obj):
        return self._sum_purchase(obj, "Equipment")

    def get_total_cost(self, obj):
        vaccine_cost = self.get_vaccine(obj)
        other_cost = self.get_other(obj)
        med_cost = self.get_medicine(obj)
        equip_cost = self.get_equipment(obj)
        lab_cost = self.get_labour(obj)
        feed_cost = self.get_total_feed_cost(obj)

        if obj.chick_cost is not None:
            return (
                med_cost + other_cost + vaccine_cost + obj.chick_cost
                + equip_cost + lab_cost + feed_cost
            )
        return med_cost + other_cost + vaccine_cost + equip_cost + lab_cost + feed_cost

    def get_chick_cost_per_kg(self, obj):
        if obj.chick_cost:
            return obj.actual_birds / obj.chick_cost
        return 0

    def get_total_feed_cost(self, obj):
        return self._sum_purchase(obj, "Feed")

    def get_feed_cost_per_kg(self, obj):
        quantity = 0
        cost = 0
        purchases = Purchase.objects.filter(flock=obj, type="Feed")
        for purchase in purchases:
            quantity += purchase.quantity or 0
            cost += purchase.cost
        if quantity == 0:
            return 0
        return round(cost / quantity, 2)

    def get_mortality(self, obj):
        daily_data = self._latest_daily_data(obj)
        if not daily_data:
            return 0
        return obj.actual_birds - daily_data.current_bird_count

    def get_total_mort(self, obj):
        daily_data = self._latest_daily_data(obj)
        if not daily_data:
            return 0
        return daily_data.total_mort

    def get_feed_intake(self, obj):
        daily_data = self._latest_daily_data(obj)
        if not daily_data:
            return 0
        return daily_data.total_feed

    def get_average_feed(self, obj):
        daily_data = self._latest_daily_data(obj)
        if not daily_data:
            return 0
        return daily_data.total_average_feed

    def get_average_bird_weight(self, obj):
        daily_data = self._latest_daily_data(obj)
        if not daily_data:
            return 0
        date = daily_data.date
        yesterday = date - datetime.timedelta(days=1)
        average_bird_weight = daily_data.average_bird_weight
        if average_bird_weight == 0:
            yes = DailyData.objects.filter(flock=obj, date=yesterday).first()
            if not yes:
                return 0
            res = yes.average_bird_weight
            d_date = yes.date
        else:
            res = daily_data.average_bird_weight
            d_date = daily_data.date
        return f"{res} on {d_date}"

    def get_fcr(self, obj):
        daily_data = self._latest_daily_data(obj)
        if not daily_data:
            return 0
        return f"{daily_data.total_fcr} on {daily_data.date}"

    def get_feed_stock(self, obj):
        daily_data = self._latest_daily_data(obj)
        if not daily_data:
            return self.get_total_feed(obj)
        return daily_data.feed_stock

    def get_status(self, obj):
        if Sales.objects.filter(flock=obj, sales_type="final_lifting").exists():
            status = 'sold'
        else:
            status = 'current'
        return status

    def get_birds_count(self, obj):
        lifting_count = 0
        sales = Sales.objects.filter(flock=obj)
        for sale in sales:
            lifting_count += sale.lifting_count
        return lifting_count

    def get_sales_amount(self, obj):
        sales_amount = 0
        sales = Sales.objects.filter(flock=obj)
        for sale in sales:
            sales_amount += sale.cost
        return sales_amount

    def get_sales_total_weight(self, obj):
        sales_total_weight = 0
        sales = Sales.objects.filter(flock=obj)
        for sale in sales:
            sales_total_weight += sale.total_weight
        return sales_total_weight

    def get_sales_average_weight(self, obj):
        sales_total_weight = 0
        lifting_count = 0
        sales = Sales.objects.filter(flock=obj)
        for sale in sales:
            sales_total_weight += sale.total_weight
            lifting_count += sale.lifting_count
        if lifting_count == 0:
            return 0
        else:
            return round(sales_total_weight / lifting_count, 2)

    def get_sales_rate_per_kg(self, obj):
        sales_total_weight = 0
        sales_amount = 0
        sales = Sales.objects.filter(flock=obj)
        for sale in sales:
            sales_total_weight += sale.total_weight
            sales_amount += sale.cost
        if sales_total_weight != 0:
            return round(sales_amount / sales_total_weight, 2)
        else:
            return 0

    def get_incentives(self, obj):
        incentives = 0
        sales = Sales.objects.filter(flock=obj, sales_type="final_lifting")
        for sale in sales:
            incentives = (
                sale.rearing_charges + sale.performance_incentives
                + sale.rate_incentives + sale.eef_incentives
                + sale.sp_rate_incentives
            )
        return incentives

    def get_penalties(self, obj):
        penalties = 0
        sales = Sales.objects.filter(flock=obj, sales_type="final_lifting")
        for sale in sales:
            penalties = (
                sale.production_cost_recovery + sale.shortages
                + sale.excess_mortality + sale.fcr_recovery
            )
        return penalties

    def get_other_taxes(self, obj):
        other_taxes = 0
        sales = Sales.objects.filter(flock=obj, sales_type="final_lifting")
        for sale in sales:
            other_taxes = sale.less_amct + sale.less_tds + sale.other_taxes
        return other_taxes

    def get_profit_loss(self, obj):
        total_cost = self.get_total_cost(obj)
        sales_amount = self.get_sales_amount(obj)
        return sales_amount - total_cost

    def get_sales_data(self, obj):
        sales = Sales.objects.filter(flock=obj).order_by("date")
        return [
            {
                "public_id": sale.public_id,
                "date": sale.date,
                "lifting_count": sale.lifting_count,
                "total_weight": round(sale.total_weight, 2),
                "average_weight": round(sale.average_weight, 2),
                "rate_per_kg": round(sale.rate_per_kg, 2),
                "cost": sale.cost,
                "sales_type": sale.sales_type,
            }
            for sale in sales
        ]

    def get_has_daily_data(self, obj):
        return DailyData.objects.filter(flock=obj).exists()

    def get_daily_data_count(self, obj):
        return DailyData.objects.filter(flock=obj).count()

    def get_purchase_count(self, obj):
        return self._purchase_count(obj)

    def get_sales_count(self, obj):
        return self._sales_count(obj)
