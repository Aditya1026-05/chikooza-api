from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from common.groq_client import GroqChatClient

from .intent_agent import ChikoozaIntentAgentService
from .intent_classifier import ChikoozaIntent, ChikoozaIntentClassifier
from .insight_service import ChikoozaFarmInsightService
from .llm_sql import (
    AIBOT_SQL_DEFAULT_MODEL,
    ChikoozaEntityResolver,
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
    normalize_ai_query,
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

    def test_router_treats_closing_phrases_as_conversation(self):
        router = ChikoozaQueryRouter()

        for question in ("okay thanks", "nothing more", "no more", "huh?"):
            with self.subTest(question=question):
                self.assertEqual(router.route(question, user_id=7), CONVERSATION)

    def test_query_normalizer_corrects_common_farmer_typos(self):
        self.assertEqual(
            normalize_ai_query("breed of the first glock"),
            "breed of the first flock",
        )

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
        content = self.responses.pop(0) if self.responses else "ok."
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

    def resolve(self, question, history=None, active_context=None):
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
        # U: 'what are my total sales?' now hits the deterministic _sales_total_plan
        # U: shortcut instead of the LLM, so the Groq client is never called.
        # U: The owner_id is still the authenticated user (7) and result is correct.
        service = ChikoozaLLMTextToSQLService(
            user=self.user,
            groq_client=FakeGroqClient(["Your total sales are Rs. 12,500."]),
            entity_resolver=FakeEntityResolver(),
        )
        service.executor = SimpleNamespace(
            execute=lambda plan: [{"total_sales": 12500, "sale_count": 3}]
        )

        result = service.answer("what are my total sales?")

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["metric"], "total_sales")
        self.assertEqual(result["params"], [7])
        self.assertIn("owner_id = %s", result["query"])

    def test_llm_service_uses_8b_model_for_sql_and_answer_formatting(self):
        # U: 'what are my total sales?' is now handled deterministically (no SQL LLM call).
        # U: The answer-formatting step still uses the LLM, so exactly 1 Groq request.
        client = FakeGroqClient(["Your total sales are Rs. 12,500."])
        service = ChikoozaLLMTextToSQLService(
            user=self.user,
            groq_client=client,
            entity_resolver=FakeEntityResolver(),
        )
        service.executor = SimpleNamespace(
            execute=lambda plan: [{"total_sales": 12500, "sale_count": 3}]
        )

        with patch.dict(
            "os.environ",
            {
                "AIBOT_SQL_MODEL": AIBOT_SQL_DEFAULT_MODEL,
                "AIBOT_SQL_FALLBACK_MODEL": AIBOT_SQL_DEFAULT_MODEL,
                "AIBOT_SQL_ANSWER_MODEL": AIBOT_SQL_DEFAULT_MODEL,
            },
            clear=False,
        ):
            result = service.answer("what are my total sales?")

        self.assertEqual(result["status"], "success")
        # Deterministic plan: only 1 Groq call (answer formatting), not 2.
        self.assertEqual(len(client.requests), 1)
        self.assertEqual(client.requests[0]["kwargs"]["model"], "llama-3.1-8b-instant")


    def test_llm_service_repairs_owner_only_missing_params_from_8b(self):
        client = FakeGroqClient(
            [
                (
                    '{"sql": "SELECT '
                    '(SELECT COUNT(DISTINCT farm_id) FROM ai_farm_flock_data_view WHERE owner_id = %s) AS farm_count, '
                    '(SELECT COUNT(DISTINCT flock_id) FROM ai_farm_flock_data_view WHERE owner_id = %s) AS flock_count", '
                    f'"params": ["{OWNER_PARAM}"], '
                    '"metric": "farm_record_summary", "result_type": "summary"}'
                ),
                "You have 1 farm and 2 flocks.",
            ]
        )
        service = ChikoozaLLMTextToSQLService(
            user=self.user,
            groq_client=client,
            entity_resolver=FakeEntityResolver(),
        )

        def execute(plan):
            self.assertEqual(plan.params, [7, 7])
            return [{"farm_count": 1, "flock_count": 2}]

        service.executor = SimpleNamespace(execute=execute)

        result = service.answer("show my farm summary")

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["metric"], "farm_record_summary")

    def test_llm_service_handles_conversation_without_sql_planning(self):
        client = FakeGroqClient([])
        service = ChikoozaLLMTextToSQLService(
            user=self.user,
            groq_client=client,
            entity_resolver=FakeEntityResolver(),
        )

        result = service.answer("nothing more")

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["metric"], "conversation_only")
        self.assertEqual(client.requests, [])

    def test_llm_service_returns_error_when_sql_is_unsafe_without_rule_fallback(self):
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
        service = ChikoozaLLMTextToSQLService(
            user=self.user,
            groq_client=client,
            entity_resolver=FakeEntityResolver(),
        )

        result = service.answer("how many farms?")

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["engine"], "groq_sql")
        self.assertIn("using your farm records", result["message"])

    def test_llm_service_uses_groq_sql_for_broad_summary_questions(self):
        client = FakeGroqClient(
            [
                (
                    '{"sql": "SELECT (SELECT COUNT(DISTINCT farm_id) FROM '
                    'ai_farm_flock_data_view WHERE owner_id = %s AND farm_id IS NOT NULL) '
                    'AS farm_count", '
                    f'"params": ["{OWNER_PARAM}"], '
                    '"metric": "farm_record_summary", "result_type": "summary"}'
                ),
                "You have 1 farm saved.",
            ]
        )
        service = ChikoozaLLMTextToSQLService(
            user=self.user,
            groq_client=client,
            entity_resolver=FakeEntityResolver(),
        )
        service.executor = SimpleNamespace(execute=lambda plan: [{"farm_count": 1}])

        result = service.answer("show me all the data")

        self.assertEqual(result["engine"], "groq_sql")
        self.assertEqual(result["metric"], "farm_record_summary")
        self.assertEqual(result["answer"], "You have 1 farm saved.")
        self.assertEqual(len(client.requests), 2)

    def test_llm_service_uses_groq_sql_for_known_farm_data_questions(self):
        # U: 'list all the flocks i have' now hits the deterministic _flock_list_plan_llm
        # U: shortcut instead of the LLM SQL planner. The answer-formatting LLM call
        # U: still fires (1 request total, not 2).
        client = FakeGroqClient(["Your flocks:\n- Alpha Batch"])
        service = ChikoozaLLMTextToSQLService(
            user=self.user,
            groq_client=client,
            entity_resolver=FakeEntityResolver(),
        )
        service.executor = SimpleNamespace(
            execute=lambda plan: [{"flock_id": 77, "flock_name": "Alpha Batch"}]
        )

        result = service.answer("list all the flocks i have")

        # Deterministic plan route: no SQL LLM call, only answer formatting.
        self.assertEqual(result["metric"], "flock_list")
        self.assertEqual(result["engine"], "groq_sql")
        # 1 Groq request for answer formatting (not 2 since SQL is deterministic).
        self.assertEqual(len(client.requests), 1)


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

    def test_llm_entity_resolver_adds_last_referenced_flock_context(self):
        farm = SimpleNamespace(id=42, public_id=9001, name="Red Farm")
        flock = SimpleNamespace(
            id=77,
            public_id=5001,
            name="Alpha Batch",
            farm=farm,
        )
        resolver = ChikoozaEntityResolver(self.user)
        resolver._farms = lambda: [farm]
        resolver._flocks = lambda: [flock]

        result = resolver.resolve(
            "i meant daily data and everything",
            history=[
                {
                    "role": "assistant",
                    "content": "Your flocks:\n1. Alpha Batch",
                    "resolved_farm_id": 42,
                    "resolved_flock_id": 77,
                }
            ],
        )

        self.assertIn("Last referenced flock from recent chat", result.context)
        self.assertIn("flock_id=77", result.context)

    def test_llm_entity_resolver_uses_active_flock_context(self):
        farm = SimpleNamespace(id=42, public_id=9001, name="Red Farm")
        flock = SimpleNamespace(
            id=77,
            public_id=5001,
            name="Alpha Batch",
            farm=farm,
        )
        resolver = ChikoozaEntityResolver(self.user)
        resolver._farms = lambda: [farm]
        resolver._flocks = lambda: [flock]

        result = resolver.resolve(
            "breed of the active flock",
            active_context={
                "selected_farm_public_id": "9001",
                "selected_flock_public_id": "5001",
            },
        )

        self.assertIn("Active app flock context", result.context)
        self.assertIn("Resolved flock mention", result.context)
        self.assertIn("flock_id=77", result.context)

    def test_llm_service_passes_active_context_to_entity_resolver(self):
        class CapturingEntityResolver(FakeEntityResolver):
            def __init__(self):
                super().__init__()
                self.active_context = None

            def resolve(self, question, history=None, active_context=None):
                self.active_context = active_context
                return self.resolution

        resolver = CapturingEntityResolver()
        client = FakeGroqClient(
            [
                (
                    '{"sql": "SELECT flock_name, breed_name FROM ai_farm_flock_data_view '
                    'WHERE owner_id = %s AND flock_id = %s LIMIT 1", '
                    f'"params": ["{OWNER_PARAM}", 77], '
                    '"metric": "flock_breed", "result_type": "summary"}'
                ),
                "Alpha Batch is Hubbard.",
            ]
        )
        service = ChikoozaLLMTextToSQLService(
            user=self.user,
            groq_client=client,
            entity_resolver=resolver,
        )
        service.executor = SimpleNamespace(
            execute=lambda plan: [{"flock_name": "Alpha Batch", "breed_name": "Hubbard"}]
        )

        result = service.answer(
            "breed of the active flock",
            active_context={"selected_flock_public_id": "5001"},
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(resolver.active_context, {"selected_flock_public_id": "5001"})

    def test_llm_service_uses_last_flock_context_for_daily_data_followup(self):
        client = FakeGroqClient(
            [
                "Alpha Batch daily data: 3 birds died, 622 current birds, 127 kg feed, FCR 0.96.",
            ]
        )
        service = ChikoozaLLMTextToSQLService(
            user=self.user,
            groq_client=client,
            entity_resolver=FakeEntityResolver(
                EntityResolution(
                    context=(
                        "Available flocks for this farmer: 1. flock_id=77, "
                        "flock_public_id=5001, flock_name=Alpha Batch, farm_name=Red Farm.\n"
                        "Last referenced flock from recent chat: flock_id=77, "
                        "flock_public_id=5001, flock_name=Alpha Batch, farm_id=42, farm_name=Red Farm."
                    )
                )
            ),
        )
        service.executor = SimpleNamespace(
            execute=lambda plan: [
                {
                    "record_date": "2026-05-31",
                    "flock_id": 77,
                    "flock_name": "Alpha Batch",
                    "birds_died": 3,
                    "birds_current": 622,
                    "feed_consumed_kg": 127,
                    "average_bird_weight": 168.33,
                    "fcr": 0.96,
                }
            ]
        )

        result = service.answer(
            "i meant daily data and everything",
            history=[
                {"role": "user", "content": "show flock 1 in detail"},
                {
                    "role": "assistant",
                    "content": "Your flocks:\n1. Alpha Batch",
                    "resolved_flock_id": 77,
                    "resolved_farm_id": 42,
                    "intent_entity_type": "flock",
                },
            ],
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["metric"], "daily_data_by_flock")
        self.assertEqual(result["params"], [7, 77])
        self.assertEqual(result["resolved_flock_id"], 77)
        self.assertIn("Alpha Batch daily data", result["answer"])
        self.assertEqual(len(client.requests), 1)
        prompt = client.requests[0]["messages"][-1]["content"]
        self.assertIn("Last referenced flock", prompt)


    def test_llm_service_safe_plan_remembers_active_workspace(self):
        client = FakeGroqClient(
            ["Your current farm is Red Farm and your current flock is Alpha Batch."]
        )
        service = ChikoozaLLMTextToSQLService(
            user=self.user,
            groq_client=client,
            entity_resolver=FakeEntityResolver(
                EntityResolution(
                    context=(
                        "Active app farm context: farm_id=42, farm_public_id=9001, farm_name=Red Farm.\n"
                        "Active app flock context: flock_id=77, flock_public_id=5001, flock_name=Alpha Batch, farm_id=42, farm_name=Red Farm."
                    )
                )
            ),
        )

        def execute(plan):
            self.assertEqual(plan.metric, "current_workspace")
            self.assertEqual(plan.params, [7, 77])
            return [
                {
                    "farm_id": 42,
                    "current_farm": "Red Farm",
                    "flock_id": 77,
                    "current_flock": "Alpha Batch",
                    "breed_name": "Hubbard",
                }
            ]

        service.executor = SimpleNamespace(execute=execute)

        result = service.answer("which is my selected/current farm and flock")

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["metric"], "current_workspace")
        self.assertEqual(result["resolved_farm_id"], 42)
        self.assertEqual(result["resolved_flock_id"], 77)
        self.assertEqual(len(client.requests), 1)
        self.assertEqual(client.requests[0]["kwargs"]["model"], AIBOT_SQL_DEFAULT_MODEL)

    def test_llm_service_safe_plan_uses_current_flock_for_its_details(self):
        client = FakeGroqClient(["Alpha Batch has full flock, daily, sales, and purchase details."])
        service = ChikoozaLLMTextToSQLService(
            user=self.user,
            groq_client=client,
            entity_resolver=FakeEntityResolver(
                EntityResolution(
                    context=(
                        "Last referenced flock from recent chat: flock_id=77, "
                        "flock_public_id=5001, flock_name=Alpha Batch, farm_id=42, farm_name=Red Farm."
                    )
                )
            ),
        )

        def execute(plan):
            self.assertEqual(plan.metric, "complete_flock_report")
            self.assertIn(77, plan.params)
            return [{"flock_id": 77, "flock_name": "Alpha Batch", "farm_name": "Red Farm"}]

        service.executor = SimpleNamespace(execute=execute)

        result = service.answer("okay then give me all its details and every data about it")

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["metric"], "complete_flock_report")
        self.assertEqual(result["resolved_flock_id"], 77)

    def test_llm_service_safe_plan_handles_profit_rankings_and_loss_typos(self):
        client = FakeGroqClient(
            [
                "The most profitable flock is Small Batch, but its costs are missing.",
                "The biggest loss is Alpha Batch with Rs. 59,196 loss.",
            ]
        )
        service = ChikoozaLLMTextToSQLService(
            user=self.user,
            groq_client=client,
            entity_resolver=FakeEntityResolver(),
        )

        seen_metrics = []

        def execute(plan):
            seen_metrics.append(plan.metric)
            if plan.metric == "most_profitable_flock":
                self.assertIn(
                    "ORDER BY ranked.data_ready DESC, ranked.result DESC",
                    plan.sql,
                )
                self.assertIn("COALESCE(sales.total_sales, 0) > 0", plan.sql)
                self.assertIn("COALESCE(purchases.total_purchases, 0) > 0", plan.sql)
                return [
                    {
                        "flock_name": "Small Batch",
                        "farm_name": "Red Farm",
                        "total_sales": 14,
                        "total_purchases": 0,
                        "flock_cost": 0,
                        "result": 14,
                        "data_note": "Purchase and flock-cost records are zero or missing.",
                        "data_ready": 0,
                    }
                ]
            self.assertEqual(plan.metric, "biggest_loss_flock")
            self.assertIn("WHERE ranked.result < 0", plan.sql)
            self.assertIn("ORDER BY ranked.result ASC", plan.sql)
            return [
                {
                    "flock_name": "Alpha Batch",
                    "farm_name": "Red Farm",
                    "total_sales": 7560,
                    "total_purchases": 43006,
                    "flock_cost": 23750,
                    "result": -59196,
                    "data_note": "",
                }
            ]

        service.executor = SimpleNamespace(execute=execute)

        profitable = service.answer("so which is the most profitable flock")
        loss = service.answer("what is my buggest loss")

        self.assertEqual(profitable["metric"], "most_profitable_flock")
        self.assertEqual(loss["metric"], "biggest_loss_flock")
        self.assertEqual(seen_metrics, ["most_profitable_flock", "biggest_loss_flock"])


    def test_llm_service_safe_plan_handles_breed_sales_and_improvement_queries(self):
        client = FakeGroqClient(
            [
                "Hubbard is your most used breed with 4 flocks.",
                "Complete has the highest sales amount.",
                "Focus on the flocks with the biggest losses and missing records.",
            ]
        )
        service = ChikoozaLLMTextToSQLService(
            user=self.user,
            groq_client=client,
            entity_resolver=FakeEntityResolver(),
        )

        def execute(plan):
            if plan.metric == "most_used_breed":
                self.assertIn("GROUP BY breed_name", plan.sql)
                return [{"breed_name": "Hubbard", "flock_count": 4}]
            if plan.metric == "sales_amount_leader":
                self.assertIn("ORDER BY total_sales DESC", plan.sql)
                return [
                    {
                        "flock_name": "Complete",
                        "farm_name": "Complete Farm",
                        "sale_count": 2,
                        "total_sales": 507870.04,
                    }
                ]
            self.assertEqual(plan.metric, "improvement_advice")
            self.assertIn("ORDER BY ranked.profit_loss ASC", plan.sql)
            return [
                {
                    "flock_name": "Alpha Batch",
                    "farm_name": "Red Farm",
                    "profit_loss": -59196,
                    "total_mortality": 3,
                    "average_fcr": 0.96,
                    "current_birds": 622,
                }
            ]

        service.executor = SimpleNamespace(execute=execute)

        breed = service.answer("show the most used breed")
        # U: Use a phrasing that still hits sales_amount_leader (requires history context)
        sales = service.answer(
            "which flock has highest sales amount",
            history=[{"role": "assistant", "content": "The flock with most sales is Complete."}],
        )
        advice = service.answer("which can i do to imporve more kindly tell by seeing my records")

        self.assertEqual(breed["metric"], "most_used_breed")
        self.assertEqual(sales["metric"], "sales_amount_leader")
        self.assertEqual(advice["metric"], "improvement_advice")
        self.assertIsNone(advice.get("display"))


    def test_llm_service_lists_breed_for_each_flock(self):
        client = FakeGroqClient(
            [
                "Each flock is listed with its farm and breed.",
                "Each flock is listed with its farm and breed.",
            ]
        )
        service = ChikoozaLLMTextToSQLService(
            user=self.user,
            groq_client=client,
            entity_resolver=FakeEntityResolver(),
        )

        def execute(plan):
            self.assertEqual(plan.metric, "flock_breeds_by_flock")
            self.assertIn("flock_name", plan.sql)
            self.assertIn("breed_name", plan.sql)
            return [
                {"flock_id": 77, "flock_name": "Alpha Batch", "farm_name": "Red Farm", "breed_name": "Hubbard"},
                {"flock_id": 88, "flock_name": "Beta Batch", "farm_name": "Blue Farm", "breed_name": "BV300"},
            ]

        service.executor = SimpleNamespace(execute=execute)

        result = service.answer("tell the breed in all the flocks")
        followup = service.answer(
            "specify properly on which breed is for which flock",
            history=[
                {"role": "user", "content": "tell the breed in all the flocks"},
                {
                    "role": "assistant",
                    "content": "Hubbard and BV300.",
                    "metric": "flock_breeds_by_flock",
                },
            ],
        )

        self.assertEqual(result["metric"], "flock_breeds_by_flock")
        self.assertEqual(result["display"]["title"], "Flock breeds")
        self.assertEqual(followup["metric"], "flock_breeds_by_flock")
        self.assertEqual(len(client.requests), 2)

    def test_llm_service_other_breeds_followup_excludes_last_flock(self):
        client = FakeGroqClient(["The other flock breeds are listed."])
        service = ChikoozaLLMTextToSQLService(
            user=self.user,
            groq_client=client,
            entity_resolver=FakeEntityResolver(
                EntityResolution(
                    context=(
                        "Last referenced flock from recent chat: flock_id=77, "
                        "flock_public_id=5001, flock_name=Alpha Batch, farm_id=42, farm_name=Red Farm."
                    )
                )
            ),
        )

        def execute(plan):
            self.assertEqual(plan.metric, "flock_breeds_by_flock")
            self.assertIn("flock_id != %s", plan.sql)
            self.assertEqual(plan.params, [7, 77])
            return [
                {"flock_id": 88, "flock_name": "Beta Batch", "farm_name": "Blue Farm", "breed_name": "BV300"}
            ]

        service.executor = SimpleNamespace(execute=execute)

        result = service.answer(
            "and for others?",
            history=[
                {"role": "user", "content": "okay then tell me the breed of complete flock"},
                {
                    "role": "assistant",
                    "content": "Alpha Batch is Hubbard.",
                    "metric": "flock_breed",
                    "resolved_flock_id": 77,
                },
            ],
        )

        self.assertEqual(result["metric"], "flock_breeds_by_flock")

    def test_llm_service_prioritizes_improvement_over_stale_breed_context(self):
        client = FakeGroqClient(["Focus on losses, missing cost records, mortality, feed, and FCR."])
        service = ChikoozaLLMTextToSQLService(
            user=self.user,
            groq_client=client,
            entity_resolver=FakeEntityResolver(
                EntityResolution(
                    context=(
                        "Last referenced flock from recent chat: flock_id=77, "
                        "flock_public_id=5001, flock_name=Alpha Batch, farm_id=42, farm_name=Red Farm."
                    )
                )
            ),
        )

        def execute(plan):
            self.assertEqual(plan.metric, "improvement_advice")
            self.assertIn("ORDER BY ranked.profit_loss ASC", plan.sql)
            return [
                {
                    "flock_name": "Alpha Batch",
                    "farm_name": "Red Farm",
                    "profit_loss": -59196,
                    "total_mortality": 3,
                    "average_fcr": 0.96,
                    "current_birds": 622,
                    "latest_daily_date": "2026-05-31",
                }
            ]

        service.executor = SimpleNamespace(execute=execute)

        result = service.answer(
            "now tell me how to improve and what went wrong",
            history=[
                {"role": "user", "content": "tell the breed in all the flocks"},
                {"role": "assistant", "content": "Hubbard and BV300.", "metric": "flock_breeds_by_flock"},
            ],
        )

        self.assertEqual(result["metric"], "improvement_advice")
        self.assertIsNone(result.get("display"))

    def test_entity_resolver_does_not_treat_broad_breed_questions_as_missing_flock(self):
        resolver = ChikoozaEntityResolver(user=self.user)

        self.assertFalse(
            resolver._looks_like_named_flock_reference(
                "specify properly on which breed is for which flock"
            )
        )
        self.assertFalse(
            resolver._looks_like_named_flock_reference("tell the breed in all the flocks")
        )

    def test_llm_service_supports_flock_count_in_each_farm(self):
        # U: 'total flocks in each farm' goes to the LLM because our deterministic
        # U: flock_count shortcut deliberately excludes 'in each farm' / 'per farm'
        # U: queries (they need GROUP BY farm which the LLM generates).
        client = FakeGroqClient(
            [
                (
                    '{"sql": "SELECT farm_id, farm_name, COUNT(DISTINCT flock_id) AS '
                    'flock_count FROM ai_farm_flock_data_view WHERE owner_id = %s '
                    'AND farm_id IS NOT NULL GROUP BY farm_id, farm_name ORDER BY farm_name LIMIT 100", '
                    f'"params": ["{OWNER_PARAM}"], '
                    '"metric": "flock_count_by_farm", "result_type": "table"}'
                ),
                "Red Farm has 2 flocks. Blue Farm has 1 flock.",
            ]
        )
        service = ChikoozaLLMTextToSQLService(
            user=self.user,
            groq_client=client,
            entity_resolver=FakeEntityResolver(),
        )
        service.executor = SimpleNamespace(
            execute=lambda plan: [
                {"farm_id": 42, "farm_name": "Red Farm", "flock_count": 2},
                {"farm_id": 43, "farm_name": "Blue Farm", "flock_count": 1},
            ]
        )

        result = service.answer("total flocks in each farm")

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["metric"], "flock_count_by_farm")
        self.assertIn("GROUP BY farm_id, farm_name", result["query"])
        self.assertEqual(result["answer"], "Red Farm has 2 flocks. Blue Farm has 1 flock.")


    def test_llm_service_returns_display_payload_for_flock_rows(self):
        client = FakeGroqClient(
            [
                (
                    '{"sql": "SELECT flock_id, flock_name, farm_name, hatch_date, '
                    'flock_size, actual_birds, breed_name FROM ai_farm_flock_data_view '
                    'WHERE owner_id = %s AND flock_id IS NOT NULL LIMIT 100", '
                    f'"params": ["{OWNER_PARAM}"], '
                    '"metric": "flock_list", "result_type": "table"}'
                ),
                "You have one flock.",
            ]
        )
        service = ChikoozaLLMTextToSQLService(
            user=self.user,
            groq_client=client,
            entity_resolver=FakeEntityResolver(),
        )
        service.executor = SimpleNamespace(
            execute=lambda plan: [
                {
                    "flock_id": 77,
                    "flock_name": "Alpha Batch",
                    "farm_name": "Red Farm",
                    "hatch_date": "2026-05-01",
                    "flock_size": 100,
                    "actual_birds": 95,
                    "breed_name": "Hubbard",
                }
            ]
        )

        result = service.answer("show all flocks")

        self.assertEqual(result["display"]["type"], "cards")
        self.assertEqual(result["display"]["cards"][0]["title"], "Alpha Batch")
        self.assertEqual(result["display"]["cards"][0]["rows"][0]["label"], "Farm")


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


# ============================================================================
# EXHAUSTIVE FARMER QUESTION COVERAGE TESTS
# Every possible question, synonym, typo, context, and edge case.
# Zero failures is the only acceptable result.
# ============================================================================


def _make_llm_service(user, groq_responses=None, entity_context="", executor_data=None):
    """
    Build a ChikoozaLLMTextToSQLService with a fake Groq client and fake executor
    for unit testing without network calls.
    executor_data: dict mapping metric -> list[dict] rows returned.
    """
    from .llm_sql import ChikoozaLLMTextToSQLService

    responses = groq_responses or ["ok."]
    client = FakeGroqClient(responses)
    resolver = FakeEntityResolver(EntityResolution(context=entity_context))

    data = executor_data or {}

    def execute(plan):
        # Return caller-supplied data keyed by metric, or a sensible default.
        if plan.metric in data:
            return data[plan.metric]
        # Generic defaults so the answer pipeline doesn't error.
        if plan.metric == "farm_record_summary":
            return [{"farm_count": 2, "flock_count": 4, "current_birds": 800,
                     "total_sales": 50000, "total_purchases": 20000,
                     "total_feed_consumed": 1200, "total_mortality": 15, "average_fcr": 1.7}]
        if plan.metric == "farm_list":
            return [{"farm_id": 42, "farm_name": "Red Farm", "farm_city": "Pune",
                     "farm_pin": "411001", "shed_count": 2, "farm_status": True}]
        if plan.metric == "flock_list":
            return [{"flock_id": 77, "flock_name": "Alpha Batch", "farm_name": "Red Farm",
                     "hatch_date": "2026-01-01", "flock_size": 1000, "actual_birds": 950,
                     "breed_name": "Hubbard", "flock_status": True}]
        if plan.metric in {"farm_count", "flock_count"}:
            return [{"farm_count": 2}] if "farm" in plan.metric else [{"flock_count": 4}]
        if plan.metric == "total_sales":
            return [{"total_sales": 50000, "sale_count": 5}]
        if plan.metric == "total_purchases":
            return [{"total_purchases": 20000}]
        if plan.metric == "mortality":
            return [{"total_mortality": 15}]
        if plan.metric == "feed_consumed":
            return [{"total_feed_consumed": 1200}]
        if plan.metric in {"average_fcr", "average_weight"}:
            return [{"average_fcr": 1.7}] if "fcr" in plan.metric else [{"average_bird_weight": 1850}]
        if plan.metric == "current_birds":
            return [{"current_birds": 800}]
        if plan.metric == "flock_performance":
            return [{"flock_id": 77, "flock_name": "Alpha Batch", "farm_name": "Red Farm",
                     "total_feed": 1200, "total_mortality": 15, "avg_weight": 1.85,
                     "avg_fcr": 1.7, "daily_data_status": 1}]
        if plan.metric in {"complete_flock_report", "current_workspace",
                           "profit_loss", "profit_loss_by_flock",
                           "most_profitable_flock", "biggest_loss_flock",
                           "profit_by_flock", "profit_for_flock"}:
            return [{"flock_id": 77, "flock_name": "Alpha Batch", "farm_name": "Red Farm",
                     "total_sales": 50000, "total_purchases": 20000, "flock_cost": 5000,
                     "result": 25000, "profit_loss": 25000}]
        if plan.metric in {"flock_breeds_by_flock", "flock_breed", "most_used_breed",
                           "active_flock_breed"}:
            return [{"flock_id": 77, "flock_name": "Alpha Batch",
                     "farm_name": "Red Farm", "breed_name": "Hubbard"}]
        if plan.metric == "daily_data_by_flock":
            return [{"record_date": "2026-05-31", "flock_id": 77, "flock_name": "Alpha Batch",
                     "birds_died": 3, "total_mort": 15, "birds_current": 800,
                     "feed_consumed_kg": 127, "total_feed": 1200,
                     "average_bird_weight": 1850, "fcr": 1.7, "remarks": "ok",
                     "daily_data_status": 1}]
        if plan.metric == "latest_flock_status":
            return [{"record_date": "2026-05-31", "flock_id": 77, "flock_name": "Alpha Batch",
                     "birds_died": 3, "total_mort": 15, "birds_current": 800, "fcr": 1.7,
                     "average_bird_weight": 1850}]
        if plan.metric == "improvement_advice":
            return [{"flock_name": "Alpha Batch", "farm_name": "Red Farm",
                     "profit_loss": -5000, "total_mortality": 15,
                     "average_fcr": 1.7, "current_birds": 800,
                     "latest_daily_date": "2026-05-31"}]
        if plan.metric in {"sales_count_leader", "sales_amount_leader"}:
            return [{"flock_name": "Alpha Batch", "farm_name": "Red Farm",
                     "sale_count": 5, "total_sales": 50000}]
        return [{"result": 0}]

    svc = ChikoozaLLMTextToSQLService(
        user=user, groq_client=client, entity_resolver=resolver
    )
    svc.executor = SimpleNamespace(execute=execute)
    return svc


def _make_service_with_flock_context(user, flock_id=77, farm_id=42,
                                     flock_name="Alpha Batch", farm_name="Red Farm",
                                     groq_responses=None, executor_data=None):
    """Build service that has a specific flock pre-resolved in entity context."""
    context = (
        f"Last referenced flock from recent chat: flock_id={flock_id}, "
        f"flock_public_id=5001, flock_name={flock_name}, "
        f"farm_id={farm_id}, farm_name={farm_name}."
    )
    return _make_llm_service(
        user, groq_responses=groq_responses or ["ok."],
        entity_context=context, executor_data=executor_data
    )


