from datetime import timedelta

from django.contrib.admin.sites import site
from django.contrib.auth.forms import AdminPasswordChangeForm, UserCreationForm
from django.contrib.contenttypes.models import ContentType
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from oauth2_provider.models import AccessToken

from aibot.models import AIChatLog
from chatbot.models import ChatLog
from common.admin_filters import FarmWorkflowFilter, FlockWorkflowFilter
from common.base_models import PublicId, Users
from common.utils import get_or_create_oauth_application
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
        # Admin page rendering may populate this process-wide cache with a
        # content type created inside the previous test's rolled-back transaction.
        ContentType.objects.clear_cache()
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
        self.assertContains(response, "Register farmer")
        self.assertContains(response, "Review pending registrations")
        self.assertContains(response, "Reset farmer passwords")
        self.assertContains(response, "common/admin.js")

    def test_admin_add_page_uses_secure_farmer_creation_form(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("admin:common_users_add"))

        self.assertEqual(response.status_code, 200)
        form = response.context["adminform"].form
        self.assertIsInstance(form, UserCreationForm)
        self.assertContains(response, 'name="username"', html=False)
        self.assertContains(response, 'name="email"', html=False)
        self.assertContains(response, 'name="mobile_number"', html=False)
        self.assertContains(response, 'name="password1"', html=False)
        self.assertContains(response, 'name="password2"', html=False)
        self.assertNotIn("password", form.fields)

    def test_admin_can_register_an_approved_verified_farmer(self):
        self.client.force_login(self.admin_user)
        password = "Farmer-Safe-Password-8729"

        response = self.client.post(
            reverse("admin:common_users_add"),
            {
                "username": "new-farmer@example.com",
                "email": "new-farmer@example.com",
                "first_name": "New Farmer",
                "mobile_number": "7777777777",
                "password1": password,
                "password2": password,
                "_save": "Save",
            },
        )

        self.assertEqual(response.status_code, 302)
        farmer = Users.objects.get(username="new-farmer@example.com")
        self.assertNotEqual(farmer.password, password)
        self.assertTrue(farmer.check_password(password))
        self.assertIsNotNone(farmer.public_id)
        self.assertGreater(farmer.public_id, 0)
        self.assertEqual(farmer.approval_status, Users.APPROVAL_APPROVED)
        self.assertTrue(farmer.is_active)
        self.assertTrue(farmer.is_email_verified)
        self.assertTrue(farmer.is_phone_verified)
        self.assertFalse(farmer.is_staff)
        self.assertFalse(farmer.is_superuser)

    def test_admin_can_reset_farmer_password_and_revoke_access_tokens(self):
        self.client.force_login(self.admin_user)
        application = get_or_create_oauth_application(self.farmer)
        token = AccessToken.objects.create(
            user=self.farmer,
            application=application,
            token="token-to-revoke-after-admin-password-reset",
            expires=timezone.now() + timedelta(hours=1),
            scope="read create update delete groups",
        )
        reset_url = reverse(
            "admin:common_users_reset_password",
            args=(self.farmer.pk,),
        )

        get_response = self.client.get(reset_url)

        self.assertEqual(get_response.status_code, 200)
        form = get_response.context["form"]
        self.assertIsInstance(form, AdminPasswordChangeForm)
        self.assertEqual(
            set(form.fields),
            {"password1", "password2", "usable_password"},
        )

        new_password = "Farmer-New-Safe-Password-9417"
        post_response = self.client.post(
            reset_url,
            {
                "password1": new_password,
                "password2": new_password,
                "usable_password": "true",
            },
        )

        self.assertEqual(post_response.status_code, 302)
        self.farmer.refresh_from_db()
        self.assertFalse(self.farmer.check_password("farmer-pass"))
        self.assertTrue(self.farmer.check_password(new_password))
        self.assertFalse(AccessToken.objects.filter(pk=token.pk).exists())

    def test_approval_action_only_approves_verified_pending_farmers(self):
        pending_farmer = Users.objects.create_user(
            username="pending-farmer@example.com",
            email="pending-farmer@example.com",
            password="pending-pass",
            mobile_number="7777777771",
            public_id=PublicId.create_public_id(),
            is_phone_verified=True,
            is_email_verified=True,
            approval_status=Users.APPROVAL_PENDING,
            is_active=False,
        )
        unverified_farmer = Users.objects.create_user(
            username="unverified-farmer@example.com",
            email="unverified-farmer@example.com",
            password="unverified-pass",
            mobile_number="7777777772",
            public_id=PublicId.create_public_id(),
            is_phone_verified=True,
            is_email_verified=False,
            approval_status=Users.APPROVAL_PENDING,
            is_active=False,
        )
        staff_user = Users.objects.create_user(
            username="pending-staff@example.com",
            email="pending-staff@example.com",
            password="staff-pass",
            mobile_number="7777777773",
            public_id=PublicId.create_public_id(),
            is_phone_verified=True,
            is_email_verified=True,
            approval_status=Users.APPROVAL_PENDING,
            is_active=False,
            is_staff=True,
        )
        self.client.force_login(self.admin_user)
        review_started_at = timezone.now()

        response = self.client.post(
            reverse("admin:common_users_changelist"),
            {
                "action": "approve_farmer_accounts",
                "_selected_action": [
                    pending_farmer.pk,
                    unverified_farmer.pk,
                    staff_user.pk,
                ],
                "select_across": "0",
                "index": "0",
            },
        )

        self.assertEqual(response.status_code, 302)
        pending_farmer.refresh_from_db()
        unverified_farmer.refresh_from_db()
        staff_user.refresh_from_db()

        self.assertEqual(pending_farmer.approval_status, Users.APPROVAL_APPROVED)
        self.assertTrue(pending_farmer.is_active)
        self.assertEqual(pending_farmer.approval_reviewed_by_id, self.admin_user.pk)
        self.assertIsNotNone(pending_farmer.approval_reviewed_at)
        self.assertGreaterEqual(pending_farmer.approval_reviewed_at, review_started_at)

        for skipped_user in (unverified_farmer, staff_user):
            with self.subTest(user=skipped_user.username):
                self.assertEqual(
                    skipped_user.approval_status,
                    Users.APPROVAL_PENDING,
                )
                self.assertFalse(skipped_user.is_active)
                self.assertIsNone(skipped_user.approval_reviewed_by)
                self.assertIsNone(skipped_user.approval_reviewed_at)

    @override_settings(CHIKOOZA_UI_BASE_URL="http://localhost:5173")
    def test_open_dashboard_as_farmer_creates_short_lived_access_token(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(
            reverse("admin:common_users_open_dashboard", args=(self.farmer.pk,))
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            response["Location"].startswith("http://localhost:5173/admin-access#")
        )
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

        self.assertEqual(
            filtered.lookup_choices,
            [(str(self.owner_farm.pk), "Owner Farm (owner-filter@example.com)")],
        )

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

        self.assertEqual(
            filtered.lookup_choices,
            [(str(self.owner_flock.pk), "Owner Flock (Owner Farm)")],
        )
