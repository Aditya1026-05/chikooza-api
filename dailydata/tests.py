from datetime import date
from types import SimpleNamespace

from django.template.loader import render_to_string
from django.test import TestCase
from rest_framework import status
from rest_framework.exceptions import ValidationError

from common.base_models import Users
from dailydata.models import (
    DailyData,
    DarknessTime,
    FeedAvailability,
    FlockVaccination,
    Vaccines,
)
from dailydata.views import (
    DailyDataAverageFeedBirdsView,
    DailyDataDetailView,
    DailyDataFCRView,
    DailyDataLastDateView,
    DailyDataListView,
    DailyDataView,
    FlockVaccinationView,
    PDFView,
)
from farm.models import Country, Farm, State
from flocks.models import Breed, Flock
from flocks.services import UpdateFlockService
from purchase.models import Purchase


class DailyDataTenantIsolationTests(TestCase):
    def setUp(self):
        self.country = Country.objects.create(name="India", code="IN", isd_code=91)
        self.state = State.objects.create(name="Delhi", code="DL", country=self.country)
        self.breed = Breed.objects.create(code="DD", name="Daily Broiler", line="A")
        self.darkness_time = DarknessTime.objects.create(public_id=9201, name="4 hours")
        self.feed_availability = FeedAvailability.objects.create(
            public_id=9202, name="Full day"
        )
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
        self.owner_flock = self._flock(
            9305, self.owner, self.owner_farm, "Owner Daily Flock"
        )
        self.other_flock = self._flock(
            9306, self.other_user, self.other_farm, "Other Daily Flock"
        )
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

    def _daily_data(
        self,
        public_id,
        user,
        flock,
        record_date=None,
        mortality=1,
        current_bird_count=99,
        feed_intake=10,
        total_feed=10,
    ):
        return DailyData.objects.create(
            public_id=public_id,
            date=record_date or self.day,
            flock=flock,
            user=user,
            mortality=mortality,
            total_mort=1,
            current_bird_count=current_bird_count,
            feed_stock=90,
            feed_intake=feed_intake,
            total_feed=total_feed,
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

    def _feed_purchase(self, public_id, user, flock, quantity, purchase_date):
        return Purchase.objects.create(
            public_id=public_id,
            flock=flock,
            user=user,
            type="Feed",
            date=purchase_date,
            cost=100,
            quantity=quantity,
            company_name="Feed Co",
            item_name="Starter",
            item_type=100,
            unit=1,
            size=quantity,
            remarks="stock",
            adjust_type="O",
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

    def test_create_rejects_feed_intake_without_feed_purchase_stock(self):
        with self.assertRaises(ValidationError) as ctx:
            DailyDataView.create(
                self._request(
                    self.owner,
                    data={
                        "date": "2026-01-03",
                        "mortality": 1,
                        "feed_intake": 10,
                        "average_bird_weight": 60,
                        "flock_public_id": self.owner_flock.public_id,
                        "cooling": False,
                        "heating": False,
                        "seek": False,
                        "medicine": False,
                        "darkness_time_public_id": self.darkness_time.public_id,
                        "feed_availability_public_id": self.feed_availability.public_id,
                    },
                )
            )

        self.assertIn(
            "Feed intake is greater than available feed stock", str(ctx.exception)
        )

    def test_create_uses_feed_purchase_as_available_stock(self):
        self._feed_purchase(
            9310,
            self.owner,
            self.owner_flock,
            50,
            date(2026, 1, 1),
        )

        response = DailyDataView.create(
            self._request(
                self.owner,
                data={
                    "date": "2026-01-03",
                    "mortality": 1,
                    "feed_intake": 20,
                    "average_bird_weight": 60,
                    "flock_public_id": self.owner_flock.public_id,
                    "cooling": False,
                    "heating": False,
                    "seek": False,
                    "medicine": False,
                    "darkness_time_public_id": self.darkness_time.public_id,
                    "feed_availability_public_id": self.feed_availability.public_id,
                },
            )
        )
        daily_data = DailyData.objects.get(
            flock=self.owner_flock,
            user=self.owner,
            date=date(2026, 1, 3),
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(daily_data.total_feed, 30)
        self.assertEqual(daily_data.feed_stock, 20)

    def test_create_recalculates_future_daily_bird_counts_immediately(self):
        self._feed_purchase(
            9311,
            self.owner,
            self.owner_flock,
            200,
            date(2026, 1, 1),
        )
        future_daily = self._daily_data(
            9312,
            self.owner,
            self.owner_flock,
            record_date=date(2026, 1, 4),
            mortality=1,
            current_bird_count=98,
            feed_intake=10,
            total_feed=20,
        )

        response = DailyDataView.create(
            self._request(
                self.owner,
                data={
                    "date": "2026-01-03",
                    "mortality": 2,
                    "feed_intake": 5,
                    "average_bird_weight": 60,
                    "flock_public_id": self.owner_flock.public_id,
                    "cooling": False,
                    "heating": False,
                    "seek": False,
                    "medicine": False,
                    "darkness_time_public_id": self.darkness_time.public_id,
                    "feed_availability_public_id": self.feed_availability.public_id,
                },
            )
        )

        created_daily = DailyData.objects.get(
            flock=self.owner_flock,
            user=self.owner,
            date=date(2026, 1, 3),
        )
        future_daily.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(created_daily.current_bird_count, 97)
        self.assertEqual(created_daily.total_mort, 3)
        self.assertEqual(future_daily.current_bird_count, 96)
        self.assertEqual(future_daily.total_mort, 4)
        self.assertEqual(future_daily.total_feed, 25)

    def test_flock_opening_bird_update_recalculates_daily_bird_counts(self):
        UpdateFlockService.execute(
            {
                "data": {"actual_birds": 120},
                "flock": self.owner_flock,
            }
        )
        self.owner_daily.refresh_from_db()

        self.assertEqual(self.owner_daily.current_bird_count, 119)
        self.assertEqual(self.owner_daily.total_mort, 0.83)

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

    def test_detail_list_rejects_other_users_flock(self):
        response = DailyDataDetailView.list(
            self._request(
                self.owner,
                query={"flock_public_id": self.other_flock.public_id},
            )
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_report_list_rejects_other_users_flock(self):
        response = DailyDataListView.list(
            self._request(
                self.owner,
                query={"flock_public_id": self.other_flock.public_id},
            )
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_last_date_rejects_other_users_flock(self):
        response = DailyDataLastDateView().retrieve(
            self._request(self.owner),
            pk=self.other_flock.public_id,
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_average_feed_rejects_other_users_flock(self):
        response = DailyDataAverageFeedBirdsView().list(
            self._request(
                self.owner,
                query={
                    "flock_public_id": self.other_flock.public_id,
                    "date": self.day,
                    "current_bird_count": 90,
                    "feed_intake": 10,
                },
            )
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_fcr_rejects_other_users_flock(self):
        response = DailyDataFCRView.list(
            self._request(
                self.owner,
                query={
                    "flock_public_id": self.other_flock.public_id,
                    "date": self.day,
                    "average_feed": 100,
                    "average_bird_weight": 50,
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
            FlockVaccination.objects.filter(
                public_id=self.other_vaccination.public_id
            ).exists()
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

    def test_pdf_template_uses_chikooza_daily_data_columns(self):
        html = render_to_string(
            "dailydata.html",
            {
                "record": [
                    {
                        "date": self.day.isoformat(),
                        "age": 1,
                        "bird_count": 99,
                        "mortality": 1,
                        "cum_mort": 1,
                        "total_mortality_percentage": 1,
                        "feed_intake": 10,
                        "total_feed_consumed": 10,
                        "feed_stock": 90,
                        "average_feed_per_bird": 101,
                        "average_bird_weight": 50,
                        "fcr": 0,
                        "total_fcr": 2,
                        "cooling": False,
                        "heating": False,
                        "seek": False,
                        "medicine": False,
                        "remarks": "Healthy flock",
                    }
                ],
                "flock": {
                    "farm_name": self.owner_farm.name,
                    "name": self.owner_flock.name,
                    "public_id": self.owner_flock.public_id,
                    "hatch_date": self.owner_flock.hatch_date,
                    "actual_birds": self.owner_flock.actual_birds,
                },
                "generated_on": self.day,
                "total_records": 1,
                "date_range": {"start": "2026-01-01", "end": "2026-01-31"},
                "totals": {
                    "mortality": 1,
                    "feed_intake": 10,
                    "latest_birds": 99,
                    "latest_feed_stock": 90,
                },
            },
        )

        self.assertIn("Chikooza Daily Flock Data", html)
        self.assertIn("Total Mortality", html)
        self.assertIn("Date From", html)
        self.assertIn("Mort. %", html)
        self.assertIn("Feed Intake", html)
        self.assertIn("Owner Daily Flock", html)
        self.assertNotIn("Roll No", html)

    def test_pdf_export_returns_pdf_for_authenticated_flock(self):
        response = PDFView.list(
            self._request(
                self.owner,
                query={"flock_public_id": self.owner_flock.public_id},
            )
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn(
            "Chikooza_DailyDataSheet_Owner_Daily_Flock", response["Content-Disposition"]
        )
        self.assertGreater(len(response.content), 0)

    def test_pdf_export_rejects_other_users_flock(self):
        response = PDFView.list(
            self._request(
                self.owner,
                query={"flock_public_id": self.other_flock.public_id},
            )
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
