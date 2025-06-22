import datetime

from service_objects import services

from common.base_models import PublicId
from common.utils import validation_return_response
from dailydata.models import DailyData, FlockVaccination, Vaccines, DarknessTime, FeedAvailability
from flocks.models import Flock
from flocks.utils import generate_remarks  
from purchase.models import Purchase
from sales.models import Sales


class CreateDailyDataService(services.Service):
    """
    Class to write business logic for creating daily data object.
    """

    def process(self):
        data = self.data.get("data")
        user = self.data.get("user")
        flock_vaccinations = data.get("flock_vaccination")
        quantity = 0
        purchases = Purchase.objects.filter(
            flock__public_id=data.get("flock_public_id"),
            type="Feed",
            date__lte=data.get("date"),
        )
        for purchase in purchases:
            if purchase.quantity is None:
                purchase.quantity = 0
            else:
                purchase.quantity = purchase.quantity
            quantity = quantity + purchase.quantity
        flock = Flock.objects.get(public_id=data.get("flock_public_id"))
        yesterday = data.get("date") - datetime.timedelta(days=1)

        if DailyData.objects.filter(date=yesterday, flock=flock).exists():
            yesterday_daily_data = DailyData.objects.get(date=yesterday, flock=flock)
            if yesterday_daily_data:
                current_bird_count = yesterday_daily_data.current_bird_count
            else:
                current_bird_count = flock.actual_birds
                
            total_feed = yesterday_daily_data.total_feed + data.get("feed_intake")
            real_current_bird_count = current_bird_count - data.get("mortality")
            avg_feed = yesterday_daily_data.total_average_feed
            res_fcr = yesterday_daily_data.fcr
        else:
            current_bird_count = flock.actual_birds
            real_current_bird_count = current_bird_count - data.get("mortality")
            total_feed = data.get("feed_intake")

            avg_feed = 0
            res_fcr = 0
        feed_stock = quantity-total_feed
        if Sales.objects.filter(flock=flock).exists():
            sale = Sales.objects.filter(flock=flock).last()
            sales_date = sale.date
            if datetime.datetime.today().date() > sales_date:
                final_current_bird_count = current_bird_count - sale.lifting_count
                actual_bird_count = final_current_bird_count - data.get('mortality')
            else:
                actual_bird_count = real_current_bird_count
            actual_bird_count = actual_bird_count
        else:
            actual_bird_count = real_current_bird_count
        average_bird_weight = data.get("average_bird_weight")
        if real_current_bird_count == 0:
            average_feed = 0
        else:
            average_feed = (data.get("feed_intake") * 1000) / real_current_bird_count
        total_average_feed = avg_feed + average_feed
        # Calculate cumulative mortality: total dead birds / initial bird count
        total_dead_birds = flock.actual_birds - actual_bird_count
        total_mortality = (total_dead_birds * 100) / flock.actual_birds
        fcr = (
            total_average_feed / (average_bird_weight - flock.chick_weight)
            if (average_bird_weight - flock.chick_weight) > 0
            else res_fcr
        )
        total_fcr = (
            total_average_feed / average_bird_weight if average_bird_weight else 0
        )
        if fcr <= 0:
            fcr = 0
        else:
            fcr = fcr
        cooling = data.get("cooling") or False
        heating = data.get("heating") or False
        seek = data.get("seek") or False
        medicine = data.get("medicine") or False
        darkness_time = DarknessTime.objects.get(public_id=data.get('darkness_time_public_id')) if data.get(
            'darkness_time_public_id') else None
        feed_availability = FeedAvailability.objects.get(public_id=data.get('feed_availability_public_id')) if data.get(
            'feed_availability_public_id') else None
        if data.get("mortality") > current_bird_count:
            return validation_return_response("mortality", "Mortality cannot be greater than bird count")

        # Generate remarks using the consolidated function
        remarks = []

        daily_data = DailyData.objects.create(
            public_id=PublicId.create_public_id(),
            flock=flock,
            user=user,
            date=data.get("date"),
            mortality=data.get("mortality"),
            current_bird_count=actual_bird_count,
            total_mort=round(total_mortality, 2),
            feed_intake=data.get("feed_intake"),
            total_feed=total_feed,
            total_average_feed=round(total_average_feed, 2),
            feed_stock=feed_stock,
            average_feed=round(average_feed, 2),
            average_bird_weight=average_bird_weight,
            fcr=round(fcr, 2),
            total_fcr=round(total_fcr, 2),
            cooling=cooling,
            heating=heating,
            seek=seek,
            medicine=medicine,
            status=True,
            darkness_time=darkness_time,
            feed_availability=feed_availability,
            remarks=remarks,
        )
        
        # Create flock vaccinations separately - no vaccine names in remarks here
        if flock_vaccinations:
            for i in range(len(flock_vaccinations['vaccine_public_id'])):
                FlockVaccination.objects.create(
                    public_id=PublicId.create_public_id(),
                    dailydata=daily_data,
                    flock=flock,
                    vaccine=Vaccines.objects.get(
                        public_id=flock_vaccinations["vaccine_public_id"][i]
                    ),
                    status=flock_vaccinations["status"][i],
                )
        
        return daily_data


