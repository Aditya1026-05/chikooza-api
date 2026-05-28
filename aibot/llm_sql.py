import json
import logging
import os
import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import httpx
from flocks.models import Flock
from farm.models import Farm

from common.groq_client import GroqAllKeysFailed, GroqChatClient

from .modern_services import (
    SQLPlan,
    TEXT_TO_SQL,
    ChikoozaTextToSQLService,
    TenantSafeSQLExecutor,
    is_broad_summary_query,
)

logger = logging.getLogger(__name__)

OWNER_PARAM = "__OWNER_ID__"


CHIKOOZA_SQL_SCHEMA = """
Allowed SQL views and columns:

1. ai_farm_flock_data_view
   Purpose: farms and flock master data, including farms with no flocks.
   Columns:
   owner_id, farm_id, farm_name, farm_address, farm_city, farm_pin, shed_count,
   farm_status, flock_id, flock_name, hatch_date, flock_size, actual_birds,
   chick_weight, feed_sys, drinking_sys, ec_shed, flock_cost, flock_bird,
   flock_status, breed_name, hatchery_name, integrator_name.

2. ai_sale_data_view
   Purpose: flock sales/revenue/lifting records.
   Columns:
   owner_id, farm_id, farm_name, farm_city, flock_id, flock_name, flock_size,
   actual_birds, sale_id, sale_type, sale_date, lifting_count, total_weight,
   average_weight, rate_per_kg, sale_amount, buyer, vehicle_no, sale_remarks,
   feed_total, med_price, vacc_price, admin_charges, rearing_charges,
   performance_incentives, rate_incentives, production_cost_recovery, shortages,
   excess_mortality, fcr_recovery, integration_cost.

3. ai_purchase_data_view
   Purpose: feed, medicine, vaccination, equipment, labour and other purchases.
   Columns:
   owner_id, farm_id, farm_name, farm_city, flock_id, flock_name, flock_size,
   actual_birds, flock_cost, purchase_type, purchase_date, purchase_amount,
   quantity, purchased_item, item_type, unit, size, company_name, purchase_remarks,
   adjust, adjust_type.

4. ai_dailydata_data_view
   Purpose: daily flock performance, mortality, feed, weight, FCR and status.
   Columns:
   owner_id, farm_id, farm_name, farm_city, flock_id, flock_name, flock_size,
   actual_birds, daily_data_id, record_date, birds_died, total_mort,
   birds_current, feed_stock, feed_consumed_kg, total_feed,
   average_bird_weight, average_feed, total_average_feed, fcr, total_fcr,
   cooling, heating, seek, medicine, remarks, daily_data_status,
   darkness_time_name, feed_availability_name, flock_birds.
""".strip()


