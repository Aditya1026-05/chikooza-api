from types import SimpleNamespace

from django.test import TestCase
from rest_framework import status

from common.base_models import Users
from common.constant import APP_RESULT
from farm.models import Country, Farm, State
from farm.views import FarmView


class FarmTenantIsolationTests(TestCase):
    def setUp(self):
        self.country = Country.objects.create(name="India", code="IN", isd_code=91)
        self.state = State.objects.create(name="Delhi", code="DL", country=self.country)
        self.owner = Users.objects.create_user(
            public_id=9501,
            username="farm_owner",
            password="password",
            mobile_number=9876543250,
        )
        self.other_user = Users.objects.create_user(
            public_id=9502,
            username="farm_other",
            password="password",
            mobile_number=9876543251,
        )
        self.owner_farm = self._farm(9503, self.owner, "Owner Farm")
        self.other_farm = self._farm(9504, self.other_user, "Other Farm")

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
            status=True,
        )

    def _request(self, user, data=None):
        return SimpleNamespace(
            user=SimpleNamespace(users=user, is_superuser=False),
            data=data or {},
        )

    def test_list_returns_only_authenticated_users_farms(self):
        response = FarmView().list(self._request(self.owner))

        farm_ids = [farm["public_id"] for farm in response.data[APP_RESULT]]
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(self.owner_farm.public_id, farm_ids)
        self.assertNotIn(self.other_farm.public_id, farm_ids)

    def test_retrieve_rejects_other_users_farm(self):
        response = FarmView().retrieve(
            self._request(self.owner),
            pk=self.other_farm.public_id,
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_rejects_other_users_farm(self):
        response = FarmView().partial_update(
            self._request(self.owner, data={"name": "Blocked Update"}),
            pk=self.other_farm.public_id,
        )
        self.other_farm.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.other_farm.name, "Other Farm")

    def test_update_allows_owned_farm(self):
        response = FarmView().partial_update(
            self._request(self.owner, data={"name": "Updated Owner Farm"}),
            pk=self.owner_farm.public_id,
        )
        self.owner_farm.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.owner_farm.name, "Updated Owner Farm")
