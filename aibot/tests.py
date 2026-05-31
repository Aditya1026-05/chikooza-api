from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from common.groq_client import GroqChatClient

from .intent_agent import ChikoozaIntentAgentService
from .intent_classifier import ChikoozaIntent, ChikoozaIntentClassifier
from .insight_service import ChikoozaFarmInsightService
from .llm_sql import (
    ChikoozaLLMTextToSQLService,
    ChikoozaSQLPromptBuilder,
    EntityResolution,
    OWNER_PARAM,
)
from .multi_report_service import ChikoozaMultiReportService
from .modern_services import (
    BLOCKED,
    CONVERSATION,
    HYBRID,
    RAG,
    SQLPlan,
    TEXT_TO_SQL,
    ChikoozaModernAgentService,
    ChikoozaQueryRouter,
    ChikoozaTextToSQLService,
    TenantSafeSQLExecutor,
)
from .views import AIChatViewSet


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

    def test_router_treats_greeting_as_conversation(self):
        router = ChikoozaQueryRouter()

        route = router.route("hello", user_id=7)
        casual_route = router.route("hello whats up", user_id=7)

        self.assertEqual(route, CONVERSATION)
        self.assertEqual(casual_route, CONVERSATION)

    def test_router_allows_conversational_farm_insight_questions(self):
        router = ChikoozaQueryRouter()

        route = router.route("how do you think my farm is progressing", user_id=7)

        self.assertEqual(route, TEXT_TO_SQL)

    def test_vague_total_things_maps_to_summary_plan(self):
        service = ChikoozaTextToSQLService(user=self.user)

        plan = service.build_plan("what is my total things i have")

        self.assertIsNotNone(plan)
        self.assertEqual(plan.metric, "farm_record_summary")
        self.assertEqual(plan.params, [7, 7, 7, 7, 7, 7, 7, 7, 7])

    def test_broad_all_data_questions_map_to_summary_plan(self):
        service = ChikoozaTextToSQLService(user=self.user)

        for question in (
            "show me all the data",
            "show me my all data",
            "show all records",
            "give me complete information",
        ):
            with self.subTest(question=question):
                plan = service.build_plan(question)

                self.assertIsNotNone(plan)
                self.assertEqual(plan.metric, "farm_record_summary")
                self.assertEqual(plan.params, [7, 7, 7, 7, 7, 7, 7, 7, 7])

    def test_farmer_stored_data_questions_map_to_safe_plans(self):
        service = ChikoozaTextToSQLService(user=self.user)
        cases = (
            ("how many farms do i have", "farm_count", "ai_farm_flock_data_view"),
            ("how many flocks", "flock_count", "ai_farm_flock_data_view"),
            ("total sales", "total_sales", "ai_sale_data_view"),
            ("my revenue", "total_sales", "ai_sale_data_view"),
            ("total purchases", "total_purchases", "ai_purchase_data_view"),
            ("medicine expenses", "total_purchases", "ai_purchase_data_view"),
            ("profit or loss", "profit_loss", "ai_sale_data_view"),
            ("current birds", "current_birds", "ai_dailydata_data_view"),
            ("birds died", "mortality", "ai_dailydata_data_view"),
            ("mortality", "mortality", "ai_dailydata_data_view"),
            ("feed consumed", "feed_consumed", "ai_dailydata_data_view"),
            ("average bird weight", "average_weight", "ai_dailydata_data_view"),
            ("average fcr", "fcr", "ai_dailydata_data_view"),
        )

        for question, metric, expected_view in cases:
            with self.subTest(question=question):
                plan = service.build_plan(question)

                self.assertIsNotNone(plan)
                self.assertEqual(plan.metric, metric)
                self.assertIn(expected_view, plan.sql)
                self.assertIn(7, plan.params)

    def test_current_birds_uses_latest_daily_record_per_flock(self):
        service = ChikoozaTextToSQLService(user=self.user)

        plan = service.build_plan("current birds")

        self.assertIsNotNone(plan)
        self.assertEqual(plan.metric, "current_birds")
        self.assertIn("MAX(compare_rows.record_date)", plan.sql)
        self.assertEqual(plan.sql.lower().count("owner_id = %s"), 2)
        self.assertEqual(plan.params, [7, 7])

    def test_birds_died_does_not_map_to_current_birds(self):
        service = ChikoozaTextToSQLService(user=self.user)

        plan = service.build_plan("how many birds died")

        self.assertIsNotNone(plan)
        self.assertEqual(plan.metric, "mortality")

    def test_list_farms_and_flocks_use_deterministic_plans(self):
        service = ChikoozaTextToSQLService(user=self.user)

        farm_plan = service.build_plan("list all farms i have")
        flock_plan = service.build_plan("list all the flocks i have")

        self.assertEqual(farm_plan.metric, "farm_list")
        self.assertEqual(farm_plan.params, [7])
        self.assertIn("ai_farm_flock_data_view", farm_plan.sql)
        self.assertEqual(flock_plan.metric, "flock_list")
        self.assertEqual(flock_plan.params, [7])
        self.assertIn("ai_farm_flock_data_view", flock_plan.sql)

    def test_entity_filters_resolve_to_owned_farm_and_flock_position(self):
        service = ChikoozaTextToSQLService(user=self.user)
        farm = SimpleNamespace(id=42, public_id=9001, name="Red Farm")
        flock = SimpleNamespace(
            id=77,
            public_id=5001,
            name="Alpha Batch",
            farm_id=42,
            farm=farm,
        )
        service._farms = lambda: [farm]
        service._flocks = lambda: [flock]

        farm_plan = service.build_plan("sales for farm 1")
        flock_plan = service.build_plan("profit for first flock")

        self.assertEqual(farm_plan.metric, "total_sales")
        self.assertEqual(farm_plan.params, [7, 42])
        self.assertEqual(flock_plan.metric, "profit_loss")
        self.assertIn(77, flock_plan.params)
        self.assertNotIn(1, flock_plan.params)

    def test_entity_filters_resolve_named_flocks(self):
        service = ChikoozaTextToSQLService(user=self.user)
        farm = SimpleNamespace(id=42, public_id=9001, name="Red Farm")
        flock = SimpleNamespace(
            id=77,
            public_id=5001,
            name="Alpha Batch",
            farm_id=42,
            farm=farm,
        )
        service._farms = lambda: [farm]
        service._flocks = lambda: [flock]

        plan = service.build_plan("feed consumed for Alpha Batch")

        self.assertEqual(plan.metric, "feed_consumed")
        self.assertEqual(plan.params, [7, 42, 77])

    def test_named_batch_from_another_account_returns_clarification(self):
        service = ChikoozaTextToSQLService(user=self.user)
        farm = SimpleNamespace(id=42, public_id=9001, name="Red Farm")
        flock = SimpleNamespace(
            id=77,
            public_id=5001,
            name="Alpha Batch",
            farm_id=42,
            farm=farm,
        )
        service._farms = lambda: [farm]
        service._flocks = lambda: [flock]

        response = service.answer("sales for Beta Private Batch")

        self.assertEqual(response["status"], "success")
        self.assertEqual(response["metric"], "missing_flock")
        self.assertIn("Alpha Batch", response["answer"])

    def test_named_farm_from_another_account_returns_clarification(self):
        service = ChikoozaTextToSQLService(user=self.user)
        farm = SimpleNamespace(id=42, public_id=9001, name="Red Farm")
        service._farms = lambda: [farm]
        service._flocks = lambda: []

        response = service.answer("sales for Blue Valley Farm")

        self.assertEqual(response["status"], "success")
        self.assertEqual(response["metric"], "missing_farm")
        self.assertIn("Red Farm", response["answer"])

    def test_missing_flock_reference_returns_clarification(self):
        service = ChikoozaTextToSQLService(user=self.user)
        farm = SimpleNamespace(id=42, public_id=9001, name="Red Farm")
        flock = SimpleNamespace(
            id=77,
            public_id=5001,
            name="Alpha Batch",
            farm_id=42,
            farm=farm,
        )
        service._farms = lambda: [farm]
        service._flocks = lambda: [flock]

        response = service.answer("profit for second flock")

        self.assertEqual(response["status"], "success")
        self.assertEqual(response["metric"], "missing_flock")
        self.assertIn("Alpha Batch", response["answer"])

    def test_followup_generic_flock_uses_only_owned_flock(self):
        service = ChikoozaTextToSQLService(user=self.user)
        farm = SimpleNamespace(id=42, public_id=9001, name="Red Farm")
        flock = SimpleNamespace(
            id=77,
            public_id=5001,
            name="Alpha Batch",
            farm_id=42,
            farm=farm,
        )
        service._farms = lambda: [farm]
        service._flocks = lambda: [flock]
        history = [
            {"role": "user", "content": "total number of flocks i have"},
            {"role": "assistant", "content": "Flock Count: 1."},
        ]

        plan = service.build_plan("i meant for the flock", history=history)

        self.assertEqual(plan.metric, "flock_list")
        self.assertEqual(plan.params, [7, 42, 77])

    def test_pronoun_data_followup_uses_recent_flock_context(self):
        service = ChikoozaTextToSQLService(user=self.user)
        farm = SimpleNamespace(id=42, public_id=9001, name="Red Farm")
        flock = SimpleNamespace(
            id=77,
            public_id=5001,
            name="Alpha Batch",
            farm_id=42,
            farm=farm,
        )
        service._farms = lambda: [farm]
        service._flocks = lambda: [flock]
        history = [
            {"role": "user", "content": "how many flocks i have"},
            {"role": "assistant", "content": "Flock Count: 1."},
        ]

        for question in (
            "what data does it have",
            "show me details about it",
            "what info does this one have",
        ):
            with self.subTest(question=question):
                plan = service.build_plan(question, history=history)

                self.assertEqual(plan.metric, "flock_list")
                self.assertEqual(plan.params, [7, 42, 77])

    def test_followup_generic_flock_uses_history_when_multiple_exist(self):
        service = ChikoozaTextToSQLService(user=self.user)
        red_farm = SimpleNamespace(id=42, public_id=9001, name="Red Farm")
        blue_farm = SimpleNamespace(id=43, public_id=9002, name="Blue Farm")
        alpha = SimpleNamespace(
            id=77,
            public_id=5001,
            name="Alpha Batch",
            farm_id=42,
            farm=red_farm,
        )
        beta = SimpleNamespace(
            id=78,
            public_id=5002,
            name="Beta Batch",
            farm_id=43,
            farm=blue_farm,
        )
        service._farms = lambda: [red_farm, blue_farm]
        service._flocks = lambda: [alpha, beta]
        history = [
            {"role": "user", "content": "show Beta Batch details"},
            {"role": "assistant", "content": "Your flocks:\n1. Beta Batch"},
        ]

        plan = service.build_plan("sales for the same flock", history=history)

        self.assertEqual(plan.metric, "total_sales")
        self.assertEqual(plan.params, [7, 43, 78])

    def test_followup_generic_flock_asks_clarification_when_ambiguous(self):
        service = ChikoozaTextToSQLService(user=self.user)
        red_farm = SimpleNamespace(id=42, public_id=9001, name="Red Farm")
        blue_farm = SimpleNamespace(id=43, public_id=9002, name="Blue Farm")
        service._farms = lambda: [red_farm, blue_farm]
        service._flocks = lambda: [
            SimpleNamespace(id=77, public_id=5001, name="Alpha Batch", farm_id=42),
            SimpleNamespace(id=78, public_id=5002, name="Beta Batch", farm_id=43),
        ]

        response = service.answer("i meant for the flock", history=[])

        self.assertEqual(response["status"], "success")
        self.assertEqual(response["metric"], "ambiguous_flock")
        self.assertIn("Which flock", response["answer"])

    def test_other_flock_followup_denies_when_only_one_exists(self):
        service = ChikoozaTextToSQLService(user=self.user)
        farm = SimpleNamespace(id=42, public_id=9001, name="Red Farm")
        flock = SimpleNamespace(
            id=77,
            public_id=5001,
            name="Alpha Batch",
            farm_id=42,
            farm=farm,
        )
        service._farms = lambda: [farm]
        service._flocks = lambda: [flock]
        history = [
            {"role": "user", "content": "show the data for that flock"},
            {"role": "assistant", "content": "Your flocks:\n1. Alpha Batch"},
        ]

        response = service.answer("any other flock i have or no?", history=history)

        self.assertEqual(response["status"], "success")
        self.assertEqual(response["metric"], "other_flocks")
        self.assertIn("only have one flock", response["answer"])
        self.assertIn("Alpha Batch", response["answer"])

    def test_more_or_remaining_followup_uses_history_entity_type(self):
        service = ChikoozaTextToSQLService(user=self.user)
        farm = SimpleNamespace(id=42, public_id=9001, name="Red Farm")
        flock = SimpleNamespace(
            id=77,
            public_id=5001,
            name="Alpha Batch",
            farm_id=42,
            farm=farm,
        )
        service._farms = lambda: [farm]
        service._flocks = lambda: [flock]
        history = [
            {"role": "user", "content": "show the data for that flock"},
            {"role": "assistant", "content": "Your flocks:\n1. Alpha Batch"},
        ]

        for question in ("anything else?", "do i have more?", "remaining ones?"):
            with self.subTest(question=question):
                response = service.answer(question, history=history)

                self.assertEqual(response["metric"], "other_flocks")
                self.assertIn("only have one flock", response["answer"])

    def test_other_followup_keeps_flock_context_when_answer_mentions_farm(self):
        service = ChikoozaTextToSQLService(user=self.user)
        farm = SimpleNamespace(id=42, public_id=9001, name="Red Farm")
        flock = SimpleNamespace(
            id=77,
            public_id=5001,
            name="Alpha Batch",
            farm_id=42,
            farm=farm,
        )
        service._farms = lambda: [farm]
        service._flocks = lambda: [flock]
        history = [
            {"role": "user", "content": "show the data for that flock"},
            {
                "role": "assistant",
                "content": "Your flocks:\n1. Alpha Batch (farm: Red Farm)",
            },
        ]

        response = service.answer("anything else?", history=history)

        self.assertEqual(response["metric"], "other_flocks")
        self.assertIn("only have one flock", response["answer"])

    def test_router_allows_vague_more_followups(self):
        router = ChikoozaQueryRouter()

        for question in ("do i have more?", "remaining ones?", "anything else?"):
            with self.subTest(question=question):
                self.assertEqual(router.route(question, user_id=7), TEXT_TO_SQL)

    def test_other_flock_followup_lists_remaining_flocks(self):
        service = ChikoozaTextToSQLService(user=self.user)
        red_farm = SimpleNamespace(id=42, public_id=9001, name="Red Farm")
        blue_farm = SimpleNamespace(id=43, public_id=9002, name="Blue Farm")
        alpha = SimpleNamespace(
            id=77,
            public_id=5001,
            name="Alpha Batch",
            farm_id=42,
            farm=red_farm,
            flock_size=100,
            actual_birds=95,
        )
        beta = SimpleNamespace(
            id=78,
            public_id=5002,
            name="Beta Batch",
            farm_id=43,
            farm=blue_farm,
            flock_size=200,
            actual_birds=190,
        )
        service._farms = lambda: [red_farm, blue_farm]
        service._flocks = lambda: [alpha, beta]
        history = [
            {"role": "user", "content": "show Alpha Batch details"},
            {"role": "assistant", "content": "Your flocks:\n1. Alpha Batch"},
        ]

        response = service.answer("any other flock i have?", history=history)

        self.assertEqual(response["status"], "success")
        self.assertEqual(response["metric"], "other_flocks")
        self.assertIn("Beta Batch", response["answer"])
        self.assertNotIn("Alpha Batch", response["answer"])

    def test_list_formatters_return_all_farm_and_flock_rows(self):
        service = ChikoozaTextToSQLService(user=self.user)

        farm_answer = service._format_answer(
            SQLPlan("SELECT", [7], "farm_list", "table"),
            [
                {
                    "farm_id": 42,
                    "farm_name": "Red Farm",
                    "farm_city": "Pune",
                    "farm_pin": "411001",
                    "shed_count": 3,
                    "farm_status": True,
                }
            ],
        )
        flock_answer = service._format_answer(
            SQLPlan("SELECT", [7], "flock_list", "table"),
            [
                {
                    "flock_id": 77,
                    "flock_name": "Alpha Batch",
                    "farm_name": "Red Farm",
                    "hatch_date": "2026-01-01",
                    "flock_size": 1000,
                    "actual_birds": 990,
                    "breed_name": "Broiler",
                }
            ],
        )

        self.assertIn("Red Farm", farm_answer)
        self.assertIn("3 sheds", farm_answer)
        self.assertIn("Alpha Batch", flock_answer)
        self.assertIn("actual birds: 990", flock_answer)

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

    def test_sql_executor_rejects_placeholder_mismatch(self):
        executor = TenantSafeSQLExecutor()
        plan = SQLPlan(
            sql="SELECT COUNT(*) AS result FROM ai_sale_data_view WHERE owner_id = %s",
            params=[],
            metric="bad_params",
            result_type="count",
        )

        with self.assertRaisesMessage(ValueError, "placeholder count"):
            executor._validate(plan)

    def test_sql_executor_rejects_literal_owner_filter(self):
        executor = TenantSafeSQLExecutor()
        plan = SQLPlan(
            sql="SELECT COUNT(*) AS result FROM ai_sale_data_view WHERE owner_id = 99",
            params=[],
            metric="bad_owner",
            result_type="count",
        )

        with self.assertRaisesMessage(ValueError, "Tenant filter"):
            executor._validate(plan)

    def test_agent_reports_rag_as_not_connected_yet(self):
        service = ChikoozaModernAgentService(user=self.user)

        response = service.query("recommend poultry practices")

        self.assertEqual(response["status"], "error")
        self.assertEqual(response["route"], RAG)

    def test_agent_answers_greeting_without_error(self):
        service = ChikoozaModernAgentService(user=self.user)

        response = service.query("hello")

        self.assertEqual(response["status"], "success")
        self.assertEqual(response["route"], CONVERSATION)
        self.assertIn("farm records", response["answer"])

    def test_summary_answer_is_not_reduced_to_feed_only(self):
        service = ChikoozaTextToSQLService(user=self.user)
        plan = service.build_plan("show me all the data")

        answer = service._format_answer(
            plan,
            {
                "farm_count": 1,
                "flock_count": 2,
                "current_birds": 95,
                "total_sales": 10000,
                "total_purchases": 2500,
                "total_feed_consumed": 120.5,
                "total_mortality": 5,
                "average_fcr": 1.65,
            },
        )

        self.assertIn("Your account summary", answer)
        self.assertIn("95 current birds", answer)
        self.assertIn("120.50 kg feed consumed", answer)

    def test_zero_summary_answer_guides_next_data_entry(self):
        service = ChikoozaTextToSQLService(user=self.user)
        plan = service.build_plan("show my farm summary")

        answer = service._format_answer(
            plan,
            {
                "farm_count": 1,
                "flock_count": 1,
                "current_birds": 0,
                "total_sales": 0,
                "total_purchases": 0,
                "total_feed_consumed": 0,
                "total_mortality": 0,
                "average_fcr": 0,
            },
        )

        self.assertIn("Your account summary", answer)
        self.assertIn("Next data to enter", answer)
        self.assertIn("Daily Data", answer)
        self.assertIn("Sales records", answer)
        self.assertIn("Purchase records", answer)

    def test_zero_sales_answer_explains_missing_sales_records(self):
        service = ChikoozaTextToSQLService(user=self.user)
        plan = SQLPlan(
            sql=(
                "SELECT COALESCE(SUM(sale_amount), 0) AS result "
                "FROM ai_sale_data_view WHERE owner_id = %s"
            ),
            params=[self.user.id],
            metric="total_sales",
            result_type="money",
        )

        answer = service._format_answer(plan, [{"result": 0}])

        self.assertIn("Total Sales: Rs. 0.00", answer)
        self.assertIn("No Sales records are saved", answer)
        self.assertIn("sale/lifting records", answer)

    def test_zero_feed_answer_guides_daily_data_entry(self):
        service = ChikoozaTextToSQLService(user=self.user)
        plan = SQLPlan(
            sql=(
                "SELECT COALESCE(SUM(feed_consumed_kg), 0) AS result "
                "FROM ai_dailydata_data_view WHERE owner_id = %s"
            ),
            params=[self.user.id],
            metric="feed_consumed",
            result_type="quantity",
        )

        answer = service._format_answer(plan, [{"result": 0}])

        self.assertIn("Total feed consumed: 0.00 kg", answer)
        self.assertIn("No feed consumption is recorded", answer)
        self.assertIn("Daily Data", answer)

    def test_zero_profit_answer_explains_missing_financial_records(self):
        service = ChikoozaTextToSQLService(user=self.user)
        plan = SQLPlan(
            sql=(
                "SELECT 0 AS total_sales, 0 AS total_purchases, "
                "0 AS flock_cost, 0 AS result"
            ),
            params=[],
            metric="profit_loss",
            result_type="money",
        )

        answer = service._format_answer(
            plan,
            [{"total_sales": 0, "total_purchases": 0, "flock_cost": 0, "result": 0}],
        )

        self.assertIn("Net result: Rs. 0.00", answer)
        self.assertIn("cannot judge profit confidently", answer)
        self.assertIn("Sales, Purchase, or flock-cost records", answer)

    def test_sales_query_supports_this_month_date_filter(self):
        service = ChikoozaTextToSQLService(user=self.user)

        with patch.object(
            ChikoozaTextToSQLService,
            "_today",
            return_value=date(2026, 5, 31),
        ):
            plan = service.build_plan("total sales this month")

        self.assertEqual(plan.metric, "total_sales")
        self.assertIn("sale_date >= %s", plan.sql)
        self.assertIn("sale_date <= %s", plan.sql)
        self.assertEqual(plan.params, [7, date(2026, 5, 1), date(2026, 5, 31)])
        self.assertEqual(plan.date_range.label, "this month")

    def test_daily_metric_query_supports_last_week_date_filter(self):
        service = ChikoozaTextToSQLService(user=self.user)

        with patch.object(
            ChikoozaTextToSQLService,
            "_today",
            return_value=date(2026, 5, 31),
        ):
            plan = service.build_plan("feed used last week")

        self.assertEqual(plan.metric, "feed_consumed")
        self.assertIn("record_date >= %s", plan.sql)
        self.assertIn("record_date <= %s", plan.sql)
        self.assertEqual(plan.params, [7, date(2026, 5, 18), date(2026, 5, 24)])
        self.assertEqual(plan.date_range.label, "last week")

    def test_mortality_query_supports_explicit_between_dates(self):
        service = ChikoozaTextToSQLService(user=self.user)

        plan = service.build_plan("mortality between 2026-01-01 and 2026-01-31")

        self.assertEqual(plan.metric, "mortality")
        self.assertIn("record_date >= %s", plan.sql)
        self.assertIn("record_date <= %s", plan.sql)
        self.assertEqual(plan.params, [7, date(2026, 1, 1), date(2026, 1, 31)])

    def test_profit_query_supports_month_name_with_flock_filter(self):
        service = ChikoozaTextToSQLService(user=self.user)
        farm = SimpleNamespace(id=42, public_id=9001, name="Red Farm")
        flock = SimpleNamespace(
            id=77,
            public_id=5001,
            name="Alpha Batch",
            farm_id=42,
            farm=farm,
        )
        service._farms = lambda: [farm]
        service._flocks = lambda: [flock]

        with patch.object(
            ChikoozaTextToSQLService,
            "_today",
            return_value=date(2026, 5, 31),
        ):
            plan = service.build_plan("profit for first flock in January")

        self.assertEqual(plan.metric, "profit_loss")
        self.assertIn("sale_date >= %s", plan.sql)
        self.assertIn("purchase_date >= %s", plan.sql)
        self.assertIn(date(2026, 1, 1), plan.params)
        self.assertIn(date(2026, 1, 31), plan.params)
        self.assertIn(42, plan.params)
        self.assertIn(77, plan.params)

    def test_current_birds_query_uses_latest_record_inside_date_range(self):
        service = ChikoozaTextToSQLService(user=self.user)

        with patch.object(
            ChikoozaTextToSQLService,
            "_today",
            return_value=date(2026, 5, 31),
        ):
            plan = service.build_plan("current birds this month")

        self.assertEqual(plan.metric, "current_birds")
        self.assertIn("current_rows.record_date >= %s", plan.sql)
        self.assertIn("compare_rows.record_date >= %s", plan.sql)
        self.assertEqual(
            plan.params,
            [7, date(2026, 5, 1), date(2026, 5, 31), 7, date(2026, 5, 1), date(2026, 5, 31)],
        )


class FakeGroqClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    @property
    def has_keys(self):
        return True

    def chat(self, messages, **kwargs):
        self.requests.append({"messages": messages, "kwargs": kwargs})
        content = self.responses.pop(0)
        return SimpleNamespace(content=content, model=kwargs.get("model", "fake-model"))


class FakeIntentClassifier:
    def __init__(self, intent):
        self.intent = intent
        self.calls = []

    def classify(self, question, history=None):
        self.calls.append({"question": question, "history": history})
        return self.intent


class FakeDeterministicSnapshotService:
    def __init__(self, user):
        self.user = user
        self.questions = []

    def answer(self, question, history=None):
        self.questions.append(question)
        if "summary" in question:
            return {
                "status": "success",
                "data": {
                    "farm_count": 1,
                    "flock_count": 1,
                    "current_birds": 0,
                    "total_sales": 1,
                    "total_purchases": 0,
                    "total_feed_consumed": 0,
                    "total_mortality": 0,
                    "average_fcr": 0,
                },
                "answer": (
                    "Your account summary: 1 farms, 1 flocks, 0 current birds, "
                    "Rs. 1.00 sales, Rs. 0.00 purchases, 0.00 kg feed consumed, "
                    "0 total mortality, and 0.00 average FCR."
                ),
                "message": "summary",
                "rows": [
                    {
                        "farm_count": 1,
                        "flock_count": 1,
                        "current_birds": 0,
                        "total_sales": 1,
                        "total_purchases": 0,
                        "total_feed_consumed": 0,
                        "total_mortality": 0,
                        "average_fcr": 0,
                    }
                ],
                "query": "SELECT summary",
                "params": [7],
                "route": TEXT_TO_SQL,
                "metric": "farm_record_summary",
            }
        if "profit" in question or "loss" in question:
            return {
                "status": "success",
                "data": {"result": 1},
                "answer": (
                    "Total sales: Rs. 1.00, total purchases: Rs. 0.00, "
                    "flock cost: Rs. 0.00. Net result: Rs. 1.00 (profit)."
                ),
                "message": "profit",
                "rows": [{"result": 1}],
                "query": "SELECT profit",
                "params": [7],
                "route": TEXT_TO_SQL,
                "metric": "profit_loss",
            }
        if "farms" in question:
            return {
                "status": "success",
                "data": [{"farm_name": "Test Farm"}],
                "answer": "Your farms:\n1. Test Farm (Pune, 411001), 1 sheds, active",
                "message": "farms",
                "rows": [{"farm_name": "Test Farm"}],
                "query": "SELECT farms",
                "params": [7],
                "route": TEXT_TO_SQL,
                "metric": "farm_list",
            }
        if "flocks" in question:
            return {
                "status": "success",
                "data": [{"flock_name": "Test Flock"}],
                "answer": "Your flocks:\n1. Test Flock (farm: Test Farm, size: 10)",
                "message": "flocks",
                "rows": [{"flock_name": "Test Flock"}],
                "query": "SELECT flocks",
                "params": [7],
                "route": TEXT_TO_SQL,
                "metric": "flock_list",
            }
        metric = "average_fcr" if "fcr" in question else "safe_metric"
        return {
            "status": "success",
            "data": {"result": 0},
            "answer": f"{question.title()}: 0.00.",
            "message": "metric",
            "rows": [{"result": 0}],
            "query": "SELECT metric",
            "params": [7],
            "route": TEXT_TO_SQL,
            "metric": metric,
        }

    def resolve_entity_filters(self, question, history=None):
        return SimpleNamespace(farm_id=None, flock_id=None, missing_response=None)