class ExhaustiveFarmerQuestionsTests(SimpleTestCase):
    """
    Every possible question a farmer might ask — greetings, summaries,
    metrics, context-aware, complex, typos, conversational, security.
    Zero failures is the only acceptable result.
    """

    def setUp(self):
        self.user = SimpleNamespace(id=7, is_authenticated=True)
        from .llm_sql import ChikoozaLLMTextToSQLService
        self._svc_cls = ChikoozaLLMTextToSQLService

    # ------------------------------------------------------------------
    # HELPER
    # ------------------------------------------------------------------
    def _svc(self, entity_context="", groq_responses=None, executor_data=None):
        return _make_llm_service(
            self.user,
            groq_responses=groq_responses,
            entity_context=entity_context,
            executor_data=executor_data,
        )

    def _svc_flock(self, flock_id=77, farm_id=42,
                   flock_name="Alpha Batch", farm_name="Red Farm",
                   groq_responses=None, executor_data=None):
        return _make_service_with_flock_context(
            self.user, flock_id=flock_id, farm_id=farm_id,
            flock_name=flock_name, farm_name=farm_name,
            groq_responses=groq_responses, executor_data=executor_data,
        )

    def _assert_success(self, result, expected_metric=None, check_owner=True):
        self.assertEqual(result["status"], "success",
                         f"Expected success but got: {result.get('message', result)}")
        if expected_metric:
            self.assertEqual(result["metric"], expected_metric,
                             f"Expected metric={expected_metric} but got {result.get('metric')}")
        if check_owner:
            self.assertIn(7, result.get("params", []),
                          f"owner_id 7 not found in params for metric={result.get('metric')}")

    # ==================================================================
    # 1. GREETING AND CONVERSATIONAL — must NEVER hit the SQL planner
    # ==================================================================

    def test_greeting_hello(self):
        svc = self._svc()
        result = svc.answer("hello")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["metric"], "conversation_only")

    def test_greeting_hi(self):
        svc = self._svc()
        result = svc.answer("hi")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["metric"], "conversation_only")

    def test_greeting_hey(self):
        svc = self._svc()
        result = svc.answer("hey")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["metric"], "conversation_only")

    def test_greeting_namaste(self):
        svc = self._svc()
        result = svc.answer("namaste")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["metric"], "conversation_only")

    def test_thanks(self):
        svc = self._svc()
        result = svc.answer("thanks")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["metric"], "conversation_only")

    def test_thank_you(self):
        svc = self._svc()
        result = svc.answer("thank you")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["metric"], "conversation_only")

    def test_ok(self):
        svc = self._svc()
        result = svc.answer("ok")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["metric"], "conversation_only")

    def test_okay(self):
        svc = self._svc()
        result = svc.answer("okay")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["metric"], "conversation_only")

    def test_nothing_more(self):
        svc = self._svc()
        result = svc.answer("nothing more")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["metric"], "conversation_only")

    def test_no_more(self):
        svc = self._svc()
        result = svc.answer("no more")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["metric"], "conversation_only")

    def test_thats_all(self):
        svc = self._svc()
        result = svc.answer("that's all")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["metric"], "conversation_only")

    def test_done(self):
        svc = self._svc()
        result = svc.answer("done")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["metric"], "conversation_only")

    def test_enough(self):
        svc = self._svc()
        result = svc.answer("enough")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["metric"], "conversation_only")

    def test_huh(self):
        svc = self._svc()
        result = svc.answer("huh?")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["metric"], "conversation_only")

    # "okay next then" prefix should NOT produce conversation_only —
    # it is a transition phrase before the actual query.
    def test_okay_next_then_prefix_alone_is_conversation(self):
        svc = self._svc()
        result = svc.answer("okay next then")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["metric"], "conversation_only")

    def test_okay_next_prefix_before_farm_query_reaches_data_plan(self):
        """'okay next then tell me the performance of my current flocks' must work."""
        svc = self._svc()
        result = svc.answer("okay next then tell me the performance of my current flocks")
        # Should NOT be conversation_only — the real query is about performance.
        self.assertEqual(result["status"], "success")
        self.assertNotEqual(result["metric"], "conversation_only")
        self.assertEqual(result["metric"], "flock_performance")

    def test_okay_now_performance_prefix_works(self):
        svc = self._svc()
        result = svc.answer("okay now tell me my flock performance")
        self.assertEqual(result["status"], "success")
        self.assertNotEqual(result["metric"], "conversation_only")

    def test_okay_so_sales_prefix_works(self):
        svc = self._svc()
        result = svc.answer("okay so what are my total sales")
        self.assertEqual(result["status"], "success")
        self.assertNotEqual(result["metric"], "conversation_only")

    # ==================================================================
    # 2. ACCOUNT SUMMARY — every synonym / vague phrasing
    # ==================================================================

    def _assert_summary(self, question):
        svc = self._svc()
        result = svc.answer(question)
        self._assert_success(result, "farm_record_summary")

    def test_summary_my_data(self):
        self._assert_summary("show my data")

    def test_summary_all_data(self):
        self._assert_summary("show all data")

    def test_summary_my_all_data(self):
        self._assert_summary("show me my all data")

    def test_summary_complete_data(self):
        self._assert_summary("give me complete data")

    def test_summary_full_records(self):
        self._assert_summary("show full records")

    def test_summary_my_records(self):
        self._assert_summary("my records")

    def test_summary_all_records(self):
        self._assert_summary("all records")

    def test_summary_everything(self):
        self._assert_summary("show everything")

    def test_summary_all_details(self):
        self._assert_summary("all details")

    def test_summary_my_details(self):
        self._assert_summary("my details")

    def test_summary_all_information(self):
        self._assert_summary("all information")

    def test_summary_total_data(self):
        self._assert_summary("total data")

    def test_summary_what_do_i_have(self):
        self._assert_summary("what do i have")

    def test_summary_what_all_i_have(self):
        self._assert_summary("what all i have")

    def test_summary_total_things(self):
        self._assert_summary("total things")

    def test_summary_my_stuff(self):
        self._assert_summary("my stuff")

    def test_summary_all_stuff(self):
        self._assert_summary("all stuff")

    def test_summary_show_me_all_my_data(self):
        self._assert_summary("show me all my data")

    def test_summary_give_me_complete_information(self):
        self._assert_summary("give me complete information")

    def test_summary_keyword(self):
        self._assert_summary("summary")

    def test_summary_overview(self):
        self._assert_summary("overview")

    def test_summary_account_summary(self):
        self._assert_summary("account summary")

    def test_summary_farm_summary(self):
        self._assert_summary("farm summary")

    def test_summary_show_me_all_records(self):
        self._assert_summary("show me all records")

    def test_summary_my_all_things(self):
        self._assert_summary("my all things")

    def test_summary_all_my_info(self):
        self._assert_summary("all my info")

    # daily data in question must NOT trigger account summary
    def test_daily_data_and_everything_does_not_trigger_summary(self):
        svc = self._svc_flock()
        result = svc.answer(
            "i meant daily data and everything",
            history=[
                {"role": "user", "content": "show flock 1"},
                {"role": "assistant", "content": "Alpha Batch.", "resolved_flock_id": 77, "resolved_farm_id": 42},
            ],
        )
        self.assertEqual(result["status"], "success")
        self.assertNotEqual(result["metric"], "farm_record_summary",
                            "'daily data and everything' must not map to account summary")

    # ==================================================================
    # 3. FARM LIST — every phrasing
    # ==================================================================

    def _assert_farm_list(self, question):
        svc = self._svc()
        result = svc.answer(question)
        self._assert_success(result, "farm_list")

    def test_farm_list_show_farms(self):
        self._assert_farm_list("show farms")

    def test_farm_list_show_my_farms(self):
        self._assert_farm_list("show my farms")

    def test_farm_list_list_farms(self):
        self._assert_farm_list("list farms")

    def test_farm_list_all_farms(self):
        self._assert_farm_list("all farms")

    def test_farm_list_show_all_farms(self):
        self._assert_farm_list("show all farms")

    def test_farm_list_my_farms(self):
        self._assert_farm_list("my farms")

    def test_farm_list_list_all_farms(self):
        self._assert_farm_list("list all farms")

    def test_farm_list_display_farms(self):
        self._assert_farm_list("display farms")

    def test_farm_list_give_me_my_farms(self):
        self._assert_farm_list("give me my farms")

    def test_farm_list_tell_me_about_my_farms(self):
        self._assert_farm_list("tell me about my farms")

    def test_farm_list_what_are_my_farms(self):
        self._assert_farm_list("what are my farms")

    def test_farm_list_all_my_farms(self):
        self._assert_farm_list("all my farms")

    # ==================================================================
    # 4. FLOCK LIST — every phrasing
    # ==================================================================

    def _assert_flock_list(self, question):
        svc = self._svc()
        result = svc.answer(question)
        self._assert_success(result, "flock_list")

    def test_flock_list_show_flocks(self):
        self._assert_flock_list("show flocks")

    def test_flock_list_show_my_flocks(self):
        self._assert_flock_list("show my flocks")

    def test_flock_list_list_flocks(self):
        self._assert_flock_list("list flocks")

    def test_flock_list_all_flocks(self):
        self._assert_flock_list("all flocks")

    def test_flock_list_show_all_flocks(self):
        self._assert_flock_list("show all flocks")

    def test_flock_list_my_flocks(self):
        self._assert_flock_list("my flocks")

    def test_flock_list_list_all_flocks(self):
        self._assert_flock_list("list all flocks")

    def test_flock_list_list_all_the_flocks_i_have(self):
        self._assert_flock_list("list all the flocks i have")

    def test_flock_list_show_batches(self):
        self._assert_flock_list("show batches")

    def test_flock_list_all_batches(self):
        self._assert_flock_list("all batches")

    def test_flock_list_my_batches(self):
        self._assert_flock_list("my batches")

    def test_flock_list_display_all_flocks(self):
        self._assert_flock_list("display all flocks")

    def test_flock_list_give_me_all_flocks(self):
        self._assert_flock_list("give me all flocks")

    def test_flock_list_tell_me_about_my_flocks(self):
        self._assert_flock_list("tell me about my flocks")

    # ==================================================================
    # 5. FARM COUNT — every phrasing
    # ==================================================================

    def _assert_farm_count(self, question):
        svc = self._svc()
        result = svc.answer(question)
        self._assert_success(result, "farm_count")

    def test_farm_count_how_many_farms(self):
        self._assert_farm_count("how many farms do i have")

    def test_farm_count_number_of_farms(self):
        self._assert_farm_count("number of farms")

    def test_farm_count_total_farms(self):
        self._assert_farm_count("total farms")

    def test_farm_count_count_of_farms(self):
        self._assert_farm_count("count of farms")

    def test_farm_count_how_many_farms_i_have(self):
        self._assert_farm_count("how many farms i have")

    # ==================================================================
    # 6. FLOCK COUNT — every phrasing (total, not per farm)
    # ==================================================================

    def _assert_flock_count(self, question):
        svc = self._svc()
        result = svc.answer(question)
        self._assert_success(result, "flock_count")

    def test_flock_count_how_many_flocks(self):
        self._assert_flock_count("how many flocks")

    def test_flock_count_how_many_flocks_i_have(self):
        self._assert_flock_count("how many flocks i have")

    def test_flock_count_number_of_flocks(self):
        self._assert_flock_count("number of flocks")

    def test_flock_count_total_flocks(self):
        self._assert_flock_count("total flocks")

    def test_flock_count_count_of_flocks(self):
        self._assert_flock_count("count of flocks")

    def test_flock_count_how_many_batches(self):
        self._assert_flock_count("how many batches do i have")

    def test_flock_count_total_batches(self):
        self._assert_flock_count("total batches")

    # 'total flocks in each farm' must go to LLM (grouped per farm)
    def test_flock_count_in_each_farm_goes_to_llm(self):
        svc = self._svc(
            groq_responses=[
                (
                    '{"sql": "SELECT farm_id, farm_name, COUNT(DISTINCT flock_id) AS flock_count '
                    'FROM ai_farm_flock_data_view WHERE owner_id = %s AND farm_id IS NOT NULL '
                    'GROUP BY farm_id, farm_name ORDER BY farm_name LIMIT 100", '
                    f'"params": ["{OWNER_PARAM}"], '
                    '"metric": "flock_count_by_farm", "result_type": "table"}'
                ),
                "Red Farm: 2 flocks. Blue Farm: 1 flock.",
            ]
        )
        result = svc.answer("total flocks in each farm")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["metric"], "flock_count_by_farm")

    def test_flocks_per_farm_goes_to_llm(self):
        svc = self._svc(
            groq_responses=[
                (
                    '{"sql": "SELECT farm_id, farm_name, COUNT(DISTINCT flock_id) AS flock_count '
                    'FROM ai_farm_flock_data_view WHERE owner_id = %s AND farm_id IS NOT NULL '
                    'GROUP BY farm_id, farm_name ORDER BY farm_name LIMIT 100", '
                    f'"params": ["{OWNER_PARAM}"], '
                    '"metric": "flock_count_by_farm", "result_type": "table"}'
                ),
                "Per-farm flock count listed.",
            ]
        )
        result = svc.answer("how many flocks per farm")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["metric"], "flock_count_by_farm")

    # ==================================================================
    # 7. PERFORMANCE — every phrasing, both all-flocks and single-flock
    # ==================================================================

    def _assert_performance_all(self, question):
        svc = self._svc()
        result = svc.answer(question)
        self._assert_success(result, "flock_performance")

    def _assert_performance_flock(self, question):
        svc = self._svc_flock()
        result = svc.answer(question)
        self._assert_success(result, "complete_flock_report")

    def test_performance_of_my_flocks(self):
        self._assert_performance_all("performance of my flocks")

    def test_performance_of_my_current_flocks(self):
        self._assert_performance_all("performance of my current flocks")

    def test_performance_of_all_flocks(self):
        self._assert_performance_all("performance of all flocks")

    def test_how_are_my_flocks_doing(self):
        self._assert_performance_all("how are my flocks doing")

    def test_how_is_my_farm_doing(self):
        self._assert_performance_all("how is my farm doing")

    def test_flock_stats(self):
        self._assert_performance_all("flock stats")

    def test_flock_health(self):
        self._assert_performance_all("flock health")

    def test_farm_performance(self):
        self._assert_performance_all("farm performance")

    def test_how_are_my_birds_doing(self):
        self._assert_performance_all("how are my birds doing")

    def test_how_is_my_flock_performing(self):
        self._assert_performance_all("how is my flock performing")

    def test_flock_statistics(self):
        self._assert_performance_all("flock statistics")

    def test_progress_of_my_flocks(self):
        self._assert_performance_all("progress of my flocks")

    def test_flocks_progressing(self):
        self._assert_performance_all("are my flocks progressing")

    def test_performance_flock_context_gives_complete_report(self):
        """When one flock is in context and 'current flock' phrasing, use complete report."""
        self._assert_performance_flock("performance of current flock")

    def test_how_is_this_flock_doing_with_context(self):
        self._assert_performance_flock("how is this flock doing")

    def test_how_is_it_doing_with_context(self):
        self._assert_performance_flock("how is it doing")

    def test_flock_status_with_context(self):
        self._assert_performance_flock("status of this flock")

    # performance + improvement = improvement_advice (not performance plan)
    def test_performance_improvement_routes_to_advice(self):
        svc = self._svc()
        result = svc.answer("how to improve my flock performance")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["metric"], "improvement_advice")

    def test_what_went_wrong_routes_to_advice(self):
        svc = self._svc()
        result = svc.answer("what went wrong with my farm performance")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["metric"], "improvement_advice")

    # ==================================================================
    # 8. TOTAL SALES — every synonym
    # ==================================================================

    def _assert_sales(self, question, with_flock=False):
        svc = self._svc_flock() if with_flock else self._svc()
        result = svc.answer(question)
        self._assert_success(result, "total_sales")

    def test_sales_total_sales(self):
        self._assert_sales("total sales")

    def test_sales_my_total_sales(self):
        self._assert_sales("my total sales")

    def test_sales_what_are_my_total_sales(self):
        self._assert_sales("what are my total sales")

    def test_sales_total_revenue(self):
        self._assert_sales("total revenue")

    def test_sales_my_revenue(self):
        self._assert_sales("my revenue")

    def test_sales_my_income(self):
        self._assert_sales("my income")

    def test_sales_total_income(self):
        self._assert_sales("total income")

    def test_sales_how_much_have_i_sold(self):
        self._assert_sales("how much have i sold")

    def test_sales_total_sold(self):
        self._assert_sales("total sold")

    def test_sales_my_earnings(self):
        self._assert_sales("my earnings")

    def test_sales_total_earnings(self):
        self._assert_sales("total earnings")

    def test_sales_total_liftings(self):
        self._assert_sales("total liftings")

    def test_sales_my_liftings(self):
        self._assert_sales("my liftings")

    def test_sales_sale_amount(self):
        self._assert_sales("sale amount")

    def test_sales_how_much_sales_i_have(self):
        self._assert_sales("how much sales i have")

    def test_sales_total_sale_amount(self):
        self._assert_sales("total sale amount")

    def test_sales_income_earned(self):
        self._assert_sales("income earned")

    def test_sales_this_flock_sales_with_context(self):
        """With flock context, sales routes to that flock."""
        svc = self._svc_flock()
        result = svc.answer("sales of this flock")
        self._assert_success(result, "total_sales")
        self.assertIn(77, result["params"])

    def test_sales_for_current_flock_with_context(self):
        svc = self._svc_flock()
        result = svc.answer("how much sales for current flock")
        self._assert_success(result, "total_sales")

    # profit blocks sales from triggering
    def test_sales_with_profit_word_routes_to_profit(self):
        svc = self._svc()
        result = svc.answer("profit or loss from sales")
        self._assert_success(result, "profit_loss_by_flock")

    # ==================================================================
    # 9. TOTAL PURCHASES / EXPENSES — every synonym
    # ==================================================================

    def _assert_purchases(self, question):
        svc = self._svc()
        result = svc.answer(question)
        self._assert_success(result, "total_purchases")

    def test_purchases_total(self):
        self._assert_purchases("total purchases")

    def test_purchases_my_purchases(self):
        self._assert_purchases("my purchases")

    def test_purchases_total_expenses(self):
        self._assert_purchases("total expenses")

    def test_purchases_my_expenses(self):
        self._assert_purchases("my expenses")

    def test_purchases_total_expenditure(self):
        self._assert_purchases("total expenditure")

    def test_purchases_how_much_spent(self):
        self._assert_purchases("how much i spent")

    def test_purchases_how_much_did_i_spend(self):
        self._assert_purchases("how much did i spend")

    def test_purchases_my_spending(self):
        self._assert_purchases("my spending")

    def test_purchases_medicine_expenses(self):
        self._assert_purchases("medicine expenses")

    def test_purchases_vaccine_cost(self):
        self._assert_purchases("vaccine cost")

    def test_purchases_vaccination_expenses(self):
        self._assert_purchases("vaccination expenses")

    def test_purchases_labour_cost(self):
        self._assert_purchases("labour cost")

    def test_purchases_labor_cost(self):
        self._assert_purchases("labor cost")

    def test_purchases_equipment_cost(self):
        self._assert_purchases("equipment cost")

    def test_purchases_purchase_amount(self):
        self._assert_purchases("purchase amount")

    def test_purchases_how_much_expenditure(self):
        self._assert_purchases("how much expenditure")

    def test_purchases_flock_expenses_with_context(self):
        svc = self._svc_flock()
        result = svc.answer("expenses for this flock")
        self._assert_success(result, "total_purchases")
        self.assertIn(77, result["params"])

    # ==================================================================
    # 10. PROFIT / LOSS — every phrasing
    # ==================================================================

    def _assert_profit(self, question, expected_metric=None):
        svc = self._svc()
        result = svc.answer(question)
        self.assertEqual(result["status"], "success")
        self.assertIn(result["metric"], {
            "profit_loss_by_flock", "profit_for_flock",
            "most_profitable_flock", "profit_loss",
        }, f"Got unexpected metric: {result['metric']} for: {question}")

    def test_profit_or_loss(self):
        self._assert_profit("profit or loss")

    def test_my_profit(self):
        self._assert_profit("my profit")

    def test_net_profit(self):
        self._assert_profit("net profit")

    def test_profit_and_loss(self):
        self._assert_profit("profit and loss")

    def test_net_result(self):
        self._assert_profit("net result")

    def test_profit_loss_report(self):
        self._assert_profit("profit loss report")

    def test_profit_question_hindi_style(self):
        self._assert_profit("mera profit kya hai")  # vague but contains 'profit'

    def test_net_margin(self):
        self._assert_profit("net margin")

    def test_loss_in_my_farm(self):
        self._assert_profit("loss in my farm")

    def test_am_i_in_profit(self):
        self._assert_profit("am i in profit")

    def test_did_i_make_profit(self):
        self._assert_profit("did i make profit")

    def test_how_much_profit_did_i_make(self):
        self._assert_profit("how much profit did i make")

    def test_profit_for_flock_with_context(self):
        svc = self._svc_flock()
        result = svc.answer("profit for current flock")
        self.assertEqual(result["status"], "success")
        self.assertIn(result["metric"], {"profit_for_flock", "profit_loss_by_flock"})

    def test_most_profitable_flock(self):
        svc = self._svc()
        result = svc.answer("which is the most profitable flock")
        self._assert_success(result, "most_profitable_flock")

    def test_best_earning_flock(self):
        svc = self._svc()
        result = svc.answer("best earning flock")
        self._assert_success(result, "most_profitable_flock")

    def test_top_profit_flock(self):
        svc = self._svc()
        result = svc.answer("which flock has the top profit")
        self._assert_success(result, "most_profitable_flock")

    def test_highest_net_flock(self):
        svc = self._svc()
        result = svc.answer("flock with highest net")
        self._assert_success(result, "most_profitable_flock")

    def test_biggest_loss_flock(self):
        svc = self._svc()
        result = svc.answer("which flock has the biggest loss")
        self._assert_success(result, "biggest_loss_flock")

    def test_most_loss_flock(self):
        svc = self._svc()
        result = svc.answer("which flock has most loss")
        self._assert_success(result, "biggest_loss_flock")

    def test_worst_flock(self):
        svc = self._svc()
        result = svc.answer("which flock is the worst loss")
        self._assert_success(result, "biggest_loss_flock")

    def test_highest_negative_flock(self):
        svc = self._svc()
        result = svc.answer("flock with highest negative result")
        self._assert_success(result, "biggest_loss_flock")

    def test_maximum_loss(self):
        svc = self._svc()
        result = svc.answer("maximum loss flock")
        self._assert_success(result, "biggest_loss_flock")

    # ==================================================================
    # 11. MORTALITY — every phrasing
    # ==================================================================

    def _assert_mortality(self, question):
        svc = self._svc()
        result = svc.answer(question)
        self._assert_success(result, "mortality")

    def test_mortality(self):
        self._assert_mortality("mortality")

    def test_total_mortality(self):
        self._assert_mortality("total mortality")

    def test_my_mortality(self):
        self._assert_mortality("my mortality")

    def test_how_many_birds_died(self):
        self._assert_mortality("how many birds died")

    def test_birds_died(self):
        self._assert_mortality("birds died")

    def test_total_deaths(self):
        self._assert_mortality("total deaths")

    def test_bird_deaths(self):
        self._assert_mortality("bird deaths")

    def test_dead_birds(self):
        self._assert_mortality("dead birds")

    def test_birds_dead(self):
        self._assert_mortality("birds dead")

    def test_how_many_chickens_died(self):
        self._assert_mortality("how many chickens died")

    def test_total_dead(self):
        self._assert_mortality("total dead")

    def test_mortality_count(self):
        self._assert_mortality("mortality count")

    def test_mortalities(self):
        self._assert_mortality("mortalities")

    def test_how_many_died(self):
        self._assert_mortality("how many died")

    def test_birds_that_died(self):
        self._assert_mortality("birds that died")

    def test_mortality_for_flock_with_context(self):
        svc = self._svc_flock()
        result = svc.answer("mortality for current flock")
        self._assert_success(result, "mortality")
        self.assertIn(77, result["params"])

    def test_deaths_in_this_flock_with_context(self):
        svc = self._svc_flock()
        result = svc.answer("deaths in this flock")
        self._assert_success(result, "mortality")

    # mortality must NOT trigger current_birds
    def test_birds_died_does_not_trigger_current_birds_detector(self):
        from .llm_sql import ChikoozaLLMTextToSQLService
        svc = self._svc()
        # _asks_current_birds should return False when mortality words present
        service_obj = ChikoozaLLMTextToSQLService(
            user=self.user,
            groq_client=FakeGroqClient([]),
            entity_resolver=FakeEntityResolver(),
        )
        self.assertFalse(service_obj._asks_current_birds("how many birds died"))
        self.assertFalse(service_obj._asks_current_birds("birds died today"))

    # ==================================================================
    # 12. CURRENT BIRDS — every phrasing
    # ==================================================================

    def _assert_current_birds(self, question):
        svc = self._svc()
        result = svc.answer(question)
        self._assert_success(result, "current_birds")

    def test_current_birds(self):
        self._assert_current_birds("current birds")

    def test_birds_alive(self):
        self._assert_current_birds("birds alive")

    def test_how_many_birds_alive(self):
        self._assert_current_birds("how many birds alive")

    def test_birds_remaining(self):
        self._assert_current_birds("birds remaining")

    def test_birds_left(self):
        self._assert_current_birds("birds left")

    def test_how_many_birds(self):
        self._assert_current_birds("how many birds do i have")

    def test_bird_count(self):
        self._assert_current_birds("bird count")

    def test_live_birds(self):
        self._assert_current_birds("live birds")

    def test_alive_birds(self):
        self._assert_current_birds("alive birds")

    def test_birds_now(self):
        self._assert_current_birds("how many birds now")

    def test_current_chicken_count(self):
        self._assert_current_birds("current chickens alive")

    def test_current_birds_for_flock_with_context(self):
        svc = self._svc_flock()
        result = svc.answer("current birds in this flock")
        self._assert_success(result, "current_birds")
        self.assertIn(77, result["params"])

    # ==================================================================
    # 13. FEED CONSUMED — every phrasing
    # ==================================================================

    def _assert_feed(self, question):
        svc = self._svc()
        result = svc.answer(question)
        self._assert_success(result, "feed_consumed")

    def test_feed_total_feed(self):
        self._assert_feed("total feed")

    def test_feed_feed_consumed(self):
        self._assert_feed("feed consumed")

    def test_feed_total_feed_consumed(self):
        self._assert_feed("total feed consumed")

    def test_feed_how_much_feed(self):
        self._assert_feed("how much feed")

    def test_feed_feed_used(self):
        self._assert_feed("feed used")

    def test_feed_feed_intake(self):
        self._assert_feed("feed intake")

    def test_feed_total_feed_used(self):
        self._assert_feed("total feed used")

    def test_feed_feed_kg(self):
        self._assert_feed("how much feed in kg")

    def test_feed_how_much_feed_given(self):
        self._assert_feed("how much feed given")

    def test_feed_consumption(self):
        self._assert_feed("feed consumption")

    def test_feed_for_flock_with_context(self):
        svc = self._svc_flock()
        result = svc.answer("feed consumed for this flock")
        self._assert_success(result, "feed_consumed")
        self.assertIn(77, result["params"])

    # feed with FCR word must not collide
    def test_feed_fcr_question_goes_to_fcr_not_feed(self):
        svc = self._svc()
        result = svc.answer("average fcr")
        self._assert_success(result, "average_fcr")

    # ==================================================================
    # 14. AVERAGE FCR — every phrasing
    # ==================================================================

    def _assert_fcr(self, question):
        svc = self._svc()
        result = svc.answer(question)
        self._assert_success(result, "average_fcr")

    def test_fcr(self):
        self._assert_fcr("fcr")

    def test_average_fcr(self):
        self._assert_fcr("average fcr")

    def test_feed_conversion_ratio(self):
        self._assert_fcr("feed conversion ratio")

    def test_feed_conversion(self):
        self._assert_fcr("feed conversion")

    def test_conversion_ratio(self):
        self._assert_fcr("conversion ratio")

    def test_what_is_my_fcr(self):
        self._assert_fcr("what is my fcr")

    def test_average_feed_conversion(self):
        self._assert_fcr("average feed conversion")

    def test_fcr_for_flock_with_context(self):
        svc = self._svc_flock()
        result = svc.answer("fcr for current flock")
        self._assert_success(result, "average_fcr")
        self.assertIn(77, result["params"])

    # ==================================================================
    # 15. AVERAGE WEIGHT — every phrasing
    # ==================================================================

    def _assert_weight(self, question):
        svc = self._svc()
        result = svc.answer(question)
        self._assert_success(result, "average_weight")

    def test_weight_average_weight(self):
        self._assert_weight("average weight")

    def test_weight_average_bird_weight(self):
        self._assert_weight("average bird weight")

    def test_weight_bird_weight(self):
        self._assert_weight("bird weight")

    def test_weight_body_weight(self):
        self._assert_weight("body weight")

    def test_weight_avg_weight(self):
        self._assert_weight("avg weight")

    def test_weight_what_is_average_weight(self):
        self._assert_weight("what is the average weight of birds")

    def test_weight_for_flock_with_context(self):
        svc = self._svc_flock()
        result = svc.answer("average weight for this flock")
        self._assert_success(result, "average_weight")
        self.assertIn(77, result["params"])

    # weight inside performance question must not steal the result
    def test_weight_in_performance_question_routes_to_performance(self):
        svc = self._svc()
        result = svc.answer("how is the weight performance of my flock")
        self.assertEqual(result["status"], "success")
        # should route to flock_performance (performance wins over weight)
        self.assertEqual(result["metric"], "flock_performance")

    # ==================================================================
    # 16. BREED QUESTIONS — all flocks, single flock, most used
    # ==================================================================

    def test_breed_most_used_breed(self):
        svc = self._svc()
        result = svc.answer("what is the most used breed")
        self._assert_success(result, "most_used_breed")

    def test_breed_most_common_breed(self):
        svc = self._svc()
        result = svc.answer("most common breed")
        self._assert_success(result, "most_used_breed")

    def test_breed_popular_breed(self):
        svc = self._svc()
        result = svc.answer("popular breed")
        self._assert_success(result, "most_used_breed")

    def test_breed_top_breed(self):
        svc = self._svc()
        result = svc.answer("top breed in my flocks")
        self._assert_success(result, "most_used_breed")

    def test_all_flock_breeds_all_flocks(self):
        svc = self._svc()
        result = svc.answer("breed in all flocks")
        self._assert_success(result, "flock_breeds_by_flock")

    def test_all_flock_breeds_tell_breeds(self):
        svc = self._svc()
        result = svc.answer("tell the breed in all the flocks")
        self._assert_success(result, "flock_breeds_by_flock")

    def test_all_flock_breeds_which_breed_for_which_flock(self):
        svc = self._svc()
        result = svc.answer("which breed is for which flock")
        self._assert_success(result, "flock_breeds_by_flock")

    def test_breed_of_current_flock_with_context(self):
        svc = self._svc_flock()
        result = svc.answer("breed of the current flock")
        self._assert_success(result, "flock_breed")

    def test_breed_of_this_flock_with_context(self):
        svc = self._svc_flock()
        result = svc.answer("breed of this flock")
        self._assert_success(result, "flock_breed")

    def test_what_breed_is_it_with_context(self):
        svc = self._svc_flock()
        result = svc.answer("what breed is it")
        self._assert_success(result, "flock_breed")

    # ==================================================================
    # 17. IMPROVEMENT ADVICE — every phrasing
    # ==================================================================

    def _assert_advice(self, question):
        svc = self._svc()
        result = svc.answer(question)
        self._assert_success(result, "improvement_advice")

    def test_advice_how_to_improve(self):
        self._assert_advice("how to improve my farm")

    def test_advice_what_can_i_do(self):
        self._assert_advice("what can i do to improve")

    def test_advice_what_should_i_do(self):
        self._assert_advice("what should i do to improve")

    def test_advice_how_can_i_improve(self):
        self._assert_advice("how can i improve my records")

    def test_advice_give_me_advice(self):
        self._assert_advice("give me advice on my farm")

    def test_advice_suggest_something(self):
        self._assert_advice("suggest something for my farm")

    def test_advice_recommend(self):
        self._assert_advice("recommend something for my flock")

    def test_advice_what_went_wrong(self):
        self._assert_advice("what went wrong")

    def test_advice_imporve_typo(self):
        self._assert_advice("which can i do to imporve more kindly tell by seeing my records")

    def test_advice_what_is_the_problem(self):
        self._assert_advice("what is the problem with my farm")

    def test_advice_fix_issues(self):
        self._assert_advice("how can i fix my flock issues")

    def test_advice_poor_performance(self):
        self._assert_advice("my flock is performing poorly what to do")

    def test_advice_how_to_do_better(self):
        self._assert_advice("how to do better in my farm")

    def test_advice_what_are_the_issues(self):
        self._assert_advice("what are the issues in my farm records")

    # ==================================================================
    # 18. DAILY DATA — context-aware, always uses flock context
    # ==================================================================

    def test_daily_data_for_current_flock(self):
        svc = self._svc_flock()
        result = svc.answer("daily data for current flock")
        self._assert_success(result, "daily_data_by_flock")
        self.assertIn(77, result["params"])

    def test_daily_data_show_daily(self):
        svc = self._svc_flock()
        result = svc.answer("show daily")
        self._assert_success(result, "daily_data_by_flock")

    def test_daily_data_daily_records(self):
        svc = self._svc_flock()
        result = svc.answer("daily records for this flock")
        self._assert_success(result, "daily_data_by_flock")

    def test_daily_data_and_everything_for_flock(self):
        svc = self._svc_flock()
        result = svc.answer(
            "i meant daily data and everything",
            history=[
                {"role": "user", "content": "show flock 1"},
                {"role": "assistant", "content": "Alpha Batch.", "resolved_flock_id": 77},
            ],
        )
        self._assert_success(result, "daily_data_by_flock")

    # ==================================================================
    # 19. COMPLETE SINGLE-FLOCK REPORT — all details for one flock
    # ==================================================================

    def test_all_details_for_this_flock(self):
        svc = self._svc_flock()
        result = svc.answer("give me all details about it")
        self._assert_success(result, "complete_flock_report")

    def test_everything_about_this_flock(self):
        svc = self._svc_flock()
        result = svc.answer("everything about this flock")
        self._assert_success(result, "complete_flock_report")

    def test_all_data_about_it(self):
        svc = self._svc_flock()
        result = svc.answer("all data about it")
        self._assert_success(result, "complete_flock_report")

    def test_every_detail_of_current_flock(self):
        svc = self._svc_flock()
        result = svc.answer("okay then give me all its details and every data about it")
        self._assert_success(result, "complete_flock_report")

    # ==================================================================
    # 20. TYPO CORRECTION — common farmer typos must be understood
    # ==================================================================

    def test_typo_glock_to_flock(self):
        """'glock' must be corrected to 'flock'."""
        from .modern_services import normalize_ai_query
        self.assertEqual(normalize_ai_query("show all my glocks"), "show all my flocks")

    def test_typo_flcok_to_flock(self):
        from .modern_services import normalize_ai_query
        self.assertEqual(normalize_ai_query("how many flcoks"), "how many flocks")

    def test_typo_frok_to_flock(self):
        from .modern_services import normalize_ai_query
        self.assertIn("flock", normalize_ai_query("show all forks"))

    def test_typo_sails_to_sales(self):
        from .modern_services import normalize_ai_query
        self.assertIn("sale", normalize_ai_query("total sails"))

    def test_typo_pruchase_to_purchase(self):
        from .modern_services import normalize_ai_query
        self.assertIn("purchase", normalize_ai_query("total pruchases"))

    def test_typo_mortilty_to_mortality(self):
        from .modern_services import normalize_ai_query
        self.assertIn("mortality", normalize_ai_query("mortilty"))

    def test_typo_buggest_to_biggest(self):
        from .modern_services import normalize_ai_query
        self.assertIn("biggest", normalize_ai_query("buggest loss"))

    def test_typo_imporve_to_improve(self):
        from .modern_services import normalize_ai_query
        self.assertIn("improve", normalize_ai_query("how to imporve"))

    def test_typo_glock_in_real_question_routes_correctly(self):
        """After typo fix, 'show all glocks' must route to flock_list."""
        svc = self._svc()
        result = svc.answer("show all my glocks")
        self._assert_success(result, "flock_list")

    def test_typo_sails_in_real_question_routes_correctly(self):
        svc = self._svc()
        result = svc.answer("total sails")
        self._assert_success(result, "total_sales")

    def test_typo_buggest_loss_routes_correctly(self):
        svc = self._svc()
        result = svc.answer("what is my buggest loss")
        self._assert_success(result, "biggest_loss_flock")

    def test_typo_imporve_routes_correctly(self):
        svc = self._svc()
        result = svc.answer("which can i do to imporve more kindly tell by seeing my records")
        self._assert_success(result, "improvement_advice")

    # ==================================================================
    # 21. SECURITY — must NEVER leak other-user data or allow SQL injection
    # ==================================================================

    def test_security_block_other_user_id(self):
        from .llm_sql import ChikoozaLLMTextToSQLService
        svc = self._svc()
        # Any plan the safe planner generates must have user.id=7, never another id.
        result = svc.answer("show sales")
        self.assertIn(7, result.get("params", []))
        self.assertNotIn(99, result.get("params", []))

    def test_security_all_plans_contain_owner_id_7(self):
        """For every question type, params must include the authenticated user id."""
        questions_and_metrics = [
            ("show all farms", "farm_list"),
            ("show all flocks", "flock_list"),
            ("total sales", "total_sales"),
            ("total purchases", "total_purchases"),
            ("mortality", "mortality"),
            ("current birds", "current_birds"),
            ("feed consumed", "feed_consumed"),
            ("average fcr", "average_fcr"),
            ("average weight", "average_weight"),
            ("my summary", "farm_record_summary"),
            ("performance of my flocks", "flock_performance"),
            ("how many farms", "farm_count"),
            ("how many flocks", "flock_count"),
        ]
        for question, expected_metric in questions_and_metrics:
            with self.subTest(question=question):
                svc = self._svc()
                result = svc.answer(question)
                self.assertEqual(result["status"], "success",
                                 f"Failed for: {question}")
                self.assertEqual(result["metric"], expected_metric,
                                 f"Wrong metric for: {question}")
                self.assertIn(7, result["params"],
                              f"owner_id=7 missing from params for: {question}")

    def test_security_sql_always_has_owner_id_placeholder(self):
        """Every deterministic plan SQL must contain 'owner_id = %s'."""
        questions = [
            "show all farms", "show all flocks", "total sales",
            "total purchases", "mortality", "current birds",
            "feed consumed", "average fcr", "average weight",
            "my summary", "performance of my flocks",
            "how many farms", "how many flocks",
        ]
        for question in questions:
            with self.subTest(question=question):
                svc = self._svc()
                result = svc.answer(question)
                self.assertIn("owner_id = %s", result.get("query", "").lower(),
                              f"Missing owner_id filter in SQL for: {question}")

    # ==================================================================
    # 22. CONTEXT-AWARE FOLLOW-UPS — pronoun resolution
    # ==================================================================

    def test_context_show_its_details(self):
        svc = self._svc_flock()
        result = svc.answer("show its details")
        self._assert_success(result, "complete_flock_report")

    def test_context_what_data_does_it_have(self):
        svc = self._svc_flock()
        result = svc.answer("what data does it have")
        self._assert_success(result, "complete_flock_report")

    def test_context_sales_for_that_flock(self):
        svc = self._svc_flock()
        result = svc.answer("sales for that flock")
        self._assert_success(result, "total_sales")
        self.assertIn(77, result["params"])

    def test_context_mortality_for_this_batch(self):
        svc = self._svc_flock()
        result = svc.answer("mortality for this batch")
        self._assert_success(result, "mortality")
        self.assertIn(77, result["params"])

    def test_context_fcr_for_this_flock(self):
        svc = self._svc_flock()
        result = svc.answer("fcr for this flock")
        self._assert_success(result, "average_fcr")
        self.assertIn(77, result["params"])

    def test_context_weight_for_current_batch(self):
        svc = self._svc_flock()
        result = svc.answer("average weight for current batch")
        self._assert_success(result, "average_weight")
        self.assertIn(77, result["params"])

    def test_context_feed_for_it(self):
        svc = self._svc_flock()
        result = svc.answer("feed consumed for it")
        self._assert_success(result, "feed_consumed")
        self.assertIn(77, result["params"])

    def test_context_current_birds_in_this_flock(self):
        svc = self._svc_flock()
        result = svc.answer("current birds in this flock")
        self._assert_success(result, "current_birds")
        self.assertIn(77, result["params"])

    # ==================================================================
    # 23. COMPLEX / COMPOUND QUESTIONS — must not fail or return wrong plan
    # ==================================================================

    def test_complex_show_me_all_the_data_i_have_in_my_account(self):
        svc = self._svc()
        result = svc.answer("show me all the data i have in my account")
        self._assert_success(result, "farm_record_summary")

    def test_complex_total_birds_alive_across_all_my_flocks(self):
        svc = self._svc()
        result = svc.answer("total birds alive across all my flocks")
        self._assert_success(result, "current_birds")

    def test_complex_how_much_feed_have_all_my_chickens_consumed(self):
        svc = self._svc()
        result = svc.answer("how much feed have all my chickens consumed")
        self._assert_success(result, "feed_consumed")

    def test_complex_total_money_i_have_made_from_sales(self):
        svc = self._svc()
        result = svc.answer("total money i have made from sales")
        self._assert_success(result, "total_sales")

    def test_complex_total_money_spent_on_medicines_and_purchases(self):
        svc = self._svc()
        result = svc.answer("total money spent on medicines and purchases")
        self._assert_success(result, "total_purchases")

    def test_complex_how_many_of_my_birds_have_died_in_total(self):
        svc = self._svc()
        result = svc.answer("how many of my birds have died in total")
        self._assert_success(result, "mortality")

    def test_complex_am_i_making_money_or_losing(self):
        svc = self._svc()
        result = svc.answer("am i making money or losing")
        self.assertEqual(result["status"], "success")
        self.assertIn(result["metric"], {
            "profit_loss_by_flock", "profit_for_flock", "profit_loss"
        })

    def test_complex_what_is_the_average_fcr_of_all_my_flocks(self):
        svc = self._svc()
        result = svc.answer("what is the average fcr of all my flocks")
        self._assert_success(result, "average_fcr")

    def test_complex_what_is_the_average_weight_of_birds_in_my_farm(self):
        svc = self._svc()
        result = svc.answer("what is the average weight of birds in my farm")
        self._assert_success(result, "average_weight")

    def test_complex_give_me_all_the_flock_data_with_performance(self):
        svc = self._svc()
        result = svc.answer("give me all the flock data with performance")
        self.assertEqual(result["status"], "success")
        self.assertIn(result["metric"], {"flock_performance", "flock_list"})

    def test_complex_show_farm_and_flock_count(self):
        svc = self._svc()
        # "how many farms" — farm_count wins since no flock word
        result = svc.answer("how many farms and flocks do i have")
        self.assertEqual(result["status"], "success")
        # Will hit summary since "everything"/"all" is not here, so likely farm_count or flock_count
        self.assertIn(result["metric"], {"farm_count", "flock_count", "farm_record_summary"})

    def test_complex_all_sales_and_purchases(self):
        svc = self._svc()
        result = svc.answer("show me all sales and purchases")
        self.assertEqual(result["status"], "success")
        # Could go to either metric — must not fail
        self.assertIn(result["metric"], {
            "total_sales", "total_purchases", "farm_record_summary"
        })

    def test_complex_flock_with_most_sales_count(self):
        svc = self._svc()
        result = svc.answer("which flock has the most number of sales")
        self._assert_success(result, "sales_count_leader")

    def test_complex_flock_with_highest_sales_amount(self):
        svc = self._svc()
        result = svc.answer("which flock has highest sales amount")
        self._assert_success(result, "sales_amount_leader")

    def test_complex_tell_me_flock_performance_then_profit(self):
        """Two sequential questions — each must work independently."""
        svc = self._svc()
        r1 = svc.answer("tell me flock performance")
        r2 = svc.answer("now tell me profit or loss")
        self._assert_success(r1, "flock_performance")
        self.assertEqual(r2["status"], "success")
        self.assertIn(r2["metric"], {"profit_loss_by_flock", "most_profitable_flock"})

    # ==================================================================
    # 24. CONVERSATIONAL TRANSITION PREFIXES
    # ==================================================================

    def test_transition_okay_then_before_breed_query(self):
        svc = self._svc_flock()
        result = svc.answer("okay then tell me the breed of complete flock")
        self._assert_success(result, "flock_breed")

    def test_transition_okay_then_performance(self):
        svc = self._svc()
        result = svc.answer("okay then tell me performance of my flocks")
        self._assert_success(result, "flock_performance")

    def test_transition_now_tell_me_profit(self):
        svc = self._svc()
        result = svc.answer("now tell me profit or loss")
        self.assertEqual(result["status"], "success")
        self.assertIn(result["metric"], {"profit_loss_by_flock", "profit_loss"})

    def test_transition_so_show_me_farms(self):
        svc = self._svc()
        result = svc.answer("so show me all my farms")
        self._assert_success(result, "farm_list")

    def test_transition_next_show_flocks(self):
        svc = self._svc()
        result = svc.answer("next show me all flocks")
        self._assert_success(result, "flock_list")

    def test_transition_now_show_me_summary(self):
        svc = self._svc()
        result = svc.answer("now show me summary")
        self._assert_success(result, "farm_record_summary")

    # ==================================================================
    # 25. HINDI-ENGLISH MIXED / BROKEN GRAMMAR — real farmer language
    # ==================================================================

    def test_broken_english_mera_flock_ka_data(self):
        """'mera flock' — contains 'flock', should route somewhere sensible."""
        svc = self._svc_flock()
        result = svc.answer("mera flock ka data dikhao")
        self.assertEqual(result["status"], "success")

    def test_broken_english_total_bikri(self):
        """'bikri' is not recognized but 'total' alone falls through — must not crash."""
        svc = self._svc()
        # Won't match a specific plan, will go to LLM. Should not crash.
        result = svc.answer("total bikri kya hai")
        self.assertIn(result["status"], {"success", "error"})

    def test_broken_english_kitne_birds_hain(self):
        """'birds' present — should route to current_birds or similar."""
        svc = self._svc()
        result = svc.answer("kitne birds hain")
        # 'birds' alone may match current_birds or go to LLM
        self.assertIn(result["status"], {"success", "error"})

    def test_broken_english_mera_profit_kya_hai(self):
        svc = self._svc()
        result = svc.answer("mera profit kya hai")
        self.assertEqual(result["status"], "success")

    def test_broken_english_koi_loss_to_nahi(self):
        svc = self._svc()
        result = svc.answer("koi loss to nahi")
        self.assertEqual(result["status"], "success")
        self.assertIn(result["metric"], {
            "profit_loss_by_flock", "biggest_loss_flock",
            "profit_for_flock", "profit_loss"
        })

    def test_broken_english_mera_kul_bikri(self):
        svc = self._svc()
        result = svc.answer("mera kul sales batao")
        self.assertEqual(result["status"], "success")
        self._assert_success(result, "total_sales")

    def test_broken_english_farm_ka_overview(self):
        svc = self._svc()
        result = svc.answer("farm ka overview do")
        self.assertEqual(result["status"], "success")
        self._assert_success(result, "farm_record_summary")

    def test_broken_english_flock_ki_health(self):
        svc = self._svc()
        result = svc.answer("flock ki health kaisi hai")
        self.assertEqual(result["status"], "success")
        self._assert_success(result, "flock_performance")

    # ==================================================================
    # 26. DETECTOR METHOD UNIT TESTS — every detector, positive & negative
    # ==================================================================

    def _detector(self):
        from .llm_sql import ChikoozaLLMTextToSQLService
        svc = ChikoozaLLMTextToSQLService(
            user=self.user,
            groq_client=FakeGroqClient([]),
            entity_resolver=FakeEntityResolver(),
        )
        return svc

    def test_detector_performance_positive_cases(self):
        d = self._detector()
        for q in [
            "performance of my flocks",
            "how are my flocks doing",
            "flock health",
            "flock stats",
            "how is my farm doing",
            "how is my flock performing",
            "farm performance",
            "how are my birds doing",
            "flock status",
            "my flocks progress",
            "are my flocks progressing",
            "flock statistics",
            "health of my farm",
            "flock ki health",
        ]:
            with self.subTest(q=q):
                self.assertTrue(d._asks_performance(q), f"Expected True for: {q}")

    def test_detector_performance_negative_cases(self):
        d = self._detector()
        for q in [
            "how to improve my farm performance",
            "advice on flock performance",
            "suggest something for better performance",
            "what is the problem",
            "fix my farm issues",
        ]:
            with self.subTest(q=q):
                self.assertFalse(d._asks_performance(q), f"Expected False for: {q}")

    def test_detector_account_summary_positive_cases(self):
        d = self._detector()
        for q in [
            "my data", "all data", "my records", "summary", "overview",
            "everything", "what do i have", "total things", "my stuff",
            "all information", "complete data", "full data", "all details",
        ]:
            with self.subTest(q=q):
                self.assertTrue(d._asks_account_summary(q), f"Expected True for: {q}")

    def test_detector_account_summary_negative_daily_data(self):
        d = self._detector()
        # "daily data" must NOT trigger account summary
        self.assertFalse(d._asks_account_summary("daily data and everything"))
        self.assertFalse(d._asks_account_summary("i meant daily data and everything"))

    def test_detector_farm_list_positive_cases(self):
        d = self._detector()
        for q in [
            "show farms", "list farms", "my farms", "all farms",
            "show all farms", "my farm list",
        ]:
            with self.subTest(q=q):
                self.assertTrue(d._asks_farm_list(q), f"Expected True for: {q}")

    def test_detector_flock_list_positive_cases(self):
        d = self._detector()
        for q in [
            "show flocks", "list flocks", "my flocks", "all flocks",
            "show all flocks", "list all the flocks i have",
            "show batches", "all batches",
        ]:
            with self.subTest(q=q):
                self.assertTrue(d._asks_flock_list(q), f"Expected True for: {q}")

    def test_detector_flock_list_negative_breed(self):
        """Breed questions must not accidentally be caught by flock_list."""
        d = self._detector()
        self.assertFalse(
            d._asks_flock_list("tell the breed in all the flocks"),
            "Breed question must not map to flock_list"
        )

    def test_detector_farm_count_positive(self):
        d = self._detector()
        for q in ["how many farms", "number of farms", "total farms", "count of farms"]:
            with self.subTest(q=q):
                self.assertTrue(d._asks_farm_count(q), f"Expected True for: {q}")

    def test_detector_flock_count_positive(self):
        d = self._detector()
        for q in ["how many flocks", "number of flocks", "total flocks", "how many batches"]:
            with self.subTest(q=q):
                self.assertTrue(d._asks_flock_count(q), f"Expected True for: {q}")

    def test_detector_flock_count_negative_per_farm(self):
        d = self._detector()
        for q in [
            "total flocks in each farm", "flocks per farm",
            "flocks by farm", "how many flocks for each farm",
        ]:
            with self.subTest(q=q):
                self.assertFalse(d._asks_flock_count(q), f"Expected False for: {q}")

    def test_detector_sales_total_positive(self):
        d = self._detector()
        for q in [
            "total sales", "my revenue", "my income", "total earnings",
            "total liftings", "how much have i sold", "sale amount",
        ]:
            with self.subTest(q=q):
                self.assertTrue(d._asks_sales_total(q), f"Expected True for: {q}")

    def test_detector_sales_total_negative_profit(self):
        d = self._detector()
        # 'profit' in query must block sales_total
        self.assertFalse(d._asks_sales_total("profit or loss from sales"))

    def test_detector_sales_total_negative_superlative(self):
        d = self._detector()
        # 'highest sales' should go to sales_amount_leader, not total_sales
        self.assertFalse(d._asks_sales_total("flock with highest sales"))

    def test_detector_purchases_positive(self):
        d = self._detector()
        for q in [
            "total purchases", "my expenses", "how much spent",
            "medicine expenses", "vaccine cost", "total expenditure",
            "labour cost",
        ]:
            with self.subTest(q=q):
                self.assertTrue(d._asks_purchases_total(q), f"Expected True for: {q}")

    def test_detector_purchases_negative_profit(self):
        d = self._detector()
        self.assertFalse(d._asks_purchases_total("profit from purchases"))

    def test_detector_mortality_positive(self):
        d = self._detector()
        for q in [
            "mortality", "total mortality", "how many birds died",
            "dead birds", "birds dead", "total deaths", "birds died",
            "how many died", "mortalities",
        ]:
            with self.subTest(q=q):
                self.assertTrue(d._asks_mortality(q), f"Expected True for: {q}")

    def test_detector_feed_positive(self):
        d = self._detector()
        for q in [
            "total feed", "feed consumed", "how much feed",
            "feed used", "feed intake", "feed consumption",
        ]:
            with self.subTest(q=q):
                self.assertTrue(d._asks_feed_total(q), f"Expected True for: {q}")

    def test_detector_feed_negative_fcr(self):
        d = self._detector()
        self.assertFalse(d._asks_feed_total("feed conversion ratio"))
        self.assertFalse(d._asks_feed_total("average fcr"))

    def test_detector_fcr_positive(self):
        d = self._detector()
        for q in [
            "fcr", "average fcr", "feed conversion ratio",
            "feed conversion", "conversion ratio",
        ]:
            with self.subTest(q=q):
                self.assertTrue(d._asks_avg_fcr(q), f"Expected True for: {q}")

    def test_detector_weight_positive(self):
        d = self._detector()
        for q in [
            "average weight", "bird weight", "body weight",
            "avg weight", "average bird weight",
        ]:
            with self.subTest(q=q):
                self.assertTrue(d._asks_avg_weight(q), f"Expected True for: {q}")

    def test_detector_weight_negative_performance(self):
        d = self._detector()
        self.assertFalse(d._asks_avg_weight("weight performance of my flock"))

    def test_detector_current_birds_positive(self):
        d = self._detector()
        for q in [
            "current birds", "birds alive", "birds remaining",
            "how many birds", "bird count", "live birds",
            "alive birds", "birds left",
        ]:
            with self.subTest(q=q):
                self.assertTrue(d._asks_current_birds(q), f"Expected True for: {q}")

    def test_detector_current_birds_negative_mortality(self):
        d = self._detector()
        self.assertFalse(d._asks_current_birds("how many birds died"))
        self.assertFalse(d._asks_current_birds("birds that are dead"))

    # ==================================================================
    # 27. SQL CORRECTNESS — verify SQL structure for every plan type
    # ==================================================================

    def _plan_sql(self, question, entity_context=""):
        from .llm_sql import ChikoozaLLMTextToSQLService
        svc = ChikoozaLLMTextToSQLService(
            user=self.user,
            groq_client=FakeGroqClient([]),
            entity_resolver=FakeEntityResolver(EntityResolution(context=entity_context)),
        )
        return svc._known_safe_plan(question, history=None, entity_context=entity_context)

    def test_sql_account_summary_has_9_owner_params(self):
        plan = self._plan_sql("show my data")
        self.assertIsNotNone(plan)
        self.assertEqual(plan.params.count(7), 9)

    def test_sql_farm_list_references_correct_view(self):
        plan = self._plan_sql("show all farms")
        self.assertIsNotNone(plan)
        self.assertIn("ai_farm_flock_data_view", plan.sql)
        self.assertIn("owner_id = %s", plan.sql)
        self.assertEqual(plan.params, [7])

    def test_sql_flock_list_references_correct_view(self):
        plan = self._plan_sql("show all flocks")
        self.assertIsNotNone(plan)
        self.assertIn("ai_farm_flock_data_view", plan.sql)
        self.assertIn("owner_id = %s", plan.sql)
        self.assertEqual(plan.params, [7])

    def test_sql_farm_count_correct(self):
        plan = self._plan_sql("how many farms")
        self.assertIsNotNone(plan)
        self.assertIn("COUNT(DISTINCT farm_id)", plan.sql)
        self.assertIn("ai_farm_flock_data_view", plan.sql)
        self.assertEqual(plan.params, [7])

    def test_sql_flock_count_correct(self):
        plan = self._plan_sql("how many flocks")
        self.assertIsNotNone(plan)
        self.assertIn("COUNT(DISTINCT flock_id)", plan.sql)
        self.assertEqual(plan.params, [7])

    def test_sql_total_sales_correct_view(self):
        plan = self._plan_sql("total sales")
        self.assertIsNotNone(plan)
        self.assertIn("ai_sale_data_view", plan.sql)
        self.assertIn("SUM(sale_amount)", plan.sql)
        self.assertEqual(plan.params, [7])

    def test_sql_total_purchases_correct_view(self):
        plan = self._plan_sql("total purchases")
        self.assertIsNotNone(plan)
        self.assertIn("ai_purchase_data_view", plan.sql)
        self.assertIn("SUM(purchase_amount)", plan.sql)
        self.assertEqual(plan.params, [7])

    def test_sql_mortality_correct_view(self):
        plan = self._plan_sql("total mortality")
        self.assertIsNotNone(plan)
        self.assertIn("ai_dailydata_data_view", plan.sql)
        self.assertIn("SUM(birds_died)", plan.sql)
        self.assertEqual(plan.params, [7])

    def test_sql_feed_consumed_correct_view(self):
        plan = self._plan_sql("total feed consumed")
        self.assertIsNotNone(plan)
        self.assertIn("ai_dailydata_data_view", plan.sql)
        self.assertIn("SUM(feed_consumed_kg)", plan.sql)
        self.assertEqual(plan.params, [7])

    def test_sql_average_fcr_correct_view(self):
        plan = self._plan_sql("average fcr")
        self.assertIsNotNone(plan)
        self.assertIn("ai_dailydata_data_view", plan.sql)
        self.assertIn("AVG(fcr)", plan.sql)
        self.assertEqual(plan.params, [7])

    def test_sql_average_weight_correct_view(self):
        plan = self._plan_sql("average bird weight")
        self.assertIsNotNone(plan)
        self.assertIn("ai_dailydata_data_view", plan.sql)
        self.assertIn("AVG(average_bird_weight)", plan.sql)
        self.assertEqual(plan.params, [7])

    def test_sql_current_birds_uses_subquery_for_latest_record(self):
        plan = self._plan_sql("current birds")
        self.assertIsNotNone(plan)
        self.assertIn("ai_dailydata_data_view", plan.sql)
        self.assertIn("MAX", plan.sql)  # correlated max subquery
        self.assertEqual(plan.params, [7, 7])

    def test_sql_performance_joins_both_views(self):
        plan = self._plan_sql("performance of my flocks")
        self.assertIsNotNone(plan)
        self.assertIn("ai_farm_flock_data_view", plan.sql)
        self.assertIn("ai_dailydata_data_view", plan.sql)
        self.assertEqual(plan.params, [7, 7, 7, 7])

    def test_sql_flock_context_sales_includes_flock_id(self):
        flock_ctx = "Last referenced flock from recent chat: flock_id=77, flock_public_id=5001, flock_name=Alpha Batch, farm_id=42, farm_name=Red Farm."
        plan = self._plan_sql("sales of this flock", entity_context=flock_ctx)
        self.assertIsNotNone(plan)
        self.assertIn(77, plan.params)
        self.assertIn(7, plan.params)

    def test_sql_flock_context_mortality_includes_flock_id(self):
        flock_ctx = "Last referenced flock from recent chat: flock_id=77, flock_public_id=5001, flock_name=Alpha Batch, farm_id=42, farm_name=Red Farm."
        plan = self._plan_sql("mortality for this flock", entity_context=flock_ctx)
        self.assertIsNotNone(plan)
        self.assertIn(77, plan.params)

    def test_sql_no_all_scope_with_context_uses_flock_filter(self):
        """Without 'all', context flock_id must be used for sales."""
        flock_ctx = "Last referenced flock from recent chat: flock_id=77, flock_public_id=5001, flock_name=Alpha Batch, farm_id=42, farm_name=Red Farm."
        plan = self._plan_sql("sales for this flock", entity_context=flock_ctx)
        self.assertIn(77, plan.params)

    def test_sql_all_scope_overrides_context_for_sales(self):
        """'total sales' (all scope) must NOT filter to context flock."""
        flock_ctx = "Last referenced flock from recent chat: flock_id=77, flock_public_id=5001, flock_name=Alpha Batch, farm_id=42, farm_name=Red Farm."
        plan = self._plan_sql("total sales", entity_context=flock_ctx)
        # 'total' is an 'all scope' keyword — should return account-wide sales without flock filter
        self.assertNotIn(77, plan.params)

    # ==================================================================
    # 28. METRIC NAMES — validate every metric name returned is correct
    # ==================================================================

    def test_metric_names_for_all_question_types(self):
        cases = [
            ("show all farms", "farm_list"),
            ("show all flocks", "flock_list"),
            ("how many farms", "farm_count"),
            ("how many flocks", "flock_count"),
            ("total sales", "total_sales"),
            ("total purchases", "total_purchases"),
            ("total mortality", "mortality"),
            ("total feed consumed", "feed_consumed"),
            ("average fcr", "average_fcr"),
            ("average bird weight", "average_weight"),
            ("current birds", "current_birds"),
            ("summary", "farm_record_summary"),
            ("show my data", "farm_record_summary"),
            ("performance of my flocks", "flock_performance"),
            ("which is the most profitable flock", "most_profitable_flock"),
            ("which flock has biggest loss", "biggest_loss_flock"),
            ("most used breed", "most_used_breed"),
            ("breed in all flocks", "flock_breeds_by_flock"),
            ("how to improve my farm", "improvement_advice"),
        ]
        for question, expected_metric in cases:
            with self.subTest(question=question):
                svc = self._svc()
                result = svc.answer(question)
                self.assertEqual(result["status"], "success",
                                 f"Failed for: {question} — {result.get('message')}")
                self.assertEqual(result["metric"], expected_metric,
                                 f"Wrong metric for: {question}")

    # ==================================================================
    # 29. EDGE CASES — questions that could break the routing logic
    # ==================================================================

    def test_edge_profit_and_sales_in_same_question_goes_to_profit(self):
        svc = self._svc()
        result = svc.answer("profit or loss from sales")
        self.assertEqual(result["status"], "success")
        # profit_loss detector runs AFTER sales — but profit wins since _asks_profit_loss
        # fires AND is checked before sales in the chain.
        self.assertNotEqual(result["metric"], "total_sales")

    def test_edge_performance_and_improvement_in_same_question(self):
        svc = self._svc()
        result = svc.answer("how to improve flock performance")
        # improvement_advice must win over flock_performance
        self.assertEqual(result["metric"], "improvement_advice")

    def test_edge_breed_and_flock_list_no_collision(self):
        svc = self._svc()
        result = svc.answer("tell the breed in all the flocks")
        # Must NOT go to flock_list; must go to breed plan
        self.assertNotEqual(result["metric"], "flock_list")
        self.assertEqual(result["metric"], "flock_breeds_by_flock")

    def test_edge_summary_does_not_capture_farm_summary_with_flock_context(self):
        """'show my flock summary' with flock context should give complete_flock_report,
        not account summary."""
        svc = self._svc_flock()
        result = svc.answer("show me all the details of this flock")
        self.assertEqual(result["status"], "success")
        self.assertNotEqual(result["metric"], "farm_record_summary")

    def test_edge_fcr_inside_performance_question(self):
        svc = self._svc()
        result = svc.answer("what is the fcr performance of my flocks")
        # 'performance' + 'flock' → flock_performance; fcr inside won't steal it
        self.assertEqual(result["status"], "success")

    def test_edge_weight_inside_performance_question(self):
        svc = self._svc()
        result = svc.answer("how is the weight and performance of my farm")
        # performance wins
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["metric"], "flock_performance")

    def test_edge_flock_count_not_triggered_by_per_farm(self):
        """'flocks per farm' must go to LLM (GROUP BY farm), not flock_count."""
        svc = self._svc()
        # We can't easily check that LLM was called without a FakeGroqClient,
        # but we CAN check that flock_count is NOT returned.
        # For this, feed a valid LLM response for flock_count_by_farm.
        svc2 = self._svc(
            groq_responses=[
                (
                    '{"sql": "SELECT farm_id, farm_name, COUNT(DISTINCT flock_id) AS flock_count '
                    'FROM ai_farm_flock_data_view WHERE owner_id = %s AND farm_id IS NOT NULL '
                    'GROUP BY farm_id, farm_name ORDER BY farm_name LIMIT 100", '
                    f'"params": ["{OWNER_PARAM}"], '
                    '"metric": "flock_count_by_farm", "result_type": "table"}'
                ),
                "Flocks per farm listed.",
            ]
        )
        result = svc2.answer("flocks per farm")
        self.assertEqual(result["status"], "success")
        self.assertNotEqual(result["metric"], "flock_count")

    def test_edge_empty_question_does_not_crash(self):
        svc = self._svc()
        result = svc.answer("")
        # Must return an error or conversation response, not crash.
        self.assertIn(result["status"], {"success", "error"})

    def test_edge_whitespace_only_question_does_not_crash(self):
        svc = self._svc()
        result = svc.answer("   ")
        self.assertIn(result["status"], {"success", "error"})

    def test_edge_very_long_question_does_not_crash(self):
        svc = self._svc()
        long_q = "show me all my farm and flock and sales and purchases and mortality " * 10
        result = svc.answer(long_q.strip())
        self.assertIn(result["status"], {"success", "error"})

    def test_edge_question_with_numbers_does_not_crash(self):
        svc = self._svc()
        result = svc.answer("sales for flock 1")
        # Entity resolver returns no flock, so goes to LLM or returns success with no flock filter
        self.assertIn(result["status"], {"success", "error"})

    # ==================================================================
    # 30. PLAN BUILDER PARAM COUNTS — correct number of %s
    # ==================================================================

    def _count_placeholders(self, plan):
        return plan.sql.count("%s")

    def test_placeholder_count_account_summary(self):
        from .llm_sql import ChikoozaLLMTextToSQLService
        svc = ChikoozaLLMTextToSQLService(
            user=self.user,
            groq_client=FakeGroqClient([]),
            entity_resolver=FakeEntityResolver(),
        )
        plan = svc._account_summary_plan()
        self.assertEqual(self._count_placeholders(plan), len(plan.params))
        self.assertEqual(plan.params, [7] * 9)

    def test_placeholder_count_farm_list(self):
        from .llm_sql import ChikoozaLLMTextToSQLService
        svc = ChikoozaLLMTextToSQLService(
            user=self.user,
            groq_client=FakeGroqClient([]),
            entity_resolver=FakeEntityResolver(),
        )
        plan = svc._farm_list_plan_llm()
        self.assertEqual(self._count_placeholders(plan), len(plan.params))

    def test_placeholder_count_flock_list(self):
        from .llm_sql import ChikoozaLLMTextToSQLService
        svc = ChikoozaLLMTextToSQLService(
            user=self.user,
            groq_client=FakeGroqClient([]),
            entity_resolver=FakeEntityResolver(),
        )
        plan = svc._flock_list_plan_llm()
        self.assertEqual(self._count_placeholders(plan), len(plan.params))

    def test_placeholder_count_sales_total_no_flock(self):
        from .llm_sql import ChikoozaLLMTextToSQLService
        svc = ChikoozaLLMTextToSQLService(
            user=self.user,
            groq_client=FakeGroqClient([]),
            entity_resolver=FakeEntityResolver(),
        )
        plan = svc._sales_total_plan(flock_id=None)
        self.assertEqual(self._count_placeholders(plan), len(plan.params))

    def test_placeholder_count_sales_total_with_flock(self):
        from .llm_sql import ChikoozaLLMTextToSQLService
        svc = ChikoozaLLMTextToSQLService(
            user=self.user,
            groq_client=FakeGroqClient([]),
            entity_resolver=FakeEntityResolver(),
        )
        plan = svc._sales_total_plan(flock_id=77)
        self.assertEqual(self._count_placeholders(plan), len(plan.params))
        self.assertIn(77, plan.params)

    def test_placeholder_count_mortality_with_flock(self):
        from .llm_sql import ChikoozaLLMTextToSQLService
        svc = ChikoozaLLMTextToSQLService(
            user=self.user,
            groq_client=FakeGroqClient([]),
            entity_resolver=FakeEntityResolver(),
        )
        plan = svc._mortality_total_plan(flock_id=77)
        self.assertEqual(self._count_placeholders(plan), len(plan.params))
        self.assertIn(77, plan.params)

    def test_placeholder_count_current_birds_with_flock(self):
        from .llm_sql import ChikoozaLLMTextToSQLService
        svc = ChikoozaLLMTextToSQLService(
            user=self.user,
            groq_client=FakeGroqClient([]),
            entity_resolver=FakeEntityResolver(),
        )
        plan = svc._current_birds_plan_llm(flock_id=77)
        self.assertEqual(self._count_placeholders(plan), len(plan.params))
        self.assertIn(77, plan.params)

    def test_placeholder_count_flock_performance(self):
        from .llm_sql import ChikoozaLLMTextToSQLService
        svc = ChikoozaLLMTextToSQLService(
            user=self.user,
            groq_client=FakeGroqClient([]),
            entity_resolver=FakeEntityResolver(),
        )
        plan = svc._all_flocks_performance_plan()
        self.assertEqual(self._count_placeholders(plan), len(plan.params))
        self.assertEqual(plan.params, [7, 7, 7, 7])

    def test_placeholder_count_avg_fcr_with_flock(self):
        from .llm_sql import ChikoozaLLMTextToSQLService
        svc = ChikoozaLLMTextToSQLService(
            user=self.user,
            groq_client=FakeGroqClient([]),
            entity_resolver=FakeEntityResolver(),
        )
        plan = svc._avg_fcr_plan(flock_id=77)
        self.assertEqual(self._count_placeholders(plan), len(plan.params))
        self.assertIn(77, plan.params)

    def test_placeholder_count_avg_weight_with_flock(self):
        from .llm_sql import ChikoozaLLMTextToSQLService
        svc = ChikoozaLLMTextToSQLService(
            user=self.user,
            groq_client=FakeGroqClient([]),
            entity_resolver=FakeEntityResolver(),
        )
        plan = svc._avg_weight_plan(flock_id=77)
        self.assertEqual(self._count_placeholders(plan), len(plan.params))
        self.assertIn(77, plan.params)

    def test_placeholder_count_purchases_with_flock(self):
        from .llm_sql import ChikoozaLLMTextToSQLService
        svc = ChikoozaLLMTextToSQLService(
            user=self.user,
            groq_client=FakeGroqClient([]),
            entity_resolver=FakeEntityResolver(),
        )
        plan = svc._purchases_total_plan(flock_id=77)
        self.assertEqual(self._count_placeholders(plan), len(plan.params))
        self.assertIn(77, plan.params)

    def test_placeholder_count_feed_with_flock(self):
        from .llm_sql import ChikoozaLLMTextToSQLService
        svc = ChikoozaLLMTextToSQLService(
            user=self.user,
            groq_client=FakeGroqClient([]),
            entity_resolver=FakeEntityResolver(),
        )
        plan = svc._feed_total_plan(flock_id=77)
        self.assertEqual(self._count_placeholders(plan), len(plan.params))
        self.assertIn(77, plan.params)

    # ==================================================================
    # 31. TENANT SAFETY — all new plans must pass TenantSafeSQLExecutor
    # ==================================================================

    def _validate_plan_tenant_safety(self, plan):
        from .modern_services import TenantSafeSQLExecutor
        executor = TenantSafeSQLExecutor()
        try:
            executor._validate(plan)
        except ValueError as e:
            self.fail(f"TenantSafeSQLExecutor rejected plan metric={plan.metric}: {e}")

    def test_tenant_safety_all_new_deterministic_plans(self):
        from .llm_sql import ChikoozaLLMTextToSQLService, SQLPlan
        svc = ChikoozaLLMTextToSQLService(
            user=self.user,
            groq_client=FakeGroqClient([]),
            entity_resolver=FakeEntityResolver(),
        )
        plans = [
            svc._account_summary_plan(),
            svc._farm_list_plan_llm(),
            svc._flock_list_plan_llm(),
            svc._farm_count_plan(),
            svc._flock_count_plan(),
            svc._sales_total_plan(),
            svc._sales_total_plan(flock_id=77),
            svc._purchases_total_plan(),
            svc._purchases_total_plan(flock_id=77),
            svc._mortality_total_plan(),
            svc._mortality_total_plan(flock_id=77),
            svc._feed_total_plan(),
            svc._feed_total_plan(flock_id=77),
            svc._avg_fcr_plan(),
            svc._avg_fcr_plan(flock_id=77),
            svc._avg_weight_plan(),
            svc._avg_weight_plan(flock_id=77),
            svc._current_birds_plan_llm(),
            svc._current_birds_plan_llm(flock_id=77),
            svc._all_flocks_performance_plan(),
        ]
        for plan in plans:
            with self.subTest(metric=plan.metric, params=plan.params):
                self._validate_plan_tenant_safety(plan)

    # ==================================================================
    # 32. ANSWER PIPELINE — every question returns success with answer text
    # ==================================================================

    def test_answer_text_present_for_all_deterministic_metrics(self):
        """Every question must return a non-empty answer string."""
        questions = [
            "show all farms",
            "show all flocks",
            "how many farms",
            "how many flocks",
            "total sales",
            "total purchases",
            "mortality",
            "current birds",
            "total feed consumed",
            "average fcr",
            "average bird weight",
            "summary",
            "performance of my flocks",
            "most profitable flock",
            "biggest loss flock",
            "most used breed",
        ]
        for question in questions:
            with self.subTest(question=question):
                svc = self._svc()
                result = svc.answer(question)
                self.assertEqual(result["status"], "success",
                                 f"Failed for: {question}")
                self.assertIsNotNone(result.get("answer"),
                                     f"No answer for: {question}")
                self.assertGreater(len(str(result.get("answer", ""))), 0,
                                   f"Empty answer for: {question}")

    def test_generic_followup_breed_all_of_them(self):
        svc = self._svc_flock()
        result = svc.answer(
            "and for all of them?",
            history=[
                {"role": "user", "content": "okay now what is the breed of the current flock"},
                {
                    "role": "assistant",
                    "content": "Alpha Batch is Hubbard.",
                    "metric": "flock_breed",
                    "resolved_flock_id": 77,
                },
            ],
        )
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["metric"], "flock_breeds_by_flock")

    def test_generic_followup_fcr_all_of_them(self):
        svc = self._svc_flock()
        result = svc.answer(
            "and for all of them?",
            history=[
                {"role": "user", "content": "what is FCR of flock 1"},
                {
                    "role": "assistant",
                    "content": "FCR of flock 1 is 1.7",
                    "metric": "average_fcr",
                    "resolved_flock_id": 77,
                },
            ],
        )
        self.assertEqual(result["metric"], "average_fcr")
        # Verify that it is not filtered to a single flock
        self.assertNotIn(77, result["params"])

    def test_comparative_performance_queries_use_all_scope(self):
        svc = self._svc_flock()  # has active flock Alpha Batch / 77 resolved
        result = svc.answer("which is the best performing flock, which is the worst performing flock and which is in the middle zone")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["metric"], "flock_performance")
        # Verify that it is not filtered to a single flock
        self.assertNotIn(77, result["params"])

    def test_is_compound_query_detector(self):
        from .llm_sql import ChikoozaLLMTextToSQLService
        svc = ChikoozaLLMTextToSQLService(
            user=self.user,
            groq_client=FakeGroqClient([]),
            entity_resolver=FakeEntityResolver(),
        )
        self.assertTrue(svc._is_compound_query("what is the FCR and sales of flock complete"))
        self.assertTrue(svc._is_compound_query("average weight and feed consumed"))
        self.assertFalse(svc._is_compound_query("show all flocks"))
        self.assertFalse(svc._is_compound_query("average FCR of complete flock"))

    def test_compound_query_bypasses_deterministic_plans(self):
        from .llm_sql import ChikoozaLLMTextToSQLService
        svc = ChikoozaLLMTextToSQLService(
            user=self.user,
            groq_client=FakeGroqClient([]),
            entity_resolver=FakeEntityResolver(),
        )
        plan = svc._known_safe_plan("average FCR and weight of flocks", history=[])
        self.assertIsNone(plan)

    def test_entity_extraction_from_sql_rows(self):
        from .llm_sql import ChikoozaLLMTextToSQLService, SQLPlan
        svc = ChikoozaLLMTextToSQLService(
            user=self.user,
            groq_client=FakeGroqClient([]),
            entity_resolver=FakeEntityResolver(),
        )
        plan = SQLPlan(sql="SELECT 1", params=[], metric="test", result_type="summary")
        rows = [{"flock_id": 99, "farm_id": 88, "flock_name": "Test Flock"}]
        svc.executor.execute = lambda p: rows
        svc.client.chat = lambda *args, **kwargs: type("FakeResponse", (), {"content": "formatted answer"})()
        result = svc._response_from_plan("what is flock X?", plan, history=[])
        self.assertEqual(result["resolved_flock_id"], 99)
        self.assertEqual(result["resolved_farm_id"], 88)

    def test_long_history_window_retained(self):
        from .llm_sql import ChikoozaSQLPromptBuilder
        builder = ChikoozaSQLPromptBuilder()
        # Create a history of 20 messages (10 turns)
        history = [{"role": "user" if i % 2 == 0 else "assistant", "content": f"msg {i}"} for i in range(20)]
        history_text = builder._history_text(history)
        # Verify that the history text contains messages from the last 16, not just 12
        self.assertIn("msg 4", history_text)
        self.assertNotIn("msg 3", history_text)




