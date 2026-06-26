from django.contrib.admin.sites import site
from django.test import TestCase, override_settings
from django.urls import reverse
from oauth2_provider.models import AccessToken

from aibot.models import AIChatLog
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
