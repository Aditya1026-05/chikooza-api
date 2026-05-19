from datetime import date
from types import SimpleNamespace

from django.test import TestCase
from rest_framework import status

from common.base_models import Users
from dailydata.models import DailyData, DarknessTime, FeedAvailability, FlockVaccination, Vaccines
from dailydata.views import DailyDataView, FlockVaccinationView
from farm.models import Country, Farm, State
from flocks.models import Breed, Flock


class DailyDataTenantIsolationTests(TestCase):
    def setUp(self):
        self.country = Country.objects.create(name="India", code="IN", isd_code=91)
        self.state = State.objects.create(name="Delhi", code="DL", country=self.country)
        self.breed = Breed.objects.create(code="DD", name="Daily Broiler", line="A")
        self.darkness_time = DarknessTime.objects.create(public_id=9201, name="4 hours")
        self.feed_availability = FeedAvailability.objects.create(public_id=9202, name="Full day")
        self.vaccine = Vaccines.objects.create(
            public_id=9203,
            name="ND",
            full_name="Newcastle Disease",
            description="Routine",
            company_id="VAC",
        )

        self.owner = self._user(9301, "daily_owner", 9876543230)
        self.other_user = self._user(9302, "daily_other", 9876543231)

        self.owner_farm = self._farm(9303, self.owner, "Owner Daily Farm")
        self.other_farm = self._farm(9304, self.other_user, "Other Daily Farm")
        self.owner_flock = self._flock(9305, self.owner, self.owner_farm, "Owner Daily Flock")
        self.other_flock = self._flock(9306, self.other_user, self.other_farm, "Other Daily Flock")
        self.day = date(2026, 1, 2)
        self.owner_daily = self._daily_data(9307, self.owner, self.owner_flock)
        self.other_daily = self._daily_data(9308, self.other_user, self.other_flock)
        self.other_vaccination = FlockVaccination.objects.create(
            public_id=9309,
            dailydata=self.other_daily,
            flock=self.other_flock,
            vaccine=self.vaccine,
            status="Start",
        )

    def _user(self, public_id, username, mobile_number):
        return Users.objects.create_user(
            public_id=public_id,
            username=username,
            password="password",
            mobile_number=mobile_number,
        )

    def _farm(self, public_id, user, name):
        return Farm.objects.create(
            public_id=public_id,
            user=user,
            name=name,
            address="Farm address",
            city="City",
            state=self.state,
            country=self.country,
            pin="110001",
            lat_long="0,0",
            shed_count=1,
        )

    def _flock(self, public_id, user, farm, name):
        return Flock.objects.create(
            public_id=public_id,
            user=user,
            farm=farm,
            name=name,
            integration=False,
            integrator=None,
            hatch_date=date(2026, 1, 1),
            flock_size=100,
            actual_birds=100,
            breed=self.breed,
            hatchery=None,
            hatchery_name="",
            chick_weight=40,
            hatchery_vaccine=1,
            feed_sys="M",
            drinking_sys="M",
            ec_shed=False,
            chick_cost=10,
            status=True,
            flock_bird=100,
        )

    def _daily_data(self, public_id, user, flock):
        return DailyData.objects.create(
            public_id=public_id,
            date=self.day,
            flock=flock,
            user=user,
            mortality=1,
            total_mort=1,
            current_bird_count=99,
            feed_stock=90,
            feed_intake=10,
            total_feed=10,
            average_bird_weight=50,
            average_feed=101,
            total_average_feed=101,
            fcr=0,
            total_fcr=2,
            cooling=False,
            heating=False,
            seek=False,
            medicine=False,
            remarks="",
            status=True,
            darkness_time=self.darkness_time,
            feed_availability=self.feed_availability,
            flock_birds=99,
        )

    def _request(self, user, data=None, query=None):
        return SimpleNamespace(
            user=SimpleNamespace(users=user, is_superuser=False),
            data=data or {},
            GET=query or {},
        )

    def test_create_rejects_other_users_flock(self):
        response = DailyDataView.create(
            self._request(
                self.owner,
                data={
                    "date": "2026-01-03",
                    "mortality": 1,
                    "feed_intake": 10,
                    "average_bird_weight": 60,
                    "flock_public_id": self.other_flock.public_id,
                    "cooling": False,
                    "heating": False,
                    "seek": False,
                    "medicine": False,
                    "darkness_time_public_id": self.darkness_time.public_id,
                    "feed_availability_public_id": self.feed_availability.public_id,
                },
            )
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_rejects_other_users_flock(self):
        response = DailyDataView.list(
            self._request(
                self.owner,
                query={
                    "flock_public_id": self.other_flock.public_id,
                    "date": self.day.isoformat(),
                },
            )
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_scopes_daily_data_to_authenticated_user(self):
        response = DailyDataView.partial_update(
            self._request(self.owner, data={"mortality": 2}),
            pk=self.other_daily.public_id,
        )
        self.other_daily.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.other_daily.mortality, 1)

    def test_vaccination_retrieve_scopes_to_authenticated_user(self):
        response = FlockVaccinationView.retrieve(
            self._request(self.owner),
            pk=self.other_vaccination.public_id,
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_vaccination_destroy_scopes_to_authenticated_user(self):
        response = FlockVaccinationView.destroy(
            self._request(self.owner),
            pk=self.other_vaccination.public_id,
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(
            FlockVaccination.objects.filter(public_id=self.other_vaccination.public_id).exists()
        )

    def test_vaccination_create_rejects_other_users_flock(self):
        response = FlockVaccinationView.create(
            self._request(
                self.owner,
                data={
                    "daily_data_public_id": self.other_daily.public_id,
                    "flock_public_id": self.other_flock.public_id,
                    "vaccine_public_id": self.vaccine.public_id,
                    "status": "Start",
                },
            )
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
