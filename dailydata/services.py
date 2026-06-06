import datetime

from service_objects import services

from common.base_models import PublicId
from common.utils import validation_return_response
from dailydata.feed_stock import (
    available_feed_stock_for_date,
    recalculate_feed_snapshots,
    total_feed_consumed_before_date,
)
from dailydata.models import DailyData, FlockVaccination, Vaccines, DarknessTime, FeedAvailability
from flocks.models import Flock

#MV-23-6-25- 17-10 import flocks/utils.py/generate_remarks
from flocks.utils import generate_remarks  
#MV-23-6-25- 17-10 change end

from sales.models import Sales


FEED_STOCK_VALIDATION_MESSAGE = (
    "Feed intake is greater than available feed stock. Add a feed purchase for this "
    "flock first, or reduce the feed intake."
)


class CreateDailyDataService(services.Service):
    """
    Class to write business logic for creating daily data object.
    """

    def process(self):
        data = self.data.get("data")
        user = self.data.get("user")
        flock = self.data.get("flock")
        flock_vaccinations = data.get("flock_vaccination")
        if flock is None:
            # U: OLD: Flock.objects.get(public_id=...) allowed daily data under another farmer's flock.
            # U: NEW: resolve the flock through the authenticated farmer.
            flock = Flock.objects.get(public_id=data.get("flock_public_id"), user=user)

        # U: OLD: feed stock was calculated inline from purchases and could drift
        # U: when purchase records were edited after daily data already existed.
        # U: NEW: use the shared stock calculator, scoped to the authenticated farmer.
        available_feed_stock = available_feed_stock_for_date(
            flock, user, data.get("date")
        )
        if data.get("feed_intake") > available_feed_stock:
            validation_return_response("feed_intake", FEED_STOCK_VALIDATION_MESSAGE)

        yesterday = data.get("date") - datetime.timedelta(days=1)

        if DailyData.objects.filter(date=yesterday, flock=flock).exists():
            yesterday_daily_data = DailyData.objects.get(date=yesterday, flock=flock)
            if yesterday_daily_data:
                current_bird_count = yesterday_daily_data.current_bird_count
            else:
                current_bird_count = flock.actual_birds
                
            total_feed = total_feed_consumed_before_date(
                flock, user, data.get("date")
            ) + data.get("feed_intake")
            real_current_bird_count = current_bird_count - data.get("mortality")
            avg_feed = yesterday_daily_data.total_average_feed
            res_fcr = yesterday_daily_data.fcr
        else:
            current_bird_count = flock.actual_birds
            real_current_bird_count = current_bird_count - data.get("mortality")
            total_feed = total_feed_consumed_before_date(
                flock, user, data.get("date")
            ) + data.get("feed_intake")

            avg_feed = 0
            res_fcr = 0
        #feed_stock = quantity - data.get("feed_intake")
#MV-23-6-25- 17-10 changed feed stock calcuation formula
        # U: OLD: feed_stock = quantity - total_feed was duplicated here.
        # U: NEW: consume from available feed stock for the selected day.
        feed_stock = available_feed_stock - data.get("feed_intake")
#MV-23-6-25- 17-10 change end

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

        # sales_date = Sales.objects.filter(flock=flock).dateAdd commentMore actions
            # if datetime.datetime.today() > sales_date:
            #     final_current_bird_count = flock.actual_birds - data.get("mortality")
            # else:
            #     final_current_bird_count = real_current_bird_count
            # final_current_bird_count = final_current_bird_count
        
#MV-23-6-25- 17-10 empty remarks
        remarks = []
#MV-23-6-25- 17-10 change ended


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
            
#MV-23-6-25- 17-10 added remarks
            remarks=remarks,
#MV-23-6-25- 17-10 change end

        )
        
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
        
        recalculate_feed_snapshots(flock, user)

        return daily_data