SQL_GENERATION_SYSTEM = f"""
You are Chikooza Farmer AI's SQL planner.
Return ONLY one valid JSON object. No markdown. No explanation.

JSON shape:
{{
  "sql": "SELECT ... WHERE owner_id = %s ...",
  "params": ["{OWNER_PARAM}", "..."],
  "metric": "short_metric_name",
  "result_type": "money|count|decimal|quantity|table|summary"
}}

Hard rules:
1. Use ONLY these views:
{CHIKOOZA_SQL_SCHEMA}
2. Every referenced view must be tenant-filtered with owner_id = %s.
3. Never put the numeric farmer/user id in SQL or params. For each owner_id = %s placeholder, put "{OWNER_PARAM}" at the same position in params. The backend replaces it with the authenticated farmer id.
4. Use %s placeholders for every dynamic value. Do not inline names, dates, ids, or text values.
5. Do not use SELECT *. Select only useful columns.
6. Generate exactly one SELECT statement. No INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, PRAGMA, ATTACH, DETACH, GRANT, REVOKE, or semicolon-separated statements.
7. Use SQLite/PostgreSQL-compatible SQL only: LOWER(col) LIKE LOWER(%s), SUBSTR(CAST(date_col AS TEXT), 1, 7) for month, SUBSTR(CAST(date_col AS TEXT), 1, 4) for year, LIMIT N.
8. For row-list queries, add LIMIT 100 unless the user asks for a smaller limit.
9. "my", "our", "me", "us", and "this farmer" mean the authenticated farmer only.
10. If the user asks for another farmer/user/customer's private data, return {{"blocked": true, "reason": "cross_tenant_request"}}.
11. If the question is not answerable from these views, return {{"blocked": true, "reason": "not_answerable_from_farm_data"}}.
12. If the user asks a follow-up like "what about that flock" or "compare it", use the recent conversation to resolve the farm/flock/metric context.
13. If Entity Context resolves a farm/flock mention, use the resolved internal farm_id/flock_id exactly. For example, if the farmer says "flock 1" and Entity Context says it means flock_id 4, use flock_id = %s with param 4.

Common Chikooza mappings:
- revenue/sales/income -> SUM(sale_amount) from ai_sale_data_view.
- cost/expense/spent/purchase -> SUM(purchase_amount) from ai_purchase_data_view.
- profit/loss/net -> sales minus purchases minus flock_cost. Avoid duplicated flock_cost by aggregating it per flock first.
- mortality/deaths/dead birds -> SUM(birds_died), total_mort, or latest birds_current from ai_dailydata_data_view.
- FCR/feed conversion -> AVG(fcr), latest fcr, or total_fcr based on wording.
- current birds/current flock size -> latest birds_current ordered by record_date DESC.
- best flock -> compare low FCR, low mortality, high average weight, or high profit based on wording.
- latest/current -> ORDER BY the relevant date column DESC LIMIT 1.
- vague farmer English like "total things", "what all I have", "show my stuff", "my data", "my records", or incomplete grammar should map to a safe account summary, not a blocked answer.

Column ownership rules:
- sale_amount exists only in ai_sale_data_view.
- purchase_amount, purchased_item, company_name, purchase_type exist only in ai_purchase_data_view.
- fcr, total_fcr, birds_died, total_mort, birds_current, feed_consumed_kg, average_bird_weight exist only in ai_dailydata_data_view.
- farm_address, shed_count, hatch_date, flock_cost, breed_name, hatchery_name exist in ai_farm_flock_data_view.
- flock_cost also exists in ai_purchase_data_view, but prefer ai_farm_flock_data_view for flock-cost-only questions.
- When Entity Context gives a resolved farm_id/flock_id, filter with that id: `flock_id = %s` or `farm_id = %s`. Do not use the farmer's rough text as the id.

Exact SQL patterns to copy when relevant:
1. Profit for a flock or farm:
{{
  "sql": "SELECT base.flock_id, base.flock_name, COALESCE(sales.total_sales, 0) AS total_sales, COALESCE(purchases.total_purchases, 0) AS total_purchases, COALESCE(base.flock_cost, 0) AS flock_cost, COALESCE(sales.total_sales, 0) - COALESCE(purchases.total_purchases, 0) - COALESCE(base.flock_cost, 0) AS result FROM (SELECT flock_id, flock_name, MAX(flock_cost) AS flock_cost FROM ai_farm_flock_data_view WHERE owner_id = %s AND LOWER(flock_name) LIKE LOWER(%s) GROUP BY flock_id, flock_name) base LEFT JOIN (SELECT flock_id, SUM(sale_amount) AS total_sales FROM ai_sale_data_view WHERE owner_id = %s GROUP BY flock_id) sales ON sales.flock_id = base.flock_id LEFT JOIN (SELECT flock_id, SUM(purchase_amount) AS total_purchases FROM ai_purchase_data_view WHERE owner_id = %s GROUP BY flock_id) purchases ON purchases.flock_id = base.flock_id",
  "params": ["{OWNER_PARAM}", "%flock name%", "{OWNER_PARAM}", "{OWNER_PARAM}"],
  "metric": "profit_by_flock",
  "result_type": "money"
}}
2. Compare feed and sales by flock:
{{
  "sql": "SELECT d.flock_id, d.flock_name, COALESCE(d.feed_consumed_kg, 0) AS feed_consumed_kg, COALESCE(s.total_sales, 0) AS total_sales FROM (SELECT flock_id, flock_name, SUM(feed_consumed_kg) AS feed_consumed_kg FROM ai_dailydata_data_view WHERE owner_id = %s GROUP BY flock_id, flock_name) d LEFT JOIN (SELECT flock_id, SUM(sale_amount) AS total_sales FROM ai_sale_data_view WHERE owner_id = %s GROUP BY flock_id) s ON s.flock_id = d.flock_id ORDER BY d.flock_name LIMIT 100",
  "params": ["{OWNER_PARAM}", "{OWNER_PARAM}"],
  "metric": "feed_sales_by_flock",
  "result_type": "table"
}}
3. Latest mortality/current birds for one flock:
{{
  "sql": "SELECT record_date, flock_id, flock_name, birds_died, total_mort, birds_current, fcr, average_bird_weight FROM ai_dailydata_data_view WHERE owner_id = %s AND LOWER(flock_name) LIKE LOWER(%s) AND daily_data_id IS NOT NULL ORDER BY record_date DESC LIMIT 1",
  "params": ["{OWNER_PARAM}", "%flock name%"],
  "metric": "latest_flock_status",
  "result_type": "summary"
}}
4. Vague account summary / total things:
{{
  "sql": "SELECT (SELECT COUNT(DISTINCT farm_id) FROM ai_farm_flock_data_view WHERE owner_id = %s AND farm_id IS NOT NULL) AS farm_count, (SELECT COUNT(DISTINCT flock_id) FROM ai_farm_flock_data_view WHERE owner_id = %s AND flock_id IS NOT NULL) AS flock_count, (SELECT COALESCE(SUM(current_rows.birds_current), 0) FROM ai_dailydata_data_view current_rows WHERE current_rows.owner_id = %s AND current_rows.daily_data_id IS NOT NULL AND current_rows.record_date = (SELECT MAX(compare_rows.record_date) FROM ai_dailydata_data_view compare_rows WHERE compare_rows.owner_id = %s AND compare_rows.flock_id = current_rows.flock_id AND compare_rows.daily_data_id IS NOT NULL)) AS current_birds, (SELECT COALESCE(SUM(sale_amount), 0) FROM ai_sale_data_view WHERE owner_id = %s) AS total_sales, (SELECT COALESCE(SUM(purchase_amount), 0) FROM ai_purchase_data_view WHERE owner_id = %s) AS total_purchases, (SELECT COALESCE(SUM(feed_consumed_kg), 0) FROM ai_dailydata_data_view WHERE owner_id = %s) AS total_feed_consumed, (SELECT COALESCE(SUM(birds_died), 0) FROM ai_dailydata_data_view WHERE owner_id = %s) AS total_mortality, (SELECT COALESCE(AVG(fcr), 0) FROM ai_dailydata_data_view WHERE owner_id = %s AND fcr IS NOT NULL) AS average_fcr",
  "params": ["{OWNER_PARAM}", "{OWNER_PARAM}", "{OWNER_PARAM}", "{OWNER_PARAM}", "{OWNER_PARAM}", "{OWNER_PARAM}", "{OWNER_PARAM}", "{OWNER_PARAM}", "{OWNER_PARAM}"],
  "metric": "farm_record_summary",
  "result_type": "summary"
}}

Do not mix aggregate functions like SUM/AVG with plain row columns unless you also GROUP BY those row columns. For latest/current questions, prefer latest row fields over SUM.
""".strip()