class ExhaustiveLongConversationTests(SimpleTestCase):
    """
    Vigorous testing for long conversations up to 12+ messages.
    Ensures context is preserved, IDs are not leaked, and specific scenarios like comparing across farms work.
    """

    def setUp(self):
        self.user = SimpleNamespace(id=7, is_authenticated=True)
        from .llm_sql import ChikoozaLLMTextToSQLService
        self._svc_cls = ChikoozaLLMTextToSQLService

    def _svc(self, entity_context="", groq_responses=None, executor_data=None):
        return _make_llm_service(
            self.user,
            groq_responses=groq_responses,
            entity_context=entity_context,
            executor_data=executor_data,
        )

    def test_specific_user_scenario_least_data(self):
        """Tests the user's specific complaint about 'in all the farms this is the one with least data?'."""
        groq_responses = [
            # Turn 1 answer formatting
            'The flock with the least data is "1" on "complet".',
            # Turn 2 answer formatting
            'Yes, flock 1 has the least data across all farms.',
        ]
        executor_data = [
            [{"flock_name": "1", "count": 0, "farm_id": 99}],
            [{"flock_name": "1", "count": 0}, {"flock_name": "2", "count": 5}]
        ]
        svc = self._svc(groq_responses=groq_responses)
        svc.executor.execute = lambda plan: executor_data.pop(0)
        history = []

        res1 = svc.answer("now tell me the flock with least data", history=history)
        self.assertEqual(res1["status"], "success", res1.get("message"))
        self.assertNotIn("farm_id", res1["message"].lower())
        history.append({"role": "user", "content": "now tell me the flock with least data"})
        history.append({"role": "assistant", "content": res1["message"]})

        res2 = svc.answer("in all the farms this is the one with least data?", history=history)
        self.assertEqual(res2["status"], "success", res2.get("message"))
        self.assertNotIn("farm_id", res2["message"].lower())
        self.assertIn("yes", res2["message"].lower())

    def test_database_id_requests_are_blocked(self):
        """Verifies that queries requesting internal database IDs are blocked."""
        svc = self._svc(groq_responses=[])
        
        # Test farm ID blocking
        res1 = svc.answer("what is my farm id")
        self.assertEqual(res1["status"], "error")
        self.assertEqual(res1["engine"], "groq_sql")
        self.assertIn("cannot display internal database IDs", res1["message"])
        
        # Test flock ID blocking
        res2 = svc.answer("give me the flock ids")
        self.assertEqual(res2["status"], "error")
        self.assertIn("cannot display internal database IDs", res2["message"])

    def test_singular_farm_flock_list_ignores_context_entities(self):
        """Verifies that show farm/flock (singular) does not trigger list plan if active context is present."""
        svc = self._svc(groq_responses=[])
        
        # Singular farm list query should NOT match list template if farm context is present
        self.assertFalse(svc._asks_farm_list("show farm", entity_context="Active app farm context: farm_id=1"))
        self.assertTrue(svc._asks_farm_list("show farm", entity_context=""))
        
        # Singular flock list query should NOT match list template if flock context is present
        self.assertFalse(svc._asks_flock_list("show flock", entity_context="Active app flock context: flock_id=2"))
        self.assertTrue(svc._asks_flock_list("show flock", entity_context=""))
        
        # Plural list queries should ALWAYS match list template
        self.assertTrue(svc._asks_farm_list("show farms", entity_context="Active app farm context: farm_id=1"))
        self.assertTrue(svc._asks_flock_list("show flocks", entity_context="Active app flock context: flock_id=2"))

    def test_relative_current_workspace_queries(self):
        """Verifies that follow-up queries referring to the active/current entity are correctly detected."""
        svc = self._svc(groq_responses=[])
        
        self.assertTrue(svc._asks_current_workspace("only the current one"))
        self.assertTrue(svc._asks_current_workspace("just the active one"))
        self.assertTrue(svc._asks_current_workspace("only the current"))

    def test_long_conversation_flow_1(self):
        """Test conversation path 1 up to 12 turns to ensure no crashes and no ID leaks."""
        groq_responses = []
        for _ in range(15):
            groq_responses.append('```json\n{"sql": "SELECT 1 FROM ai_farm_flock_data_view WHERE owner_id = %s", "params": ["__OWNER_ID__"], "metric": "test_metric", "result_type": "summary"}\n```')
            groq_responses.append('Perfectly correct answer based on SQL data.')
        svc = self._svc(groq_responses=groq_responses)
        svc.executor.execute = lambda plan: [{"flock_name": "Alpha", "farm_id": 88, "flock_id": 99}]
        history = []
        # Turn 1
        result = svc.answer("Question 1", history=history)
        history.append({"role": "user", "content": "Question 1"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 2
        result = svc.answer("Question 2", history=history)
        history.append({"role": "user", "content": "Question 2"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 3
        result = svc.answer("Question 3", history=history)
        history.append({"role": "user", "content": "Question 3"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 4
        result = svc.answer("Question 4", history=history)
        history.append({"role": "user", "content": "Question 4"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 5
        result = svc.answer("Question 5", history=history)
        history.append({"role": "user", "content": "Question 5"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 6
        result = svc.answer("Question 6", history=history)
        history.append({"role": "user", "content": "Question 6"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 7
        result = svc.answer("Question 7", history=history)
        history.append({"role": "user", "content": "Question 7"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 8
        result = svc.answer("Question 8", history=history)
        history.append({"role": "user", "content": "Question 8"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 9
        result = svc.answer("Question 9", history=history)
        history.append({"role": "user", "content": "Question 9"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 10
        result = svc.answer("Question 10", history=history)
        history.append({"role": "user", "content": "Question 10"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 11
        result = svc.answer("Question 11", history=history)
        history.append({"role": "user", "content": "Question 11"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 12
        result = svc.answer("Question 12", history=history)
        history.append({"role": "user", "content": "Question 12"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())

    def test_long_conversation_flow_2(self):
        """Test conversation path 2 up to 12 turns to ensure no crashes and no ID leaks."""
        groq_responses = []
        for _ in range(15):
            groq_responses.append('```json\n{"sql": "SELECT 1 FROM ai_farm_flock_data_view WHERE owner_id = %s", "params": ["__OWNER_ID__"], "metric": "test_metric", "result_type": "summary"}\n```')
            groq_responses.append('Perfectly correct answer based on SQL data.')
        svc = self._svc(groq_responses=groq_responses)
        svc.executor.execute = lambda plan: [{"flock_name": "Alpha", "farm_id": 88, "flock_id": 99}]
        history = []
        # Turn 1
        result = svc.answer("Question 1", history=history)
        history.append({"role": "user", "content": "Question 1"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 2
        result = svc.answer("Question 2", history=history)
        history.append({"role": "user", "content": "Question 2"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 3
        result = svc.answer("Question 3", history=history)
        history.append({"role": "user", "content": "Question 3"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 4
        result = svc.answer("Question 4", history=history)
        history.append({"role": "user", "content": "Question 4"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 5
        result = svc.answer("Question 5", history=history)
        history.append({"role": "user", "content": "Question 5"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 6
        result = svc.answer("Question 6", history=history)
        history.append({"role": "user", "content": "Question 6"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 7
        result = svc.answer("Question 7", history=history)
        history.append({"role": "user", "content": "Question 7"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 8
        result = svc.answer("Question 8", history=history)
        history.append({"role": "user", "content": "Question 8"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 9
        result = svc.answer("Question 9", history=history)
        history.append({"role": "user", "content": "Question 9"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 10
        result = svc.answer("Question 10", history=history)
        history.append({"role": "user", "content": "Question 10"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 11
        result = svc.answer("Question 11", history=history)
        history.append({"role": "user", "content": "Question 11"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 12
        result = svc.answer("Question 12", history=history)
        history.append({"role": "user", "content": "Question 12"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())

    def test_long_conversation_flow_3(self):
        """Test conversation path 3 up to 12 turns to ensure no crashes and no ID leaks."""
        groq_responses = []
        for _ in range(15):
            groq_responses.append('```json\n{"sql": "SELECT 1 FROM ai_farm_flock_data_view WHERE owner_id = %s", "params": ["__OWNER_ID__"], "metric": "test_metric", "result_type": "summary"}\n```')
            groq_responses.append('Perfectly correct answer based on SQL data.')
        svc = self._svc(groq_responses=groq_responses)
        svc.executor.execute = lambda plan: [{"flock_name": "Alpha", "farm_id": 88, "flock_id": 99}]
        history = []
        # Turn 1
        result = svc.answer("Question 1", history=history)
        history.append({"role": "user", "content": "Question 1"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 2
        result = svc.answer("Question 2", history=history)
        history.append({"role": "user", "content": "Question 2"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 3
        result = svc.answer("Question 3", history=history)
        history.append({"role": "user", "content": "Question 3"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 4
        result = svc.answer("Question 4", history=history)
        history.append({"role": "user", "content": "Question 4"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 5
        result = svc.answer("Question 5", history=history)
        history.append({"role": "user", "content": "Question 5"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 6
        result = svc.answer("Question 6", history=history)
        history.append({"role": "user", "content": "Question 6"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 7
        result = svc.answer("Question 7", history=history)
        history.append({"role": "user", "content": "Question 7"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 8
        result = svc.answer("Question 8", history=history)
        history.append({"role": "user", "content": "Question 8"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 9
        result = svc.answer("Question 9", history=history)
        history.append({"role": "user", "content": "Question 9"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 10
        result = svc.answer("Question 10", history=history)
        history.append({"role": "user", "content": "Question 10"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 11
        result = svc.answer("Question 11", history=history)
        history.append({"role": "user", "content": "Question 11"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 12
        result = svc.answer("Question 12", history=history)
        history.append({"role": "user", "content": "Question 12"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())

    def test_long_conversation_flow_4(self):
        """Test conversation path 4 up to 12 turns to ensure no crashes and no ID leaks."""
        groq_responses = []
        for _ in range(15):
            groq_responses.append('```json\n{"sql": "SELECT 1 FROM ai_farm_flock_data_view WHERE owner_id = %s", "params": ["__OWNER_ID__"], "metric": "test_metric", "result_type": "summary"}\n```')
            groq_responses.append('Perfectly correct answer based on SQL data.')
        svc = self._svc(groq_responses=groq_responses)
        svc.executor.execute = lambda plan: [{"flock_name": "Alpha", "farm_id": 88, "flock_id": 99}]
        history = []
        # Turn 1
        result = svc.answer("Question 1", history=history)
        history.append({"role": "user", "content": "Question 1"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 2
        result = svc.answer("Question 2", history=history)
        history.append({"role": "user", "content": "Question 2"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 3
        result = svc.answer("Question 3", history=history)
        history.append({"role": "user", "content": "Question 3"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 4
        result = svc.answer("Question 4", history=history)
        history.append({"role": "user", "content": "Question 4"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 5
        result = svc.answer("Question 5", history=history)
        history.append({"role": "user", "content": "Question 5"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 6
        result = svc.answer("Question 6", history=history)
        history.append({"role": "user", "content": "Question 6"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 7
        result = svc.answer("Question 7", history=history)
        history.append({"role": "user", "content": "Question 7"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 8
        result = svc.answer("Question 8", history=history)
        history.append({"role": "user", "content": "Question 8"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 9
        result = svc.answer("Question 9", history=history)
        history.append({"role": "user", "content": "Question 9"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 10
        result = svc.answer("Question 10", history=history)
        history.append({"role": "user", "content": "Question 10"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 11
        result = svc.answer("Question 11", history=history)
        history.append({"role": "user", "content": "Question 11"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 12
        result = svc.answer("Question 12", history=history)
        history.append({"role": "user", "content": "Question 12"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())

    def test_long_conversation_flow_5(self):
        """Test conversation path 5 up to 12 turns to ensure no crashes and no ID leaks."""
        groq_responses = []
        for _ in range(15):
            groq_responses.append('```json\n{"sql": "SELECT 1 FROM ai_farm_flock_data_view WHERE owner_id = %s", "params": ["__OWNER_ID__"], "metric": "test_metric", "result_type": "summary"}\n```')
            groq_responses.append('Perfectly correct answer based on SQL data.')
        svc = self._svc(groq_responses=groq_responses)
        svc.executor.execute = lambda plan: [{"flock_name": "Alpha", "farm_id": 88, "flock_id": 99}]
        history = []
        # Turn 1
        result = svc.answer("Question 1", history=history)
        history.append({"role": "user", "content": "Question 1"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 2
        result = svc.answer("Question 2", history=history)
        history.append({"role": "user", "content": "Question 2"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 3
        result = svc.answer("Question 3", history=history)
        history.append({"role": "user", "content": "Question 3"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 4
        result = svc.answer("Question 4", history=history)
        history.append({"role": "user", "content": "Question 4"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 5
        result = svc.answer("Question 5", history=history)
        history.append({"role": "user", "content": "Question 5"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 6
        result = svc.answer("Question 6", history=history)
        history.append({"role": "user", "content": "Question 6"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 7
        result = svc.answer("Question 7", history=history)
        history.append({"role": "user", "content": "Question 7"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 8
        result = svc.answer("Question 8", history=history)
        history.append({"role": "user", "content": "Question 8"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 9
        result = svc.answer("Question 9", history=history)
        history.append({"role": "user", "content": "Question 9"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 10
        result = svc.answer("Question 10", history=history)
        history.append({"role": "user", "content": "Question 10"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 11
        result = svc.answer("Question 11", history=history)
        history.append({"role": "user", "content": "Question 11"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 12
        result = svc.answer("Question 12", history=history)
        history.append({"role": "user", "content": "Question 12"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())

    def test_long_conversation_flow_6(self):
        """Test conversation path 6 up to 12 turns to ensure no crashes and no ID leaks."""
        groq_responses = []
        for _ in range(15):
            groq_responses.append('```json\n{"sql": "SELECT 1 FROM ai_farm_flock_data_view WHERE owner_id = %s", "params": ["__OWNER_ID__"], "metric": "test_metric", "result_type": "summary"}\n```')
            groq_responses.append('Perfectly correct answer based on SQL data.')
        svc = self._svc(groq_responses=groq_responses)
        svc.executor.execute = lambda plan: [{"flock_name": "Alpha", "farm_id": 88, "flock_id": 99}]
        history = []
        # Turn 1
        result = svc.answer("Question 1", history=history)
        history.append({"role": "user", "content": "Question 1"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 2
        result = svc.answer("Question 2", history=history)
        history.append({"role": "user", "content": "Question 2"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 3
        result = svc.answer("Question 3", history=history)
        history.append({"role": "user", "content": "Question 3"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 4
        result = svc.answer("Question 4", history=history)
        history.append({"role": "user", "content": "Question 4"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 5
        result = svc.answer("Question 5", history=history)
        history.append({"role": "user", "content": "Question 5"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 6
        result = svc.answer("Question 6", history=history)
        history.append({"role": "user", "content": "Question 6"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 7
        result = svc.answer("Question 7", history=history)
        history.append({"role": "user", "content": "Question 7"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 8
        result = svc.answer("Question 8", history=history)
        history.append({"role": "user", "content": "Question 8"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 9
        result = svc.answer("Question 9", history=history)
        history.append({"role": "user", "content": "Question 9"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 10
        result = svc.answer("Question 10", history=history)
        history.append({"role": "user", "content": "Question 10"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 11
        result = svc.answer("Question 11", history=history)
        history.append({"role": "user", "content": "Question 11"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 12
        result = svc.answer("Question 12", history=history)
        history.append({"role": "user", "content": "Question 12"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())

    def test_long_conversation_flow_7(self):
        """Test conversation path 7 up to 12 turns to ensure no crashes and no ID leaks."""
        groq_responses = []
        for _ in range(15):
            groq_responses.append('```json\n{"sql": "SELECT 1 FROM ai_farm_flock_data_view WHERE owner_id = %s", "params": ["__OWNER_ID__"], "metric": "test_metric", "result_type": "summary"}\n```')
            groq_responses.append('Perfectly correct answer based on SQL data.')
        svc = self._svc(groq_responses=groq_responses)
        svc.executor.execute = lambda plan: [{"flock_name": "Alpha", "farm_id": 88, "flock_id": 99}]
        history = []
        # Turn 1
        result = svc.answer("Question 1", history=history)
        history.append({"role": "user", "content": "Question 1"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 2
        result = svc.answer("Question 2", history=history)
        history.append({"role": "user", "content": "Question 2"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 3
        result = svc.answer("Question 3", history=history)
        history.append({"role": "user", "content": "Question 3"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 4
        result = svc.answer("Question 4", history=history)
        history.append({"role": "user", "content": "Question 4"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 5
        result = svc.answer("Question 5", history=history)
        history.append({"role": "user", "content": "Question 5"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 6
        result = svc.answer("Question 6", history=history)
        history.append({"role": "user", "content": "Question 6"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 7
        result = svc.answer("Question 7", history=history)
        history.append({"role": "user", "content": "Question 7"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 8
        result = svc.answer("Question 8", history=history)
        history.append({"role": "user", "content": "Question 8"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 9
        result = svc.answer("Question 9", history=history)
        history.append({"role": "user", "content": "Question 9"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 10
        result = svc.answer("Question 10", history=history)
        history.append({"role": "user", "content": "Question 10"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 11
        result = svc.answer("Question 11", history=history)
        history.append({"role": "user", "content": "Question 11"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 12
        result = svc.answer("Question 12", history=history)
        history.append({"role": "user", "content": "Question 12"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())

    def test_long_conversation_flow_8(self):
        """Test conversation path 8 up to 12 turns to ensure no crashes and no ID leaks."""
        groq_responses = []
        for _ in range(15):
            groq_responses.append('```json\n{"sql": "SELECT 1 FROM ai_farm_flock_data_view WHERE owner_id = %s", "params": ["__OWNER_ID__"], "metric": "test_metric", "result_type": "summary"}\n```')
            groq_responses.append('Perfectly correct answer based on SQL data.')
        svc = self._svc(groq_responses=groq_responses)
        svc.executor.execute = lambda plan: [{"flock_name": "Alpha", "farm_id": 88, "flock_id": 99}]
        history = []
        # Turn 1
        result = svc.answer("Question 1", history=history)
        history.append({"role": "user", "content": "Question 1"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 2
        result = svc.answer("Question 2", history=history)
        history.append({"role": "user", "content": "Question 2"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 3
        result = svc.answer("Question 3", history=history)
        history.append({"role": "user", "content": "Question 3"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 4
        result = svc.answer("Question 4", history=history)
        history.append({"role": "user", "content": "Question 4"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 5
        result = svc.answer("Question 5", history=history)
        history.append({"role": "user", "content": "Question 5"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 6
        result = svc.answer("Question 6", history=history)
        history.append({"role": "user", "content": "Question 6"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 7
        result = svc.answer("Question 7", history=history)
        history.append({"role": "user", "content": "Question 7"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 8
        result = svc.answer("Question 8", history=history)
        history.append({"role": "user", "content": "Question 8"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 9
        result = svc.answer("Question 9", history=history)
        history.append({"role": "user", "content": "Question 9"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 10
        result = svc.answer("Question 10", history=history)
        history.append({"role": "user", "content": "Question 10"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 11
        result = svc.answer("Question 11", history=history)
        history.append({"role": "user", "content": "Question 11"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 12
        result = svc.answer("Question 12", history=history)
        history.append({"role": "user", "content": "Question 12"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())

    def test_long_conversation_flow_9(self):
        """Test conversation path 9 up to 12 turns to ensure no crashes and no ID leaks."""
        groq_responses = []
        for _ in range(15):
            groq_responses.append('```json\n{"sql": "SELECT 1 FROM ai_farm_flock_data_view WHERE owner_id = %s", "params": ["__OWNER_ID__"], "metric": "test_metric", "result_type": "summary"}\n```')
            groq_responses.append('Perfectly correct answer based on SQL data.')
        svc = self._svc(groq_responses=groq_responses)
        svc.executor.execute = lambda plan: [{"flock_name": "Alpha", "farm_id": 88, "flock_id": 99}]
        history = []
        # Turn 1
        result = svc.answer("Question 1", history=history)
        history.append({"role": "user", "content": "Question 1"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 2
        result = svc.answer("Question 2", history=history)
        history.append({"role": "user", "content": "Question 2"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 3
        result = svc.answer("Question 3", history=history)
        history.append({"role": "user", "content": "Question 3"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 4
        result = svc.answer("Question 4", history=history)
        history.append({"role": "user", "content": "Question 4"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 5
        result = svc.answer("Question 5", history=history)
        history.append({"role": "user", "content": "Question 5"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 6
        result = svc.answer("Question 6", history=history)
        history.append({"role": "user", "content": "Question 6"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 7
        result = svc.answer("Question 7", history=history)
        history.append({"role": "user", "content": "Question 7"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 8
        result = svc.answer("Question 8", history=history)
        history.append({"role": "user", "content": "Question 8"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 9
        result = svc.answer("Question 9", history=history)
        history.append({"role": "user", "content": "Question 9"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 10
        result = svc.answer("Question 10", history=history)
        history.append({"role": "user", "content": "Question 10"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 11
        result = svc.answer("Question 11", history=history)
        history.append({"role": "user", "content": "Question 11"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 12
        result = svc.answer("Question 12", history=history)
        history.append({"role": "user", "content": "Question 12"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())

    def test_long_conversation_flow_10(self):
        """Test conversation path 10 up to 12 turns to ensure no crashes and no ID leaks."""
        groq_responses = []
        for _ in range(15):
            groq_responses.append('```json\n{"sql": "SELECT 1 FROM ai_farm_flock_data_view WHERE owner_id = %s", "params": ["__OWNER_ID__"], "metric": "test_metric", "result_type": "summary"}\n```')
            groq_responses.append('Perfectly correct answer based on SQL data.')
        svc = self._svc(groq_responses=groq_responses)
        svc.executor.execute = lambda plan: [{"flock_name": "Alpha", "farm_id": 88, "flock_id": 99}]
        history = []
        # Turn 1
        result = svc.answer("Question 1", history=history)
        history.append({"role": "user", "content": "Question 1"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 2
        result = svc.answer("Question 2", history=history)
        history.append({"role": "user", "content": "Question 2"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 3
        result = svc.answer("Question 3", history=history)
        history.append({"role": "user", "content": "Question 3"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 4
        result = svc.answer("Question 4", history=history)
        history.append({"role": "user", "content": "Question 4"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 5
        result = svc.answer("Question 5", history=history)
        history.append({"role": "user", "content": "Question 5"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 6
        result = svc.answer("Question 6", history=history)
        history.append({"role": "user", "content": "Question 6"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 7
        result = svc.answer("Question 7", history=history)
        history.append({"role": "user", "content": "Question 7"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 8
        result = svc.answer("Question 8", history=history)
        history.append({"role": "user", "content": "Question 8"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 9
        result = svc.answer("Question 9", history=history)
        history.append({"role": "user", "content": "Question 9"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 10
        result = svc.answer("Question 10", history=history)
        history.append({"role": "user", "content": "Question 10"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 11
        result = svc.answer("Question 11", history=history)
        history.append({"role": "user", "content": "Question 11"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 12
        result = svc.answer("Question 12", history=history)
        history.append({"role": "user", "content": "Question 12"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())

    def test_long_conversation_flow_11(self):
        """Test conversation path 11 up to 12 turns to ensure no crashes and no ID leaks."""
        groq_responses = []
        for _ in range(15):
            groq_responses.append('```json\n{"sql": "SELECT 1 FROM ai_farm_flock_data_view WHERE owner_id = %s", "params": ["__OWNER_ID__"], "metric": "test_metric", "result_type": "summary"}\n```')
            groq_responses.append('Perfectly correct answer based on SQL data.')
        svc = self._svc(groq_responses=groq_responses)
        svc.executor.execute = lambda plan: [{"flock_name": "Alpha", "farm_id": 88, "flock_id": 99}]
        history = []
        # Turn 1
        result = svc.answer("Question 1", history=history)
        history.append({"role": "user", "content": "Question 1"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 2
        result = svc.answer("Question 2", history=history)
        history.append({"role": "user", "content": "Question 2"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 3
        result = svc.answer("Question 3", history=history)
        history.append({"role": "user", "content": "Question 3"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 4
        result = svc.answer("Question 4", history=history)
        history.append({"role": "user", "content": "Question 4"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 5
        result = svc.answer("Question 5", history=history)
        history.append({"role": "user", "content": "Question 5"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 6
        result = svc.answer("Question 6", history=history)
        history.append({"role": "user", "content": "Question 6"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 7
        result = svc.answer("Question 7", history=history)
        history.append({"role": "user", "content": "Question 7"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 8
        result = svc.answer("Question 8", history=history)
        history.append({"role": "user", "content": "Question 8"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 9
        result = svc.answer("Question 9", history=history)
        history.append({"role": "user", "content": "Question 9"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 10
        result = svc.answer("Question 10", history=history)
        history.append({"role": "user", "content": "Question 10"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 11
        result = svc.answer("Question 11", history=history)
        history.append({"role": "user", "content": "Question 11"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 12
        result = svc.answer("Question 12", history=history)
        history.append({"role": "user", "content": "Question 12"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())

    def test_long_conversation_flow_12(self):
        """Test conversation path 12 up to 12 turns to ensure no crashes and no ID leaks."""
        groq_responses = []
        for _ in range(15):
            groq_responses.append('```json\n{"sql": "SELECT 1 FROM ai_farm_flock_data_view WHERE owner_id = %s", "params": ["__OWNER_ID__"], "metric": "test_metric", "result_type": "summary"}\n```')
            groq_responses.append('Perfectly correct answer based on SQL data.')
        svc = self._svc(groq_responses=groq_responses)
        svc.executor.execute = lambda plan: [{"flock_name": "Alpha", "farm_id": 88, "flock_id": 99}]
        history = []
        # Turn 1
        result = svc.answer("Question 1", history=history)
        history.append({"role": "user", "content": "Question 1"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 2
        result = svc.answer("Question 2", history=history)
        history.append({"role": "user", "content": "Question 2"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 3
        result = svc.answer("Question 3", history=history)
        history.append({"role": "user", "content": "Question 3"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 4
        result = svc.answer("Question 4", history=history)
        history.append({"role": "user", "content": "Question 4"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 5
        result = svc.answer("Question 5", history=history)
        history.append({"role": "user", "content": "Question 5"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 6
        result = svc.answer("Question 6", history=history)
        history.append({"role": "user", "content": "Question 6"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 7
        result = svc.answer("Question 7", history=history)
        history.append({"role": "user", "content": "Question 7"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 8
        result = svc.answer("Question 8", history=history)
        history.append({"role": "user", "content": "Question 8"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 9
        result = svc.answer("Question 9", history=history)
        history.append({"role": "user", "content": "Question 9"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 10
        result = svc.answer("Question 10", history=history)
        history.append({"role": "user", "content": "Question 10"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 11
        result = svc.answer("Question 11", history=history)
        history.append({"role": "user", "content": "Question 11"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 12
        result = svc.answer("Question 12", history=history)
        history.append({"role": "user", "content": "Question 12"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())

    def test_long_conversation_flow_13(self):
        """Test conversation path 13 up to 12 turns to ensure no crashes and no ID leaks."""
        groq_responses = []
        for _ in range(15):
            groq_responses.append('```json\n{"sql": "SELECT 1 FROM ai_farm_flock_data_view WHERE owner_id = %s", "params": ["__OWNER_ID__"], "metric": "test_metric", "result_type": "summary"}\n```')
            groq_responses.append('Perfectly correct answer based on SQL data.')
        svc = self._svc(groq_responses=groq_responses)
        svc.executor.execute = lambda plan: [{"flock_name": "Alpha", "farm_id": 88, "flock_id": 99}]
        history = []
        # Turn 1
        result = svc.answer("Question 1", history=history)
        history.append({"role": "user", "content": "Question 1"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 2
        result = svc.answer("Question 2", history=history)
        history.append({"role": "user", "content": "Question 2"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 3
        result = svc.answer("Question 3", history=history)
        history.append({"role": "user", "content": "Question 3"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 4
        result = svc.answer("Question 4", history=history)
        history.append({"role": "user", "content": "Question 4"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 5
        result = svc.answer("Question 5", history=history)
        history.append({"role": "user", "content": "Question 5"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 6
        result = svc.answer("Question 6", history=history)
        history.append({"role": "user", "content": "Question 6"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 7
        result = svc.answer("Question 7", history=history)
        history.append({"role": "user", "content": "Question 7"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 8
        result = svc.answer("Question 8", history=history)
        history.append({"role": "user", "content": "Question 8"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 9
        result = svc.answer("Question 9", history=history)
        history.append({"role": "user", "content": "Question 9"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 10
        result = svc.answer("Question 10", history=history)
        history.append({"role": "user", "content": "Question 10"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 11
        result = svc.answer("Question 11", history=history)
        history.append({"role": "user", "content": "Question 11"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 12
        result = svc.answer("Question 12", history=history)
        history.append({"role": "user", "content": "Question 12"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())

    def test_long_conversation_flow_14(self):
        """Test conversation path 14 up to 12 turns to ensure no crashes and no ID leaks."""
        groq_responses = []
        for _ in range(15):
            groq_responses.append('```json\n{"sql": "SELECT 1 FROM ai_farm_flock_data_view WHERE owner_id = %s", "params": ["__OWNER_ID__"], "metric": "test_metric", "result_type": "summary"}\n```')
            groq_responses.append('Perfectly correct answer based on SQL data.')
        svc = self._svc(groq_responses=groq_responses)
        svc.executor.execute = lambda plan: [{"flock_name": "Alpha", "farm_id": 88, "flock_id": 99}]
        history = []
        # Turn 1
        result = svc.answer("Question 1", history=history)
        history.append({"role": "user", "content": "Question 1"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 2
        result = svc.answer("Question 2", history=history)
        history.append({"role": "user", "content": "Question 2"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 3
        result = svc.answer("Question 3", history=history)
        history.append({"role": "user", "content": "Question 3"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 4
        result = svc.answer("Question 4", history=history)
        history.append({"role": "user", "content": "Question 4"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 5
        result = svc.answer("Question 5", history=history)
        history.append({"role": "user", "content": "Question 5"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 6
        result = svc.answer("Question 6", history=history)
        history.append({"role": "user", "content": "Question 6"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 7
        result = svc.answer("Question 7", history=history)
        history.append({"role": "user", "content": "Question 7"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 8
        result = svc.answer("Question 8", history=history)
        history.append({"role": "user", "content": "Question 8"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 9
        result = svc.answer("Question 9", history=history)
        history.append({"role": "user", "content": "Question 9"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 10
        result = svc.answer("Question 10", history=history)
        history.append({"role": "user", "content": "Question 10"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 11
        result = svc.answer("Question 11", history=history)
        history.append({"role": "user", "content": "Question 11"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 12
        result = svc.answer("Question 12", history=history)
        history.append({"role": "user", "content": "Question 12"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())

    def test_long_conversation_flow_15(self):
        """Test conversation path 15 up to 12 turns to ensure no crashes and no ID leaks."""
        groq_responses = []
        for _ in range(15):
            groq_responses.append('```json\n{"sql": "SELECT 1 FROM ai_farm_flock_data_view WHERE owner_id = %s", "params": ["__OWNER_ID__"], "metric": "test_metric", "result_type": "summary"}\n```')
            groq_responses.append('Perfectly correct answer based on SQL data.')
        svc = self._svc(groq_responses=groq_responses)
        svc.executor.execute = lambda plan: [{"flock_name": "Alpha", "farm_id": 88, "flock_id": 99}]
        history = []
        # Turn 1
        result = svc.answer("Question 1", history=history)
        history.append({"role": "user", "content": "Question 1"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 2
        result = svc.answer("Question 2", history=history)
        history.append({"role": "user", "content": "Question 2"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 3
        result = svc.answer("Question 3", history=history)
        history.append({"role": "user", "content": "Question 3"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 4
        result = svc.answer("Question 4", history=history)
        history.append({"role": "user", "content": "Question 4"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 5
        result = svc.answer("Question 5", history=history)
        history.append({"role": "user", "content": "Question 5"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 6
        result = svc.answer("Question 6", history=history)
        history.append({"role": "user", "content": "Question 6"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 7
        result = svc.answer("Question 7", history=history)
        history.append({"role": "user", "content": "Question 7"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 8
        result = svc.answer("Question 8", history=history)
        history.append({"role": "user", "content": "Question 8"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 9
        result = svc.answer("Question 9", history=history)
        history.append({"role": "user", "content": "Question 9"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 10
        result = svc.answer("Question 10", history=history)
        history.append({"role": "user", "content": "Question 10"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 11
        result = svc.answer("Question 11", history=history)
        history.append({"role": "user", "content": "Question 11"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 12
        result = svc.answer("Question 12", history=history)
        history.append({"role": "user", "content": "Question 12"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())

    def test_long_conversation_flow_16(self):
        """Test conversation path 16 up to 12 turns to ensure no crashes and no ID leaks."""
        groq_responses = []
        for _ in range(15):
            groq_responses.append('```json\n{"sql": "SELECT 1 FROM ai_farm_flock_data_view WHERE owner_id = %s", "params": ["__OWNER_ID__"], "metric": "test_metric", "result_type": "summary"}\n```')
            groq_responses.append('Perfectly correct answer based on SQL data.')
        svc = self._svc(groq_responses=groq_responses)
        svc.executor.execute = lambda plan: [{"flock_name": "Alpha", "farm_id": 88, "flock_id": 99}]
        history = []
        # Turn 1
        result = svc.answer("Question 1", history=history)
        history.append({"role": "user", "content": "Question 1"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 2
        result = svc.answer("Question 2", history=history)
        history.append({"role": "user", "content": "Question 2"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 3
        result = svc.answer("Question 3", history=history)
        history.append({"role": "user", "content": "Question 3"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 4
        result = svc.answer("Question 4", history=history)
        history.append({"role": "user", "content": "Question 4"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 5
        result = svc.answer("Question 5", history=history)
        history.append({"role": "user", "content": "Question 5"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 6
        result = svc.answer("Question 6", history=history)
        history.append({"role": "user", "content": "Question 6"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 7
        result = svc.answer("Question 7", history=history)
        history.append({"role": "user", "content": "Question 7"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 8
        result = svc.answer("Question 8", history=history)
        history.append({"role": "user", "content": "Question 8"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 9
        result = svc.answer("Question 9", history=history)
        history.append({"role": "user", "content": "Question 9"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 10
        result = svc.answer("Question 10", history=history)
        history.append({"role": "user", "content": "Question 10"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 11
        result = svc.answer("Question 11", history=history)
        history.append({"role": "user", "content": "Question 11"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 12
        result = svc.answer("Question 12", history=history)
        history.append({"role": "user", "content": "Question 12"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())

    def test_long_conversation_flow_17(self):
        """Test conversation path 17 up to 12 turns to ensure no crashes and no ID leaks."""
        groq_responses = []
        for _ in range(15):
            groq_responses.append('```json\n{"sql": "SELECT 1 FROM ai_farm_flock_data_view WHERE owner_id = %s", "params": ["__OWNER_ID__"], "metric": "test_metric", "result_type": "summary"}\n```')
            groq_responses.append('Perfectly correct answer based on SQL data.')
        svc = self._svc(groq_responses=groq_responses)
        svc.executor.execute = lambda plan: [{"flock_name": "Alpha", "farm_id": 88, "flock_id": 99}]
        history = []
        # Turn 1
        result = svc.answer("Question 1", history=history)
        history.append({"role": "user", "content": "Question 1"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 2
        result = svc.answer("Question 2", history=history)
        history.append({"role": "user", "content": "Question 2"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 3
        result = svc.answer("Question 3", history=history)
        history.append({"role": "user", "content": "Question 3"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 4
        result = svc.answer("Question 4", history=history)
        history.append({"role": "user", "content": "Question 4"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 5
        result = svc.answer("Question 5", history=history)
        history.append({"role": "user", "content": "Question 5"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 6
        result = svc.answer("Question 6", history=history)
        history.append({"role": "user", "content": "Question 6"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 7
        result = svc.answer("Question 7", history=history)
        history.append({"role": "user", "content": "Question 7"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 8
        result = svc.answer("Question 8", history=history)
        history.append({"role": "user", "content": "Question 8"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 9
        result = svc.answer("Question 9", history=history)
        history.append({"role": "user", "content": "Question 9"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 10
        result = svc.answer("Question 10", history=history)
        history.append({"role": "user", "content": "Question 10"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 11
        result = svc.answer("Question 11", history=history)
        history.append({"role": "user", "content": "Question 11"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 12
        result = svc.answer("Question 12", history=history)
        history.append({"role": "user", "content": "Question 12"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())

    def test_long_conversation_flow_18(self):
        """Test conversation path 18 up to 12 turns to ensure no crashes and no ID leaks."""
        groq_responses = []
        for _ in range(15):
            groq_responses.append('```json\n{"sql": "SELECT 1 FROM ai_farm_flock_data_view WHERE owner_id = %s", "params": ["__OWNER_ID__"], "metric": "test_metric", "result_type": "summary"}\n```')
            groq_responses.append('Perfectly correct answer based on SQL data.')
        svc = self._svc(groq_responses=groq_responses)
        svc.executor.execute = lambda plan: [{"flock_name": "Alpha", "farm_id": 88, "flock_id": 99}]
        history = []
        # Turn 1
        result = svc.answer("Question 1", history=history)
        history.append({"role": "user", "content": "Question 1"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 2
        result = svc.answer("Question 2", history=history)
        history.append({"role": "user", "content": "Question 2"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 3
        result = svc.answer("Question 3", history=history)
        history.append({"role": "user", "content": "Question 3"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 4
        result = svc.answer("Question 4", history=history)
        history.append({"role": "user", "content": "Question 4"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 5
        result = svc.answer("Question 5", history=history)
        history.append({"role": "user", "content": "Question 5"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 6
        result = svc.answer("Question 6", history=history)
        history.append({"role": "user", "content": "Question 6"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 7
        result = svc.answer("Question 7", history=history)
        history.append({"role": "user", "content": "Question 7"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 8
        result = svc.answer("Question 8", history=history)
        history.append({"role": "user", "content": "Question 8"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 9
        result = svc.answer("Question 9", history=history)
        history.append({"role": "user", "content": "Question 9"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 10
        result = svc.answer("Question 10", history=history)
        history.append({"role": "user", "content": "Question 10"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 11
        result = svc.answer("Question 11", history=history)
        history.append({"role": "user", "content": "Question 11"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 12
        result = svc.answer("Question 12", history=history)
        history.append({"role": "user", "content": "Question 12"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())

    def test_long_conversation_flow_19(self):
        """Test conversation path 19 up to 12 turns to ensure no crashes and no ID leaks."""
        groq_responses = []
        for _ in range(15):
            groq_responses.append('```json\n{"sql": "SELECT 1 FROM ai_farm_flock_data_view WHERE owner_id = %s", "params": ["__OWNER_ID__"], "metric": "test_metric", "result_type": "summary"}\n```')
            groq_responses.append('Perfectly correct answer based on SQL data.')
        svc = self._svc(groq_responses=groq_responses)
        svc.executor.execute = lambda plan: [{"flock_name": "Alpha", "farm_id": 88, "flock_id": 99}]
        history = []
        # Turn 1
        result = svc.answer("Question 1", history=history)
        history.append({"role": "user", "content": "Question 1"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 2
        result = svc.answer("Question 2", history=history)
        history.append({"role": "user", "content": "Question 2"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 3
        result = svc.answer("Question 3", history=history)
        history.append({"role": "user", "content": "Question 3"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 4
        result = svc.answer("Question 4", history=history)
        history.append({"role": "user", "content": "Question 4"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 5
        result = svc.answer("Question 5", history=history)
        history.append({"role": "user", "content": "Question 5"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 6
        result = svc.answer("Question 6", history=history)
        history.append({"role": "user", "content": "Question 6"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 7
        result = svc.answer("Question 7", history=history)
        history.append({"role": "user", "content": "Question 7"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 8
        result = svc.answer("Question 8", history=history)
        history.append({"role": "user", "content": "Question 8"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 9
        result = svc.answer("Question 9", history=history)
        history.append({"role": "user", "content": "Question 9"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 10
        result = svc.answer("Question 10", history=history)
        history.append({"role": "user", "content": "Question 10"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 11
        result = svc.answer("Question 11", history=history)
        history.append({"role": "user", "content": "Question 11"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 12
        result = svc.answer("Question 12", history=history)
        history.append({"role": "user", "content": "Question 12"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())

    def test_long_conversation_flow_20(self):
        """Test conversation path 20 up to 12 turns to ensure no crashes and no ID leaks."""
        groq_responses = []
        for _ in range(15):
            groq_responses.append('```json\n{"sql": "SELECT 1 FROM ai_farm_flock_data_view WHERE owner_id = %s", "params": ["__OWNER_ID__"], "metric": "test_metric", "result_type": "summary"}\n```')
            groq_responses.append('Perfectly correct answer based on SQL data.')
        svc = self._svc(groq_responses=groq_responses)
        svc.executor.execute = lambda plan: [{"flock_name": "Alpha", "farm_id": 88, "flock_id": 99}]
        history = []
        # Turn 1
        result = svc.answer("Question 1", history=history)
        history.append({"role": "user", "content": "Question 1"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 2
        result = svc.answer("Question 2", history=history)
        history.append({"role": "user", "content": "Question 2"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 3
        result = svc.answer("Question 3", history=history)
        history.append({"role": "user", "content": "Question 3"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 4
        result = svc.answer("Question 4", history=history)
        history.append({"role": "user", "content": "Question 4"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 5
        result = svc.answer("Question 5", history=history)
        history.append({"role": "user", "content": "Question 5"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 6
        result = svc.answer("Question 6", history=history)
        history.append({"role": "user", "content": "Question 6"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 7
        result = svc.answer("Question 7", history=history)
        history.append({"role": "user", "content": "Question 7"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 8
        result = svc.answer("Question 8", history=history)
        history.append({"role": "user", "content": "Question 8"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 9
        result = svc.answer("Question 9", history=history)
        history.append({"role": "user", "content": "Question 9"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 10
        result = svc.answer("Question 10", history=history)
        history.append({"role": "user", "content": "Question 10"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 11
        result = svc.answer("Question 11", history=history)
        history.append({"role": "user", "content": "Question 11"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 12
        result = svc.answer("Question 12", history=history)
        history.append({"role": "user", "content": "Question 12"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())

    def test_long_conversation_flow_21(self):
        """Test conversation path 21 up to 12 turns to ensure no crashes and no ID leaks."""
        groq_responses = []
        for _ in range(15):
            groq_responses.append('```json\n{"sql": "SELECT 1 FROM ai_farm_flock_data_view WHERE owner_id = %s", "params": ["__OWNER_ID__"], "metric": "test_metric", "result_type": "summary"}\n```')
            groq_responses.append('Perfectly correct answer based on SQL data.')
        svc = self._svc(groq_responses=groq_responses)
        svc.executor.execute = lambda plan: [{"flock_name": "Alpha", "farm_id": 88, "flock_id": 99}]
        history = []
        # Turn 1
        result = svc.answer("Question 1", history=history)
        history.append({"role": "user", "content": "Question 1"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 2
        result = svc.answer("Question 2", history=history)
        history.append({"role": "user", "content": "Question 2"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 3
        result = svc.answer("Question 3", history=history)
        history.append({"role": "user", "content": "Question 3"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 4
        result = svc.answer("Question 4", history=history)
        history.append({"role": "user", "content": "Question 4"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 5
        result = svc.answer("Question 5", history=history)
        history.append({"role": "user", "content": "Question 5"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 6
        result = svc.answer("Question 6", history=history)
        history.append({"role": "user", "content": "Question 6"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 7
        result = svc.answer("Question 7", history=history)
        history.append({"role": "user", "content": "Question 7"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 8
        result = svc.answer("Question 8", history=history)
        history.append({"role": "user", "content": "Question 8"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 9
        result = svc.answer("Question 9", history=history)
        history.append({"role": "user", "content": "Question 9"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 10
        result = svc.answer("Question 10", history=history)
        history.append({"role": "user", "content": "Question 10"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 11
        result = svc.answer("Question 11", history=history)
        history.append({"role": "user", "content": "Question 11"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 12
        result = svc.answer("Question 12", history=history)
        history.append({"role": "user", "content": "Question 12"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())

    def test_long_conversation_flow_22(self):
        """Test conversation path 22 up to 12 turns to ensure no crashes and no ID leaks."""
        groq_responses = []
        for _ in range(15):
            groq_responses.append('```json\n{"sql": "SELECT 1 FROM ai_farm_flock_data_view WHERE owner_id = %s", "params": ["__OWNER_ID__"], "metric": "test_metric", "result_type": "summary"}\n```')
            groq_responses.append('Perfectly correct answer based on SQL data.')
        svc = self._svc(groq_responses=groq_responses)
        svc.executor.execute = lambda plan: [{"flock_name": "Alpha", "farm_id": 88, "flock_id": 99}]
        history = []
        # Turn 1
        result = svc.answer("Question 1", history=history)
        history.append({"role": "user", "content": "Question 1"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 2
        result = svc.answer("Question 2", history=history)
        history.append({"role": "user", "content": "Question 2"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 3
        result = svc.answer("Question 3", history=history)
        history.append({"role": "user", "content": "Question 3"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 4
        result = svc.answer("Question 4", history=history)
        history.append({"role": "user", "content": "Question 4"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 5
        result = svc.answer("Question 5", history=history)
        history.append({"role": "user", "content": "Question 5"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 6
        result = svc.answer("Question 6", history=history)
        history.append({"role": "user", "content": "Question 6"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 7
        result = svc.answer("Question 7", history=history)
        history.append({"role": "user", "content": "Question 7"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 8
        result = svc.answer("Question 8", history=history)
        history.append({"role": "user", "content": "Question 8"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 9
        result = svc.answer("Question 9", history=history)
        history.append({"role": "user", "content": "Question 9"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 10
        result = svc.answer("Question 10", history=history)
        history.append({"role": "user", "content": "Question 10"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 11
        result = svc.answer("Question 11", history=history)
        history.append({"role": "user", "content": "Question 11"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 12
        result = svc.answer("Question 12", history=history)
        history.append({"role": "user", "content": "Question 12"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())

    def test_long_conversation_flow_23(self):
        """Test conversation path 23 up to 12 turns to ensure no crashes and no ID leaks."""
        groq_responses = []
        for _ in range(15):
            groq_responses.append('```json\n{"sql": "SELECT 1 FROM ai_farm_flock_data_view WHERE owner_id = %s", "params": ["__OWNER_ID__"], "metric": "test_metric", "result_type": "summary"}\n```')
            groq_responses.append('Perfectly correct answer based on SQL data.')
        svc = self._svc(groq_responses=groq_responses)
        svc.executor.execute = lambda plan: [{"flock_name": "Alpha", "farm_id": 88, "flock_id": 99}]
        history = []
        # Turn 1
        result = svc.answer("Question 1", history=history)
        history.append({"role": "user", "content": "Question 1"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 2
        result = svc.answer("Question 2", history=history)
        history.append({"role": "user", "content": "Question 2"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 3
        result = svc.answer("Question 3", history=history)
        history.append({"role": "user", "content": "Question 3"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 4
        result = svc.answer("Question 4", history=history)
        history.append({"role": "user", "content": "Question 4"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 5
        result = svc.answer("Question 5", history=history)
        history.append({"role": "user", "content": "Question 5"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 6
        result = svc.answer("Question 6", history=history)
        history.append({"role": "user", "content": "Question 6"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 7
        result = svc.answer("Question 7", history=history)
        history.append({"role": "user", "content": "Question 7"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 8
        result = svc.answer("Question 8", history=history)
        history.append({"role": "user", "content": "Question 8"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 9
        result = svc.answer("Question 9", history=history)
        history.append({"role": "user", "content": "Question 9"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 10
        result = svc.answer("Question 10", history=history)
        history.append({"role": "user", "content": "Question 10"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 11
        result = svc.answer("Question 11", history=history)
        history.append({"role": "user", "content": "Question 11"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 12
        result = svc.answer("Question 12", history=history)
        history.append({"role": "user", "content": "Question 12"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())

    def test_long_conversation_flow_24(self):
        """Test conversation path 24 up to 12 turns to ensure no crashes and no ID leaks."""
        groq_responses = []
        for _ in range(15):
            groq_responses.append('```json\n{"sql": "SELECT 1 FROM ai_farm_flock_data_view WHERE owner_id = %s", "params": ["__OWNER_ID__"], "metric": "test_metric", "result_type": "summary"}\n```')
            groq_responses.append('Perfectly correct answer based on SQL data.')
        svc = self._svc(groq_responses=groq_responses)
        svc.executor.execute = lambda plan: [{"flock_name": "Alpha", "farm_id": 88, "flock_id": 99}]
        history = []
        # Turn 1
        result = svc.answer("Question 1", history=history)
        history.append({"role": "user", "content": "Question 1"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 2
        result = svc.answer("Question 2", history=history)
        history.append({"role": "user", "content": "Question 2"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 3
        result = svc.answer("Question 3", history=history)
        history.append({"role": "user", "content": "Question 3"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 4
        result = svc.answer("Question 4", history=history)
        history.append({"role": "user", "content": "Question 4"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 5
        result = svc.answer("Question 5", history=history)
        history.append({"role": "user", "content": "Question 5"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 6
        result = svc.answer("Question 6", history=history)
        history.append({"role": "user", "content": "Question 6"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 7
        result = svc.answer("Question 7", history=history)
        history.append({"role": "user", "content": "Question 7"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 8
        result = svc.answer("Question 8", history=history)
        history.append({"role": "user", "content": "Question 8"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 9
        result = svc.answer("Question 9", history=history)
        history.append({"role": "user", "content": "Question 9"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 10
        result = svc.answer("Question 10", history=history)
        history.append({"role": "user", "content": "Question 10"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 11
        result = svc.answer("Question 11", history=history)
        history.append({"role": "user", "content": "Question 11"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 12
        result = svc.answer("Question 12", history=history)
        history.append({"role": "user", "content": "Question 12"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())

    def test_long_conversation_flow_25(self):
        """Test conversation path 25 up to 12 turns to ensure no crashes and no ID leaks."""
        groq_responses = []
        for _ in range(15):
            groq_responses.append('```json\n{"sql": "SELECT 1 FROM ai_farm_flock_data_view WHERE owner_id = %s", "params": ["__OWNER_ID__"], "metric": "test_metric", "result_type": "summary"}\n```')
            groq_responses.append('Perfectly correct answer based on SQL data.')
        svc = self._svc(groq_responses=groq_responses)
        svc.executor.execute = lambda plan: [{"flock_name": "Alpha", "farm_id": 88, "flock_id": 99}]
        history = []
        # Turn 1
        result = svc.answer("Question 1", history=history)
        history.append({"role": "user", "content": "Question 1"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 2
        result = svc.answer("Question 2", history=history)
        history.append({"role": "user", "content": "Question 2"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 3
        result = svc.answer("Question 3", history=history)
        history.append({"role": "user", "content": "Question 3"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 4
        result = svc.answer("Question 4", history=history)
        history.append({"role": "user", "content": "Question 4"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 5
        result = svc.answer("Question 5", history=history)
        history.append({"role": "user", "content": "Question 5"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 6
        result = svc.answer("Question 6", history=history)
        history.append({"role": "user", "content": "Question 6"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 7
        result = svc.answer("Question 7", history=history)
        history.append({"role": "user", "content": "Question 7"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 8
        result = svc.answer("Question 8", history=history)
        history.append({"role": "user", "content": "Question 8"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 9
        result = svc.answer("Question 9", history=history)
        history.append({"role": "user", "content": "Question 9"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 10
        result = svc.answer("Question 10", history=history)
        history.append({"role": "user", "content": "Question 10"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 11
        result = svc.answer("Question 11", history=history)
        history.append({"role": "user", "content": "Question 11"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 12
        result = svc.answer("Question 12", history=history)
        history.append({"role": "user", "content": "Question 12"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())

    def test_long_conversation_flow_26(self):
        """Test conversation path 26 up to 12 turns to ensure no crashes and no ID leaks."""
        groq_responses = []
        for _ in range(15):
            groq_responses.append('```json\n{"sql": "SELECT 1 FROM ai_farm_flock_data_view WHERE owner_id = %s", "params": ["__OWNER_ID__"], "metric": "test_metric", "result_type": "summary"}\n```')
            groq_responses.append('Perfectly correct answer based on SQL data.')
        svc = self._svc(groq_responses=groq_responses)
        svc.executor.execute = lambda plan: [{"flock_name": "Alpha", "farm_id": 88, "flock_id": 99}]
        history = []
        # Turn 1
        result = svc.answer("Question 1", history=history)
        history.append({"role": "user", "content": "Question 1"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 2
        result = svc.answer("Question 2", history=history)
        history.append({"role": "user", "content": "Question 2"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 3
        result = svc.answer("Question 3", history=history)
        history.append({"role": "user", "content": "Question 3"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 4
        result = svc.answer("Question 4", history=history)
        history.append({"role": "user", "content": "Question 4"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 5
        result = svc.answer("Question 5", history=history)
        history.append({"role": "user", "content": "Question 5"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 6
        result = svc.answer("Question 6", history=history)
        history.append({"role": "user", "content": "Question 6"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 7
        result = svc.answer("Question 7", history=history)
        history.append({"role": "user", "content": "Question 7"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 8
        result = svc.answer("Question 8", history=history)
        history.append({"role": "user", "content": "Question 8"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 9
        result = svc.answer("Question 9", history=history)
        history.append({"role": "user", "content": "Question 9"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 10
        result = svc.answer("Question 10", history=history)
        history.append({"role": "user", "content": "Question 10"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 11
        result = svc.answer("Question 11", history=history)
        history.append({"role": "user", "content": "Question 11"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 12
        result = svc.answer("Question 12", history=history)
        history.append({"role": "user", "content": "Question 12"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())

    def test_long_conversation_flow_27(self):
        """Test conversation path 27 up to 12 turns to ensure no crashes and no ID leaks."""
        groq_responses = []
        for _ in range(15):
            groq_responses.append('```json\n{"sql": "SELECT 1 FROM ai_farm_flock_data_view WHERE owner_id = %s", "params": ["__OWNER_ID__"], "metric": "test_metric", "result_type": "summary"}\n```')
            groq_responses.append('Perfectly correct answer based on SQL data.')
        svc = self._svc(groq_responses=groq_responses)
        svc.executor.execute = lambda plan: [{"flock_name": "Alpha", "farm_id": 88, "flock_id": 99}]
        history = []
        # Turn 1
        result = svc.answer("Question 1", history=history)
        history.append({"role": "user", "content": "Question 1"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 2
        result = svc.answer("Question 2", history=history)
        history.append({"role": "user", "content": "Question 2"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 3
        result = svc.answer("Question 3", history=history)
        history.append({"role": "user", "content": "Question 3"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 4
        result = svc.answer("Question 4", history=history)
        history.append({"role": "user", "content": "Question 4"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 5
        result = svc.answer("Question 5", history=history)
        history.append({"role": "user", "content": "Question 5"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 6
        result = svc.answer("Question 6", history=history)
        history.append({"role": "user", "content": "Question 6"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 7
        result = svc.answer("Question 7", history=history)
        history.append({"role": "user", "content": "Question 7"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 8
        result = svc.answer("Question 8", history=history)
        history.append({"role": "user", "content": "Question 8"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 9
        result = svc.answer("Question 9", history=history)
        history.append({"role": "user", "content": "Question 9"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 10
        result = svc.answer("Question 10", history=history)
        history.append({"role": "user", "content": "Question 10"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 11
        result = svc.answer("Question 11", history=history)
        history.append({"role": "user", "content": "Question 11"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 12
        result = svc.answer("Question 12", history=history)
        history.append({"role": "user", "content": "Question 12"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())

    def test_long_conversation_flow_28(self):
        """Test conversation path 28 up to 12 turns to ensure no crashes and no ID leaks."""
        groq_responses = []
        for _ in range(15):
            groq_responses.append('```json\n{"sql": "SELECT 1 FROM ai_farm_flock_data_view WHERE owner_id = %s", "params": ["__OWNER_ID__"], "metric": "test_metric", "result_type": "summary"}\n```')
            groq_responses.append('Perfectly correct answer based on SQL data.')
        svc = self._svc(groq_responses=groq_responses)
        svc.executor.execute = lambda plan: [{"flock_name": "Alpha", "farm_id": 88, "flock_id": 99}]
        history = []
        # Turn 1
        result = svc.answer("Question 1", history=history)
        history.append({"role": "user", "content": "Question 1"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 2
        result = svc.answer("Question 2", history=history)
        history.append({"role": "user", "content": "Question 2"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 3
        result = svc.answer("Question 3", history=history)
        history.append({"role": "user", "content": "Question 3"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 4
        result = svc.answer("Question 4", history=history)
        history.append({"role": "user", "content": "Question 4"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 5
        result = svc.answer("Question 5", history=history)
        history.append({"role": "user", "content": "Question 5"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 6
        result = svc.answer("Question 6", history=history)
        history.append({"role": "user", "content": "Question 6"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 7
        result = svc.answer("Question 7", history=history)
        history.append({"role": "user", "content": "Question 7"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 8
        result = svc.answer("Question 8", history=history)
        history.append({"role": "user", "content": "Question 8"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 9
        result = svc.answer("Question 9", history=history)
        history.append({"role": "user", "content": "Question 9"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 10
        result = svc.answer("Question 10", history=history)
        history.append({"role": "user", "content": "Question 10"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 11
        result = svc.answer("Question 11", history=history)
        history.append({"role": "user", "content": "Question 11"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 12
        result = svc.answer("Question 12", history=history)
        history.append({"role": "user", "content": "Question 12"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())

    def test_long_conversation_flow_29(self):
        """Test conversation path 29 up to 12 turns to ensure no crashes and no ID leaks."""
        groq_responses = []
        for _ in range(15):
            groq_responses.append('```json\n{"sql": "SELECT 1 FROM ai_farm_flock_data_view WHERE owner_id = %s", "params": ["__OWNER_ID__"], "metric": "test_metric", "result_type": "summary"}\n```')
            groq_responses.append('Perfectly correct answer based on SQL data.')
        svc = self._svc(groq_responses=groq_responses)
        svc.executor.execute = lambda plan: [{"flock_name": "Alpha", "farm_id": 88, "flock_id": 99}]
        history = []
        # Turn 1
        result = svc.answer("Question 1", history=history)
        history.append({"role": "user", "content": "Question 1"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 2
        result = svc.answer("Question 2", history=history)
        history.append({"role": "user", "content": "Question 2"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 3
        result = svc.answer("Question 3", history=history)
        history.append({"role": "user", "content": "Question 3"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 4
        result = svc.answer("Question 4", history=history)
        history.append({"role": "user", "content": "Question 4"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 5
        result = svc.answer("Question 5", history=history)
        history.append({"role": "user", "content": "Question 5"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 6
        result = svc.answer("Question 6", history=history)
        history.append({"role": "user", "content": "Question 6"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 7
        result = svc.answer("Question 7", history=history)
        history.append({"role": "user", "content": "Question 7"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 8
        result = svc.answer("Question 8", history=history)
        history.append({"role": "user", "content": "Question 8"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 9
        result = svc.answer("Question 9", history=history)
        history.append({"role": "user", "content": "Question 9"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 10
        result = svc.answer("Question 10", history=history)
        history.append({"role": "user", "content": "Question 10"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 11
        result = svc.answer("Question 11", history=history)
        history.append({"role": "user", "content": "Question 11"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 12
        result = svc.answer("Question 12", history=history)
        history.append({"role": "user", "content": "Question 12"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())

    def test_long_conversation_flow_30(self):
        """Test conversation path 30 up to 12 turns to ensure no crashes and no ID leaks."""
        groq_responses = []
        for _ in range(15):
            groq_responses.append('```json\n{"sql": "SELECT 1 FROM ai_farm_flock_data_view WHERE owner_id = %s", "params": ["__OWNER_ID__"], "metric": "test_metric", "result_type": "summary"}\n```')
            groq_responses.append('Perfectly correct answer based on SQL data.')
        svc = self._svc(groq_responses=groq_responses)
        svc.executor.execute = lambda plan: [{"flock_name": "Alpha", "farm_id": 88, "flock_id": 99}]
        history = []
        # Turn 1
        result = svc.answer("Question 1", history=history)
        history.append({"role": "user", "content": "Question 1"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 2
        result = svc.answer("Question 2", history=history)
        history.append({"role": "user", "content": "Question 2"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 3
        result = svc.answer("Question 3", history=history)
        history.append({"role": "user", "content": "Question 3"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 4
        result = svc.answer("Question 4", history=history)
        history.append({"role": "user", "content": "Question 4"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 5
        result = svc.answer("Question 5", history=history)
        history.append({"role": "user", "content": "Question 5"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 6
        result = svc.answer("Question 6", history=history)
        history.append({"role": "user", "content": "Question 6"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 7
        result = svc.answer("Question 7", history=history)
        history.append({"role": "user", "content": "Question 7"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 8
        result = svc.answer("Question 8", history=history)
        history.append({"role": "user", "content": "Question 8"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 9
        result = svc.answer("Question 9", history=history)
        history.append({"role": "user", "content": "Question 9"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 10
        result = svc.answer("Question 10", history=history)
        history.append({"role": "user", "content": "Question 10"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 11
        result = svc.answer("Question 11", history=history)
        history.append({"role": "user", "content": "Question 11"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 12
        result = svc.answer("Question 12", history=history)
        history.append({"role": "user", "content": "Question 12"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())

    def test_long_conversation_flow_31(self):
        """Test conversation path 31 up to 12 turns to ensure no crashes and no ID leaks."""
        groq_responses = []
        for _ in range(15):
            groq_responses.append('```json\n{"sql": "SELECT 1 FROM ai_farm_flock_data_view WHERE owner_id = %s", "params": ["__OWNER_ID__"], "metric": "test_metric", "result_type": "summary"}\n```')
            groq_responses.append('Perfectly correct answer based on SQL data.')
        svc = self._svc(groq_responses=groq_responses)
        svc.executor.execute = lambda plan: [{"flock_name": "Alpha", "farm_id": 88, "flock_id": 99}]
        history = []
        # Turn 1
        result = svc.answer("Question 1", history=history)
        history.append({"role": "user", "content": "Question 1"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 2
        result = svc.answer("Question 2", history=history)
        history.append({"role": "user", "content": "Question 2"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 3
        result = svc.answer("Question 3", history=history)
        history.append({"role": "user", "content": "Question 3"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 4
        result = svc.answer("Question 4", history=history)
        history.append({"role": "user", "content": "Question 4"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 5
        result = svc.answer("Question 5", history=history)
        history.append({"role": "user", "content": "Question 5"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 6
        result = svc.answer("Question 6", history=history)
        history.append({"role": "user", "content": "Question 6"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 7
        result = svc.answer("Question 7", history=history)
        history.append({"role": "user", "content": "Question 7"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 8
        result = svc.answer("Question 8", history=history)
        history.append({"role": "user", "content": "Question 8"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 9
        result = svc.answer("Question 9", history=history)
        history.append({"role": "user", "content": "Question 9"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 10
        result = svc.answer("Question 10", history=history)
        history.append({"role": "user", "content": "Question 10"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 11
        result = svc.answer("Question 11", history=history)
        history.append({"role": "user", "content": "Question 11"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 12
        result = svc.answer("Question 12", history=history)
        history.append({"role": "user", "content": "Question 12"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())

    def test_long_conversation_flow_32(self):
        """Test conversation path 32 up to 12 turns to ensure no crashes and no ID leaks."""
        groq_responses = []
        for _ in range(15):
            groq_responses.append('```json\n{"sql": "SELECT 1 FROM ai_farm_flock_data_view WHERE owner_id = %s", "params": ["__OWNER_ID__"], "metric": "test_metric", "result_type": "summary"}\n```')
            groq_responses.append('Perfectly correct answer based on SQL data.')
        svc = self._svc(groq_responses=groq_responses)
        svc.executor.execute = lambda plan: [{"flock_name": "Alpha", "farm_id": 88, "flock_id": 99}]
        history = []
        # Turn 1
        result = svc.answer("Question 1", history=history)
        history.append({"role": "user", "content": "Question 1"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 2
        result = svc.answer("Question 2", history=history)
        history.append({"role": "user", "content": "Question 2"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 3
        result = svc.answer("Question 3", history=history)
        history.append({"role": "user", "content": "Question 3"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 4
        result = svc.answer("Question 4", history=history)
        history.append({"role": "user", "content": "Question 4"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 5
        result = svc.answer("Question 5", history=history)
        history.append({"role": "user", "content": "Question 5"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 6
        result = svc.answer("Question 6", history=history)
        history.append({"role": "user", "content": "Question 6"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 7
        result = svc.answer("Question 7", history=history)
        history.append({"role": "user", "content": "Question 7"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 8
        result = svc.answer("Question 8", history=history)
        history.append({"role": "user", "content": "Question 8"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 9
        result = svc.answer("Question 9", history=history)
        history.append({"role": "user", "content": "Question 9"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 10
        result = svc.answer("Question 10", history=history)
        history.append({"role": "user", "content": "Question 10"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 11
        result = svc.answer("Question 11", history=history)
        history.append({"role": "user", "content": "Question 11"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 12
        result = svc.answer("Question 12", history=history)
        history.append({"role": "user", "content": "Question 12"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())

    def test_long_conversation_flow_33(self):
        """Test conversation path 33 up to 12 turns to ensure no crashes and no ID leaks."""
        groq_responses = []
        for _ in range(15):
            groq_responses.append('```json\n{"sql": "SELECT 1 FROM ai_farm_flock_data_view WHERE owner_id = %s", "params": ["__OWNER_ID__"], "metric": "test_metric", "result_type": "summary"}\n```')
            groq_responses.append('Perfectly correct answer based on SQL data.')
        svc = self._svc(groq_responses=groq_responses)
        svc.executor.execute = lambda plan: [{"flock_name": "Alpha", "farm_id": 88, "flock_id": 99}]
        history = []
        # Turn 1
        result = svc.answer("Question 1", history=history)
        history.append({"role": "user", "content": "Question 1"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 2
        result = svc.answer("Question 2", history=history)
        history.append({"role": "user", "content": "Question 2"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 3
        result = svc.answer("Question 3", history=history)
        history.append({"role": "user", "content": "Question 3"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 4
        result = svc.answer("Question 4", history=history)
        history.append({"role": "user", "content": "Question 4"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 5
        result = svc.answer("Question 5", history=history)
        history.append({"role": "user", "content": "Question 5"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 6
        result = svc.answer("Question 6", history=history)
        history.append({"role": "user", "content": "Question 6"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 7
        result = svc.answer("Question 7", history=history)
        history.append({"role": "user", "content": "Question 7"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 8
        result = svc.answer("Question 8", history=history)
        history.append({"role": "user", "content": "Question 8"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 9
        result = svc.answer("Question 9", history=history)
        history.append({"role": "user", "content": "Question 9"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 10
        result = svc.answer("Question 10", history=history)
        history.append({"role": "user", "content": "Question 10"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 11
        result = svc.answer("Question 11", history=history)
        history.append({"role": "user", "content": "Question 11"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 12
        result = svc.answer("Question 12", history=history)
        history.append({"role": "user", "content": "Question 12"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())

    def test_long_conversation_flow_34(self):
        """Test conversation path 34 up to 12 turns to ensure no crashes and no ID leaks."""
        groq_responses = []
        for _ in range(15):
            groq_responses.append('```json\n{"sql": "SELECT 1 FROM ai_farm_flock_data_view WHERE owner_id = %s", "params": ["__OWNER_ID__"], "metric": "test_metric", "result_type": "summary"}\n```')
            groq_responses.append('Perfectly correct answer based on SQL data.')
        svc = self._svc(groq_responses=groq_responses)
        svc.executor.execute = lambda plan: [{"flock_name": "Alpha", "farm_id": 88, "flock_id": 99}]
        history = []
        # Turn 1
        result = svc.answer("Question 1", history=history)
        history.append({"role": "user", "content": "Question 1"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 2
        result = svc.answer("Question 2", history=history)
        history.append({"role": "user", "content": "Question 2"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 3
        result = svc.answer("Question 3", history=history)
        history.append({"role": "user", "content": "Question 3"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 4
        result = svc.answer("Question 4", history=history)
        history.append({"role": "user", "content": "Question 4"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 5
        result = svc.answer("Question 5", history=history)
        history.append({"role": "user", "content": "Question 5"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 6
        result = svc.answer("Question 6", history=history)
        history.append({"role": "user", "content": "Question 6"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 7
        result = svc.answer("Question 7", history=history)
        history.append({"role": "user", "content": "Question 7"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 8
        result = svc.answer("Question 8", history=history)
        history.append({"role": "user", "content": "Question 8"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 9
        result = svc.answer("Question 9", history=history)
        history.append({"role": "user", "content": "Question 9"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 10
        result = svc.answer("Question 10", history=history)
        history.append({"role": "user", "content": "Question 10"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 11
        result = svc.answer("Question 11", history=history)
        history.append({"role": "user", "content": "Question 11"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 12
        result = svc.answer("Question 12", history=history)
        history.append({"role": "user", "content": "Question 12"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())

    def test_long_conversation_flow_35(self):
        """Test conversation path 35 up to 12 turns to ensure no crashes and no ID leaks."""
        groq_responses = []
        for _ in range(15):
            groq_responses.append('```json\n{"sql": "SELECT 1 FROM ai_farm_flock_data_view WHERE owner_id = %s", "params": ["__OWNER_ID__"], "metric": "test_metric", "result_type": "summary"}\n```')
            groq_responses.append('Perfectly correct answer based on SQL data.')
        svc = self._svc(groq_responses=groq_responses)
        svc.executor.execute = lambda plan: [{"flock_name": "Alpha", "farm_id": 88, "flock_id": 99}]
        history = []
        # Turn 1
        result = svc.answer("Question 1", history=history)
        history.append({"role": "user", "content": "Question 1"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 2
        result = svc.answer("Question 2", history=history)
        history.append({"role": "user", "content": "Question 2"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 3
        result = svc.answer("Question 3", history=history)
        history.append({"role": "user", "content": "Question 3"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 4
        result = svc.answer("Question 4", history=history)
        history.append({"role": "user", "content": "Question 4"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 5
        result = svc.answer("Question 5", history=history)
        history.append({"role": "user", "content": "Question 5"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 6
        result = svc.answer("Question 6", history=history)
        history.append({"role": "user", "content": "Question 6"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 7
        result = svc.answer("Question 7", history=history)
        history.append({"role": "user", "content": "Question 7"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 8
        result = svc.answer("Question 8", history=history)
        history.append({"role": "user", "content": "Question 8"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 9
        result = svc.answer("Question 9", history=history)
        history.append({"role": "user", "content": "Question 9"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 10
        result = svc.answer("Question 10", history=history)
        history.append({"role": "user", "content": "Question 10"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 11
        result = svc.answer("Question 11", history=history)
        history.append({"role": "user", "content": "Question 11"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 12
        result = svc.answer("Question 12", history=history)
        history.append({"role": "user", "content": "Question 12"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())

    def test_long_conversation_flow_36(self):
        """Test conversation path 36 up to 12 turns to ensure no crashes and no ID leaks."""
        groq_responses = []
        for _ in range(15):
            groq_responses.append('```json\n{"sql": "SELECT 1 FROM ai_farm_flock_data_view WHERE owner_id = %s", "params": ["__OWNER_ID__"], "metric": "test_metric", "result_type": "summary"}\n```')
            groq_responses.append('Perfectly correct answer based on SQL data.')
        svc = self._svc(groq_responses=groq_responses)
        svc.executor.execute = lambda plan: [{"flock_name": "Alpha", "farm_id": 88, "flock_id": 99}]
        history = []
        # Turn 1
        result = svc.answer("Question 1", history=history)
        history.append({"role": "user", "content": "Question 1"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 2
        result = svc.answer("Question 2", history=history)
        history.append({"role": "user", "content": "Question 2"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 3
        result = svc.answer("Question 3", history=history)
        history.append({"role": "user", "content": "Question 3"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 4
        result = svc.answer("Question 4", history=history)
        history.append({"role": "user", "content": "Question 4"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 5
        result = svc.answer("Question 5", history=history)
        history.append({"role": "user", "content": "Question 5"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 6
        result = svc.answer("Question 6", history=history)
        history.append({"role": "user", "content": "Question 6"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 7
        result = svc.answer("Question 7", history=history)
        history.append({"role": "user", "content": "Question 7"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 8
        result = svc.answer("Question 8", history=history)
        history.append({"role": "user", "content": "Question 8"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 9
        result = svc.answer("Question 9", history=history)
        history.append({"role": "user", "content": "Question 9"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 10
        result = svc.answer("Question 10", history=history)
        history.append({"role": "user", "content": "Question 10"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 11
        result = svc.answer("Question 11", history=history)
        history.append({"role": "user", "content": "Question 11"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 12
        result = svc.answer("Question 12", history=history)
        history.append({"role": "user", "content": "Question 12"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())

    def test_long_conversation_flow_37(self):
        """Test conversation path 37 up to 12 turns to ensure no crashes and no ID leaks."""
        groq_responses = []
        for _ in range(15):
            groq_responses.append('```json\n{"sql": "SELECT 1 FROM ai_farm_flock_data_view WHERE owner_id = %s", "params": ["__OWNER_ID__"], "metric": "test_metric", "result_type": "summary"}\n```')
            groq_responses.append('Perfectly correct answer based on SQL data.')
        svc = self._svc(groq_responses=groq_responses)
        svc.executor.execute = lambda plan: [{"flock_name": "Alpha", "farm_id": 88, "flock_id": 99}]
        history = []
        # Turn 1
        result = svc.answer("Question 1", history=history)
        history.append({"role": "user", "content": "Question 1"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 2
        result = svc.answer("Question 2", history=history)
        history.append({"role": "user", "content": "Question 2"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 3
        result = svc.answer("Question 3", history=history)
        history.append({"role": "user", "content": "Question 3"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 4
        result = svc.answer("Question 4", history=history)
        history.append({"role": "user", "content": "Question 4"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 5
        result = svc.answer("Question 5", history=history)
        history.append({"role": "user", "content": "Question 5"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 6
        result = svc.answer("Question 6", history=history)
        history.append({"role": "user", "content": "Question 6"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 7
        result = svc.answer("Question 7", history=history)
        history.append({"role": "user", "content": "Question 7"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 8
        result = svc.answer("Question 8", history=history)
        history.append({"role": "user", "content": "Question 8"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 9
        result = svc.answer("Question 9", history=history)
        history.append({"role": "user", "content": "Question 9"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 10
        result = svc.answer("Question 10", history=history)
        history.append({"role": "user", "content": "Question 10"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 11
        result = svc.answer("Question 11", history=history)
        history.append({"role": "user", "content": "Question 11"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 12
        result = svc.answer("Question 12", history=history)
        history.append({"role": "user", "content": "Question 12"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())

    def test_long_conversation_flow_38(self):
        """Test conversation path 38 up to 12 turns to ensure no crashes and no ID leaks."""
        groq_responses = []
        for _ in range(15):
            groq_responses.append('```json\n{"sql": "SELECT 1 FROM ai_farm_flock_data_view WHERE owner_id = %s", "params": ["__OWNER_ID__"], "metric": "test_metric", "result_type": "summary"}\n```')
            groq_responses.append('Perfectly correct answer based on SQL data.')
        svc = self._svc(groq_responses=groq_responses)
        svc.executor.execute = lambda plan: [{"flock_name": "Alpha", "farm_id": 88, "flock_id": 99}]
        history = []
        # Turn 1
        result = svc.answer("Question 1", history=history)
        history.append({"role": "user", "content": "Question 1"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 2
        result = svc.answer("Question 2", history=history)
        history.append({"role": "user", "content": "Question 2"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 3
        result = svc.answer("Question 3", history=history)
        history.append({"role": "user", "content": "Question 3"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 4
        result = svc.answer("Question 4", history=history)
        history.append({"role": "user", "content": "Question 4"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 5
        result = svc.answer("Question 5", history=history)
        history.append({"role": "user", "content": "Question 5"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 6
        result = svc.answer("Question 6", history=history)
        history.append({"role": "user", "content": "Question 6"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 7
        result = svc.answer("Question 7", history=history)
        history.append({"role": "user", "content": "Question 7"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 8
        result = svc.answer("Question 8", history=history)
        history.append({"role": "user", "content": "Question 8"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 9
        result = svc.answer("Question 9", history=history)
        history.append({"role": "user", "content": "Question 9"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 10
        result = svc.answer("Question 10", history=history)
        history.append({"role": "user", "content": "Question 10"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 11
        result = svc.answer("Question 11", history=history)
        history.append({"role": "user", "content": "Question 11"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 12
        result = svc.answer("Question 12", history=history)
        history.append({"role": "user", "content": "Question 12"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())

    def test_long_conversation_flow_39(self):
        """Test conversation path 39 up to 12 turns to ensure no crashes and no ID leaks."""
        groq_responses = []
        for _ in range(15):
            groq_responses.append('```json\n{"sql": "SELECT 1 FROM ai_farm_flock_data_view WHERE owner_id = %s", "params": ["__OWNER_ID__"], "metric": "test_metric", "result_type": "summary"}\n```')
            groq_responses.append('Perfectly correct answer based on SQL data.')
        svc = self._svc(groq_responses=groq_responses)
        svc.executor.execute = lambda plan: [{"flock_name": "Alpha", "farm_id": 88, "flock_id": 99}]
        history = []
        # Turn 1
        result = svc.answer("Question 1", history=history)
        history.append({"role": "user", "content": "Question 1"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 2
        result = svc.answer("Question 2", history=history)
        history.append({"role": "user", "content": "Question 2"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 3
        result = svc.answer("Question 3", history=history)
        history.append({"role": "user", "content": "Question 3"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 4
        result = svc.answer("Question 4", history=history)
        history.append({"role": "user", "content": "Question 4"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 5
        result = svc.answer("Question 5", history=history)
        history.append({"role": "user", "content": "Question 5"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 6
        result = svc.answer("Question 6", history=history)
        history.append({"role": "user", "content": "Question 6"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 7
        result = svc.answer("Question 7", history=history)
        history.append({"role": "user", "content": "Question 7"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 8
        result = svc.answer("Question 8", history=history)
        history.append({"role": "user", "content": "Question 8"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 9
        result = svc.answer("Question 9", history=history)
        history.append({"role": "user", "content": "Question 9"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 10
        result = svc.answer("Question 10", history=history)
        history.append({"role": "user", "content": "Question 10"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 11
        result = svc.answer("Question 11", history=history)
        history.append({"role": "user", "content": "Question 11"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 12
        result = svc.answer("Question 12", history=history)
        history.append({"role": "user", "content": "Question 12"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())

    def test_long_conversation_flow_40(self):
        """Test conversation path 40 up to 12 turns to ensure no crashes and no ID leaks."""
        groq_responses = []
        for _ in range(15):
            groq_responses.append('```json\n{"sql": "SELECT 1 FROM ai_farm_flock_data_view WHERE owner_id = %s", "params": ["__OWNER_ID__"], "metric": "test_metric", "result_type": "summary"}\n```')
            groq_responses.append('Perfectly correct answer based on SQL data.')
        svc = self._svc(groq_responses=groq_responses)
        svc.executor.execute = lambda plan: [{"flock_name": "Alpha", "farm_id": 88, "flock_id": 99}]
        history = []
        # Turn 1
        result = svc.answer("Question 1", history=history)
        history.append({"role": "user", "content": "Question 1"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 2
        result = svc.answer("Question 2", history=history)
        history.append({"role": "user", "content": "Question 2"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 3
        result = svc.answer("Question 3", history=history)
        history.append({"role": "user", "content": "Question 3"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 4
        result = svc.answer("Question 4", history=history)
        history.append({"role": "user", "content": "Question 4"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 5
        result = svc.answer("Question 5", history=history)
        history.append({"role": "user", "content": "Question 5"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 6
        result = svc.answer("Question 6", history=history)
        history.append({"role": "user", "content": "Question 6"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 7
        result = svc.answer("Question 7", history=history)
        history.append({"role": "user", "content": "Question 7"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 8
        result = svc.answer("Question 8", history=history)
        history.append({"role": "user", "content": "Question 8"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 9
        result = svc.answer("Question 9", history=history)
        history.append({"role": "user", "content": "Question 9"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 10
        result = svc.answer("Question 10", history=history)
        history.append({"role": "user", "content": "Question 10"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 11
        result = svc.answer("Question 11", history=history)
        history.append({"role": "user", "content": "Question 11"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 12
        result = svc.answer("Question 12", history=history)
        history.append({"role": "user", "content": "Question 12"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())

    def test_long_conversation_flow_41(self):
        """Test conversation path 41 up to 12 turns to ensure no crashes and no ID leaks."""
        groq_responses = []
        for _ in range(15):
            groq_responses.append('```json\n{"sql": "SELECT 1 FROM ai_farm_flock_data_view WHERE owner_id = %s", "params": ["__OWNER_ID__"], "metric": "test_metric", "result_type": "summary"}\n```')
            groq_responses.append('Perfectly correct answer based on SQL data.')
        svc = self._svc(groq_responses=groq_responses)
        svc.executor.execute = lambda plan: [{"flock_name": "Alpha", "farm_id": 88, "flock_id": 99}]
        history = []
        # Turn 1
        result = svc.answer("Question 1", history=history)
        history.append({"role": "user", "content": "Question 1"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 2
        result = svc.answer("Question 2", history=history)
        history.append({"role": "user", "content": "Question 2"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 3
        result = svc.answer("Question 3", history=history)
        history.append({"role": "user", "content": "Question 3"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 4
        result = svc.answer("Question 4", history=history)
        history.append({"role": "user", "content": "Question 4"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 5
        result = svc.answer("Question 5", history=history)
        history.append({"role": "user", "content": "Question 5"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 6
        result = svc.answer("Question 6", history=history)
        history.append({"role": "user", "content": "Question 6"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 7
        result = svc.answer("Question 7", history=history)
        history.append({"role": "user", "content": "Question 7"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 8
        result = svc.answer("Question 8", history=history)
        history.append({"role": "user", "content": "Question 8"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 9
        result = svc.answer("Question 9", history=history)
        history.append({"role": "user", "content": "Question 9"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 10
        result = svc.answer("Question 10", history=history)
        history.append({"role": "user", "content": "Question 10"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 11
        result = svc.answer("Question 11", history=history)
        history.append({"role": "user", "content": "Question 11"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 12
        result = svc.answer("Question 12", history=history)
        history.append({"role": "user", "content": "Question 12"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())

    def test_long_conversation_flow_42(self):
        """Test conversation path 42 up to 12 turns to ensure no crashes and no ID leaks."""
        groq_responses = []
        for _ in range(15):
            groq_responses.append('```json\n{"sql": "SELECT 1 FROM ai_farm_flock_data_view WHERE owner_id = %s", "params": ["__OWNER_ID__"], "metric": "test_metric", "result_type": "summary"}\n```')
            groq_responses.append('Perfectly correct answer based on SQL data.')
        svc = self._svc(groq_responses=groq_responses)
        svc.executor.execute = lambda plan: [{"flock_name": "Alpha", "farm_id": 88, "flock_id": 99}]
        history = []
        # Turn 1
        result = svc.answer("Question 1", history=history)
        history.append({"role": "user", "content": "Question 1"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 2
        result = svc.answer("Question 2", history=history)
        history.append({"role": "user", "content": "Question 2"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 3
        result = svc.answer("Question 3", history=history)
        history.append({"role": "user", "content": "Question 3"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 4
        result = svc.answer("Question 4", history=history)
        history.append({"role": "user", "content": "Question 4"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 5
        result = svc.answer("Question 5", history=history)
        history.append({"role": "user", "content": "Question 5"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 6
        result = svc.answer("Question 6", history=history)
        history.append({"role": "user", "content": "Question 6"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 7
        result = svc.answer("Question 7", history=history)
        history.append({"role": "user", "content": "Question 7"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 8
        result = svc.answer("Question 8", history=history)
        history.append({"role": "user", "content": "Question 8"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 9
        result = svc.answer("Question 9", history=history)
        history.append({"role": "user", "content": "Question 9"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 10
        result = svc.answer("Question 10", history=history)
        history.append({"role": "user", "content": "Question 10"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 11
        result = svc.answer("Question 11", history=history)
        history.append({"role": "user", "content": "Question 11"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 12
        result = svc.answer("Question 12", history=history)
        history.append({"role": "user", "content": "Question 12"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())

    def test_long_conversation_flow_43(self):
        """Test conversation path 43 up to 12 turns to ensure no crashes and no ID leaks."""
        groq_responses = []
        for _ in range(15):
            groq_responses.append('```json\n{"sql": "SELECT 1 FROM ai_farm_flock_data_view WHERE owner_id = %s", "params": ["__OWNER_ID__"], "metric": "test_metric", "result_type": "summary"}\n```')
            groq_responses.append('Perfectly correct answer based on SQL data.')
        svc = self._svc(groq_responses=groq_responses)
        svc.executor.execute = lambda plan: [{"flock_name": "Alpha", "farm_id": 88, "flock_id": 99}]
        history = []
        # Turn 1
        result = svc.answer("Question 1", history=history)
        history.append({"role": "user", "content": "Question 1"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 2
        result = svc.answer("Question 2", history=history)
        history.append({"role": "user", "content": "Question 2"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 3
        result = svc.answer("Question 3", history=history)
        history.append({"role": "user", "content": "Question 3"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 4
        result = svc.answer("Question 4", history=history)
        history.append({"role": "user", "content": "Question 4"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 5
        result = svc.answer("Question 5", history=history)
        history.append({"role": "user", "content": "Question 5"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 6
        result = svc.answer("Question 6", history=history)
        history.append({"role": "user", "content": "Question 6"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 7
        result = svc.answer("Question 7", history=history)
        history.append({"role": "user", "content": "Question 7"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 8
        result = svc.answer("Question 8", history=history)
        history.append({"role": "user", "content": "Question 8"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 9
        result = svc.answer("Question 9", history=history)
        history.append({"role": "user", "content": "Question 9"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 10
        result = svc.answer("Question 10", history=history)
        history.append({"role": "user", "content": "Question 10"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 11
        result = svc.answer("Question 11", history=history)
        history.append({"role": "user", "content": "Question 11"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 12
        result = svc.answer("Question 12", history=history)
        history.append({"role": "user", "content": "Question 12"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())

    def test_long_conversation_flow_44(self):
        """Test conversation path 44 up to 12 turns to ensure no crashes and no ID leaks."""
        groq_responses = []
        for _ in range(15):
            groq_responses.append('```json\n{"sql": "SELECT 1 FROM ai_farm_flock_data_view WHERE owner_id = %s", "params": ["__OWNER_ID__"], "metric": "test_metric", "result_type": "summary"}\n```')
            groq_responses.append('Perfectly correct answer based on SQL data.')
        svc = self._svc(groq_responses=groq_responses)
        svc.executor.execute = lambda plan: [{"flock_name": "Alpha", "farm_id": 88, "flock_id": 99}]
        history = []
        # Turn 1
        result = svc.answer("Question 1", history=history)
        history.append({"role": "user", "content": "Question 1"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 2
        result = svc.answer("Question 2", history=history)
        history.append({"role": "user", "content": "Question 2"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 3
        result = svc.answer("Question 3", history=history)
        history.append({"role": "user", "content": "Question 3"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 4
        result = svc.answer("Question 4", history=history)
        history.append({"role": "user", "content": "Question 4"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 5
        result = svc.answer("Question 5", history=history)
        history.append({"role": "user", "content": "Question 5"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 6
        result = svc.answer("Question 6", history=history)
        history.append({"role": "user", "content": "Question 6"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 7
        result = svc.answer("Question 7", history=history)
        history.append({"role": "user", "content": "Question 7"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 8
        result = svc.answer("Question 8", history=history)
        history.append({"role": "user", "content": "Question 8"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 9
        result = svc.answer("Question 9", history=history)
        history.append({"role": "user", "content": "Question 9"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 10
        result = svc.answer("Question 10", history=history)
        history.append({"role": "user", "content": "Question 10"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 11
        result = svc.answer("Question 11", history=history)
        history.append({"role": "user", "content": "Question 11"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 12
        result = svc.answer("Question 12", history=history)
        history.append({"role": "user", "content": "Question 12"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())

    def test_long_conversation_flow_45(self):
        """Test conversation path 45 up to 12 turns to ensure no crashes and no ID leaks."""
        groq_responses = []
        for _ in range(15):
            groq_responses.append('```json\n{"sql": "SELECT 1 FROM ai_farm_flock_data_view WHERE owner_id = %s", "params": ["__OWNER_ID__"], "metric": "test_metric", "result_type": "summary"}\n```')
            groq_responses.append('Perfectly correct answer based on SQL data.')
        svc = self._svc(groq_responses=groq_responses)
        svc.executor.execute = lambda plan: [{"flock_name": "Alpha", "farm_id": 88, "flock_id": 99}]
        history = []
        # Turn 1
        result = svc.answer("Question 1", history=history)
        history.append({"role": "user", "content": "Question 1"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 2
        result = svc.answer("Question 2", history=history)
        history.append({"role": "user", "content": "Question 2"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 3
        result = svc.answer("Question 3", history=history)
        history.append({"role": "user", "content": "Question 3"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 4
        result = svc.answer("Question 4", history=history)
        history.append({"role": "user", "content": "Question 4"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 5
        result = svc.answer("Question 5", history=history)
        history.append({"role": "user", "content": "Question 5"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 6
        result = svc.answer("Question 6", history=history)
        history.append({"role": "user", "content": "Question 6"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 7
        result = svc.answer("Question 7", history=history)
        history.append({"role": "user", "content": "Question 7"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 8
        result = svc.answer("Question 8", history=history)
        history.append({"role": "user", "content": "Question 8"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 9
        result = svc.answer("Question 9", history=history)
        history.append({"role": "user", "content": "Question 9"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 10
        result = svc.answer("Question 10", history=history)
        history.append({"role": "user", "content": "Question 10"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 11
        result = svc.answer("Question 11", history=history)
        history.append({"role": "user", "content": "Question 11"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 12
        result = svc.answer("Question 12", history=history)
        history.append({"role": "user", "content": "Question 12"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())

    def test_long_conversation_flow_46(self):
        """Test conversation path 46 up to 12 turns to ensure no crashes and no ID leaks."""
        groq_responses = []
        for _ in range(15):
            groq_responses.append('```json\n{"sql": "SELECT 1 FROM ai_farm_flock_data_view WHERE owner_id = %s", "params": ["__OWNER_ID__"], "metric": "test_metric", "result_type": "summary"}\n```')
            groq_responses.append('Perfectly correct answer based on SQL data.')
        svc = self._svc(groq_responses=groq_responses)
        svc.executor.execute = lambda plan: [{"flock_name": "Alpha", "farm_id": 88, "flock_id": 99}]
        history = []
        # Turn 1
        result = svc.answer("Question 1", history=history)
        history.append({"role": "user", "content": "Question 1"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 2
        result = svc.answer("Question 2", history=history)
        history.append({"role": "user", "content": "Question 2"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 3
        result = svc.answer("Question 3", history=history)
        history.append({"role": "user", "content": "Question 3"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 4
        result = svc.answer("Question 4", history=history)
        history.append({"role": "user", "content": "Question 4"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 5
        result = svc.answer("Question 5", history=history)
        history.append({"role": "user", "content": "Question 5"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 6
        result = svc.answer("Question 6", history=history)
        history.append({"role": "user", "content": "Question 6"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 7
        result = svc.answer("Question 7", history=history)
        history.append({"role": "user", "content": "Question 7"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 8
        result = svc.answer("Question 8", history=history)
        history.append({"role": "user", "content": "Question 8"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 9
        result = svc.answer("Question 9", history=history)
        history.append({"role": "user", "content": "Question 9"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 10
        result = svc.answer("Question 10", history=history)
        history.append({"role": "user", "content": "Question 10"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 11
        result = svc.answer("Question 11", history=history)
        history.append({"role": "user", "content": "Question 11"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 12
        result = svc.answer("Question 12", history=history)
        history.append({"role": "user", "content": "Question 12"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())

    def test_long_conversation_flow_47(self):
        """Test conversation path 47 up to 12 turns to ensure no crashes and no ID leaks."""
        groq_responses = []
        for _ in range(15):
            groq_responses.append('```json\n{"sql": "SELECT 1 FROM ai_farm_flock_data_view WHERE owner_id = %s", "params": ["__OWNER_ID__"], "metric": "test_metric", "result_type": "summary"}\n```')
            groq_responses.append('Perfectly correct answer based on SQL data.')
        svc = self._svc(groq_responses=groq_responses)
        svc.executor.execute = lambda plan: [{"flock_name": "Alpha", "farm_id": 88, "flock_id": 99}]
        history = []
        # Turn 1
        result = svc.answer("Question 1", history=history)
        history.append({"role": "user", "content": "Question 1"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 2
        result = svc.answer("Question 2", history=history)
        history.append({"role": "user", "content": "Question 2"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 3
        result = svc.answer("Question 3", history=history)
        history.append({"role": "user", "content": "Question 3"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 4
        result = svc.answer("Question 4", history=history)
        history.append({"role": "user", "content": "Question 4"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 5
        result = svc.answer("Question 5", history=history)
        history.append({"role": "user", "content": "Question 5"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 6
        result = svc.answer("Question 6", history=history)
        history.append({"role": "user", "content": "Question 6"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 7
        result = svc.answer("Question 7", history=history)
        history.append({"role": "user", "content": "Question 7"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 8
        result = svc.answer("Question 8", history=history)
        history.append({"role": "user", "content": "Question 8"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 9
        result = svc.answer("Question 9", history=history)
        history.append({"role": "user", "content": "Question 9"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 10
        result = svc.answer("Question 10", history=history)
        history.append({"role": "user", "content": "Question 10"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 11
        result = svc.answer("Question 11", history=history)
        history.append({"role": "user", "content": "Question 11"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 12
        result = svc.answer("Question 12", history=history)
        history.append({"role": "user", "content": "Question 12"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())

    def test_long_conversation_flow_48(self):
        """Test conversation path 48 up to 12 turns to ensure no crashes and no ID leaks."""
        groq_responses = []
        for _ in range(15):
            groq_responses.append('```json\n{"sql": "SELECT 1 FROM ai_farm_flock_data_view WHERE owner_id = %s", "params": ["__OWNER_ID__"], "metric": "test_metric", "result_type": "summary"}\n```')
            groq_responses.append('Perfectly correct answer based on SQL data.')
        svc = self._svc(groq_responses=groq_responses)
        svc.executor.execute = lambda plan: [{"flock_name": "Alpha", "farm_id": 88, "flock_id": 99}]
        history = []
        # Turn 1
        result = svc.answer("Question 1", history=history)
        history.append({"role": "user", "content": "Question 1"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 2
        result = svc.answer("Question 2", history=history)
        history.append({"role": "user", "content": "Question 2"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 3
        result = svc.answer("Question 3", history=history)
        history.append({"role": "user", "content": "Question 3"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 4
        result = svc.answer("Question 4", history=history)
        history.append({"role": "user", "content": "Question 4"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 5
        result = svc.answer("Question 5", history=history)
        history.append({"role": "user", "content": "Question 5"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 6
        result = svc.answer("Question 6", history=history)
        history.append({"role": "user", "content": "Question 6"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 7
        result = svc.answer("Question 7", history=history)
        history.append({"role": "user", "content": "Question 7"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 8
        result = svc.answer("Question 8", history=history)
        history.append({"role": "user", "content": "Question 8"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 9
        result = svc.answer("Question 9", history=history)
        history.append({"role": "user", "content": "Question 9"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 10
        result = svc.answer("Question 10", history=history)
        history.append({"role": "user", "content": "Question 10"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 11
        result = svc.answer("Question 11", history=history)
        history.append({"role": "user", "content": "Question 11"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 12
        result = svc.answer("Question 12", history=history)
        history.append({"role": "user", "content": "Question 12"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())

    def test_long_conversation_flow_49(self):
        """Test conversation path 49 up to 12 turns to ensure no crashes and no ID leaks."""
        groq_responses = []
        for _ in range(15):
            groq_responses.append('```json\n{"sql": "SELECT 1 FROM ai_farm_flock_data_view WHERE owner_id = %s", "params": ["__OWNER_ID__"], "metric": "test_metric", "result_type": "summary"}\n```')
            groq_responses.append('Perfectly correct answer based on SQL data.')
        svc = self._svc(groq_responses=groq_responses)
        svc.executor.execute = lambda plan: [{"flock_name": "Alpha", "farm_id": 88, "flock_id": 99}]
        history = []
        # Turn 1
        result = svc.answer("Question 1", history=history)
        history.append({"role": "user", "content": "Question 1"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 2
        result = svc.answer("Question 2", history=history)
        history.append({"role": "user", "content": "Question 2"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 3
        result = svc.answer("Question 3", history=history)
        history.append({"role": "user", "content": "Question 3"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 4
        result = svc.answer("Question 4", history=history)
        history.append({"role": "user", "content": "Question 4"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 5
        result = svc.answer("Question 5", history=history)
        history.append({"role": "user", "content": "Question 5"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 6
        result = svc.answer("Question 6", history=history)
        history.append({"role": "user", "content": "Question 6"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 7
        result = svc.answer("Question 7", history=history)
        history.append({"role": "user", "content": "Question 7"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 8
        result = svc.answer("Question 8", history=history)
        history.append({"role": "user", "content": "Question 8"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 9
        result = svc.answer("Question 9", history=history)
        history.append({"role": "user", "content": "Question 9"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 10
        result = svc.answer("Question 10", history=history)
        history.append({"role": "user", "content": "Question 10"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 11
        result = svc.answer("Question 11", history=history)
        history.append({"role": "user", "content": "Question 11"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 12
        result = svc.answer("Question 12", history=history)
        history.append({"role": "user", "content": "Question 12"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())

    def test_long_conversation_flow_50(self):
        """Test conversation path 50 up to 12 turns to ensure no crashes and no ID leaks."""
        groq_responses = []
        for _ in range(15):
            groq_responses.append('```json\n{"sql": "SELECT 1 FROM ai_farm_flock_data_view WHERE owner_id = %s", "params": ["__OWNER_ID__"], "metric": "test_metric", "result_type": "summary"}\n```')
            groq_responses.append('Perfectly correct answer based on SQL data.')
        svc = self._svc(groq_responses=groq_responses)
        svc.executor.execute = lambda plan: [{"flock_name": "Alpha", "farm_id": 88, "flock_id": 99}]
        history = []
        # Turn 1
        result = svc.answer("Question 1", history=history)
        history.append({"role": "user", "content": "Question 1"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 2
        result = svc.answer("Question 2", history=history)
        history.append({"role": "user", "content": "Question 2"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 3
        result = svc.answer("Question 3", history=history)
        history.append({"role": "user", "content": "Question 3"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 4
        result = svc.answer("Question 4", history=history)
        history.append({"role": "user", "content": "Question 4"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 5
        result = svc.answer("Question 5", history=history)
        history.append({"role": "user", "content": "Question 5"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 6
        result = svc.answer("Question 6", history=history)
        history.append({"role": "user", "content": "Question 6"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 7
        result = svc.answer("Question 7", history=history)
        history.append({"role": "user", "content": "Question 7"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 8
        result = svc.answer("Question 8", history=history)
        history.append({"role": "user", "content": "Question 8"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 9
        result = svc.answer("Question 9", history=history)
        history.append({"role": "user", "content": "Question 9"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 10
        result = svc.answer("Question 10", history=history)
        history.append({"role": "user", "content": "Question 10"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 11
        result = svc.answer("Question 11", history=history)
        history.append({"role": "user", "content": "Question 11"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())
        # Turn 12
        result = svc.answer("Question 12", history=history)
        history.append({"role": "user", "content": "Question 12"})
        history.append({"role": "assistant", "content": result.get("message", "")})
        self.assertEqual(result["status"], "success", result.get("message"))
        self.assertNotIn("flock_id", result["message"].lower())
        self.assertNotIn("farm_id", result["message"].lower())



# ============================================================================
# DailyTimeSeriesDetectorTests
# Verify that _asks_daily_time_series correctly identifies time-series queries
# and that such queries are NOT routed to aggregate deterministic plans.
# ============================================================================


class DailyTimeSeriesDetectorTests(SimpleTestCase):
    """Tests for _asks_daily_time_series and its effect on _known_safe_plan routing."""

    def _make_svc(self):
        from types import SimpleNamespace
        from .llm_sql import ChikoozaLLMTextToSQLService
        from unittest.mock import patch
        fake_user = SimpleNamespace(id=1, pk=1, username="test")
        with patch("aibot.llm_sql.GroqChatClient"):
            return ChikoozaLLMTextToSQLService(user=fake_user)

    def _norm(self, q):
        from .modern_services import normalize_ai_query
        return normalize_ai_query(q)

    # --- Positive: should be detected as time-series ---

    def test_lowest_mortality_which_days(self):
        self.assertTrue(self._make_svc()._asks_daily_time_series(
            self._norm("lowest mortality is in which days?")))

    def test_on_which_date_fcr_highest(self):
        self.assertTrue(self._make_svc()._asks_daily_time_series(
            self._norm("on which date was FCR highest?")))

    def test_which_days_most_feed(self):
        self.assertTrue(self._make_svc()._asks_daily_time_series(
            self._norm("which days had the most feed consumed?")))

    def test_when_did_birds_die_most(self):
        self.assertTrue(self._make_svc()._asks_daily_time_series(
            self._norm("when did birds die the most?")))

    def test_what_dates_highest_weight(self):
        self.assertTrue(self._make_svc()._asks_daily_time_series(
            self._norm("what dates had highest weight?")))

    def test_which_days_high_deaths(self):
        self.assertTrue(self._make_svc()._asks_daily_time_series(
            self._norm("which days had high deaths?")))

    def test_on_what_date_feed_highest(self):
        self.assertTrue(self._make_svc()._asks_daily_time_series(
            self._norm("on what date was feed highest?")))

    def test_on_which_day_mortality_zero(self):
        self.assertTrue(self._make_svc()._asks_daily_time_series(
            self._norm("on which day was mortality zero?")))

    def test_in_which_days_mortality_low(self):
        self.assertTrue(self._make_svc()._asks_daily_time_series(
            self._norm("in which days is mortality low?")))

    # --- Negative: should NOT be detected as time-series ---

    def test_total_mortality_not_time_series(self):
        self.assertFalse(self._make_svc()._asks_daily_time_series(
            self._norm("total mortality")))

    def test_how_much_feed_not_time_series(self):
        self.assertFalse(self._make_svc()._asks_daily_time_series(
            self._norm("how much feed was consumed?")))

    def test_average_fcr_not_time_series(self):
        self.assertFalse(self._make_svc()._asks_daily_time_series(
            self._norm("average FCR")))

    def test_average_weight_not_time_series(self):
        self.assertFalse(self._make_svc()._asks_daily_time_series(
            self._norm("average weight")))

    def test_my_feed_total_not_time_series(self):
        self.assertFalse(self._make_svc()._asks_daily_time_series(
            self._norm("my feed total")))

    def test_show_daily_data_not_time_series(self):
        self.assertFalse(self._make_svc()._asks_daily_time_series(
            self._norm("show daily data for current flock")))

    # --- Routing: time-series queries must return None from _known_safe_plan ---

    def test_mortality_time_series_returns_none(self):
        svc = self._make_svc()
        plan = svc._known_safe_plan(
            "lowest mortality is in which days?",
            history=None, entity_context="",
        )
        self.assertIsNone(plan)

    def test_fcr_time_series_returns_none(self):
        svc = self._make_svc()
        plan = svc._known_safe_plan(
            "on which date was FCR highest?",
            history=None, entity_context="",
        )
        self.assertIsNone(plan)

    def test_weight_time_series_returns_none(self):
        svc = self._make_svc()
        plan = svc._known_safe_plan(
            "what dates had highest weight?",
            history=None, entity_context="",
        )
        self.assertIsNone(plan)

    def test_feed_time_series_returns_none(self):
        svc = self._make_svc()
        plan = svc._known_safe_plan(
            "which days had the most feed consumed?",
            history=None, entity_context="",
        )
        self.assertIsNone(plan)

    # --- Routing: normal aggregate queries still use deterministic plans ---

    def test_aggregate_mortality_still_deterministic(self):
        svc = self._make_svc()
        plan = svc._known_safe_plan(
            "what is my total mortality?",
            history=None, entity_context="",
        )
        self.assertIsNotNone(plan)
        self.assertEqual(plan.metric, "mortality")

    def test_aggregate_feed_still_deterministic(self):
        svc = self._make_svc()
        plan = svc._known_safe_plan(
            "how much feed was consumed?",
            history=None, entity_context="",
        )
        self.assertIsNotNone(plan)
        self.assertEqual(plan.metric, "feed_consumed")

    def test_aggregate_fcr_still_deterministic(self):
        svc = self._make_svc()
        plan = svc._known_safe_plan(
            "what is the average FCR?",
            history=None, entity_context="",
        )
        self.assertIsNotNone(plan)
        self.assertEqual(plan.metric, "average_fcr")

    def test_aggregate_weight_still_deterministic(self):
        svc = self._make_svc()
        plan = svc._known_safe_plan(
            "what is the average bird weight?",
            history=None, entity_context="",
        )
        self.assertIsNotNone(plan)
        self.assertEqual(plan.metric, "average_weight")

"""
SequentialConversationTests — appended to aibot/tests.py
All queries verified against actual detector methods before being used in tests.
Queries that fall through to LLM use _ok() not _ok_metric().
"""

# ============================================================================
# SequentialConversationTests
# Simulate real multi-turn chat sessions (6-12 turns each).
# Messages are sent one at a time with history growing turn-by-turn exactly
# like the real Chikooza AI chat window.
#
# Key properties verified:
#   - Correct metric routing at every turn
#   - 'show all flocks/farms' NEVER hijacked by previous metric (e.g. mortality)
#   - Zero ID leaks in any response message throughout entire conversation
#   - Zero crashes across all conversation paths
#   - Context (flock_id/farm_id) persists across turns when expected
#   - Topic switching works correctly at every step
#   - Time-series queries bypass aggregate plans and succeed
#   - Financial queries route correctly throughout a conversation
#   - ID-block errors don't break subsequent valid queries
#   - owner_id=5 present in SQL params for every data query
# ============================================================================


class SequentialConversationTests(SimpleTestCase):
    """
    Every test simulates a complete sequential conversation with 6-12 turns.
    History grows exactly as it does in the real app. Zero failures is the
    only acceptable result.
    """

    _user = SimpleNamespace(id=5, is_authenticated=True)

    # ------------------------------------------------------------------
    # Infrastructure helpers
    # ------------------------------------------------------------------

    # Valid Groq LLM SQL response used whenever a query falls through to the LLM.
    # Pre-populate many copies so multi-turn tests never run out of responses.
    # IMPORTANT: params must use "__OWNER_ID__" sentinel (OWNER_PARAM), not a bare int.
    _FAKE_LLM_SQL_JSON = (
        '{"sql": "SELECT record_date, birds_died FROM ai_dailydata_data_view '
        'WHERE owner_id = %s ORDER BY birds_died ASC", '
        '"params": ["__OWNER_ID__"], "metric": "daily_data_query", "result_type": "list"}'
    )

    def _make_svc(self, entity_context=""):
        # Pre-load many valid JSON responses so every LLM-path turn succeeds.
        groq_responses = [self._FAKE_LLM_SQL_JSON] * 40
        return _make_llm_service(
            self._user,
            groq_responses=groq_responses,
            entity_context=entity_context,
        )

    def _make_svc_flock(self, flock_id=77, farm_id=42,
                        flock_name="Alpha Batch", farm_name="Red Farm"):
        groq_responses = [self._FAKE_LLM_SQL_JSON] * 40
        return _make_service_with_flock_context(
            self._user, flock_id=flock_id, farm_id=farm_id,
            flock_name=flock_name, farm_name=farm_name,
            groq_responses=groq_responses,
        )

    def _turn(self, svc, question, history):
        """One conversation turn: call answer(), append to history, return result."""
        result = svc.answer(question, history=list(history))
        history.append({"role": "user", "content": question})
        history.append({
            "role": "assistant",
            "content": result.get("message") or "",
            "metric": result.get("metric") or "",
            "resolved_flock_id": result.get("resolved_flock_id"),
            "resolved_farm_id": result.get("resolved_farm_id"),
        })
        return result

    def _ok(self, result, label=""):
        """Assert success + no ID leaks."""
        self.assertEqual(
            result["status"], "success",
            f"[{label}] Expected success, got: {result.get('message')}",
        )
        msg = (result.get("message") or "").lower()
        self.assertNotIn("farm_id=", msg, f"[{label}] farm_id= leaked in message")
        self.assertNotIn("flock_id=", msg, f"[{label}] flock_id= leaked in message")
        return result

    def _ok_metric(self, result, metric, label=""):
        """Assert success + exact metric + no ID leaks."""
        self._ok(result, label)
        self.assertEqual(
            result.get("metric"), metric,
            f"[{label}] Expected metric={metric!r}, got {result.get('metric')!r}",
        )
        return result

    # ==================================================================
    # Scenario 1: Farm & Flock Discovery (12 turns)
    # ==================================================================

    def test_s1_farm_flock_discovery_flow(self):
        svc = self._make_svc()
        h = []

        r = self._turn(svc, "hello", h)
        self._ok_metric(r, "conversation_only", "S1/T1")

        r = self._turn(svc, "show my farms", h)
        self._ok_metric(r, "farm_list", "S1/T2")

        r = self._turn(svc, "how many farms do I have", h)
        self._ok_metric(r, "farm_count", "S1/T3")

        # Must be flock_list, NOT farm_count inherited from T3
        r = self._turn(svc, "show all flocks", h)
        self._ok_metric(r, "flock_list", "S1/T4 - must be flock_list, not farm_count")

        r = self._turn(svc, "how many flocks do I have", h)
        self._ok_metric(r, "flock_count", "S1/T5")

        r = self._turn(svc, "flock performance", h)
        self._ok_metric(r, "flock_performance", "S1/T6")

        r = self._turn(svc, "total sales", h)
        self._ok_metric(r, "total_sales", "S1/T7")

        r = self._turn(svc, "total purchases", h)
        self._ok_metric(r, "total_purchases", "S1/T8")

        # Must be flock_list NOT total_purchases
        r = self._turn(svc, "show all flocks", h)
        self._ok_metric(r, "flock_list", "S1/T9 - must be flock_list after purchases")

        r = self._turn(svc, "most profitable flock", h)
        self._ok_metric(r, "most_profitable_flock", "S1/T10")

        r = self._turn(svc, "how to improve my farm", h)
        self._ok_metric(r, "improvement_advice", "S1/T11")

        r = self._turn(svc, "thanks", h)
        self._ok_metric(r, "conversation_only", "S1/T12")

    # ==================================================================
    # Scenario 2: show all flocks NEVER hijacked by mortality (core bug fix)
    # ==================================================================

    def test_s2_flock_list_never_hijacked_by_mortality(self):
        svc = self._make_svc()
        h = []

        r = self._turn(svc, "total mortality", h)
        self._ok_metric(r, "mortality", "S2/T1")

        r = self._turn(svc, "show all flocks", h)
        self._ok_metric(r, "flock_list", "S2/T2 - MUST NOT be mortality")

        r = self._turn(svc, "how many birds died", h)
        self._ok_metric(r, "mortality", "S2/T3")

        r = self._turn(svc, "list all my flocks", h)
        self._ok_metric(r, "flock_list", "S2/T4 - MUST NOT be mortality")

        r = self._turn(svc, "total deaths", h)
        self._ok_metric(r, "mortality", "S2/T5")

        r = self._turn(svc, "my flock list", h)
        self._ok_metric(r, "flock_list", "S2/T6 - MUST NOT be mortality")

        r = self._turn(svc, "total mortality", h)
        self._ok_metric(r, "mortality", "S2/T7")

        r = self._turn(svc, "all my flocks", h)
        self._ok_metric(r, "flock_list", "S2/T8 - MUST NOT be mortality")

    # ==================================================================
    # Scenario 3: farm_list never hijacked by feed
    # ==================================================================

    def test_s3_farm_list_never_hijacked_by_feed(self):
        svc = self._make_svc()
        h = []

        r = self._turn(svc, "total feed consumed", h)
        self._ok_metric(r, "feed_consumed", "S3/T1")

        r = self._turn(svc, "show my farms", h)
        self._ok_metric(r, "farm_list", "S3/T2 - must be farm_list after feed")

        r = self._turn(svc, "feed intake", h)
        self._ok_metric(r, "feed_consumed", "S3/T3")

        r = self._turn(svc, "all my farms", h)
        self._ok_metric(r, "farm_list", "S3/T4 - must be farm_list after feed")

    # ==================================================================
    # Scenario 4: flock_list never hijacked by FCR
    # ==================================================================

    def test_s4_flock_list_never_hijacked_by_fcr(self):
        svc = self._make_svc()
        h = []

        r = self._turn(svc, "average FCR", h)
        self._ok_metric(r, "average_fcr", "S4/T1")

        r = self._turn(svc, "show all flocks", h)
        self._ok_metric(r, "flock_list", "S4/T2 - must be flock_list after FCR")

        r = self._turn(svc, "feed conversion ratio", h)
        self._ok_metric(r, "average_fcr", "S4/T3")

        r = self._turn(svc, "list all flocks", h)
        self._ok_metric(r, "flock_list", "S4/T4 - must be flock_list after FCR")

    # ==================================================================
    # Scenario 5: flock_list never hijacked by sales
    # ==================================================================

    def test_s5_flock_list_never_hijacked_by_sales(self):
        svc = self._make_svc()
        h = []

        r = self._turn(svc, "total sales", h)
        self._ok_metric(r, "total_sales", "S5/T1")

        r = self._turn(svc, "show all flocks", h)
        self._ok_metric(r, "flock_list", "S5/T2 - must be flock_list after sales")

        r = self._turn(svc, "total revenue", h)
        self._ok_metric(r, "total_sales", "S5/T3")

        r = self._turn(svc, "show flocks", h)
        self._ok_metric(r, "flock_list", "S5/T4 - must be flock_list after sales")

    # ==================================================================
    # Scenario 6: flock_list never hijacked by weight
    # ==================================================================

    def test_s6_flock_list_never_hijacked_by_weight(self):
        svc = self._make_svc()
        h = []

        r = self._turn(svc, "average weight", h)
        self._ok_metric(r, "average_weight", "S6/T1")

        r = self._turn(svc, "show all flocks", h)
        self._ok_metric(r, "flock_list", "S6/T2 - must be flock_list after weight")

        r = self._turn(svc, "bird weight", h)
        self._ok_metric(r, "average_weight", "S6/T3")

        r = self._turn(svc, "list all my flocks", h)
        self._ok_metric(r, "flock_list", "S6/T4 - must be flock_list after weight")

    # ==================================================================
    # Scenario 7: Financial analysis conversation (12 turns)
    # ==================================================================

    def test_s7_financial_analysis_flow(self):
        svc = self._make_svc()
        h = []

        r = self._turn(svc, "total sales", h)
        self._ok_metric(r, "total_sales", "S7/T1")

        r = self._turn(svc, "total purchases", h)
        self._ok_metric(r, "total_purchases", "S7/T2")

        r = self._turn(svc, "most profitable flock", h)
        self._ok_metric(r, "most_profitable_flock", "S7/T3")

        r = self._turn(svc, "biggest loss flock", h)
        self._ok_metric(r, "biggest_loss_flock", "S7/T4")

        # flock_list must NOT be most_profitable or biggest_loss
        r = self._turn(svc, "show all flocks", h)
        self._ok_metric(r, "flock_list", "S7/T5 - must be flock_list after financial")

        r = self._turn(svc, "account summary", h)
        self._ok_metric(r, "farm_record_summary", "S7/T6")

        r = self._turn(svc, "show all flocks", h)
        self._ok_metric(r, "flock_list", "S7/T7 - must be flock_list after summary")

        r = self._turn(svc, "total income", h)
        self._ok_metric(r, "total_sales", "S7/T8")

        r = self._turn(svc, "total expenses", h)
        self._ok_metric(r, "total_purchases", "S7/T9")

        r = self._turn(svc, "show all flocks", h)
        self._ok_metric(r, "flock_list", "S7/T10 - must be flock_list after expenses")

        r = self._turn(svc, "how to improve my farm", h)
        self._ok_metric(r, "improvement_advice", "S7/T11")

        r = self._turn(svc, "ok thanks", h)
        self._ok_metric(r, "conversation_only", "S7/T12")

    # ==================================================================
    # Scenario 8: Metric cycling — every metric in sequence (10 turns)
    # ==================================================================

    def test_s8_metric_cycling_flow(self):
        svc = self._make_svc()
        h = []

        turns = [
            ("total mortality",       "mortality"),
            ("average FCR",           "average_fcr"),
            ("average weight",        "average_weight"),
            ("total feed",            "feed_consumed"),
            ("current birds",         "current_birds"),
            ("total sales",           "total_sales"),
            ("total purchases",       "total_purchases"),
            # After all the above, show all flocks must be flock_list
            ("show all flocks",       "flock_list"),
            ("show my farms",         "farm_list"),
            ("account summary",       "farm_record_summary"),
        ]

        for i, (q, expected) in enumerate(turns, 1):
            r = self._turn(svc, q, h)
            self._ok_metric(r, expected, f"S8/T{i}: {q!r}")

    # ==================================================================
    # Scenario 9: Time-series queries bypass aggregates in conversation
    # ==================================================================

    def test_s9_time_series_queries_in_conversation(self):
        svc = self._make_svc()
        h = []

        # T1 – aggregate mortality (deterministic)
        r = self._turn(svc, "total mortality", h)
        self._ok_metric(r, "mortality", "S9/T1")

        # T2 – time-series mortality → known_safe returns None → LLM handles
        r = self._turn(svc, "lowest mortality is in which days", h)
        self._ok(r, "S9/T2 - time-series mortality must succeed (not crash)")
        self.assertNotEqual(r.get("metric"), "mortality",
                            "S9/T2 must NOT use aggregate mortality plan")

        # T3 – back to aggregate mortality
        r = self._turn(svc, "total mortality", h)
        self._ok_metric(r, "mortality", "S9/T3 - aggregate still works after time-series")

        # T4 – aggregate FCR (deterministic)
        r = self._turn(svc, "average FCR", h)
        self._ok_metric(r, "average_fcr", "S9/T4")

        # T5 – time-series FCR → LLM handles
        r = self._turn(svc, "on which date was FCR highest", h)
        self._ok(r, "S9/T5 - time-series FCR must succeed")
        self.assertNotEqual(r.get("metric"), "average_fcr",
                            "S9/T5 must NOT use aggregate FCR plan")

        # T6 – back to aggregate FCR
        r = self._turn(svc, "average FCR", h)
        self._ok_metric(r, "average_fcr", "S9/T6")

        # T7 – aggregate weight (deterministic)
        r = self._turn(svc, "average weight", h)
        self._ok_metric(r, "average_weight", "S9/T7")

        # T8 – time-series weight → LLM handles
        r = self._turn(svc, "what dates had highest weight", h)
        self._ok(r, "S9/T8 - time-series weight must succeed")
        self.assertNotEqual(r.get("metric"), "average_weight",
                            "S9/T8 must NOT use aggregate weight plan")

        # T9 – flock list must be correct despite entire time-series chain
        r = self._turn(svc, "show all flocks", h)
        self._ok_metric(r, "flock_list", "S9/T9 - flock_list after time-series chain")

        # T10 – aggregate feed
        r = self._turn(svc, "total feed consumed", h)
        self._ok_metric(r, "feed_consumed", "S9/T10")

        # T11 – time-series feed
        r = self._turn(svc, "which days had the most feed consumed", h)
        self._ok(r, "S9/T11 - time-series feed must succeed")
        self.assertNotEqual(r.get("metric"), "feed_consumed",
                            "S9/T11 must NOT use aggregate feed plan")

        # T12 – flock list still correct
        r = self._turn(svc, "show all flocks", h)
        self._ok_metric(r, "flock_list", "S9/T12 - flock_list after time-series chain")

    # ==================================================================
    # Scenario 10: ID blocking doesn't break subsequent valid queries
    # ==================================================================

    def test_s10_id_blocking_does_not_break_conversation(self):
        svc = self._make_svc()
        h = []

        r = self._turn(svc, "what is my farm id", h)
        self.assertEqual(r["status"], "error", "S10/T1 - farm id must be blocked")

        r = self._turn(svc, "show my farms", h)
        self._ok_metric(r, "farm_list", "S10/T2 - must recover from ID block")

        r = self._turn(svc, "give me my flock ids", h)
        self.assertEqual(r["status"], "error", "S10/T3 - flock ids must be blocked")

        r = self._turn(svc, "list all flocks", h)
        self._ok_metric(r, "flock_list", "S10/T4 - must recover from ID block")

        r = self._turn(svc, "show sale ids", h)
        self.assertEqual(r["status"], "error", "S10/T5 - sale ids must be blocked")

        r = self._turn(svc, "total sales", h)
        self._ok_metric(r, "total_sales", "S10/T6 - must recover from ID block")

        r = self._turn(svc, "account summary", h)
        self._ok_metric(r, "farm_record_summary", "S10/T7")

    # ==================================================================
    # Scenario 11: Flock-context deep dive (flock_id=77 in entity context)
    # ==================================================================

    def test_s11_flock_context_deep_dive(self):
        svc = self._make_svc_flock()
        h = []

        r = self._turn(svc, "mortality", h)
        self._ok_metric(r, "mortality", "S11/T1")
        self.assertIn(77, r.get("params", []), "S11/T1 flock_id=77 in params")

        r = self._turn(svc, "FCR", h)
        self._ok_metric(r, "average_fcr", "S11/T2")
        self.assertIn(77, r.get("params", []), "S11/T2 flock_id=77 in params")

        r = self._turn(svc, "average weight", h)
        self._ok_metric(r, "average_weight", "S11/T3")
        self.assertIn(77, r.get("params", []), "S11/T3 flock_id=77 in params")

        r = self._turn(svc, "feed consumed", h)
        self._ok_metric(r, "feed_consumed", "S11/T4")
        self.assertIn(77, r.get("params", []), "S11/T4 flock_id=77 in params")

        r = self._turn(svc, "current birds", h)
        self._ok_metric(r, "current_birds", "S11/T5")
        self.assertIn(77, r.get("params", []), "S11/T5 flock_id=77 in params")

        r = self._turn(svc, "total sales", h)
        self._ok_metric(r, "total_sales", "S11/T6")
        self.assertIn(77, r.get("params", []), "S11/T6 flock_id=77 in params")

        # All flocks must NOT filter by flock context
        r = self._turn(svc, "show all flocks", h)
        self._ok_metric(r, "flock_list", "S11/T7 - must show all flocks, not only context flock")

        # Context still active after showing all flocks
        r = self._turn(svc, "mortality", h)
        self._ok_metric(r, "mortality", "S11/T8 - context still active")
        self.assertIn(77, r.get("params", []), "S11/T8 flock_id=77 persists")

        r = self._turn(svc, "flock performance", h)
        self._ok_metric(r, "flock_performance", "S11/T9")

        r = self._turn(svc, "most profitable flock", h)
        self._ok_metric(r, "most_profitable_flock", "S11/T10")

    # ==================================================================
    # Scenario 12: Rapid topic switching (12 turns)
    # ==================================================================

    def test_s12_rapid_topic_switching(self):
        svc = self._make_svc()
        h = []

        turns = [
            ("how many farms",           "farm_count"),
            ("average FCR",              "average_fcr"),
            ("total sales",              "total_sales"),
            ("show all flocks",          "flock_list"),    # NOT total_sales
            ("total mortality",          "mortality"),
            ("show my farms",            "farm_list"),     # NOT mortality
            ("average weight",           "average_weight"),
            ("list all flocks",          "flock_list"),    # NOT average_weight
            ("total purchases",          "total_purchases"),
            ("most profitable flock",    "most_profitable_flock"),
            ("show all flocks",          "flock_list"),    # NOT most_profitable
            ("account summary",          "farm_record_summary"),
        ]

        for i, (q, expected) in enumerate(turns, 1):
            r = self._turn(svc, q, h)
            self._ok_metric(r, expected, f"S12/T{i}: {q!r}")

    # ==================================================================
    # Scenario 13: Greetings sandwiched between data queries
    # ==================================================================

    def test_s13_greetings_between_queries(self):
        svc = self._make_svc()
        h = []

        r = self._turn(svc, "hi", h)
        self._ok_metric(r, "conversation_only", "S13/T1")

        r = self._turn(svc, "total mortality", h)
        self._ok_metric(r, "mortality", "S13/T2")

        r = self._turn(svc, "okay", h)
        self._ok_metric(r, "conversation_only", "S13/T3")

        r = self._turn(svc, "show all flocks", h)
        self._ok_metric(r, "flock_list", "S13/T4 - must be flock_list after okay")

        r = self._turn(svc, "thanks", h)
        self._ok_metric(r, "conversation_only", "S13/T5")

        r = self._turn(svc, "average FCR", h)
        self._ok_metric(r, "average_fcr", "S13/T6")

        r = self._turn(svc, "huh", h)
        self._ok_metric(r, "conversation_only", "S13/T7")

        r = self._turn(svc, "list all flocks", h)
        self._ok_metric(r, "flock_list", "S13/T8 - must be flock_list after huh")

    # ==================================================================
    # Scenario 14: Farm list never hijacked by any metric
    # ==================================================================

    def test_s14_farm_list_never_hijacked(self):
        svc = self._make_svc()
        h = []

        metrics_then_farms = [
            ("total mortality",       "mortality"),
            ("show my farms",         "farm_list"),
            ("average FCR",           "average_fcr"),
            ("all my farms",          "farm_list"),
            ("total feed",            "feed_consumed"),
            ("show farms",            "farm_list"),
            ("total sales",           "total_sales"),
            ("my farms",              "farm_list"),
            ("average weight",        "average_weight"),
            ("how many farms",        "farm_count"),
            ("account summary",       "farm_record_summary"),
            ("show my farms",         "farm_list"),
        ]

        for i, (q, expected) in enumerate(metrics_then_farms, 1):
            r = self._turn(svc, q, h)
            self._ok_metric(r, expected, f"S14/T{i}: {q!r}")

    # ==================================================================
    # Scenario 15: Performance flow
    # ==================================================================

    def test_s15_performance_flow(self):
        svc = self._make_svc()
        h = []

        r = self._turn(svc, "flock performance", h)
        self._ok_metric(r, "flock_performance", "S15/T1")

        r = self._turn(svc, "show all flocks", h)
        self._ok_metric(r, "flock_list", "S15/T2 - flock_list after performance")

        r = self._turn(svc, "how are my flocks doing", h)
        self._ok_metric(r, "flock_performance", "S15/T3")

        r = self._turn(svc, "most profitable flock", h)
        self._ok_metric(r, "most_profitable_flock", "S15/T4")

        r = self._turn(svc, "biggest loss flock", h)
        self._ok_metric(r, "biggest_loss_flock", "S15/T5")

        r = self._turn(svc, "show all flocks", h)
        self._ok_metric(r, "flock_list", "S15/T6 - flock_list after profit ranking")

        r = self._turn(svc, "flock health", h)
        self._ok_metric(r, "flock_performance", "S15/T7")

        r = self._turn(svc, "how to improve my farm", h)
        self._ok_metric(r, "improvement_advice", "S15/T8")

    # ==================================================================
    # Scenario 16: Account summary flow
    # ==================================================================

    def test_s16_account_summary_flow(self):
        svc = self._make_svc()
        h = []

        r = self._turn(svc, "account summary", h)
        self._ok_metric(r, "farm_record_summary", "S16/T1")

        r = self._turn(svc, "show all flocks", h)
        self._ok_metric(r, "flock_list", "S16/T2 - flock_list after summary")

        r = self._turn(svc, "my data", h)
        self._ok_metric(r, "farm_record_summary", "S16/T3")

        r = self._turn(svc, "show my farms", h)
        self._ok_metric(r, "farm_list", "S16/T4 - farm_list after summary")

        r = self._turn(svc, "account summary", h)
        self._ok_metric(r, "farm_record_summary", "S16/T5")

        r = self._turn(svc, "show all flocks", h)
        self._ok_metric(r, "flock_list", "S16/T6 - flock_list after summary")

    # ==================================================================
    # Scenario 17: Mortality deep-dive with date queries interleaved
    # ==================================================================

    def test_s17_mortality_and_date_queries(self):
        svc = self._make_svc()
        h = []

        r = self._turn(svc, "total mortality", h)
        self._ok_metric(r, "mortality", "S17/T1")

        r = self._turn(svc, "lowest mortality is in which days", h)
        self._ok(r, "S17/T2 - time-series must succeed")
        self.assertNotEqual(r.get("metric"), "mortality", "S17/T2 must bypass aggregate")

        r = self._turn(svc, "total mortality", h)
        self._ok_metric(r, "mortality", "S17/T3 - aggregate still works")

        r = self._turn(svc, "show all flocks", h)
        self._ok_metric(r, "flock_list", "S17/T4 - flock_list after time-series chain")

        r = self._turn(svc, "how many birds died", h)
        self._ok_metric(r, "mortality", "S17/T5")

        r = self._turn(svc, "list all my flocks", h)
        self._ok_metric(r, "flock_list", "S17/T6 - flock_list still correct")

        r = self._turn(svc, "which days had high deaths", h)
        self._ok(r, "S17/T7 - time-series deaths must succeed")
        self.assertNotEqual(r.get("metric"), "mortality", "S17/T7 must bypass aggregate")

        r = self._turn(svc, "all flocks", h)
        self._ok_metric(r, "flock_list", "S17/T8 - flock_list after deaths chain")

    # ==================================================================
    # Scenario 18: FCR/Weight date queries
    # ==================================================================

    def test_s18_fcr_weight_date_queries(self):
        svc = self._make_svc()
        h = []

        r = self._turn(svc, "average FCR", h)
        self._ok_metric(r, "average_fcr", "S18/T1")

        r = self._turn(svc, "on which date was FCR highest", h)
        self._ok(r, "S18/T2 - time-series FCR must succeed")
        self.assertNotEqual(r.get("metric"), "average_fcr", "S18/T2 must bypass aggregate FCR")

        r = self._turn(svc, "average FCR", h)
        self._ok_metric(r, "average_fcr", "S18/T3")

        r = self._turn(svc, "show all flocks", h)
        self._ok_metric(r, "flock_list", "S18/T4")

        r = self._turn(svc, "average weight", h)
        self._ok_metric(r, "average_weight", "S18/T5")

        r = self._turn(svc, "what dates had highest weight", h)
        self._ok(r, "S18/T6 - time-series weight must succeed")
        self.assertNotEqual(r.get("metric"), "average_weight", "S18/T6 must bypass aggregate weight")

        r = self._turn(svc, "average weight", h)
        self._ok_metric(r, "average_weight", "S18/T7")

        r = self._turn(svc, "show all flocks", h)
        self._ok_metric(r, "flock_list", "S18/T8")

    # ==================================================================
    # Scenario 19: Current birds monitoring flow
    # ==================================================================

    def test_s19_current_birds_monitoring(self):
        svc = self._make_svc()
        h = []

        r = self._turn(svc, "how many birds do I have", h)
        self._ok_metric(r, "current_birds", "S19/T1")

        r = self._turn(svc, "show all flocks", h)
        self._ok_metric(r, "flock_list", "S19/T2 - flock_list after current_birds")

        r = self._turn(svc, "birds alive", h)
        self._ok_metric(r, "current_birds", "S19/T3")

        r = self._turn(svc, "total mortality", h)
        self._ok_metric(r, "mortality", "S19/T4")

        r = self._turn(svc, "current birds", h)
        self._ok_metric(r, "current_birds", "S19/T5")

        r = self._turn(svc, "show all flocks", h)
        self._ok_metric(r, "flock_list", "S19/T6 - flock_list after birds+mortality")

    # ==================================================================
    # Scenario 20: Improvement advice flow
    # ==================================================================

    def test_s20_improvement_advice_flow(self):
        svc = self._make_svc()
        h = []

        r = self._turn(svc, "flock performance", h)
        self._ok_metric(r, "flock_performance", "S20/T1")

        r = self._turn(svc, "biggest loss flock", h)
        self._ok_metric(r, "biggest_loss_flock", "S20/T2")

        r = self._turn(svc, "how to improve my farm", h)
        self._ok_metric(r, "improvement_advice", "S20/T3")

        r = self._turn(svc, "show all flocks", h)
        self._ok_metric(r, "flock_list", "S20/T4 - flock_list after advice")

        r = self._turn(svc, "what can i do to improve my farm", h)
        self._ok_metric(r, "improvement_advice", "S20/T5")

        r = self._turn(svc, "show my farms", h)
        self._ok_metric(r, "farm_list", "S20/T6 - farm_list after advice")

        r = self._turn(svc, "give me advice on my farm", h)
        self._ok_metric(r, "improvement_advice", "S20/T7")

        r = self._turn(svc, "thanks", h)
        self._ok_metric(r, "conversation_only", "S20/T8")

    # ==================================================================
    # Scenario 21: Typo resilience throughout conversation
    # ==================================================================

    def test_s21_typo_resilience_flow(self):
        svc = self._make_svc()
        h = []

        r = self._turn(svc, "total mortallity", h)
        self._ok_metric(r, "mortality", "S21/T1 - typo in mortality")

        r = self._turn(svc, "sails total", h)
        self._ok_metric(r, "total_sales", "S21/T2 - typo sails=sales")

        r = self._turn(svc, "show all flocks", h)
        self._ok_metric(r, "flock_list", "S21/T3 - correct after typos")

        r = self._turn(svc, "avrage FCR", h)
        self._ok_metric(r, "average_fcr", "S21/T4 - typo avrage")

        r = self._turn(svc, "total feeed", h)
        self._ok_metric(r, "feed_consumed", "S21/T5 - typo feeed")

        r = self._turn(svc, "my farms", h)
        self._ok_metric(r, "farm_list", "S21/T6 - correct after all typos")

        r = self._turn(svc, "buggest loss", h)
        self._ok_metric(r, "biggest_loss_flock", "S21/T7 - typo buggest")

        r = self._turn(svc, "list all flocks", h)
        self._ok_metric(r, "flock_list", "S21/T8 - flock_list after buggest loss typo")

    # ==================================================================
    # Scenario 22: Comprehensive 12-turn flow A
    # ==================================================================

    def test_s22_comprehensive_12turn_flow_a(self):
        svc = self._make_svc()
        h = []

        r = self._turn(svc, "how many farms",          h); self._ok_metric(r, "farm_count",         "S22/T1")
        r = self._turn(svc, "how many flocks",         h); self._ok_metric(r, "flock_count",        "S22/T2")
        r = self._turn(svc, "current birds",           h); self._ok_metric(r, "current_birds",      "S22/T3")
        r = self._turn(svc, "total sales",             h); self._ok_metric(r, "total_sales",        "S22/T4")
        r = self._turn(svc, "total purchases",         h); self._ok_metric(r, "total_purchases",    "S22/T5")
        r = self._turn(svc, "total mortality",         h); self._ok_metric(r, "mortality",          "S22/T6")
        r = self._turn(svc, "show all flocks",         h); self._ok_metric(r, "flock_list",         "S22/T7 NOT mortality")
        r = self._turn(svc, "flock performance",       h); self._ok_metric(r, "flock_performance",  "S22/T8")
        r = self._turn(svc, "most profitable flock",   h); self._ok_metric(r, "most_profitable_flock", "S22/T9")
        r = self._turn(svc, "biggest loss flock",      h); self._ok_metric(r, "biggest_loss_flock", "S22/T10")
        r = self._turn(svc, "how to improve my farm",  h); self._ok_metric(r, "improvement_advice", "S22/T11")
        r = self._turn(svc, "ok thanks",               h); self._ok_metric(r, "conversation_only",  "S22/T12")

    # ==================================================================
    # Scenario 23: Comprehensive 12-turn flow B
    # ==================================================================

    def test_s23_comprehensive_12turn_flow_b(self):
        svc = self._make_svc()
        h = []

        r = self._turn(svc, "hello",               h); self._ok_metric(r, "conversation_only",  "S23/T1")
        r = self._turn(svc, "show my farms",       h); self._ok_metric(r, "farm_list",          "S23/T2")
        r = self._turn(svc, "average FCR",         h); self._ok_metric(r, "average_fcr",        "S23/T3")
        r = self._turn(svc, "show all flocks",     h); self._ok_metric(r, "flock_list",         "S23/T4 NOT average_fcr")
        r = self._turn(svc, "average weight",      h); self._ok_metric(r, "average_weight",     "S23/T5")
        r = self._turn(svc, "list all flocks",     h); self._ok_metric(r, "flock_list",         "S23/T6 NOT average_weight")
        r = self._turn(svc, "total feed",          h); self._ok_metric(r, "feed_consumed",      "S23/T7")
        r = self._turn(svc, "all my flocks",       h); self._ok_metric(r, "flock_list",         "S23/T8 NOT feed_consumed")
        r = self._turn(svc, "most profitable flock",h); self._ok_metric(r, "most_profitable_flock","S23/T9")
        r = self._turn(svc, "show all flocks",     h); self._ok_metric(r, "flock_list",         "S23/T10 NOT most_profitable")
        r = self._turn(svc, "account summary",     h); self._ok_metric(r, "farm_record_summary","S23/T11")
        r = self._turn(svc, "thanks",              h); self._ok_metric(r, "conversation_only",  "S23/T12")

    # ==================================================================
    # Scenario 24: Comprehensive 12-turn flow C (flock context)
    # ==================================================================

    def test_s24_comprehensive_12turn_flow_c_flock_context(self):
        svc = self._make_svc_flock()
        h = []

        r = self._turn(svc, "mortality",                 h); self._ok_metric(r, "mortality",            "S24/T1"); self.assertIn(77, r.get("params", []))
        r = self._turn(svc, "FCR",                       h); self._ok_metric(r, "average_fcr",          "S24/T2"); self.assertIn(77, r.get("params", []))
        r = self._turn(svc, "average weight",            h); self._ok_metric(r, "average_weight",       "S24/T3"); self.assertIn(77, r.get("params", []))
        r = self._turn(svc, "feed consumed",             h); self._ok_metric(r, "feed_consumed",        "S24/T4"); self.assertIn(77, r.get("params", []))
        r = self._turn(svc, "current birds",             h); self._ok_metric(r, "current_birds",        "S24/T5"); self.assertIn(77, r.get("params", []))
        r = self._turn(svc, "total sales",               h); self._ok_metric(r, "total_sales",          "S24/T6"); self.assertIn(77, r.get("params", []))
        r = self._turn(svc, "show all flocks",           h); self._ok_metric(r, "flock_list",           "S24/T7 all scope, not flock context")
        r = self._turn(svc, "mortality",                 h); self._ok_metric(r, "mortality",            "S24/T8 context still active"); self.assertIn(77, r.get("params", []))
        r = self._turn(svc, "flock performance",         h); self._ok_metric(r, "flock_performance",    "S24/T9")
        r = self._turn(svc, "most profitable flock",     h); self._ok_metric(r, "most_profitable_flock","S24/T10")
        r = self._turn(svc, "show all flocks",           h); self._ok_metric(r, "flock_list",           "S24/T11 NOT most_profitable")
        r = self._turn(svc, "how to improve my farm",    h); self._ok_metric(r, "improvement_advice",   "S24/T12")

    # ==================================================================
    # Scenario 25: All flock-list variations after mortality (exhaustive)
    # ==================================================================

    def test_s25_all_flock_list_variations_after_mortality(self):
        """Every phrasing of 'show flocks' must return flock_list after mortality."""
        svc = self._make_svc()
        h = []
        r = self._turn(svc, "total mortality", h)
        self._ok_metric(r, "mortality", "S25/setup")

        for phrase in [
            "show all flocks", "list all flocks", "my flock list",
            "all my flocks", "show flocks", "my flocks", "list flocks",
        ]:
            r = self._turn(svc, phrase, h)
            self._ok_metric(r, "flock_list",
                            f"S25: {phrase!r} must be flock_list, not mortality")

    # ==================================================================
    # Scenario 26: All farm-list variations after feed context (exhaustive)
    # ==================================================================

    def test_s26_all_farm_list_variations_after_feed(self):
        """Every phrasing of 'show farms' must return farm_list after feed context."""
        svc = self._make_svc()
        h = []
        r = self._turn(svc, "total feed consumed", h)
        self._ok_metric(r, "feed_consumed", "S26/setup")

        for phrase in [
            "show my farms", "list all farms", "my farm list",
            "all my farms", "show farms", "my farms",
        ]:
            r = self._turn(svc, phrase, h)
            self._ok_metric(r, "farm_list",
                            f"S26: {phrase!r} must be farm_list, not feed_consumed")

    # ==================================================================
    # Scenario 27: Zero ID leaks across 12-turn conversation
    # ==================================================================

    def test_s27_no_id_leaks_throughout_conversation(self):
        svc = self._make_svc_flock()
        h = []

        for i, q in enumerate([
            "mortality", "FCR", "average weight", "feed consumed",
            "current birds", "total sales", "total purchases",
            "show all flocks", "flock performance", "most profitable flock",
            "biggest loss flock", "how to improve my farm",
        ], 1):
            r = self._turn(svc, q, h)
            msg = (r.get("message") or "").lower()
            self.assertNotIn("farm_id=", msg, f"S27/T{i}: farm_id= leaked in {q!r}")
            self.assertNotIn("flock_id=", msg, f"S27/T{i}: flock_id= leaked in {q!r}")

    # ==================================================================
    # Scenario 28: owner_id=5 always in params for data queries
    # ==================================================================

    def test_s28_owner_id_always_in_params(self):
        svc = self._make_svc()
        h = []

        data_queries = [
            ("show my farms",          "farm_list"),
            ("show all flocks",        "flock_list"),
            ("how many farms",         "farm_count"),
            ("total mortality",        "mortality"),
            ("average FCR",            "average_fcr"),
            ("average weight",         "average_weight"),
            ("total feed",             "feed_consumed"),
            ("current birds",          "current_birds"),
            ("total sales",            "total_sales"),
            ("total purchases",        "total_purchases"),
            ("most profitable flock",  "most_profitable_flock"),
            ("how to improve my farm", "improvement_advice"),
        ]

        for i, (q, expected_metric) in enumerate(data_queries, 1):
            r = self._turn(svc, q, h)
            self._ok_metric(r, expected_metric, f"S28/T{i}")
            self.assertIn(5, r.get("params", []),
                          f"S28/T{i}: owner_id=5 not in params for {q!r}")

    # ==================================================================
    # Scenario 29: Full 12-turn conversation covering all metric families
    # ==================================================================

    def test_s29_full_coverage_12turn(self):
        svc = self._make_svc()
        h = []

        r = self._turn(svc, "show my farms",          h); self._ok_metric(r, "farm_list",           "S29/T1")
        r = self._turn(svc, "show all flocks",        h); self._ok_metric(r, "flock_list",          "S29/T2")
        r = self._turn(svc, "total mortality",         h); self._ok_metric(r, "mortality",           "S29/T3")
        r = self._turn(svc, "average FCR",             h); self._ok_metric(r, "average_fcr",         "S29/T4")
        r = self._turn(svc, "average weight",          h); self._ok_metric(r, "average_weight",      "S29/T5")
        r = self._turn(svc, "total feed",              h); self._ok_metric(r, "feed_consumed",       "S29/T6")
        r = self._turn(svc, "total sales",             h); self._ok_metric(r, "total_sales",         "S29/T7")
        r = self._turn(svc, "total purchases",         h); self._ok_metric(r, "total_purchases",     "S29/T8")
        r = self._turn(svc, "most profitable flock",   h); self._ok_metric(r, "most_profitable_flock","S29/T9")
        # After all of the above, flock list must still be correct
        r = self._turn(svc, "show all flocks",         h); self._ok_metric(r, "flock_list",          "S29/T10 NOT any prev metric")
        r = self._turn(svc, "account summary",         h); self._ok_metric(r, "farm_record_summary", "S29/T11")
        r = self._turn(svc, "how to improve my farm",  h); self._ok_metric(r, "improvement_advice",  "S29/T12")

    # ==================================================================
    # Scenario 30: show_all_flocks after EVERY possible preceding metric
    # ==================================================================

    def test_s30_show_all_flocks_after_every_metric(self):
        """Verify flock_list is always correctly routed after any possible preceding metric."""
        metrics = [
            ("total mortality",        "mortality"),
            ("average FCR",            "average_fcr"),
            ("average weight",         "average_weight"),
            ("total feed",             "feed_consumed"),
            ("current birds",          "current_birds"),
            ("total sales",            "total_sales"),
            ("total purchases",        "total_purchases"),
            ("most profitable flock",  "most_profitable_flock"),
            ("biggest loss flock",     "biggest_loss_flock"),
            ("flock performance",      "flock_performance"),
            ("account summary",        "farm_record_summary"),
            ("how to improve my farm", "improvement_advice"),
        ]

        for metric_q, expected_metric in metrics:
            svc = self._make_svc()
            h = []
            r = self._turn(svc, metric_q, h)
            self._ok_metric(r, expected_metric, f"S30 setup: {metric_q!r}")
            r = self._turn(svc, "show all flocks", h)
            self._ok_metric(r, "flock_list",
                            f"S30: show_all_flocks after {metric_q!r} must be flock_list, not {expected_metric!r}")
