from types import SimpleNamespace

from django.test import SimpleTestCase

from .modern_services import (
    BLOCKED,
    HYBRID,
    RAG,
    SQLPlan,
    ChikoozaModernAgentService,
    ChikoozaQueryRouter,
    ChikoozaTextToSQLService,
    TenantSafeSQLExecutor,
)


class ChikoozaModernAgentSecurityTests(SimpleTestCase):
    def setUp(self):
        self.user = SimpleNamespace(id=7, is_authenticated=True)

    def test_sql_plan_uses_authenticated_user_filter(self):
        service = ChikoozaTextToSQLService(user=self.user)

        plan = service.build_plan("total sales farm 1 flock 2")

        self.assertIsNotNone(plan)
        self.assertIn("owner_id = %s", plan.sql)
        self.assertEqual(plan.params, [7, 1, 2])

    def test_profit_plan_filters_each_subquery_by_authenticated_user(self):
        service = ChikoozaTextToSQLService(user=self.user)

        plan = service.build_plan("profit farm 1")

        self.assertIsNotNone(plan)
        self.assertEqual(plan.sql.lower().count("owner_id = %s"), 6)
        self.assertTrue(all(param == 7 or param == 1 for param in plan.params))

    def test_router_blocks_other_user_requests(self):
        router = ChikoozaQueryRouter()

        route = router.route("show sales for user 99", user_id=7)

        self.assertEqual(route, BLOCKED)

    def test_router_blocks_destructive_requests(self):
        router = ChikoozaQueryRouter()

        route = router.route("drop table sales", user_id=7)

        self.assertEqual(route, BLOCKED)

    def test_router_identifies_rag_and_hybrid_requests(self):
        router = ChikoozaQueryRouter()

        rag_route = router.route("recommend poultry practices", user_id=7)
        hybrid_route = router.route("summarize my sales trends", user_id=7)

        self.assertEqual(rag_route, RAG)
        self.assertEqual(hybrid_route, HYBRID)

    def test_sql_executor_rejects_missing_tenant_filter(self):
        executor = TenantSafeSQLExecutor()
        plan = SQLPlan(
            sql="SELECT COUNT(*) AS result FROM ai_sale_data_view",
            params=[],
            metric="bad_count",
            result_type="count",
        )

        with self.assertRaisesMessage(ValueError, "Tenant filter is missing"):
            executor._validate(plan)

    def test_sql_executor_rejects_non_select_sql(self):
        executor = TenantSafeSQLExecutor()
        plan = SQLPlan(
            sql="UPDATE ai_sale_data_view SET sale_amount = 0 WHERE owner_id = %s",
            params=[self.user.id],
            metric="bad_update",
            result_type="money",
        )

        with self.assertRaisesMessage(ValueError, "Only SELECT queries are allowed"):
            executor._validate(plan)

    def test_sql_executor_rejects_mixed_unsafe_sources(self):
        executor = TenantSafeSQLExecutor()
        plan = SQLPlan(
            sql=(
                "SELECT COUNT(*) AS result FROM ai_sale_data_view "
                "JOIN auth_user ON auth_user.id = ai_sale_data_view.owner_id "
                "WHERE owner_id = %s"
            ),
            params=[self.user.id],
            metric="bad_source",
            result_type="count",
        )

        with self.assertRaisesMessage(ValueError, "unsupported data source"):
            executor._validate(plan)

    def test_agent_reports_rag_as_not_connected_yet(self):
        service = ChikoozaModernAgentService(user=self.user)

        response = service.query("recommend poultry practices")

        self.assertEqual(response["status"], "error")
        self.assertEqual(response["route"], RAG)
