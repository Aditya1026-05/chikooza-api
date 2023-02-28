from django.db import models

# Create your models here.
from common.base_models import BaseModel, Users
from flocks.models import Flock

feed_type_choice = [
    ("Feed", "Feed"),
    ("Medicine", "Medicine"),
    ("Vaccination", "Vaccination"),
    ("Equipment", "Equipment"),
    ("Labour", "Labour"),
    ("Other", "Other"),
]

item_type_choice = [(100, "Pre Starter"), (101, "Starter"), (102, "Finisher")]
adjust_type_choice = [("A", "addition"), ("R", "reduction"), ("O", "original")]


class Purchase(BaseModel):
    """
    Class to create db table of purchase.
    """

    flock = models.ForeignKey(
        Flock, on_delete=models.CASCADE, related_name="flock_purchase"
    )
    user = models.ForeignKey(
        Users, on_delete=models.CASCADE, related_name="purchase_user"
    )
    type = models.CharField(choices=feed_type_choice, max_length=255, null=True)
    date = models.DateField()
    cost = models.IntegerField()
    quantity = models.IntegerField(null=True)
    company_id = models.IntegerField(null=True)
    company_name = models.CharField(max_length=255)
    item_name = models.CharField(max_length=255)
    item_type = models.CharField(choices=item_type_choice, max_length=100, null=True)
    unit = models.IntegerField(null=True)
    size = models.IntegerField(null=True)
    remarks = models.TextField()
    adjust = models.IntegerField(default=1)
    adjust_type = models.CharField(max_length=30, choices=adjust_type_choice)
