from datetime import date
from types import SimpleNamespace

from django.test import TestCase
from rest_framework import status

from common.base_models import Users
from farm.models import Country, Farm, State
from flocks.models import Breed, Flock
from flocks.services import AddFlockService
from flocks.views import FlockSummaryView, FlockView


class FlockTenantIsolationTests(TestCase):
    def setUp(self):
        self.country = Country.objects.create(name="India", code="IN", isd_code=91)
        self.state = State.objects.create(name="Delhi", code="DL", country=self.country)
        self.breed = Breed.objects.create(code="BR", name="Broiler", line="A")

        self.owner = self._user(9101, "flock_owner", 9876543220)
        self.other_user = self._user(9102, "flock_other", 9876543221)

        self.owner_farm = self._farm(8101, self.owner, "Owner Farm")
        self.other_farm = self._farm(8102, self.other_user, "Other Farm")
        self.owner_flock = self._flock(7101, self.owner, self.owner_farm, "Owner Flock")
        self.other_flock = self._flock(7102, self.other_user, self.other_farm, "Other Flock")

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

    def _request(self, user, data=None):
        return SimpleNamespace(
            user=SimpleNamespace(users=user, is_superuser=False),
            data=data or {},
        )

    def test_update_scopes_flock_to_authenticated_user(self):
        response = FlockView().partial_update(
            self._request(self.owner),
            pk=self.other_flock.public_id,
        )
        self.other_flock.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.other_flock.name, "Other Flock")

    def test_summary_scopes_flock_to_authenticated_user(self):
        response = FlockSummaryView.retrieve(
            self._request(self.owner),
            pk=self.other_flock.public_id,
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_summary_handles_flock_without_daily_data(self):
        response = FlockSummaryView.retrieve(
            self._request(self.owner),
            pk=self.owner_flock.public_id,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["results"]["has_daily_data"])
        self.assertEqual(response.data["results"]["daily_data_count"], 0)
        self.assertEqual(response.data["results"]["current_bird_count"], 100)

    def test_create_rejects_other_users_farm(self):
        with self.assertRaises(Farm.DoesNotExist):
            AddFlockService.execute(
                {
                    "user": self.owner,
                    "data": {
                        "farm_public_id": self.other_farm.public_id,
                        "flock_name": "Blocked Flock",
                        "integration": False,
                        "hatch_date": date(2026, 1, 2),
                        "flock_size": 100,
                        "actual_birds": 100,
                        "breed_public_id": self.breed.public_id,
                        "hatchery_name": "Local Hatchery",
                        "chick_weight": 40,
                        "hatchery_vaccine": 1,
                        "feed_sys": "M",
                        "drinking_sys": "M",
                        "ec_shed": False,
                        "chick_cost": 10,
                    },
                }
            )
