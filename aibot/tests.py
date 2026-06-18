from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase

from .modern_services import (
    BLOCKED,
    CONVERSATION,
    SQLPlan,
    TEXT_TO_SQL,
    ChikoozaModernAgentService,
    ChikoozaQueryRouter,
    TenantSafeSQLExecutor,
    normalize_ai_query,
)


class QueryNormalizationTests(SimpleTestCase):
    def test_common_farmer_typos_are_normalized(self):
        self.assertEqual(normalize_ai_query("breed of the first glock"), "breed of the first flock")
        self.assertEqual(normalize_ai_query("total sails"), "total sales")
        self.assertIn("purchase", normalize_ai_query("total pruchases"))
        self.assertIn("mortality", normalize_ai_query("mortilty"))
        self.assertIn("biggest", normalize_ai_query("buggest loss"))


class QueryRouterTests(SimpleTestCase):
    def test_routes_farm_questions_to_text_to_sql(self):
        router = ChikoozaQueryRouter()
        self.assertEqual(router.route("show all my flocks", user_id=1), TEXT_TO_SQL)
        self.assertEqual(router.route("what is my profit", user_id=1), TEXT_TO_SQL)
        self.assertEqual(router.route("when is mortality highest", user_id=1), TEXT_TO_SQL)

    def test_routes_conversation_without_calling_sql(self):
        router = ChikoozaQueryRouter()
        self.assertEqual(router.route("hello", user_id=1), CONVERSATION)
        self.assertEqual(router.route("okay thanks", user_id=1), CONVERSATION)
        self.assertEqual(router.route("nothing more", user_id=1), CONVERSATION)

    def test_blocks_cross_tenant_requests(self):
        router = ChikoozaQueryRouter()
        self.assertEqual(router.route("show another farmer data", user_id=1), BLOCKED)


class TenantSafeSQLExecutorTests(SimpleTestCase):
    def setUp(self):
        self.executor = TenantSafeSQLExecutor()

    def test_accepts_safe_tenant_scoped_select(self):
        plan = SQLPlan(
            sql="SELECT farm_name FROM ai_farm_flock_data_view WHERE owner_id = %s LIMIT 10",
            params=[7],
            metric="farm_list",
            result_type="table",
        )
        self.executor._validate(plan)

    def test_rejects_unsupported_table(self):
        plan = SQLPlan(
            sql="SELECT username FROM auth_user WHERE owner_id = %s",
            params=[7],
            metric="unsafe",
            result_type="table",
        )
        with self.assertRaises(ValueError):
            self.executor._validate(plan)

    def test_rejects_missing_owner_filter(self):
        plan = SQLPlan(
            sql="SELECT farm_name FROM ai_farm_flock_data_view LIMIT 10",
            params=[],
            metric="unsafe",
            result_type="table",
        )
        with self.assertRaises(ValueError):
            self.executor._validate(plan)

    def test_rejects_literal_owner_id(self):
        plan = SQLPlan(
            sql="SELECT farm_name FROM ai_farm_flock_data_view WHERE owner_id = 7",
            params=[],
            metric="unsafe",
            result_type="table",
        )
        with self.assertRaises(ValueError):
            self.executor._validate(plan)


class ModernAgentServiceTests(TestCase):
    def test_conversation_does_not_require_sql_service(self):
        user = User.objects.create_user(username="farmer@example.com", password="test")
        service = ChikoozaModernAgentService(user=user)

        response = service.query("hello")

        self.assertEqual(response["status"], "success")
        self.assertEqual(response["route"], CONVERSATION)
        self.assertIn("Chikooza farm records", response["answer"])
