from datetime import date
from types import SimpleNamespace

from django.test import TestCase
from rest_framework import status

from common.base_models import Users
from common.constant import APP_RESULT, TOTAL_RECORDS
from farm.models import Country, Farm, State
from flocks.models import Breed, Flock
from purchase.models import Purchase
from purchase.services import AddPurchaseService
from purchase.views import PurchaseView


class PurchaseTenantIsolationTests(TestCase):
    def setUp(self):
        self.country = Country.objects.create(name="India", code="IN", isd_code=91)
        self.state = State.objects.create(name="Delhi", code="DL", country=self.country)
        self.breed = Breed.objects.create(code="BR", name="Broiler", line="A")

        self.owner = self._user(9001, "owner", 9876543210)
        self.other_user = self._user(9002, "other", 9876543211)

        self.owner_farm = self._farm(8001, self.owner, "Owner Farm")
        self.other_farm = self._farm(8002, self.other_user, "Other Farm")
        self.owner_flock = self._flock(7001, self.owner, self.owner_farm, "Owner Flock")
        self.other_flock = self._flock(7002, self.other_user, self.other_farm, "Other Flock")

        self.owner_purchase = self._purchase(6001, self.owner, self.owner_flock, 100)
        self.other_purchase = self._purchase(6002, self.other_user, self.other_flock, 200)

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

    def _purchase(self, public_id, user, flock, cost):
        return Purchase.objects.create(
            public_id=public_id,
            flock=flock,
            user=user,
            type="Feed",
            date=date(2026, 1, 10),
            cost=cost,
            quantity=50,
            company_name="Feed Co",
            item_name="Starter",
            item_type=100,
            unit=1,
            size=50,
            remarks="ok",
            adjust_type="O",
        )

    def _request(self, user, data=None, query=None):
        return SimpleNamespace(
            user=SimpleNamespace(users=user, is_superuser=False),
            data=data or {},
            GET=query or {},
        )

    def test_retrieve_scopes_purchase_to_authenticated_user(self):
        response = PurchaseView.retrieve(
            self._request(self.owner),
            pk=self.other_purchase.public_id,
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_scopes_purchases_to_authenticated_user(self):
        response = PurchaseView.list(
            self._request(
                self.owner,
                query={"flock_public_id": str(self.other_flock.public_id)},
            )
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[APP_RESULT][TOTAL_RECORDS], 0)
        self.assertEqual(response.data[APP_RESULT]["purchase_list"], [])

    def test_update_scopes_purchase_to_authenticated_user(self):
        response = PurchaseView.partial_update(
            self._request(self.owner, data={"cost": 999}),
            pk=self.other_purchase.public_id,
        )
        self.other_purchase.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.other_purchase.cost, 200)

    def test_create_rejects_other_users_flock(self):
        with self.assertRaises(Flock.DoesNotExist):
            AddPurchaseService.execute(
                {
                    "users": self.owner,
                    "data": {
                        "flock_public_id": self.other_flock.public_id,
                        "type": "Feed",
                        "date": date(2026, 1, 11),
                        "cost": 100,
                        "remarks": "blocked",
                        "company_name": "Feed Co",
                        "item_name": "Starter",
                        "unit": 1,
                        "size": 50,
                        "item_type": 100,
                    },
                }
            )
