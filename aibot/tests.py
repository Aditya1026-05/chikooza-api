from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from common.groq_client import GroqChatClient

from .llm_sql import (
    ChikoozaLLMTextToSQLService,
    ChikoozaSQLPromptBuilder,
    EntityResolution,
    OWNER_PARAM,
)
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

        self.assertEqual(route, CONVERSATION)

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
        self.assertIn("farm summary", response["answer"])

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
