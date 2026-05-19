from types import SimpleNamespace

from django.test import SimpleTestCase

from .modern_services import BLOCKED, ChikoozaQueryRouter, ChikoozaTextToSQLService


class ChikoozaModernAgentSecurityTests(SimpleTestCase):
    def setUp(self):
        self.user = SimpleNamespace(id=7)

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
