from datetime import date
from types import SimpleNamespace

from django.test import TestCase
from rest_framework import status

from common.base_models import Users
from dailydata.models import DailyData, DarknessTime, FeedAvailability
from farm.models import Country, Farm, State
from flocks.models import Breed, Flock
from sales.models import Sales
from sales.views import GraphView, SalesView


class SalesTenantIsolationTests(TestCase):
    def setUp(self):
        self.country = Country.objects.create(name="India", code="IN", isd_code=91)
        self.state = State.objects.create(name="Delhi", code="DL", country=self.country)
        self.breed = Breed.objects.create(code="SL", name="Sales Broiler", line="A")
        self.darkness_time = DarknessTime.objects.create(public_id=9401, name="4 hours")
        self.feed_availability = FeedAvailability.objects.create(public_id=9402, name="Full day")

        self.owner = self._user(9403, "sales_owner", 9876543240)
        self.other_user = self._user(9404, "sales_other", 9876543241)

        self.owner_farm = self._farm(9405, self.owner, "Owner Sales Farm")
        self.other_farm = self._farm(9406, self.other_user, "Other Sales Farm")
        self.owner_flock = self._flock(9407, self.owner, self.owner_farm, "Owner Sales Flock")
        self.other_flock = self._flock(9408, self.other_user, self.other_farm, "Other Sales Flock")
        self.owner_daily = self._daily_data(9409, self.owner, self.owner_flock)
        self.other_daily = self._daily_data(9410, self.other_user, self.other_flock)
        self.other_sale = self._sale(9411, self.other_flock)

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
            date=date(2026, 1, 2),
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

    def _sale(self, public_id, flock):
        return Sales.objects.create(
            public_id=public_id,
            flock=flock,
            sales_type="partial_lifting",
            date=date(2026, 1, 3),
            lifting_count=10,
            total_weight=20,
            average_weight=2,
            rate_per_kg=100,
            cost=2000,
            buyer="Buyer",
            vehicle_no="DL01AA0001",
            remarks="",
            buyer_phone_no=9876543210,
            buyer_address="Address",
            buyer_email="buyer@example.com",
        )

    def _request(self, user, data=None, query=None):
        return SimpleNamespace(
            user=SimpleNamespace(users=user, is_superuser=False),
            data=data or {},
            GET=query or {},
        )

    def test_create_rejects_other_users_flock(self):
        response = SalesView.create(
            self._request(
                self.owner,
                data={
                    "flock_public_id": self.other_flock.public_id,
                    "sales_type": "partial_lifting",
                    "date": "2026-01-03",
                    "lifting_count": 10,
                    "total_weight": 20,
                    "rate_per_kg": 100,
                    "buyer": "Buyer",
                    "vehicle_no": "DL01AA0001",
                    "remarks": "Sale remarks",
                    "buyer_phone_no": 9876543210,
                    "buyer_address": "Address",
                    "buyer_email": "buyer@example.com",
                },
            )
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_scopes_sale_to_authenticated_user(self):
        response = SalesView.retrieve(
            self._request(self.owner),
            pk=self.other_sale.public_id,
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_rejects_other_users_flock(self):
        response = SalesView.list(
            self._request(
                self.owner,
                query={"flock_public_id": self.other_flock.public_id},
            )
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_scopes_sale_to_authenticated_user(self):
        response = SalesView.partial_update(
            self._request(self.owner, data={"buyer": "Blocked Buyer"}),
            pk=self.other_sale.public_id,
        )
        self.other_sale.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.other_sale.buyer, "Buyer")

    def test_graph_rejects_other_users_flock(self):
        response = GraphView.retrieve(
            self._request(self.owner),
            pk=self.other_flock.public_id,
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
