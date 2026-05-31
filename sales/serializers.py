from rest_framework import serializers

from dailydata.models import DailyData
from sales.models import Sales, sales_type_choices


class AddSalesSerializer(serializers.ModelSerializer):
    """
    Class to validate incoming data to create sales object.
    """
    flock_public_id = serializers.IntegerField(source='flock.public_id')
    sales_type = serializers.ChoiceField(choices=sales_type_choices)
    date = serializers.DateField()
    lifting_count = serializers.IntegerField()
    total_weight = serializers.FloatField()
    rate_per_kg = serializers.FloatField()
    buyer = serializers.CharField(max_length=255, required=False, default='')
    vehicle_no = serializers.CharField(max_length=255, required=False, default='')
    remarks = serializers.CharField(max_length=555, required=False, default='')
    buyer_phone_no = serializers.IntegerField(required=False, default='')
    buyer_address = serializers.CharField(max_length=255, required=False, default='')
    buyer_email = serializers.EmailField(required=False, default='')

    def __init__(self, *args, **kwargs):
        super(AddSalesSerializer, self).__init__(*args, **kwargs)
        if kwargs.get("data").get("sales_type") == "final_lifting":
            self.fields["other_taxes"] = serializers.IntegerField(allow_null=True)
            self.fields["feed_total"] = serializers.FloatField(allow_null=True)
            self.fields["med_price"] = serializers.IntegerField(allow_null=True)
            self.fields["vacc_price"] = serializers.IntegerField(allow_null=True)
            self.fields["admin_charges"] = serializers.FloatField(allow_null=True)
            self.fields["rearing_charges"] = serializers.IntegerField(allow_null=True)
            self.fields["performance_incentives"] = serializers.IntegerField(allow_null=True)
            self.fields["rate_incentives"] = serializers.IntegerField(allow_null=True)
            self.fields["eef_incentives"] = serializers.IntegerField(allow_null=True)
            self.fields["sp_rate_incentives"] = serializers.IntegerField(allow_null=True)
            self.fields["production_cost_recovery"] = serializers.IntegerField(allow_null=True)
            self.fields["shortages"] = serializers.IntegerField(allow_null=True)
            self.fields["excess_mortality"] = serializers.IntegerField(allow_null=True)
            self.fields["fcr_recovery"] = serializers.IntegerField(allow_null=True)
            self.fields["less_tds"] = serializers.IntegerField(allow_null=True)
            self.fields["less_amct"] = serializers.IntegerField(allow_null=True)

    class Meta:
        model = Sales
        fields = ['flock_public_id', 'sales_type', 'date', 'lifting_count', 'total_weight',
                  'rate_per_kg', 'buyer', 'vehicle_no', 'remarks',
                  'feed_total', 'vacc_price', 'rearing_charges', 'performance_incentives', 'rate_incentives',
                  'eef_incentives', 'sp_rate_incentives',
                  'production_cost_recovery', 'shortages', 'excess_mortality', 'fcr_recovery', 'less_tds', 'less_amct',
                  'other_taxes', 'med_price', 'admin_charges', 'buyer_phone_no'
            , 'buyer_address', 'buyer_email']


class GetSalesSerializer(serializers.ModelSerializer):
    flock_public_id = serializers.IntegerField(source='flock.public_id')
    flock_name = serializers.CharField(max_length=255, source='flock.name')
    current_bird_count = serializers.SerializerMethodField()
    age = serializers.SerializerMethodField()

    class Meta:
        model = Sales
        fields = ['public_id', 'flock_public_id', 'flock_name','sales_type', 'date', 'lifting_count', 'total_weight',
                  'average_weight',
                  'rate_per_kg', 'cost', 'buyer', 'vehicle_no', 'remarks', 'admin_charges',
                  'feed_total', 'med_price', 'vacc_price', 'rearing_charges',
                  'performance_incentives', 'rate_incentives', 'eef_incentives', 'sp_rate_incentives',
                  'production_cost_recovery', 'shortages', 'excess_mortality', 'fcr_recovery', 'less_tds', 'less_amct',
                  'other_taxes', 'integration_cost', 'buyer_address', 'buyer_phone_no', 'buyer_email','current_bird_count', 'age']

    def get_current_bird_count(self, obj):
        cbc = 0
        latest_daily_data = DailyData.objects.filter(flock=obj.flock).order_by("date").last()
        count = latest_daily_data.current_bird_count if latest_daily_data else obj.flock.actual_birds
        sales = Sales.objects.filter(flock=obj.flock)
        for sale in sales:
            cbc += sale.lifting_count
        return count - cbc

    def get_age(self, obj):
        sale_date = obj.date
        hatch_date = obj.flock.hatch_date
        days = sale_date - hatch_date
        return days.days


class GetSalesListSerializer(serializers.ModelSerializer):
    flock_public_id = serializers.IntegerField(source='flock.public_id')

    class Meta:
        model = Sales
        fields = ['flock_public_id']


class UpdateSalesSerializer(serializers.ModelSerializer):
    date = serializers.DateField(required=False, allow_null=True)
    lifting_count = serializers.IntegerField(required=False, allow_null=True)
    total_weight = serializers.FloatField(required=False, allow_null=True)
    rate_per_kg = serializers.FloatField(required=False, allow_null=True)
    buyer = serializers.CharField(max_length=255, required=False, allow_null=True)
    vehicle_no = serializers.CharField(max_length=255, required=False, allow_null=True)
    remarks = serializers.CharField(max_length=555, required=False, allow_null=True)
    buyer_phone_no = serializers.IntegerField(required=False, allow_null=True )
    buyer_address = serializers.CharField(max_length=255, required=False)
    buyer_email = serializers.EmailField(required=False, allow_null=True)
    other_taxes= serializers.IntegerField(allow_null=True, required=False)
    feed_total= serializers.FloatField(allow_null=True, required=False)
    med_price= serializers.IntegerField(allow_null=True, required=False)
    vacc_price= serializers.IntegerField(allow_null=True, required=False)
    admin_charges = serializers.FloatField(allow_null=True, required=False)
    rearing_charges= serializers.IntegerField(allow_null=True, required=False)
    performance_incentives = serializers.IntegerField(allow_null=True, required=False)
    rate_incentives= serializers.IntegerField(allow_null=True, required=False)
    eef_incentives= serializers.IntegerField(allow_null=True, required=False)
    sp_rate_incentives= serializers.IntegerField(allow_null=True, required=False)
    production_cost_recovery=serializers.IntegerField(allow_null=True, required=False)
    shortages=serializers.IntegerField(allow_null=True, required=False)
    excess_mortality=serializers.IntegerField(allow_null=True, required=False)
    fcr_recovery = serializers.IntegerField(allow_null=True, required=False)
    less_tds = serializers.IntegerField(allow_null=True, required=False)
    less_amct= serializers.IntegerField(allow_null=True, required=False)

    class Meta:
        model = Sales
        fields = ['date', 'lifting_count', 'total_weight',
                  'rate_per_kg', 'buyer', 'vehicle_no', 'remarks',
                  'feed_total', 'med_price', 'vacc_price', 'rearing_charges', 'admin_charges',
                  'performance_incentives', 'rate_incentives', 'eef_incentives', 'sp_rate_incentives',
                  'production_cost_recovery', 'shortages', 'excess_mortality', 'fcr_recovery', 'less_tds', 'less_amct',
                  'other_taxes', 'buyer_phone_no', 'buyer_address', 'buyer_email']