class UpdateDailyDataService(services.Service):
    """
    Class to write business logic for updating daily data object.
    """

    def process(self):
        data = self.data.get("data")
        daily_data = self.data.get("daily_data")
        flock_vaccinations = data.get("flock_vaccination")
        quantity = 0
        flock = daily_data.flock
        purchases = Purchase.objects.filter(
            flock=flock, type="Feed", date__lte=daily_data.date
        )
        for purchase in purchases:
            if purchase.quantity is None:
                purchase.quantity = 0
            else:
                purchase.quantity = purchase.quantity
            quantity = quantity + purchase.quantity
        yesterday = daily_data.date - datetime.timedelta(days=1)
        mortality = data.get("mortality") if data.get("mortality") else daily_data.mortality
        feed_intake = data.get("feed_intake") if data.get("feed_intake") else daily_data.feed_intake
        if DailyData.objects.filter(date=yesterday, flock=flock).exists():
            yesterday_daily_data = DailyData.objects.get(date=yesterday, flock=flock)
            current_bird_count = yesterday_daily_data.current_bird_count
            total_feed = yesterday_daily_data.total_feed + feed_intake
            feed_stock = yesterday_daily_data.feed_stock - feed_intake
            real_current_bird_count = current_bird_count - mortality
            average_feed = round(yesterday_daily_data.total_average_feed, 2)
        else:
            current_bird_count = flock.actual_birds
            real_current_bird_count = current_bird_count - mortality
            total_feed = feed_intake
            feed_stock = quantity - feed_intake
            average_feed = 0
        average_bird_weight = data.get("average_bird_weight") if data.get("average_bird_weight") else 0
        if real_current_bird_count == 0:
            avg_feed =0
        else:
            avg_feed = round((feed_intake * 1000) / real_current_bird_count, 2)
        total_average_feed = avg_feed + average_feed
        # Calculate cumulative mortality: total dead birds / initial bird count
        total_dead_birds = flock.actual_birds - real_current_bird_count
        total_mortality = (total_dead_birds * 100) / flock.actual_birds
        fcr = (
            total_average_feed / (average_bird_weight - flock.chick_weight)
            if (average_bird_weight - flock.chick_weight)
            else yesterday_daily_data.fcr
        )
        total_fcr = (
            total_average_feed / average_bird_weight if average_bird_weight else yesterday_daily_data.total_fcr
        )
        if fcr <= 0:
            fcr = 0
        else:
            fcr = fcr
        if data.get('darkness_time_public_id'):
            if data.get('darkness_time_public_id') == 0:
                darkness_time = None
            elif data.get('darkness_time_public_id') != 0:
                darkness_time = DarknessTime.objects.get(public_id=data.get('darkness_time_public_id'))
            else:
                darkness_time = daily_data.darkness_time
            darkness_time_final = darkness_time
        else:
            darkness_time_final= daily_data.darkness_time
        if data.get('feed_availability_public_id'):
            if data.get('feed_availability_public_id') == 0:
                feed_availability = None
            elif data.get('feed_availability_public_id') != 0:
                feed_availability = FeedAvailability.objects.get(public_id=data.get('feed_availability_public_id'))
            else:
                feed_availability = daily_data.feed_availability
            feed_availability_final = feed_availability
        else:
            feed_availability_final = daily_data.feed_availability
        cooling = data.get("cooling") or False
        heating = data.get("heating") or False
        seek = data.get("seek") or False

        medicine = data.get("medicine") or False
        if data.get("mortality") > current_bird_count:
            return validation_return_response("mortality", "Mortality cannot be greater than bird count")
        
        # Generate remarks using the consolidated function
        remarks = []
        
        daily_data.mortality = mortality
        daily_data.feed_intake = feed_intake
        daily_data.current_bird_count = real_current_bird_count
        daily_data.total_feed = total_feed
        daily_data.total_mort = round(total_mortality, 2)
        daily_data.average_feed = round(avg_feed, 2)
        daily_data.total_average_feed = round(total_average_feed, 2)
        daily_data.average_bird_weight = average_bird_weight
        daily_data.cooling = cooling
        daily_data.heating = heating
        daily_data.seek = seek
        daily_data.medicine = medicine
        daily_data.fcr = round(fcr, 2)
        daily_data.total_fcr = round(total_fcr, 2)
        daily_data.feed_stock = feed_stock
        daily_data.darkness_time = darkness_time_final
        daily_data.feed_availability = feed_availability_final
        daily_data.remarks = remarks
        
        # Handle flock vaccinations separately - no vaccine names in remarks here
        if flock_vaccinations:
            for i in range(len(flock_vaccinations['flock_vaccination_public_id'])):
                if flock_vaccinations['flock_vaccination_public_id'][i] == 0:
                    FlockVaccination.objects.create(
                        public_id=PublicId.create_public_id(),
                        dailydata=daily_data,
                        flock=flock,
                        vaccine=Vaccines.objects.get(
                            public_id=flock_vaccinations["vaccine_public_id"][i]
                        ),
                        status=flock_vaccinations["status"][i],
                    )
                else:
                    flock_vaccine = FlockVaccination.objects.get(
                        public_id=flock_vaccinations['flock_vaccination_public_id'][i])
                    vaccine = Vaccines.objects.get(public_id=flock_vaccinations['vaccine_public_id'][i])
                    flock_vaccine.vaccine = vaccine
                    flock_vaccine.status = flock_vaccinations['status'][i]
                    flock_vaccine.save()
        daily_data.save()
        dailydatas = DailyData.objects.filter(date__gt=daily_data.date, flock=flock)
        for dailydata in dailydatas:
            yes = dailydata.date - datetime.timedelta(days=1)
            yes_daily_data = DailyData.objects.get(date=yes, flock=flock)
            if data.get('mortality'):
                dailydata.current_bird_count = yes_daily_data.current_bird_count - dailydata.mortality
                # Calculate cumulative mortality: total dead birds / initial bird count
                total_dead_birds = flock.actual_birds - dailydata.current_bird_count
                dailydata.total_mort = round((total_dead_birds * 100) / flock.actual_birds, 2)
                dailydata.save()
            if data.get('feed_intake'):
                dailydata.feed_stock = yes_daily_data.feed_stock - dailydata.feed_intake
                dailydata.total_feed = yes_daily_data.total_feed + dailydata.feed_intake
                dailydata.average_feed = round((dailydata.feed_intake * 1000) / dailydata.current_bird_count, 2)
                dailydata.total_average_feed = round(yes_daily_data.total_average_feed + dailydata.average_feed, 2)
                dailydata.save()
            if data.get('average_bird_weight'):
                dailydata.fcr = dailydata.total_average_feed / (dailydata.average_bird_weight - flock.chick_weight) \
                    if (dailydata.average_bird_weight - flock.chick_weight) > 0 else yes_daily_data.fcr
                dailydata.total_fcr = round((
                    dailydata.total_average_feed / dailydata.average_bird_weight if dailydata.average_bird_weight else yes_daily_data.total_fcr
                ), 2)
                dailydata.save()


class CreateFlockVaccinationService(services.Service):
    """
    Class to write logic for creating flock vaccination object
    """

    def process(self):
        data = self.data.get("data")
        daily_data_public_id = data.get("dailydata").get("public_id")
        flock_public_id = data.get("flock").get("public_id")
        vaccine_public_id = data.get("vaccine").get("public_id")
        flock_vaccination = FlockVaccination.objects.create(
            public_id=PublicId.create_public_id(),
            dailydata=DailyData.objects.get(
                public_id=daily_data_public_id, flock__public_id=flock_public_id
            ),
            flock=Flock.objects.get(public_id=flock_public_id),
            vaccine=Vaccines.objects.get(public_id=vaccine_public_id),
            status=data.get("status"),
        )

        return flock_vaccination