class FakeMultiReportExecutor:
    def execute(self, plan):
        if plan.metric == "farm_list":
            return [
                {
                    "farm_id": 42,
                    "farm_name": "Test Farm",
                    "farm_city": "Pune",
                    "farm_pin": "411001",
                    "shed_count": 2,
                    "farm_status": True,
                }
            ]
        if plan.metric == "flock_list":
            return [
                {
                    "flock_id": 77,
                    "flock_name": "Test Flock",
                    "farm_id": 42,
                    "farm_name": "Test Farm",
                    "hatch_date": "2026-01-01",
                    "flock_size": 100,
                    "actual_birds": 95,
                    "flock_status": True,
                    "breed_name": "Broiler",
                }
            ]
        if plan.metric == "profit_loss":
            return [
                {
                    "total_sales": 1000,
                    "total_purchases": 250,
                    "flock_cost": 100,
                    "result": 650,
                }
            ]
        if plan.metric == "farm_count":
            return [{"result": 1}]
        if plan.metric == "flock_count":
            return [{"result": 1}]
        if plan.metric == "total_sales":
            return [{"result": 1000}]
        if plan.metric == "total_purchases":
            return [{"result": 250}]
        if plan.metric == "current_birds":
            return [{"result": 95}]
        if plan.metric == "mortality":
            return [{"result": 5}]
        if plan.metric == "feed_consumed":
            return [{"result": 120.5}]
        if plan.metric in {"average_weight", "fcr"}:
            return [{"result": 1.6}]
        if plan.metric == "farm_record_summary":
            return [
                {
                    "farm_count": 1,
                    "flock_count": 1,
                    "current_birds": 95,
                    "total_sales": 1000,
                    "total_purchases": 250,
                    "total_feed_consumed": 120.5,
                    "total_mortality": 5,
                    "average_fcr": 1.6,
                }
            ]
        return [{"result": 0}]


