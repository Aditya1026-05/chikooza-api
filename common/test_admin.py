from django.contrib.admin.sites import site
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from oauth2_provider.models import AccessToken

from aibot.models import AIChatLog
from common.admin_filters import FarmWorkflowFilter, FlockWorkflowFilter
from common.base_models import PublicId, Users
from chatbot.models import ChatLog
from dailydata.models import DailyData, FlockVaccination, Vaccines
from farm.models import Country, Farm, State
from flocks.models import Breed, Flock, Integrator
from purchase.models import Purchase
from sales.models import Sales


class AdminRegistrationTests(TestCase):
    def test_business_models_are_registered_in_admin(self):
        required_models = (
            Country,
            State,
            Farm,
            Breed,
            Integrator,
            Flock,
            DailyData,
            Vaccines,
            FlockVaccination,
            Purchase,
            Sales,
            ChatLog,
            AIChatLog,
        )

        for model in required_models:
            with self.subTest(model=model.__name__):
                self.assertIn(model, site._registry)

    def test_master_public_ids_do_not_change_on_update(self):
        country = Country.objects.create(name="India", code="IN", isd_code=91)
        state = State.objects.create(name="Uttar Pradesh", code="UP", country=country)
        breed = Breed.objects.create(code="HUB", name="Hubbard", line="Broiler")
        integrator = Integrator.objects.create(name="Integrator", nickname="INT")

        original_ids = {
            "country": country.public_id,
            "state": state.public_id,
            "breed": breed.public_id,
            "integrator": integrator.public_id,
        }

        country.name = "India Updated"
        state.name = "Uttar Pradesh Updated"
        breed.name = "Hubbard Updated"
        integrator.name = "Integrator Updated"
        country.save()
        state.save()
        breed.save()
        integrator.save()

        self.assertEqual(country.public_id, original_ids["country"])
        self.assertEqual(state.public_id, original_ids["state"])
        self.assertEqual(breed.public_id, original_ids["breed"])
        self.assertEqual(integrator.public_id, original_ids["integrator"])


