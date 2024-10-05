from django.db import models

# Create your models here.
from common.base_models import BaseModel, Users, PublicId
from farm.models import Country, Farm, State


class Hatchery(BaseModel):
    """
    Class to create hatchery object.
    """

    name = models.CharField(max_length=255)
    nickname = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    pin = models.CharField(max_length=20)
    state = models.ForeignKey(
        State, on_delete=models.CASCADE, related_name="hatchery_state"
    )
    country = models.ForeignKey(
        Country, on_delete=models.CASCADE, related_name="hatchery_country"
    )
    email = models.EmailField()
    phone = models.CharField(max_length=255)
    phone2 = models.CharField(max_length=255)
    contact = models.CharField(max_length=255)


class Breed(BaseModel):
    """
    Class to create breed object.
    """

    code = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    line = models.CharField(max_length=255)

    def save(self, *args, **kwargs):
        self.public_id = PublicId.create_public_id()
        super(Breed, self).save(*args, **kwargs)


class Integrator(BaseModel):
    """
    Class to create integrator object.
    """

    name = models.CharField(max_length=255)
    nickname = models.CharField(max_length=255)
    address = models.CharField(max_length=255, null=True)
    city = models.CharField(max_length=100, null=True)
    pin = models.CharField(max_length=20, null=True)
    state = models.ForeignKey(
        State, on_delete=models.CASCADE, related_name="integrator_state", null=True
    )
    country = models.ForeignKey(
        Country, on_delete=models.CASCADE, related_name="integrator_country", null=True
    )
    email = models.EmailField(null=True)
    phone = models.CharField(max_length=255, null=True)
    phone2 = models.CharField(max_length=255, null=True)
    contact = models.CharField(max_length=255, null=True)

    def save(self, *args, **kwargs):
        self.public_id = PublicId.create_public_id()
        super(Integrator, self).save(*args, **kwargs)


sys_choices = [("M", "M"), ("A", "A"), ("B", "B")]


class Flock(BaseModel):
    """
    Class to create flock object.
    """

    user = models.ForeignKey(
        Users, on_delete=models.CASCADE, related_name="flock_users"
    )
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name="farm_flock")
    name = models.CharField(max_length=255)
    integration = models.BooleanField()
    integrator = models.ForeignKey(
        Integrator, on_delete=models.CASCADE, related_name="flock_integrator", null=True
    )
    hatch_date = models.DateField()
    flock_size = models.IntegerField()
    actual_birds = models.IntegerField()
    breed = models.ForeignKey(
        Breed, on_delete=models.CASCADE, related_name="flock_breed"
    )
    hatchery = models.ForeignKey(
        Hatchery, on_delete=models.CASCADE, related_name="flock_hatchery", null=True
    )
    hatchery_name = models.CharField(max_length=555, null=True)
    chick_weight = models.IntegerField()
    hatchery_vaccine = models.IntegerField()
    feed_sys = models.CharField(choices=sys_choices, max_length=255)
    drinking_sys = models.CharField(choices=sys_choices, max_length=255)
    ec_shed = models.BooleanField()
    chick_cost = models.IntegerField(null=True)
    status = models.BooleanField(default=1)
    flock_bird = models.IntegerField()

    def __str__(self):
        return self.name