class CapturingExecutor(FakeMultiReportExecutor):
    def __init__(self):
        self.plans = []

    def execute(self, plan):
        self.plans.append(plan)
        return super().execute(plan)


class FakeTrendExecutor(FakeMultiReportExecutor):
    def execute(self, plan):
        if plan.metric == "mortality_trend":
            return [
                {"period": "2026-05-01", "result": 1},
                {"period": "2026-05-02", "result": 3},
            ]
        if plan.metric == "best_flock_profit":
            return [
                {
                    "flock_id": 77,
                    "flock_name": "Alpha Batch",
                    "farm_name": "Red Farm",
                    "total_sales": 5000,
                    "total_purchases": 1000,
                    "flock_cost": 500,
                    "result": 3500,
                }
            ]
        return super().execute(plan)


class FakeScopedFarmExecutor(FakeMultiReportExecutor):
    def execute(self, plan):
        if plan.metric == "farm_list":
            rows = [
                {
                    "farm_id": 42,
                    "farm_name": "Red Farm",
                    "farm_city": "Pune",
                    "farm_pin": "411001",
                    "shed_count": 2,
                    "farm_status": True,
                },
                {
                    "farm_id": 43,
                    "farm_name": "Blue Farm",
                    "farm_city": "Nashik",
                    "farm_pin": "422001",
                    "shed_count": 3,
                    "farm_status": True,
                },
            ]
            if 42 in plan.params:
                return [rows[0]]
            if 43 in plan.params:
                return [rows[1]]
            return rows
        if plan.metric == "flock_list":
            rows = [
                {
                    "flock_id": 77,
                    "flock_name": "Alpha Batch",
                    "farm_id": 42,
                    "farm_name": "Red Farm",
                    "hatch_date": "2026-01-01",
                    "flock_size": 100,
                    "actual_birds": 95,
                    "flock_status": True,
                    "breed_name": "Broiler",
                },
                {
                    "flock_id": 78,
                    "flock_name": "Beta Batch",
                    "farm_id": 43,
                    "farm_name": "Blue Farm",
                    "hatch_date": "2026-02-01",
                    "flock_size": 200,
                    "actual_birds": 190,
                    "flock_status": True,
                    "breed_name": "Hubbard",
                },
            ]
            if 77 in plan.params:
                return [rows[0]]
            if 78 in plan.params:
                return [rows[1]]
            if 42 in plan.params:
                return [rows[0]]
            if 43 in plan.params:
                return [rows[1]]
            return rows
        return super().execute(plan)


class FakeEntityResolver:
    def __init__(self, resolution=None):
        self.resolution = resolution or EntityResolution(
            context="No fake entity context."
        )

    def resolve(self, question):
        return self.resolution


class ChikoozaLLMSQLServiceTests(SimpleTestCase):
    def setUp(self):
        self.user = SimpleNamespace(id=7, is_authenticated=True)

    def test_prompt_builder_includes_chikooza_views_and_history(self):
        builder = ChikoozaSQLPromptBuilder()

        messages = builder.messages(
            "what about that flock profit?",
            history=[
                {"role": "user", "content": "show flock A sales"},
                {"role": "assistant", "content": "Flock A sales are Rs. 10,000."},
            ],
            entity_context="Resolved flock mention: flock_id=4, flock_name=Flock A.",
        )

        self.assertIn("ai_sale_data_view", messages[0]["content"])
        self.assertIn("ai_farm_flock_data_view", messages[0]["content"])
        self.assertIn("Flock A sales", messages[1]["content"])
        self.assertIn("flock_id=4", messages[1]["content"])

    def test_llm_service_replaces_owner_token_with_authenticated_user(self):
        client = FakeGroqClient(
            [
                (
                    '{"sql": "SELECT COALESCE(SUM(sale_amount), 0) AS result '
                    'FROM ai_sale_data_view WHERE owner_id = %s", '
                    f'"params": ["{OWNER_PARAM}"], "metric": "total_sales", '
                    '"result_type": "money"}'
                ),
                "Your total sales are Rs. 12,500.",
            ]
        )
        service = ChikoozaLLMTextToSQLService(
            user=self.user,
            groq_client=client,
            entity_resolver=FakeEntityResolver(),
        )
        service.executor = SimpleNamespace(execute=lambda plan: [{"result": 12500}])

        result = service.answer("what are my total sales?")

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["params"], [7])
        self.assertEqual(result["answer"], "Your total sales are Rs. 12,500.")

    def test_llm_service_falls_back_when_sql_is_unsafe(self):
        client = FakeGroqClient(
            [
                (
                    '{"sql": "SELECT COUNT(*) AS result FROM auth_user", '
                    '"params": [], "metric": "bad", "result_type": "count"}'
                ),
                (
                    '{"sql": "SELECT COUNT(*) AS result FROM auth_user", '
                    '"params": [], "metric": "bad", "result_type": "count"}'
                ),
            ]
        )
        fallback = SimpleNamespace(
            answer=lambda question, history=None: {
                "status": "success",
                "data": 3,
                "answer": "Fallback answer.",
                "message": "Fallback answer.",
                "rows": [{"result": 3}],
                "query": "SELECT 3 AS result",
                "params": [],
                "route": TEXT_TO_SQL,
            }
        )
        service = ChikoozaLLMTextToSQLService(
            user=self.user,
            groq_client=client,
            fallback_service=fallback,
            entity_resolver=FakeEntityResolver(),
        )

        result = service.answer("how many farms?")

        self.assertEqual(result["engine"], "rule_based_fallback")
        self.assertEqual(result["answer"], "Fallback answer.")

    def test_llm_service_bypasses_groq_for_broad_summary_questions(self):
        client = FakeGroqClient(
            [
                (
                    '{"sql": "SELECT COALESCE(SUM(feed_consumed_kg), 0) AS '
                    "total_feed_consumed FROM ai_dailydata_data_view WHERE "
                    f'owner_id = %s", "params": ["{OWNER_PARAM}"], '
                    '"metric": "feed_consumed", "result_type": "quantity"}'
                )
            ]
        )
        fallback = SimpleNamespace(
            answer=lambda question, history=None: {
                "status": "success",
                "data": {"farm_count": 1},
                "answer": "Your account summary: 1 farms, 0 flocks.",
                "message": "Your account summary: 1 farms, 0 flocks.",
                "rows": [{"farm_count": 1}],
                "query": "SELECT summary",
                "params": [7],
                "route": TEXT_TO_SQL,
                "metric": "farm_record_summary",
            }
        )
        service = ChikoozaLLMTextToSQLService(
            user=self.user,
            groq_client=client,
            fallback_service=fallback,
            entity_resolver=FakeEntityResolver(),
        )

        result = service.answer("show me all the data")

        self.assertEqual(result["engine"], "rule_based_fallback")
        self.assertEqual(result["metric"], "farm_record_summary")
        self.assertEqual(client.requests, [])

    def test_llm_service_bypasses_groq_for_known_farm_data_questions(self):
        client = FakeGroqClient([])
        fallback = SimpleNamespace(
            answer=lambda question, history=None: {
                "status": "success",
                "data": [{"flock_name": "Alpha Batch"}],
                "answer": "Your flocks:\n1. Alpha Batch",
                "message": "Your flocks:\n1. Alpha Batch",
                "rows": [{"flock_name": "Alpha Batch"}],
                "query": "SELECT flock list",
                "params": [7],
                "route": TEXT_TO_SQL,
                "metric": "flock_list",
            }
        )
        service = ChikoozaLLMTextToSQLService(
            user=self.user,
            groq_client=client,
            fallback_service=fallback,
            entity_resolver=FakeEntityResolver(),
        )

        result = service.answer("list all the flocks i have")

        self.assertEqual(result["engine"], "rule_based_fallback")
        self.assertEqual(result["metric"], "flock_list")
        self.assertEqual(client.requests, [])

    def test_llm_deterministic_formatter_handles_summary_rows(self):
        service = ChikoozaLLMTextToSQLService(
            user=self.user,
            groq_client=FakeGroqClient([]),
            entity_resolver=FakeEntityResolver(),
        )

        answer = service._deterministic_metric_answer(
            [
                {
                    "farm_count": 1,
                    "flock_count": 2,
                    "current_birds": 95,
                    "total_sales": 10000,
                    "total_purchases": 2500,
                    "total_feed_consumed": 120.5,
                    "total_mortality": 5,
                    "average_fcr": 1.65,
                }
            ]
        )

        self.assertIn("Your account summary", answer)
        self.assertIn("95 current birds", answer)
        self.assertNotEqual(answer, "Total feed consumed: 120.50 kg.")

    def test_llm_deterministic_formatter_handles_missing_daily_rows(self):
        service = ChikoozaLLMTextToSQLService(
            user=self.user,
            groq_client=FakeGroqClient([]),
            entity_resolver=FakeEntityResolver(),
        )

        answer = service._deterministic_metric_answer(
            [
                {
                    "record_date": None,
                    "flock_name": "Test Flock",
                    "birds_died": None,
                    "total_mort": None,
                    "birds_current": None,
                }
            ]
        )

        self.assertIn("no daily data record", answer)
        self.assertNotIn("None", answer)

    def test_llm_service_returns_entity_clarification_before_llm(self):
        direct_response = {
            "status": "success",
            "answer": "I could not find that flock in your account.",
            "message": "I could not find that flock in your account.",
            "rows": [],
            "query": None,
            "params": [],
            "route": TEXT_TO_SQL,
            "engine": "entity_resolver",
        }
        client = FakeGroqClient([])
        service = ChikoozaLLMTextToSQLService(
            user=self.user,
            groq_client=client,
            entity_resolver=FakeEntityResolver(
                EntityResolution(context="", direct_response=direct_response)
            ),
        )

        result = service.answer("profit for flock 999")

        self.assertEqual(result["engine"], "entity_resolver")
        self.assertEqual(client.requests, [])