ANSWER_SYSTEM = """
You are Chikooza Farmer AI.
Explain the SQL result in simple farmer-friendly English.
Do not mention SQL, database tables, JSON, prompts, or implementation details.
Be precise with numbers and units. Use Rs. for money.
If a result column is feed_consumed_kg, call it kg of feed, not generic units.
If records are missing, say what data is missing and what the farmer should enter.
For comparison answers, state the winner and the main reason.
Keep simple answers to 1-3 sentences. Use short bullets only for multi-row results.
Never claim to know another farmer's private data.
""".strip()


@dataclass(frozen=True)
class LLMPlanPayload:
    sql: str
    params: list[Any]
    metric: str
    result_type: str


class ChikoozaSQLPromptBuilder:
    """Builds the strict SQL-generation messages sent to Groq."""

    def messages(
        self,
        question: str,
        history: list[dict] | None = None,
        entity_context: str = "",
    ) -> list[dict[str, str]]:
        history_text = self._history_text(history or [])
        user_prompt = f"""
Recent conversation:
{history_text or "No previous conversation in this chat."}

Entity Context:
{entity_context or "No farm/flock entity was pre-resolved."}

Current farmer question:
{question}

Return the JSON SQL plan now.
""".strip()
        return [
            {"role": "system", "content": SQL_GENERATION_SYSTEM},
            {"role": "user", "content": user_prompt},
        ]

    def _history_text(self, history: list[dict]) -> str:
        parts = []
        for item in history[-8:]:
            role = item.get("role", "user")
            content = str(item.get("content", "")).strip()
            if content:
                parts.append(f"{role.title()}: {content}")
        return "\n".join(parts)


