from django.db import models

from common.base_models import BaseModel
from flocks.models import Flock

sales_type_choices = (('partial_lifting', 'partial_lifting'),
                      ('final_lifting', 'final_lifting'))


class Sales(BaseModel):
    """
    Class to create db table for sales.
    """
    flock = models.ForeignKey(Flock, on_delete=models.CASCADE, related_name='flock_sales')
    sales_type = models.CharField(max_length=255,
                                  choices=sales_type_choices)
    date = models.DateField()
    lifting_count = models.IntegerField()
    total_weight = models.FloatField()
    average_weight = models.FloatField()
    rate_per_kg = models.FloatField()
    cost = models.FloatField()
    buyer = models.CharField(max_length=255)
    vehicle_no = models.CharField(max_length=255)
    remarks = models.CharField(max_length=555)
    feed_total = models.FloatField(default=0.0)
    med_price = models.FloatField(default=0)
    vacc_price = models.FloatField(default=0)
    admin_charges = models.FloatField(default=0)
    rearing_charges = models.IntegerField(default=0)
    performance_incentives = models.IntegerField(default=0)
    rate_incentives = models.IntegerField(default=0)
    eef_incentives = models.IntegerField(default=0)
    sp_rate_incentives = models.IntegerField(default=0)
    production_cost_recovery = models.IntegerField(default=0)
    shortages = models.IntegerField(default=0)
    excess_mortality = models.IntegerField(default=0)
    fcr_recovery = models.IntegerField(default=0)
    less_tds = models.IntegerField(default=0)
    less_amct = models.IntegerField(default=0)
    other_taxes = models.IntegerField(default=0)
    integration_cost = models.FloatField(default=0)
    buyer_phone_no = models.IntegerField(null=True)
    buyer_address = models.CharField(max_length=255, null=True)
    buyer_email = models.EmailField(null=True)