class GroqChatClientTests(SimpleTestCase):
    def test_groq_client_rotates_after_retryable_response(self):
        calls = []

        class FakeResponse:
            def __init__(self, status_code, content):
                self.status_code = status_code
                self._content = content
                self.request = SimpleNamespace()

            def raise_for_status(self):
                if self.status_code >= 400:
                    raise AssertionError(
                        "non-retryable status should not be raised here"
                    )

            def json(self):
                return {"choices": [{"message": {"content": self._content}}]}

        def fake_post(url, headers, json, timeout):
            calls.append(headers["Authorization"])
            if len(calls) == 1:
                return FakeResponse(429, "")
            return FakeResponse(200, "ok")

        client = GroqChatClient(api_keys=["first", "second"], fallback_model="")
        with patch("common.groq_client.httpx.post", side_effect=fake_post):
            result = client.chat([{"role": "user", "content": "hi"}])

        self.assertEqual(result.content, "ok")
        self.assertEqual(calls, ["Bearer first", "Bearer second"])


class ChikoozaIntentArchitectureTests(SimpleTestCase):
    def setUp(self):
        self.user = SimpleNamespace(id=7, is_authenticated=True)

    def test_rule_intent_classifier_detects_progress_insight(self):
        classifier = ChikoozaIntentClassifier(
            user=self.user,
            groq_client=FakeGroqClient([]),
        )

        intent = classifier.classify(
            "okay and now how do you think my farm is progressing"
        )

        self.assertEqual(intent.intent, "farm_progress_insight")
        self.assertEqual(intent.entity_type, "farm")

    def test_rule_intent_classifier_detects_capability_help(self):
        classifier = ChikoozaIntentClassifier(
            user=self.user,
            groq_client=FakeGroqClient([]),
        )

        intent = classifier.classify("what can you do for me?")

        self.assertEqual(intent.intent, "capability_help")

    def test_rule_intent_classifier_detects_multi_part_report(self):
        classifier = ChikoozaIntentClassifier(
            user=self.user,
            groq_client=FakeGroqClient([]),
        )

        intent = classifier.classify(
            "tell me how many farms and flocks i have, all sales, and inside each farm flock all their stuff individually"
        )

        self.assertEqual(intent.intent, "multi_farm_report")

    def test_rule_intent_classifier_routes_complete_data_to_multi_report(self):
        classifier = ChikoozaIntentClassifier(
            user=self.user,
            groq_client=FakeGroqClient([]),
        )

        for question in (
            "show me all the data",
            "show me my all data",
            "give complete report",
            "tell me everything",
        ):
            with self.subTest(question=question):
                intent = classifier.classify(question)

                self.assertEqual(intent.intent, "multi_farm_report")

        flock_intent = classifier.classify("complete report for first flock")
        farm_intent = classifier.classify("show all data for this farm")

        self.assertEqual(flock_intent.intent, "multi_farm_report")
        self.assertEqual(flock_intent.entity_type, "flock")
        self.assertEqual(flock_intent.entity_reference, "first")
        self.assertEqual(farm_intent.intent, "multi_farm_report")
        self.assertEqual(farm_intent.entity_type, "farm")
        self.assertEqual(farm_intent.entity_reference, "this")

    def test_rule_intent_classifier_detects_trend_comparison_and_best_flock(self):
        classifier = ChikoozaIntentClassifier(
            user=self.user,
            groq_client=FakeGroqClient([]),
        )

        comparison = classifier.classify("compare sales this month with last month")
        trend = classifier.classify("is mortality increasing")
        best = classifier.classify("which flock performed best")

        self.assertEqual(comparison.intent, "comparison_report")
        self.assertEqual(trend.intent, "trend_report")
        self.assertEqual(best.intent, "best_flock_report")
        self.assertEqual(best.entity_type, "flock")

    def test_rule_intent_classifier_uses_history_for_pronoun_detail(self):
        classifier = ChikoozaIntentClassifier(
            user=self.user,
            groq_client=FakeGroqClient([]),
        )
        history = [
            {"role": "user", "content": "how many flocks i have"},
            {"role": "assistant", "content": "Flock Count: 1."},
        ]

        intent = classifier.classify("what data does it have", history=history)

        self.assertEqual(intent.intent, "flock_details")
        self.assertEqual(intent.entity_type, "flock")
        self.assertEqual(intent.entity_reference, "it")

    def test_rule_intent_classifier_uses_history_for_other_followup(self):
        classifier = ChikoozaIntentClassifier(
            user=self.user,
            groq_client=FakeGroqClient([]),
        )
        history = [
            {"role": "assistant", "content": "Your flocks:\n1. Alpha Batch"},
        ]

        intent = classifier.classify("anything else?", history=history)

        self.assertEqual(intent.intent, "other_entity")
        self.assertEqual(intent.entity_type, "flock")
        self.assertEqual(intent.scope, "other")

    def test_intent_agent_uses_intent_before_safe_query_executor(self):
        deterministic = ChikoozaTextToSQLService(user=self.user)
        farm = SimpleNamespace(id=42, public_id=9001, name="Red Farm")
        flock = SimpleNamespace(
            id=77,
            public_id=5001,
            name="Alpha Batch",
            farm_id=42,
            farm=farm,
        )
        deterministic._farms = lambda: [farm]
        deterministic._flocks = lambda: [flock]
        deterministic.executor = SimpleNamespace(execute=lambda plan: [{"result": 12}])
        classifier = FakeIntentClassifier(
            ChikoozaIntent(
                intent="sales_total",
                entity_type="flock",
                entity_reference="first",
                source="test_intent",
            )
        )
        agent = ChikoozaIntentAgentService(
            user=self.user,
            deterministic_service=deterministic,
            classifier=classifier,
        )

        response = agent.answer("how much did this batch sell for?")

        self.assertEqual(response["intent"], "sales_total")
        self.assertEqual(response["intent_source"], "test_intent")
        self.assertEqual(response["metric"], "total_sales")
        self.assertEqual(response["params"], [7, 42, 77])
        self.assertIn("total sales for first flock", response["canonical_question"])

    def test_intent_agent_preserves_date_filter_for_single_metric_queries(self):
        deterministic = ChikoozaTextToSQLService(user=self.user)
        executor = CapturingExecutor()
        deterministic.executor = executor
        classifier = FakeIntentClassifier(
            ChikoozaIntent(intent="sales_total", source="test_intent")
        )
        agent = ChikoozaIntentAgentService(
            user=self.user,
            deterministic_service=deterministic,
            classifier=classifier,
        )

        with patch.object(
            ChikoozaTextToSQLService,
            "_today",
            return_value=date(2026, 5, 31),
        ):
            response = agent.answer("what are my total sales this month?")

        self.assertEqual(response["canonical_question"], "total sales this month")
        self.assertEqual(executor.plans[0].date_range.label, "this month")
        self.assertIn("for this month", response["answer"])

    def test_intent_agent_preserves_target_and_date_filter_together(self):
        deterministic = ChikoozaTextToSQLService(user=self.user)
        farm = SimpleNamespace(id=42, public_id=9001, name="Red Farm")
        flock = SimpleNamespace(
            id=77,
            public_id=5001,
            name="Alpha Batch",
            farm_id=42,
            farm=farm,
        )
        deterministic._farms = lambda: [farm]
        deterministic._flocks = lambda: [flock]
        executor = CapturingExecutor()
        deterministic.executor = executor
        classifier = FakeIntentClassifier(
            ChikoozaIntent(
                intent="feed_consumed",
                entity_type="flock",
                entity_reference="first",
                source="test_intent",
            )
        )
        agent = ChikoozaIntentAgentService(
            user=self.user,
            deterministic_service=deterministic,
            classifier=classifier,
        )

        with patch.object(
            ChikoozaTextToSQLService,
            "_today",
            return_value=date(2026, 5, 31),
        ):
            response = agent.answer("feed consumed by first flock last week")

        self.assertEqual(
            response["canonical_question"],
            "feed consumed for first flock last week",
        )
        self.assertEqual(executor.plans[0].date_range.label, "last week")
        self.assertEqual(executor.plans[0].params[:3], [7, 42, 77])

    def test_intent_agent_uses_safe_insight_for_conversational_progress(self):
        deterministic = FakeDeterministicSnapshotService(user=self.user)
        classifier = FakeIntentClassifier(
            ChikoozaIntent(
                intent="farm_progress_insight",
                entity_type="farm",
                source="test_intent",
            )
        )
        agent = ChikoozaIntentAgentService(
            user=self.user,
            deterministic_service=deterministic,
            classifier=classifier,
        )

        response = agent.answer("how do you think my farm is progressing?")

        self.assertEqual(response["intent"], "farm_progress_insight")
        self.assertEqual(response["metric"], "farm_progress_insight")
        self.assertEqual(response["query"], None)
        self.assertIn("cannot judge", response["answer"].lower())
        self.assertIn("daily data", response["answer"].lower())
        self.assertIn("show my account summary", deterministic.questions)

    def test_insight_service_can_use_groq_without_exposing_sql_authority(self):
        client = FakeGroqClient(["Your farm has too little daily data to judge yet."])
        deterministic = FakeDeterministicSnapshotService(user=self.user)
        user = SimpleNamespace(id=7, is_authenticated=True, _meta=True)
        deterministic.user = user
        service = ChikoozaFarmInsightService(
            user,
            deterministic_service=deterministic,
            groq_client=client,
        )

        response = service.answer("how am i doing?")

        self.assertEqual(response["engine"], "safe_insight_groq")
        self.assertEqual(
            response["answer"], "Your farm has too little daily data to judge yet."
        )
        prompt = client.requests[0]["messages"][1]["content"].lower()
        self.assertIn("safe farm snapshot", prompt)
        self.assertNotIn("create sql", prompt)

    def test_multi_report_service_answers_compound_account_and_breakdown_query(self):
        deterministic = ChikoozaTextToSQLService(user=self.user)
        deterministic.executor = FakeMultiReportExecutor()
        service = ChikoozaMultiReportService(deterministic)

        response = service.answer(
            "okay now tell me about how many flocks i have how many farms i have "
            "and all the sales. and then tell me about inside each of the farm,flock "
            "all their stuff individually"
        )

        self.assertEqual(response["status"], "success")
        self.assertEqual(response["metric"], "multi_farm_report")
        self.assertIn("Account totals", response["answer"])
        self.assertIn("Farm Count: 1", response["answer"])
        self.assertIn("Flock Count: 1", response["answer"])
        self.assertIn("Total Sales: Rs. 1,000.00", response["answer"])
        self.assertIn("Farm-wise details", response["answer"])
        self.assertIn("Flock-wise details", response["answer"])
        self.assertIn("Test Farm", response["answer"])
        self.assertIn("Test Flock", response["answer"])

    def test_multi_report_service_expands_complete_data_to_farms_and_flocks(self):
        deterministic = ChikoozaTextToSQLService(user=self.user)
        deterministic.executor = FakeMultiReportExecutor()
        service = ChikoozaMultiReportService(deterministic)

        response = service.answer("show me all the data")

        self.assertEqual(response["status"], "success")
        self.assertEqual(response["metric"], "multi_farm_report")
        self.assertIn("Account totals", response["answer"])
        self.assertIn("Farm-wise details", response["answer"])
        self.assertIn("Flock-wise details", response["answer"])
        self.assertIn("Test Farm", response["answer"])
        self.assertIn("Test Flock", response["answer"])

    def test_multi_report_service_applies_month_filter_to_complete_data(self):
        deterministic = ChikoozaTextToSQLService(user=self.user)
        deterministic.executor = FakeMultiReportExecutor()
        service = ChikoozaMultiReportService(deterministic)

        with patch.object(
            ChikoozaTextToSQLService,
            "_today",
            return_value=date(2026, 5, 31),
        ):
            response = service.answer("show all data for January")

        self.assertEqual(response["data"]["date_range"]["start"], "2026-01-01")
        self.assertEqual(response["data"]["date_range"]["end"], "2026-01-31")
        self.assertIn("for january 2026", response["answer"])

    def test_multi_report_service_scopes_complete_data_to_resolved_flock(self):
        deterministic = ChikoozaTextToSQLService(user=self.user)
        deterministic.executor = FakeMultiReportExecutor()
        service = ChikoozaMultiReportService(deterministic)

        response = service.answer(
            "complete report for first flock",
            intent=ChikoozaIntent(
                intent="multi_farm_report",
                entity_type="flock",
                entity_reference="first",
            ),
            entity_resolution=SimpleNamespace(farm_id=42, flock_id=77),
        )

        self.assertEqual(response["status"], "success")
        self.assertIn("Selected item", response["answer"])
        self.assertIn("Test Flock", response["answer"])
        self.assertNotIn("Account totals", response["answer"])
        self.assertNotIn("Farm-wise details", response["answer"])
        self.assertNotIn("Flock-wise details", response["answer"])
        self.assertEqual(response["data"]["target"][0]["details"]["flock_id"], 77)

    def test_multi_report_service_scopes_complete_data_to_resolved_farm(self):
        deterministic = ChikoozaTextToSQLService(user=self.user)
        deterministic.executor = FakeMultiReportExecutor()
        service = ChikoozaMultiReportService(deterministic)

        response = service.answer(
            "complete report for first farm",
            intent=ChikoozaIntent(
                intent="multi_farm_report",
                entity_type="farm",
                entity_reference="first",
            ),
            entity_resolution=SimpleNamespace(farm_id=42, flock_id=None),
        )

        self.assertEqual(response["status"], "success")
        self.assertIn("Selected item", response["answer"])
        self.assertIn("Test Farm", response["answer"])
        self.assertNotIn("Account totals", response["answer"])
        self.assertNotIn("Farm-wise details", response["answer"])
        self.assertNotIn("Flock-wise details", response["answer"])
        self.assertEqual(response["data"]["target"][0]["details"]["farm_id"], 42)

    def test_intent_agent_runs_multi_report_before_single_summary(self):
        deterministic = ChikoozaTextToSQLService(user=self.user)
        deterministic.executor = FakeMultiReportExecutor()
        agent = ChikoozaIntentAgentService(
            user=self.user,
            deterministic_service=deterministic,
        )

        response = agent.answer(
            "how many flocks i have, how many farms i have and all the sales inside each flock"
        )

        self.assertEqual(response["intent"], "multi_farm_report")
        self.assertEqual(response["metric"], "multi_farm_report")
        self.assertIn("Flock-wise details", response["answer"])

    def test_intent_agent_runs_complete_data_questions_as_multi_report(self):
        deterministic = ChikoozaTextToSQLService(user=self.user)
        deterministic.executor = FakeMultiReportExecutor()
        agent = ChikoozaIntentAgentService(
            user=self.user,
            deterministic_service=deterministic,
        )

        response = agent.answer("show me all the data")

        self.assertEqual(response["intent"], "multi_farm_report")
        self.assertEqual(response["metric"], "multi_farm_report")
        self.assertIn("Farm-wise details", response["answer"])
        self.assertIn("Flock-wise details", response["answer"])

    def test_intent_agent_scopes_complete_report_to_first_flock(self):
        deterministic = ChikoozaTextToSQLService(user=self.user)
        farm = SimpleNamespace(id=42, public_id=9001, name="Test Farm")
        flock = SimpleNamespace(
            id=77,
            public_id=5001,
            name="Test Flock",
            farm_id=42,
            farm=farm,
        )
        deterministic._farms = lambda: [farm]
        deterministic._flocks = lambda: [flock]
        deterministic.executor = FakeMultiReportExecutor()
        agent = ChikoozaIntentAgentService(
            user=self.user,
            deterministic_service=deterministic,
        )

        response = agent.answer("complete report for first flock")

        self.assertEqual(response["intent"], "multi_farm_report")
        self.assertEqual(response["metric"], "multi_farm_report")
        self.assertIn("Selected item", response["answer"])
        self.assertIn("Test Flock", response["answer"])
        self.assertNotIn("Account totals", response["answer"])
        self.assertNotIn("Farm-wise details", response["answer"])
        self.assertNotIn("Flock-wise details", response["answer"])

    def test_intent_agent_scopes_complete_report_to_named_farm(self):
        deterministic = ChikoozaTextToSQLService(user=self.user)
        farm = SimpleNamespace(id=42, public_id=9001, name="Test Farm")
        flock = SimpleNamespace(
            id=77,
            public_id=5001,
            name="Test Flock",
            farm_id=42,
            farm=farm,
        )
        deterministic._farms = lambda: [farm]
        deterministic._flocks = lambda: [flock]
        deterministic.executor = FakeMultiReportExecutor()
        agent = ChikoozaIntentAgentService(
            user=self.user,
            deterministic_service=deterministic,
        )

        response = agent.answer("everything inside Test Farm")

        self.assertEqual(response["intent"], "multi_farm_report")
        self.assertEqual(response["metric"], "multi_farm_report")
        self.assertIn("Selected item", response["answer"])
        self.assertIn("Test Farm", response["answer"])
        self.assertNotIn("Account totals", response["answer"])
        self.assertNotIn("Flock-wise details", response["answer"])

    def test_intent_agent_answers_month_comparison_report(self):
        deterministic = ChikoozaTextToSQLService(user=self.user)
        deterministic.executor = FakeTrendExecutor()
        agent = ChikoozaIntentAgentService(
            user=self.user,
            deterministic_service=deterministic,
        )

        with patch.object(
            ChikoozaTextToSQLService,
            "_today",
            return_value=date(2026, 5, 31),
        ):
            response = agent.answer("compare sales this month with last month")

        self.assertEqual(response["intent"], "comparison_report")
        self.assertEqual(response["metric"], "comparison_report")
        self.assertIn("this month vs last month", response["answer"])
        self.assertEqual(response["data"]["items"][0]["current_range"]["start"], "2026-05-01")
        self.assertEqual(response["data"]["items"][0]["previous_range"]["start"], "2026-04-01")

    def test_intent_agent_answers_mortality_trend_report(self):
        deterministic = ChikoozaTextToSQLService(user=self.user)
        deterministic.executor = FakeTrendExecutor()
        agent = ChikoozaIntentAgentService(
            user=self.user,
            deterministic_service=deterministic,
        )

        response = agent.answer("is mortality increasing")

        self.assertEqual(response["intent"], "trend_report")
        self.assertEqual(response["metric"], "trend_report")
        self.assertEqual(response["data"]["direction"], "increasing")
        self.assertIn("Mortality trend", response["answer"])

    def test_intent_agent_answers_best_flock_report(self):
        deterministic = ChikoozaTextToSQLService(user=self.user)
        deterministic.executor = FakeTrendExecutor()
        agent = ChikoozaIntentAgentService(
            user=self.user,
            deterministic_service=deterministic,
        )

        response = agent.answer("which flock performed best")

        self.assertEqual(response["intent"], "best_flock_report")
        self.assertEqual(response["metric"], "best_flock_report")
        self.assertIn("Alpha Batch", response["answer"])
        self.assertIn("Rs. 3,500.00", response["answer"])