@dataclass(frozen=True)
class EntityResolution:
    context: str
    direct_response: dict | None = None


class ChikoozaEntityResolver:
    """
    U: NEW: Resolve rough farmer language such as "flock 1", "first flock", or
    U: a public id into the authenticated farmer's actual farm/flock before the
    U: LLM builds SQL. This prevents the LLM from treating "flock 1" as a raw
    U: database id that may not exist for this farmer.
    """

    FLOCK_NUMBER_PATTERN = re.compile(r"\bflock\s*(?:id|#)?\s*(\d+)\b")
    FARM_NUMBER_PATTERN = re.compile(r"\bfarm\s*(?:id|#)?\s*(\d+)\b")
    ORDINAL_WORDS = {
        "first": 1,
        "1st": 1,
        "second": 2,
        "2nd": 2,
        "third": 3,
        "3rd": 3,
        "fourth": 4,
        "4th": 4,
        "fifth": 5,
        "5th": 5,
    }

    def __init__(self, user):
        self.user = user

    def resolve(self, question: str) -> EntityResolution:
        farms = self._farms()
        flocks = self._flocks()
        query = re.sub(r"\s+", " ", (question or "").lower()).strip()
        context_lines = [
            self._available_farms_context(farms),
            self._available_flocks_context(flocks),
        ]

        flock_resolution = self._resolve_flock(query, flocks)
        if flock_resolution == "not_found":
            return EntityResolution(
                context="\n".join(context_lines),
                direct_response=self._missing_flock_response(query, flocks),
            )
        if flock_resolution:
            context_lines.append(
                "Resolved flock mention: "
                f"flock_id={flock_resolution.id}, "
                f"flock_public_id={flock_resolution.public_id}, "
                f"flock_name={flock_resolution.name}."
            )

        farm_resolution = self._resolve_farm(query, farms)
        if farm_resolution == "not_found":
            return EntityResolution(
                context="\n".join(context_lines),
                direct_response=self._missing_farm_response(query, farms),
            )
        if farm_resolution:
            context_lines.append(
                "Resolved farm mention: "
                f"farm_id={farm_resolution.id}, "
                f"farm_public_id={farm_resolution.public_id}, "
                f"farm_name={farm_resolution.name}."
            )

        return EntityResolution(context="\n".join(context_lines))

    def _farms(self):
        return list(Farm.objects.filter(user=self.user).order_by("id")[:30])

    def _flocks(self):
        return list(
            Flock.objects.filter(user=self.user)
            .select_related("farm")
            .order_by("id")[:50]
        )

    def _resolve_flock(self, query: str, flocks: list):
        if not flocks:
            return None

        numeric_match = self.FLOCK_NUMBER_PATTERN.search(query)
        if numeric_match:
            number = int(numeric_match.group(1))
            exact = self._find_by_id_or_public_id(flocks, number)
            if exact:
                return exact
            if 1 <= number <= len(flocks):
                return flocks[number - 1]
            return "not_found"

        ordinal = self._ordinal_for_phrase(query, "flock")
        if ordinal:
            if 1 <= ordinal <= len(flocks):
                return flocks[ordinal - 1]
            return "not_found"

        for flock in flocks:
            if flock.name and flock.name.lower() in query:
                return flock

        if self._looks_like_named_flock_reference(query):
            return "not_found"

        return None

    def _resolve_farm(self, query: str, farms: list):
        if not farms:
            return None

        numeric_match = self.FARM_NUMBER_PATTERN.search(query)
        if numeric_match:
            number = int(numeric_match.group(1))
            exact = self._find_by_id_or_public_id(farms, number)
            if exact:
                return exact
            if 1 <= number <= len(farms):
                return farms[number - 1]
            return "not_found"

        ordinal = self._ordinal_for_phrase(query, "farm")
        if ordinal:
            if 1 <= ordinal <= len(farms):
                return farms[ordinal - 1]
            return "not_found"

        for farm in farms:
            if farm.name and farm.name.lower() in query:
                return farm

        return None

    def _find_by_id_or_public_id(self, objects: list, number: int):
        return next(
            (
                obj
                for obj in objects
                if int(obj.id) == number or int(obj.public_id) == number
            ),
            None,
        )

    def _ordinal_for_phrase(self, query: str, label: str) -> int | None:
        for word, value in self.ORDINAL_WORDS.items():
            if re.search(rf"\b(?:{word}\s+{label}|{label}\s+{word})\b", query):
                return value
        return None

    def _looks_like_named_flock_reference(self, query: str) -> bool:
        return bool(
            re.search(r"\b(?:for|of|in|about)\s+[a-z0-9 ]*(?:batch|flock)\b", query)
        )

    def _available_farms_context(self, farms: list) -> str:
        if not farms:
            return "Available farms for this farmer: none."
        farm_text = "; ".join(
            f"{index}. farm_id={farm.id}, farm_public_id={farm.public_id}, farm_name={farm.name}"
            for index, farm in enumerate(farms, start=1)
        )
        return f"Available farms for this farmer: {farm_text}."

    def _available_flocks_context(self, flocks: list) -> str:
        if not flocks:
            return "Available flocks for this farmer: none."
        flock_text = "; ".join(
            (
                f"{index}. flock_id={flock.id}, flock_public_id={flock.public_id}, "
                f"flock_name={flock.name}, farm_name={flock.farm.name}"
            )
            for index, flock in enumerate(flocks, start=1)
        )
        return f"Available flocks for this farmer: {flock_text}."

    def _missing_flock_response(self, query: str, flocks: list) -> dict:
        available = ", ".join(flock.name for flock in flocks) if flocks else "none yet"
        return {
            "status": "success",
            "data": {"available_flocks": [flock.name for flock in flocks]},
            "answer": (
                "I could not find that flock in your account. "
                f"Available flocks: {available}. "
                "Please ask using the flock name, or use first/second flock if you mean list position."
            ),
            "message": (
                "I could not find that flock in your account. "
                f"Available flocks: {available}."
            ),
            "rows": [],
            "query": None,
            "params": [],
            "route": TEXT_TO_SQL,
            "metric": "missing_flock",
            "engine": "entity_resolver",
        }

    def _missing_farm_response(self, query: str, farms: list) -> dict:
        available = ", ".join(farm.name for farm in farms) if farms else "none yet"
        return {
            "status": "success",
            "data": {"available_farms": [farm.name for farm in farms]},
            "answer": (
                "I could not find that farm in your account. "
                f"Available farms: {available}. "
                "Please ask using the farm name, or use first/second farm if you mean list position."
            ),
            "message": (
                "I could not find that farm in your account. "
                f"Available farms: {available}."
            ),
            "rows": [],
            "query": None,
            "params": [],
            "route": TEXT_TO_SQL,
            "metric": "missing_farm",
            "engine": "entity_resolver",
        }


