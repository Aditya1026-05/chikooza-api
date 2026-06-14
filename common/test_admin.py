from django.contrib.admin.sites import site
from django.test import TestCase

from aibot.models import AIChatLog
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