class ChikoozaFarmerAIImprovementTests(SimpleTestCase):
    def setUp(self):
        self.user = SimpleNamespace(id=7, is_authenticated=True)
        self.red_farm = SimpleNamespace(id=42, public_id=9001, name="Red Farm")
        self.blue_farm = SimpleNamespace(id=43, public_id=9002, name="Blue Farm")
        self.alpha = SimpleNamespace(
            id=77,
            public_id=5001,
            name="Alpha Batch",
            farm_id=42,
            farm=self.red_farm,
        )
        self.beta = SimpleNamespace(
            id=78,
            public_id=5002,
            name="Beta Batch",
            farm_id=43,
            farm=self.blue_farm,
        )
        self.service = ChikoozaTextToSQLService(user=self.user)
        self.service._farms = lambda: [self.red_farm, self.blue_farm]
        self.service._flocks = lambda: [self.alpha, self.beta]

    def test_rough_english_query_types_map_to_safe_plans(self):
        cases = (
            ("how many farms i got", "farm_count"),
            ("how many batches are there", "flock_count"),
            ("money from sold birds", "total_sales"),
            ("what costs did i spend", "total_purchases"),
            ("chick cost", "flock_cost"),
            ("net earning", "profit_loss"),
            ("how many chickens are alive", "current_birds"),
            ("how many birds dead", "mortality"),
            ("how much feed used", "feed_consumed"),
            ("average bird weight", "average_weight"),
            ("feed conversion", "fcr"),
        )

        for question, metric in cases:
            with self.subTest(question=question):
                plan = self.service.build_plan(question)

                self.assertIsNotNone(plan)
                self.assertEqual(plan.metric, metric)
                self.assertIn(self.user.id, plan.params)

    def test_rule_classifier_keeps_this_month_as_time_not_farm_reference(self):
        classifier = ChikoozaIntentClassifier(
            user=self.user,
            groq_client=FakeGroqClient([]),
        )

        intent = classifier.classify("sales for Red Farm this month")

        self.assertEqual(intent.intent, "sales_total")
        self.assertEqual(intent.entity_type, "farm")
        self.assertEqual(intent.entity_reference, "")

    def test_last_one_followup_resolves_last_owned_flock(self):
        executor = CapturingExecutor()
        self.service.executor = executor
        history = [
            {
                "role": "assistant",
                "content": "Your flocks:\n1. Alpha Batch\n2. Beta Batch",
                "intent_entity_type": "flock",
            }
        ]
        agent = ChikoozaIntentAgentService(
            user=self.user,
            deterministic_service=self.service,
        )

        response = agent.answer("sales for last one", history=history)

        self.assertEqual(response["metric"], "total_sales")
        self.assertEqual(response["resolved_farm_id"], self.blue_farm.id)
        self.assertEqual(response["resolved_flock_id"], self.beta.id)
        self.assertEqual(executor.plans[0].params, [7, 43, 78])

    def test_that_flock_followup_uses_structured_metadata(self):
        executor = CapturingExecutor()
        self.service.executor = executor
        history = [
            {
                "role": "assistant",
                "content": "Your selected flock is Beta Batch.",
                "intent_entity_type": "flock",
                "resolved_farm_id": self.blue_farm.id,
                "resolved_flock_id": self.beta.id,
            }
        ]
        agent = ChikoozaIntentAgentService(
            user=self.user,
            deterministic_service=self.service,
        )

        response = agent.answer("what are sales for that flock", history=history)

        self.assertEqual(response["intent"], "sales_total")
        self.assertEqual(response["resolved_farm_id"], self.blue_farm.id)
        self.assertEqual(response["resolved_flock_id"], self.beta.id)
        self.assertEqual(executor.plans[0].params, [7, 43, 78])

    def test_second_farm_followup_lists_only_that_farms_flocks(self):
        deterministic = ChikoozaTextToSQLService(user=self.user)
        deterministic._farms = lambda: [self.red_farm, self.blue_farm]
        deterministic._flocks = lambda: [self.alpha, self.beta]
        deterministic.executor = FakeScopedFarmExecutor()
        agent = ChikoozaIntentAgentService(
            user=self.user,
            deterministic_service=deterministic,
        )
        history = [
            {"role": "user", "content": "all my farms"},
            {
                "role": "assistant",
                "content": "Your farms:\n1. Red Farm\n2. Blue Farm",
                "intent_entity_type": "farm",
                "metric": "farm_list",
            },
        ]

        response = agent.answer(
            "show flocks and all the stuff for 2nd one",
            history=history,
        )

        self.assertEqual(response["intent"], "multi_farm_report")
        self.assertEqual(response["intent_entity_type"], "farm")
        self.assertEqual(response["intent_entity_reference"], "second")
        self.assertEqual(response["resolved_farm_id"], self.blue_farm.id)
        self.assertIn("Blue Farm", response["answer"])
        self.assertIn("Beta Batch", response["answer"])
        self.assertNotIn("Alpha Batch", response["answer"])

    def test_same_farm_followup_uses_structured_history_metadata(self):
        history = [
            {
                "role": "assistant",
                "content": "Selected farm details.",
                "intent_entity_type": "farm",
                "resolved_farm_id": self.blue_farm.id,
            }
        ]

        plan = self.service.build_plan("sales for same farm", history=history)

        self.assertEqual(plan.metric, "total_sales")
        self.assertEqual(plan.params, [7, self.blue_farm.id])

    def test_multiple_names_in_previous_list_require_clarification(self):
        history = [
            {
                "role": "assistant",
                "content": "Your flocks:\n1. Alpha Batch\n2. Beta Batch",
            }
        ]

        response = self.service.answer("sales for that flock", history=history)

        self.assertEqual(response["metric"], "ambiguous_flock")
        self.assertIn("Which flock", response["answer"])

    def test_foreign_history_metadata_cannot_select_another_farmers_flock(self):
        history = [
            {
                "role": "assistant",
                "content": "Private Other Farmer Batch",
                "intent_entity_type": "flock",
                "resolved_flock_id": 999,
            }
        ]

        response = self.service.answer("sales for same flock", history=history)

        self.assertEqual(response["metric"], "ambiguous_flock")
        self.assertIn("Alpha Batch", response["answer"])
        self.assertIn("Beta Batch", response["answer"])
        self.assertNotIn("Private Other Farmer Batch", response["answer"])

    def test_conflicting_owned_farm_and_flock_ask_for_correction(self):
        response = self.service.answer("sales for Red Farm Beta Batch")

        self.assertEqual(response["metric"], "conflicting_farm_flock")
        self.assertIn("Beta Batch belongs to Blue Farm, not Red Farm", response["answer"])
        self.assertIsNone(response["query"])

    def test_specific_flock_question_with_no_flocks_has_natural_missing_answer(self):
        self.service._flocks = lambda: []

        response = self.service.answer("sales for that flock")

        self.assertEqual(response["metric"], "missing_flock")
        self.assertIn("Available flocks: none yet", response["answer"])

    def test_vague_followup_without_history_asks_scope_clarification(self):
        classifier = FakeIntentClassifier(
            ChikoozaIntent(intent="sales_total", source="test_intent")
        )
        agent = ChikoozaIntentAgentService(
            user=self.user,
            deterministic_service=self.service,
            classifier=classifier,
        )

        response = agent.answer("sales for that one", history=[])

        self.assertEqual(response["metric"], "ambiguous_scope")
        self.assertIn("do you mean a farm or a flock", response["answer"])

    def test_vague_data_request_asks_for_scope(self):
        agent = ChikoozaIntentAgentService(
            user=self.user,
            deterministic_service=self.service,
        )

        response = agent.answer("show me data", history=[])

        self.assertEqual(response["metric"], "ambiguous_scope")
        self.assertIn("whole account, a farm, or a flock", response["answer"])

    def test_foreign_numeric_flock_id_is_not_used(self):
        response = self.service.answer("sales for flock id 999")

        self.assertEqual(response["metric"], "missing_flock")
        self.assertIn("Available flocks", response["answer"])
        self.assertNotIn("999", str(response.get("params")))
        self.assertIsNone(response["query"])

    def test_missing_flock_answer_explains_next_step_naturally(self):
        self.service._flocks = lambda: []

        response = self.service.answer("profit for that flock")

        self.assertEqual(response["metric"], "missing_flock")
        self.assertIn("no flocks are saved", response["answer"].lower())
        self.assertIn("Available flocks: none yet", response["answer"])
        self.assertIn("add a flock", response["answer"].lower())

    def test_farm_summary_does_not_shorten_previous_greeting(self):
        deterministic = ChikoozaTextToSQLService(user=self.user)
        deterministic.executor = FakeMultiReportExecutor()
        agent = ChikoozaModernAgentService(user=self.user)
        agent.sql_service = ChikoozaIntentAgentService(
            user=self.user,
            deterministic_service=deterministic,
        )
        history = [
            {"role": "user", "content": "hello"},
            {
                "role": "assistant",
                "content": (
                    "Hello. I can help with your own Chikooza farm records."
                ),
                "metric": "conversation",
            },
        ]

        response = agent.query("show me my farm summary", history=history)

        self.assertEqual(response["metric"], "farm_record_summary")
        self.assertIn("Your account summary", response["answer"])
        self.assertNotIn("Short version", response["answer"])

    def test_detail_followup_after_account_summary_expands_full_report(self):
        deterministic = ChikoozaTextToSQLService(user=self.user)
        deterministic._farms = lambda: [self.red_farm, self.blue_farm]
        deterministic._flocks = lambda: [self.alpha, self.beta]
        deterministic.executor = FakeScopedFarmExecutor()
        agent = ChikoozaIntentAgentService(
            user=self.user,
            deterministic_service=deterministic,
        )
        history = [
            {"role": "user", "content": "show me my farm summary"},
            {
                "role": "assistant",
                "content": (
                    "Your account summary: 2 farms, 2 flocks, 285 current birds, "
                    "Rs. 1,000.00 sales, Rs. 250.00 purchases."
                ),
                "intent": "farm_summary",
                "metric": "farm_record_summary",
            },
        ]

        response = agent.answer("now tell this in detail", history=history)

        self.assertEqual(response["intent"], "multi_farm_report")
        self.assertEqual(response["intent_source"], "rule_summary_detail_followup")
        self.assertIn("Farm-wise details", response["answer"])
        self.assertIn("Flock-wise details", response["answer"])
        self.assertIn("Red Farm", response["answer"])
        self.assertIn("Blue Farm", response["answer"])
        self.assertIn("Alpha Batch", response["answer"])
        self.assertIn("Beta Batch", response["answer"])

    def test_detail_followup_after_full_report_stays_account_scoped(self):
        deterministic = ChikoozaTextToSQLService(user=self.user)
        deterministic._farms = lambda: [self.red_farm, self.blue_farm]
        deterministic._flocks = lambda: [self.alpha, self.beta]
        deterministic.executor = FakeScopedFarmExecutor()
        agent = ChikoozaIntentAgentService(
            user=self.user,
            deterministic_service=deterministic,
        )
        history = [
            {"role": "user", "content": "show me all my farm data"},
            {
                "role": "assistant",
                "content": "Here is the combined report from your Chikooza records.",
                "intent": "multi_farm_report",
                "metric": "multi_farm_report",
            },
        ]

        response = agent.answer("now in detail", history=history)

        self.assertEqual(response["intent"], "multi_farm_report")
        self.assertNotEqual(response["metric"], "ambiguous_farm")
        self.assertIn("Farm-wise details", response["answer"])
        self.assertIn("Flock-wise details", response["answer"])

    def test_all_my_farm_data_routes_to_full_report_not_farm_list(self):
        deterministic = ChikoozaTextToSQLService(user=self.user)
        deterministic._farms = lambda: [self.red_farm, self.blue_farm]
        deterministic._flocks = lambda: [self.alpha, self.beta]
        deterministic.executor = FakeScopedFarmExecutor()
        agent = ChikoozaIntentAgentService(
            user=self.user,
            deterministic_service=deterministic,
        )

        response = agent.answer("show me all my farm data")

        self.assertEqual(response["intent"], "multi_farm_report")
        self.assertIn("Account totals", response["answer"])
        self.assertIn("Farm-wise details", response["answer"])
        self.assertIn("Flock-wise details", response["answer"])

    def test_species_question_uses_field_lookup_not_broad_flock_list(self):
        deterministic = ChikoozaTextToSQLService(user=self.user)
        deterministic._farms = lambda: [self.red_farm, self.blue_farm]
        deterministic._flocks = lambda: [self.alpha, self.beta]
        deterministic.executor = FakeScopedFarmExecutor()
        agent = ChikoozaIntentAgentService(
            user=self.user,
            deterministic_service=deterministic,
        )

        response = agent.answer("okay now what is species in my flock 1")

        self.assertEqual(response["intent"], "field_lookup")
        self.assertEqual(response["metric"], "flock_breed_name")
        self.assertEqual(response["resolved_flock_id"], self.alpha.id)
        self.assertIn("Breed/species for Alpha Batch: Broiler", response["answer"])
        self.assertNotIn("Your flocks:", response["answer"])

    def test_broad_farm_progress_stays_account_scoped(self):
        deterministic = FakeDeterministicSnapshotService(user=self.user)
        agent = ChikoozaIntentAgentService(
            user=self.user,
            deterministic_service=deterministic,
        )
        history = [
            {"role": "user", "content": "show me all my farm data"},
            {
                "role": "assistant",
                "content": "Here is the combined report from your Chikooza records.",
                "intent": "multi_farm_report",
                "metric": "multi_farm_report",
            },
        ]

        response = agent.answer("now how is the farm doing", history=history)

        self.assertEqual(response["intent"], "farm_progress_insight")
        self.assertEqual(response["metric"], "farm_progress_insight")
        self.assertNotIn("for the farm", " ".join(deterministic.questions))
        self.assertNotIn("which farm do you mean", response["answer"].lower())
        self.assertIn("your farm", response["answer"].lower())

    def test_insight_zero_detector_does_not_flag_nonzero_decimals(self):
        service = ChikoozaFarmInsightService(
            self.user,
            deterministic_service=FakeDeterministicSnapshotService(self.user),
        )

        self.assertFalse(service._looks_zero("Total feed consumed: 254.00 kg."))
        self.assertFalse(service._looks_zero("Fcr: 0.96."))
        self.assertTrue(service._looks_zero("Fcr: 0.00."))

    def test_calculated_answers_explain_their_source(self):
        cases = (
            (
                SQLPlan("SELECT", [], "profit_loss", "money"),
                [{"total_sales": 1000, "total_purchases": 250, "flock_cost": 100, "result": 650}],
                "net result = recorded sales - recorded purchases - flock cost",
            ),
            (
                SQLPlan("SELECT", [], "current_birds", "count"),
                [{"result": 95}],
                "latest saved Daily Data current-bird count",
            ),
            (
                SQLPlan("SELECT", [], "mortality", "count"),
                [{"result": 5}],
                "adds the birds recorded as mortality",
            ),
            (
                SQLPlan("SELECT", [], "fcr", "decimal"),
                [{"result": 1.65}],
                "average of the saved daily FCR values",
            ),
        )

        for plan, rows, expected_text in cases:
            with self.subTest(metric=plan.metric):
                answer = self.service._format_answer(plan, rows)

                self.assertIn("Calculation:", answer)
                self.assertIn(expected_text, answer)

    def test_recent_history_keeps_safe_resolution_metadata(self):
        logs = [
            SimpleNamespace(
                query="sales for Beta Batch",
                response=(
                    '{"answer": "Total Sales: Rs. 1,000.00.", '
                    '"resolved_farm_id": 43, "resolved_flock_id": 78, '
                    '"intent_entity_type": "flock", "metric": "total_sales"}'
                ),
            )
        ]

        class FakeLogs(list):
            def order_by(self, *_args):
                return self

        view = AIChatViewSet.__new__(AIChatViewSet)
        with patch.dict("os.environ", {"AIBOT_HISTORY_TURNS": "not-a-number"}):
            with patch(
                "aibot.views.AIChatLog.objects.filter",
                return_value=FakeLogs(logs),
            ):
                history = view._recent_history(self.user)

        self.assertEqual(history[1]["resolved_farm_id"], 43)
        self.assertEqual(history[1]["resolved_flock_id"], 78)
        self.assertEqual(history[1]["intent_entity_type"], "flock")