class ChikoozaLLMTextToSQLService:
    """
    U: Groq-backed Farmer AI SQL service adapted from the separate chatbot repo.
    U: The old deterministic ChikoozaTextToSQLService remains as fallback; this
    U: class adds stronger natural-language coverage, conversation context, and
    U: key-rotated LLM calls while still executing only tenant-safe SQL plans.
    """

    MAX_SQL_ATTEMPTS = 2

    def __init__(
        self,
        user,
        *,
        groq_client: GroqChatClient | None = None,
        fallback_service: ChikoozaTextToSQLService | None = None,
        entity_resolver: ChikoozaEntityResolver | None = None,
    ):
        self.user = user
        self.executor = TenantSafeSQLExecutor()
        self.prompt_builder = ChikoozaSQLPromptBuilder()
        self.fallback_service = fallback_service or ChikoozaTextToSQLService(user=user)
        self.entity_resolver = entity_resolver or ChikoozaEntityResolver(user=user)
        self.client = groq_client or GroqChatClient(
            model=os.getenv("AIBOT_SQL_MODEL", "llama-3.3-70b-versatile"),
            fallback_model=os.getenv(
                "AIBOT_SQL_FALLBACK_MODEL", "llama-3.1-8b-instant"
            ),
            timeout=float(os.getenv("AIBOT_SQL_TIMEOUT", "30")),
        )

    @property
    def is_available(self) -> bool:
        return self.client.has_keys

    def answer(self, question: str, history: list[dict] | None = None) -> dict:
        if is_broad_summary_query(question):
            # U: NEW: broad "show me all data" questions use the deterministic
            # U: summary plan so Groq cannot reduce them to one random metric.
            return self._fallback_answer(
                question,
                history,
                reason="Broad account summary query.",
            )

        deterministic = self._known_deterministic_answer(question, history)
        if deterministic:
            return deterministic

        if not self.is_available:
            return self._fallback_answer(
                question, history, reason="Groq is not configured."
            )

        last_error: Exception | None = None
        error_feedback = ""
        entity_resolution = self.entity_resolver.resolve(question)
        if entity_resolution.direct_response:
            return entity_resolution.direct_response

        for _attempt in range(self.MAX_SQL_ATTEMPTS):
            try:
                plan = self._build_plan(
                    question,
                    history,
                    entity_context=entity_resolution.context,
                    error_feedback=error_feedback,
                )
                rows = self.executor.execute(plan)
                answer = self._format_answer(
                    question,
                    plan,
                    rows,
                    history,
                    entity_context=entity_resolution.context,
                )
                return {
                    "status": "success",
                    "data": rows[0] if len(rows) == 1 else rows,
                    "answer": answer,
                    "message": answer,
                    "rows": rows,
                    "query": plan.sql,
                    "params": plan.params,
                    "route": TEXT_TO_SQL,
                    "metric": plan.metric,
                    "engine": "groq_sql",
                }
            except BlockedAIQuery as exc:
                return {
                    "status": "error",
                    "message": self._blocked_message(str(exc)),
                    "suggestion": self._blocked_suggestion(str(exc)),
                    "route": TEXT_TO_SQL,
                    "engine": "groq_sql",
                }
            except Exception as exc:
                last_error = exc
                error_feedback = str(exc)[:500]
                logger.warning("Groq SQL attempt failed: %s", exc)

        return self._fallback_answer(
            question, history, reason=str(last_error or "Unknown LLM SQL failure.")
        )

    def _build_plan(
        self,
        question: str,
        history: list[dict] | None,
        *,
        entity_context: str = "",
        error_feedback: str = "",
    ) -> SQLPlan:
        messages = self.prompt_builder.messages(question, history, entity_context)
        if error_feedback:
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "The previous SQL plan failed validation/execution with this error: "
                        f"{error_feedback}. Return a corrected JSON SQL plan only."
                    ),
                }
            )

        result = self.client.chat(
            messages,
            model=os.getenv("AIBOT_SQL_MODEL", "llama-3.3-70b-versatile"),
            fallback_model=os.getenv(
                "AIBOT_SQL_FALLBACK_MODEL", "llama-3.1-8b-instant"
            ),
            temperature=0,
            max_tokens=900,
            timeout=float(os.getenv("AIBOT_SQL_TIMEOUT", "30")),
        )
        payload = self._parse_plan_payload(result.content)
        return self._to_sql_plan(payload)

    def _parse_plan_payload(self, content: str) -> LLMPlanPayload:
        cleaned = self._strip_code_fences(content)
        try:
            raw = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ValueError("The AI did not return valid JSON.") from exc

        if raw.get("blocked"):
            raise BlockedAIQuery(raw.get("reason") or "blocked")

        sql = str(raw.get("sql", "")).strip().rstrip(";")
        params = raw.get("params", [])
        if not isinstance(params, list):
            raise ValueError("AI SQL params must be a list.")

        return LLMPlanPayload(
            sql=sql,
            params=params,
            metric=str(raw.get("metric") or "farm_data_query"),
            result_type=str(raw.get("result_type") or "summary"),
        )

    def _to_sql_plan(self, payload: LLMPlanPayload) -> SQLPlan:
        placeholder_count = payload.sql.count("%s")
        owner_filter_count = re.sub(r"\s*=\s*", " = ", payload.sql.lower()).count(
            "owner_id = %s"
        )
        owner_param_count = sum(1 for param in payload.params if param == OWNER_PARAM)

        if placeholder_count != len(payload.params):
            raise ValueError("SQL placeholder count does not match params.")
        if owner_filter_count == 0:
            raise ValueError("SQL is missing the tenant owner filter.")
        if owner_param_count != owner_filter_count:
            raise ValueError("SQL owner filters must use authenticated owner params.")

        safe_params = [
            self.user.id if param == OWNER_PARAM else param for param in payload.params
        ]
        return SQLPlan(
            sql=payload.sql,
            params=safe_params,
            metric=payload.metric,
            result_type=payload.result_type,
        )

    def _format_answer(
        self,
        question: str,
        plan: SQLPlan,
        rows: list[dict],
        history: list[dict] | None,
        entity_context: str = "",
    ) -> str:
        deterministic = self._deterministic_metric_answer(rows, entity_context)
        if deterministic:
            return deterministic

        compact_rows = self._json_safe_rows(rows[:25])
        prompt = f"""
Farmer question:
{question}

Entity context:
{entity_context or "No entity context."}

Metric:
{plan.metric}

Result rows:
{json.dumps(compact_rows, ensure_ascii=True)}

If there are more than 25 matching rows, only the first 25 are shown here.
Write the answer for the farmer.
If the farmer used a rough phrase like "flock 1" but Entity Context resolved it to a real flock, answer for the resolved flock name/id and do not say the rough phrase has no data.
""".strip()
        try:
            result = self.client.chat(
                [
                    {"role": "system", "content": ANSWER_SYSTEM},
                    *self._history_messages(history or []),
                    {"role": "user", "content": prompt},
                ],
                model=os.getenv(
                    "AIBOT_SQL_ANSWER_MODEL",
                    os.getenv("AIBOT_SQL_MODEL", "llama-3.3-70b-versatile"),
                ),
                fallback_model=os.getenv(
                    "AIBOT_SQL_FALLBACK_MODEL", "llama-3.1-8b-instant"
                ),
                temperature=0.1,
                max_tokens=600,
                timeout=float(os.getenv("AIBOT_SQL_TIMEOUT", "30")),
            )
            return result.content
        except (GroqAllKeysFailed, KeyError, ValueError, httpx.HTTPError):
            logger.warning(
                "Groq answer formatting failed; using deterministic formatter.",
                exc_info=True,
            )
            return self._deterministic_answer(plan, rows)

    def _history_messages(self, history: list[dict]) -> list[dict[str, str]]:
        messages = []
        for item in history[-8:]:
            role = "assistant" if item.get("role") == "assistant" else "user"
            content = str(item.get("content", "")).strip()
            if content:
                messages.append({"role": role, "content": content})
        return messages

    def _fallback_answer(
        self, question: str, history: list[dict] | None, *, reason: str
    ) -> dict:
        logger.info("Using deterministic Farmer AI fallback: %s", reason)
        response = self.fallback_service.answer(question, history=history)
        response["engine"] = "rule_based_fallback"
        response["fallback_reason"] = reason
        return response

    def _known_deterministic_answer(
        self, question: str, history: list[dict] | None
    ) -> dict | None:
        if isinstance(self.fallback_service, ChikoozaTextToSQLService) and not hasattr(
            self.user, "_meta"
        ):
            return None
        response = self.fallback_service.answer(question, history=history)
        if response.get("status") == "success":
            response["engine"] = "rule_based_fallback"
            response["fallback_reason"] = "Deterministic Chikooza farm-data query."
            return response
        return None

    def _deterministic_answer(self, plan: SQLPlan, rows: list[dict]) -> str:
        if not rows:
            return (
                "I could not find matching records in your farm data for that question."
            )

        if len(rows) == 1:
            readable = ", ".join(
                f"{key.replace('_', ' ')}: {self._format_value(value)}"
                for key, value in rows[0].items()
                if value not in (None, "")
            )
            return (
                readable
                or "I found one matching record, but it has no filled values yet."
            )

        return f"I found {len(rows)} matching records. The first record is: {self._deterministic_answer(plan, [rows[0]])}"

    def _deterministic_metric_answer(
        self, rows: list[dict], entity_context: str = ""
    ) -> str | None:
        if not rows:
            return None

        row = rows[0]
        keys = set(row.keys())
        summary_keys = {
            "farm_count",
            "flock_count",
            "total_sales",
            "total_purchases",
            "total_feed_consumed",
            "total_mortality",
            "average_fcr",
        }
        if summary_keys.issubset(keys):
            return (
                "Your account summary: "
                f"{row.get('farm_count') or 0} farms, "
                f"{row.get('flock_count') or 0} flocks, "
                f"{row.get('current_birds') or 0} current birds, "
                f"Rs. {float(row.get('total_sales') or 0):,.2f} sales, "
                f"Rs. {float(row.get('total_purchases') or 0):,.2f} purchases, "
                f"{float(row.get('total_feed_consumed') or 0):,.2f} kg feed consumed, "
                f"{row.get('total_mortality') or 0} total mortality, and "
                f"{float(row.get('average_fcr') or 0):,.2f} average FCR."
            )

        if {"total_sales", "total_purchases", "flock_cost", "result"}.issubset(keys):
            flock_name = row.get("flock_name") or "this flock"
            net = float(row.get("result") or 0)
            status = "profit" if net > 0 else "loss" if net < 0 else "break-even"
            return (
                f"{flock_name} has Rs. {abs(net):,.2f} {status}. "
                f"Sales are Rs. {float(row.get('total_sales') or 0):,.2f}, "
                f"purchases are Rs. {float(row.get('total_purchases') or 0):,.2f}, "
                f"and flock cost is Rs. {float(row.get('flock_cost') or 0):,.2f}."
            )

        if {"record_date", "birds_died", "total_mort", "birds_current"}.issubset(keys):
            flock_name = row.get("flock_name") or "this flock"
            if not row.get("record_date"):
                return (
                    f"I found {flock_name}, but there is no daily data record for it yet. "
                    "Enter daily mortality, current birds, feed, weight, and FCR data to answer this accurately."
                )
            return (
                f"For {flock_name}, the latest record is {row.get('record_date')}. "
                f"Birds died that day: {row.get('birds_died') or 0}. "
                f"Total mortality: {row.get('total_mort') or 0}. "
                f"Current birds: {row.get('birds_current') or 0}."
            )

        if "total_feed_consumed" in keys and len(rows) == 1:
            flock_name = row.get("flock_name") or self._resolved_flock_name(
                entity_context
            )
            prefix = f"{flock_name} consumed" if flock_name else "Total feed consumed"
            return f"{prefix}: {float(row.get('total_feed_consumed') or 0):,.2f} kg."

        return None

    def _resolved_flock_name(self, entity_context: str) -> str:
        match = re.search(
            r"Resolved flock mention: .*?flock_name=([^.\n]+)", entity_context
        )
        return match.group(1).strip() if match else ""

    def _blocked_message(self, reason: str) -> str:
        if "cross_tenant" in reason:
            return "I can only answer questions about your own Chikooza farm data."
        return (
            "I could not connect that question to a safe farm-record query. "
            "I can answer about your farms, flocks, sales, purchases, daily data, "
            "mortality, feed, weight, FCR, and profit."
        )

    def _blocked_suggestion(self, reason: str) -> str:
        if "cross_tenant" in reason:
            return "Ask only about the farm records in your own logged-in account."
        return "Try: 'show my farm summary', 'total sales', 'current birds', 'average FCR', or 'profit or loss'."

    def _json_safe_rows(self, rows: list[dict]) -> list[dict]:
        return [
            {key: self._json_safe_value(value) for key, value in row.items()}
            for row in rows
        ]

    def _json_safe_value(self, value):
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        return value

    def _format_value(self, value):
        if isinstance(value, Decimal):
            return f"{float(value):,.2f}"
        if isinstance(value, float):
            return f"{value:,.2f}"
        return value

    def _strip_code_fences(self, content: str) -> str:
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        return cleaned.strip()


class BlockedAIQuery(ValueError):
    pass