class UpdateDailyDataService(services.Service):
    """
    Class to write business logic for updating daily data object.
    """

    def process(self):
        data = self.data.get("data")
        daily_data = self.data.get("daily_data")
        flock_vaccinations = data.get("flock_vaccination")
        flock = daily_data.flock
        yesterday = daily_data.date - datetime.timedelta(days=1)
        mortality = data.get("mortality") if "mortality" in data else daily_data.mortality
        feed_intake = data.get("feed_intake") if "feed_intake" in data else daily_data.feed_intake
        available_feed_stock = available_feed_stock_for_date(
            flock, daily_data.user, daily_data.date
        )
        if feed_intake > available_feed_stock:
            validation_return_response("feed_intake", FEED_STOCK_VALIDATION_MESSAGE)

        if DailyData.objects.filter(date=yesterday, flock=flock).exists():
            yesterday_daily_data = DailyData.objects.get(date=yesterday, flock=flock)
            current_bird_count = yesterday_daily_data.current_bird_count
            total_feed = total_feed_consumed_before_date(
                flock, daily_data.user, daily_data.date
            ) + feed_intake
            feed_stock = available_feed_stock - feed_intake
            real_current_bird_count = current_bird_count - mortality
            average_feed = round(yesterday_daily_data.total_average_feed, 2)
            fallback_fcr = yesterday_daily_data.fcr
            fallback_total_fcr = yesterday_daily_data.total_fcr
        else:
            current_bird_count = flock.actual_birds
            real_current_bird_count = current_bird_count - mortality
            total_feed = total_feed_consumed_before_date(
                flock, daily_data.user, daily_data.date
            ) + feed_intake
            feed_stock = available_feed_stock - feed_intake
            average_feed = 0
            fallback_fcr = daily_data.fcr
            fallback_total_fcr = daily_data.total_fcr
        average_bird_weight = data.get("average_bird_weight") if "average_bird_weight" in data else daily_data.average_bird_weight
        if real_current_bird_count == 0:
            avg_feed =0
        else:
            avg_feed = round((feed_intake * 1000) / real_current_bird_count, 2)
        total_average_feed = avg_feed + average_feed
        
        total_dead_birds = flock.actual_birds - real_current_bird_count
        total_mortality = (total_dead_birds * 100) / flock.actual_birds

        
        fcr = (
            total_average_feed / (average_bird_weight - flock.chick_weight)
            if (average_bird_weight - flock.chick_weight) > 0
            else fallback_fcr
        )
        total_fcr = (
            total_average_feed / average_bird_weight if average_bird_weight else fallback_total_fcr
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
        if mortality > current_bird_count:
            return validation_return_response("mortality", "Mortality cannot be greater than bird count")
        
#MV-23-6-25- 17-10 empty remarks
        remarks = []
#MV-23-6-25- 17-10 change end

        
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
        
#MV-23-6-25- 17-10 added remarks
        daily_data.remarks = remarks
#MV-23-6-25- 17-10 change end

        
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
                    # U: OLD: FlockVaccination.objects.get(public_id=...) allowed editing another farmer's vaccination row.
                    # U: NEW: limit updates to vaccinations attached to the current daily data and flock.
                    flock_vaccine = FlockVaccination.objects.get(
                        public_id=flock_vaccinations['flock_vaccination_public_id'][i],
                        dailydata=daily_data,
                        flock=flock,
                    )
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
                
                total_dead_birds = flock.actual_birds - dailydata.current_bird_count
                dailydata.total_mort = round((total_dead_birds * 100) / flock.actual_birds, 2)

                dailydata.save()
            if "feed_intake" in data:
                # U: OLD: future stock was derived from the previous day's saved
                # U: snapshot, so adding/editing feed purchases later left stale stock.
                # U: NEW: feed stock and total feed are recalculated after the loop.
                # dailydata.feed_stock = yes_daily_data.feed_stock - dailydata.feed_intake
                # dailydata.total_feed = yes_daily_data.total_feed + dailydata.feed_intake
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
        recalculate_feed_snapshots(flock, daily_data.user)


class CreateFlockVaccinationService(services.Service):
    """
    Class to write logic for creating flock vaccination object
    """

    def process(self):
        data = self.data.get("data")
        daily_data_public_id = data.get("dailydata").get("public_id")
        flock_public_id = data.get("flock").get("public_id")
        vaccine_public_id = data.get("vaccine").get("public_id")
        user = self.data.get("user")
        # U: OLD: create looked up daily data/flock by public IDs only.
        # U: NEW: resolve the flock and daily data through the authenticated farmer.
        flock = Flock.objects.get(public_id=flock_public_id, user=user)
        flock_vaccination = FlockVaccination.objects.create(
            public_id=PublicId.create_public_id(),
            dailydata=DailyData.objects.get(
                public_id=daily_data_public_id, flock=flock, user=user
            ),
            flock=flock,
            vaccine=Vaccines.objects.get(public_id=vaccine_public_id),
            status=data.get("status"),
        )

        return flock_vaccination