class AdminWorkflowTests(TestCase):
    def setUp(self):
        self.admin_user = Users.objects.create_superuser(
            username="admin@example.com",
            email="admin@example.com",
            password="admin-pass",
            mobile_number="9999999999",
            public_id=PublicId.create_public_id(),
            is_phone_verified=True,
            is_email_verified=True,
            approval_status=Users.APPROVAL_APPROVED,
        )
        self.farmer = Users.objects.create_user(
            username="farmer@example.com",
            email="farmer@example.com",
            password="farmer-pass",
            mobile_number="8888888888",
            public_id=PublicId.create_public_id(),
            is_phone_verified=True,
            is_email_verified=True,
            approval_status=Users.APPROVAL_APPROVED,
            is_active=True,
        )

    def test_admin_dashboard_renders_product_flow(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("admin:index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Manage Chikooza from farmer to flock to sale.")
        self.assertContains(response, "Farmers")
        self.assertContains(response, "Operations")
        self.assertContains(response, "common/admin.js")

    @override_settings(CHIKOOZA_UI_BASE_URL="http://localhost:5173")
    def test_open_dashboard_as_farmer_creates_short_lived_access_token(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(
            reverse("admin:common_users_open_dashboard", args=(self.farmer.pk,))
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith("http://localhost:5173/admin-access#"))
        token = AccessToken.objects.get(user=self.farmer)
        self.assertIn(token.token, response["Location"])
        self.assertEqual(token.scope, "read create update delete groups")


class AdminCascadingFilterTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.admin_user = Users.objects.create_superuser(
            username="admin-filter@example.com",
            email="admin-filter@example.com",
            password="admin-pass",
            mobile_number="9999999991",
            public_id=PublicId.create_public_id(),
            is_phone_verified=True,
            is_email_verified=True,
            approval_status=Users.APPROVAL_APPROVED,
        )
        self.owner = Users.objects.create_user(
            username="owner-filter@example.com",
            email="owner-filter@example.com",
            password="owner-pass",
            mobile_number="9999999992",
            public_id=PublicId.create_public_id(),
            is_phone_verified=True,
            is_email_verified=True,
            approval_status=Users.APPROVAL_APPROVED,
            is_active=True,
        )
        self.other = Users.objects.create_user(
            username="other-filter@example.com",
            email="other-filter@example.com",
            password="other-pass",
            mobile_number="9999999993",
            public_id=PublicId.create_public_id(),
            is_phone_verified=True,
            is_email_verified=True,
            approval_status=Users.APPROVAL_APPROVED,
            is_active=True,
        )
        country = Country.objects.create(
            name="India",
            code="IN",
            isd_code=91,
            public_id=PublicId.create_public_id(),
        )
        state = State.objects.create(
            name="Delhi",
            code="DL",
            country=country,
            public_id=PublicId.create_public_id(),
        )
        breed = Breed.objects.create(
            code="B1",
            name="Broiler",
            line="Commercial",
            public_id=PublicId.create_public_id(),
        )
        self.owner_farm = Farm.objects.create(
            user=self.owner,
            name="Owner Farm",
            address="A",
            city="Delhi",
            district="Central",
            state=state,
            country=country,
            pin="110001",
            lat_long="0,0",
            shed_count=1,
            public_id=PublicId.create_public_id(),
        )
        self.other_farm = Farm.objects.create(
            user=self.other,
            name="Other Farm",
            address="B",
            city="Delhi",
            district="Central",
            state=state,
            country=country,
            pin="110002",
            lat_long="0,0",
            shed_count=1,
            public_id=PublicId.create_public_id(),
        )
        self.owner_flock = Flock.objects.create(
            user=self.owner,
            farm=self.owner_farm,
            name="Owner Flock",
            integration=False,
            hatch_date="2026-01-01",
            flock_size=100,
            actual_birds=100,
            breed=breed,
            chick_weight=40,
            hatchery_vaccine=1,
            feed_sys="M",
            drinking_sys="M",
            ec_shed=False,
            chick_cost=10,
            status=True,
            flock_bird=100,
            public_id=PublicId.create_public_id(),
        )
        self.other_flock = Flock.objects.create(
            user=self.other,
            farm=self.other_farm,
            name="Other Flock",
            integration=False,
            hatch_date="2026-01-01",
            flock_size=100,
            actual_birds=100,
            breed=breed,
            chick_weight=40,
            hatchery_vaccine=1,
            feed_sys="M",
            drinking_sys="M",
            ec_shed=False,
            chick_cost=10,
            status=True,
            flock_bird=100,
            public_id=PublicId.create_public_id(),
        )

    def _request(self, params=None):
        request = self.factory.get("/admin/", data=params or {})
        request.user = self.admin_user
        return request

    def test_farm_filter_waits_for_farmer_then_shows_only_that_farmers_farms(self):
        empty_filter = FarmWorkflowFilter(
            self._request(),
            {},
            Flock,
            site._registry[Flock],
        )
        self.assertEqual(empty_filter.lookup_choices, [])

        filtered = FarmWorkflowFilter(
            self._request({"farmer": self.owner.pk}),
            {},
            Flock,
            site._registry[Flock],
        )

        self.assertEqual(filtered.lookup_choices, [(str(self.owner_farm.pk), "Owner Farm (owner-filter@example.com)")])

    def test_flock_filter_waits_for_farmer_or_farm_then_scopes_choices(self):
        empty_filter = FlockWorkflowFilter(
            self._request(),
            {},
            Flock,
            site._registry[Flock],
        )
        self.assertEqual(empty_filter.lookup_choices, [])

        filtered = FlockWorkflowFilter(
            self._request({"farmer": self.owner.pk, "farm": self.owner_farm.pk}),
            {},
            Flock,
            site._registry[Flock],
        )

        self.assertEqual(filtered.lookup_choices, [(str(self.owner_flock.pk), "Owner Flock (Owner Farm)")])
