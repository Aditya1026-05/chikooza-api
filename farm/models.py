from django.db import models

# Create your models here.
from common.base_models import BaseModel, PublicId, Users


class Country(BaseModel):
    """
    Class is used to create db table of country.
    """

    name = models.CharField(max_length=30)
    code = models.CharField(max_length=255)
    isd_code = models.DecimalField(max_digits=6, decimal_places=0)

    def save(self, *args, **kwargs):
        self.public_id = PublicId.create_public_id()
        super(Country, self).save(*args, **kwargs)


class State(BaseModel):
    """
    Class is used to create db table of state.
    """

    name = models.CharField(max_length=30)
    code = models.CharField(max_length=255)
    country = models.ForeignKey(
        Country, on_delete=models.CASCADE, related_name="country_state"
    )

    def save(self, *args, **kwargs):
        self.public_id = PublicId.create_public_id()
        super(State, self).save(*args, **kwargs)


class Farm(BaseModel):
    """
    Class is used to create db table of farm.
    """

    user = models.ForeignKey(
        Users, on_delete=models.CASCADE, related_name="farm_users", null=True
    )
    name = models.CharField(max_length=30)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=255)
    district = models.CharField(max_length=255, blank=True, default="")
    state = models.ForeignKey(
        State, on_delete=models.CASCADE, related_name="farm_state"
    )
    country = models.ForeignKey(
        Country, on_delete=models.CASCADE, related_name="farm_country"
    )
    pin = models.CharField(max_length=20)
    lat_long = models.CharField(max_length=50)
    shed_count = models.IntegerField()
    status = models.BooleanField(default=1)

    class Meta:
        db_table = "farms"
