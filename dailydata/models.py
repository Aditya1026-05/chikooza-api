from django.db import models

from common.base_models import BaseModel, Users
from flocks.models import Flock

status_choices = (
    ("Start", "Start"),
    ("Continue", "Continue"),
    ("Complete", "Complete"),
)


class DarknessTime(BaseModel):
    """Available darkness-time option for daily flock records."""

    name = models.CharField(max_length=55)


class FeedAvailability(BaseModel):
    """Available feed-status option for daily flock records."""

    name = models.CharField(max_length=55)


class DailyData(BaseModel):
    """
    Create daily data objects in db.
    """

    date = models.DateField()
    flock = models.ForeignKey(
        Flock, on_delete=models.CASCADE, related_name="flock_daily_data"
    )
    user = models.ForeignKey(
        Users, on_delete=models.CASCADE, related_name="user_daily_data"
    )
    mortality = models.IntegerField()
    total_mort = models.FloatField()
    current_bird_count = models.IntegerField()
    feed_stock = models.IntegerField()
    feed_intake = models.IntegerField()
    total_feed = models.IntegerField()
    average_bird_weight = models.IntegerField()
    average_feed = models.FloatField()
    total_average_feed = models.FloatField(default=0)
    fcr = models.FloatField()
    total_fcr = models.FloatField(default=0)
    cooling = models.BooleanField()
    heating = models.BooleanField()
    seek = models.BooleanField()
    medicine = models.BooleanField()
    remarks = models.CharField(max_length=555)
    status = models.BooleanField(default=False)
    darkness_time = models.ForeignKey(
        DarknessTime, on_delete=models.CASCADE, related_name="darkness_time"
    )
    feed_availability = models.ForeignKey(
        FeedAvailability, on_delete=models.CASCADE, related_name="feed_availability"
    )
    flock_birds = models.IntegerField(null=True, default=0)


class Vaccines(BaseModel):
    """
    Class to create vaccines object.
    """

    name = models.CharField(max_length=255)
    full_name = models.CharField(max_length=255)
    description = models.CharField(max_length=555, null=True)
    company_id = models.CharField(max_length=255, null=True)
    status = models.BooleanField(default=1)


class FlockVaccination(BaseModel):
    """
    Class to create flocks vaccination.
    """

    dailydata = models.ForeignKey(
        DailyData, on_delete=models.CASCADE, related_name="dailydata_flock_vaccine"
    )
    flock = models.ForeignKey(
        Flock, on_delete=models.CASCADE, related_name="flock_flock_vaccine"
    )
    vaccine = models.ForeignKey(
        Vaccines, on_delete=models.CASCADE, related_name="vaccine_flock_vaccine"
    )
    status = models.CharField(max_length=255, choices=status_choices)

