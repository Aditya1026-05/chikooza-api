import logging
import calendar
import os
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from django.db import connection

logger = logging.getLogger(__name__)


TEXT_TO_SQL = "TEXT_TO_SQL"
RAG = "RAG"
HYBRID = "HYBRID"
CONVERSATION = "CONVERSATION"
BLOCKED = "BLOCKED"


SUMMARY_QUERY_PHRASES = (
    "account summary",
    "farm summary",
    "overall summary",
    "summary",
    "overview",
    "everything",
    "all data",
    "all the data",
    "all my data",
    "my all data",
    "my data",
    "total data",
    "full data",
    "complete data",
    "all records",
    "all my records",
    "my records",
    "complete records",
    "all details",
    "my details",
    "all information",
    "my information",
    "total things",
    "my total things",
    "all things",
    "total stuff",
    "all my stuff",
    "what do i have",
    "what i have",
    "what all i have",
    "what all do i have",
)

COMMON_QUERY_TYPO_REPLACEMENTS = (
    (r"\bglock(s)?\b", r"flock\1"),
    (r"\bflcok(s)?\b", r"flock\1"),
    (r"\bfork(s)?\b", r"flock\1"),
    (r"\bfamr(s)?\b", r"farm\1"),
    (r"\bsail(s)?\b", r"sale\1"),
    (r"\bpruchase(s)?\b", r"purchase\1"),
    (r"\bpurchaes\b", "purchase"),
    (r"\bmortilty\b", "mortality"),
    (r"\bmortaltiy\b", "mortality"),
    (r"\bbuggest\b", "biggest"),
    (r"\bimporve\b", "improve"),
)


def normalize_ai_query(question: str) -> str:
    query = re.sub(r"\s+", " ", (question or "").lower()).strip()
    for pattern, replacement in COMMON_QUERY_TYPO_REPLACEMENTS:
        query = re.sub(pattern, replacement, query)
    return query


def is_broad_summary_query(question: str) -> bool:
    query = normalize_ai_query(question)
    if any(phrase in query for phrase in SUMMARY_QUERY_PHRASES):
        return True

    # U: NEW: rough farmer English like "show me all the data" must be treated
    # U: as an account summary, not as a feed/daily-data metric.
    return bool(
        re.search(
            r"\b(?:show|give|tell|display|list)\s+"
            r"(?:me\s+)?(?:my\s+|our\s+)?(?:all|complete|full)\s+"
            r"(?:the\s+)?(?:data|records|details|information|stuff|things)\b",
            query,
        )
    )


@dataclass(frozen=True)
class DateRange:
    start: date
    end: date
    label: str


@dataclass(frozen=True)
class SQLPlan:
    sql: str
    params: list
    metric: str
    result_type: str
    date_range: DateRange | None = None


@dataclass(frozen=True)
class EntityFilterResolution:
    farm_id: int | None = None
    flock_id: int | None = None
    missing_response: dict | None = None


@dataclass(frozen=True)
class ResolvedEntityReference:
    id: int
    name: str = ""
    public_id: int | None = None
    farm_id: int | None = None
    farm: object | None = None


class ChikoozaQueryRouter:
    """
    U: Port of the BizBot router idea from utkarsh-goel-21/chatbot, adapted for
    U: Chikooza farm data. The router is deterministic here so the first
    U: integration step does not depend on another LLM service being available.
    """

    DATA_KEYWORDS = {
        "sale",
        "sales",
        "revenue",
        "purchase",
        "purchases",
        "expense",
        "expenses",
        "cost",
        "costs",
        "farm",
        "farms",
        "flock",
        "flocks",
        "bird",
        "birds",
        "chick",
        "chicks",
        "chicken",
        "chickens",
        "alive",
        "mortality",
        "death",
        "deaths",
        "feed",
        "fcr",
        "weight",
        "profit",
        "loss",
        "net",
        "count",
        "total",
        "average",
        "avg",
        "how many",
        "number of",
        "thing",
        "things",
        "everything",
        "record",
        "records",
        "detail",
        "details",
        "info",
        "information",
        "data",
        "all",
        "more",
        "another",
        "other",
        "remaining",
        "else",
        "ones",
        "progress",
        "progressing",
        "performance",
        "performing",
        "improve",
        "improvement",
        "advice",
        "advise",
        "insight",
        "insights",
        "assess",
        "evaluate",
        "review",
        "risk",
        "risks",
        "problem",
        "problems",
        "issue",
        "issues",
        "healthy",
        "health",
    }
    RAG_KEYWORDS = {
        "overview",
        "summary",
        "summarize",
        "trend",
        "trends",
        "pattern",
        "patterns",
        "insight",
        "insights",
        "analysis",
        "analyze",
        "why",
        "recommend",
        "suggest",
        "advice",
        "advise",
        "improve",
        "improvement",
        "progress",
        "progressing",
        "performance",
        "performing",
        "assess",
        "evaluate",
    }
    DESTRUCTIVE_KEYWORDS = {
        "drop",
        "delete",
        "truncate",
        "update",
        "insert",
        "alter",
        "create",
        "replace",
        "grant",
        "revoke",
    }
    GREETING_PATTERNS = (
        r"^(hi|hello|hey|namaste|hii|helo|good morning|good afternoon|good evening)(?:[!. ]+.*)?$",
        r"^(thanks|thank you|ok|okay|okay thanks|ok thanks|thanks okay|thank you okay)[!. ]*$",
        r"^(nothing more|no more|that's all|thats all|all good|done|stop|enough)[!. ]*$",
        r"^(huh|what do you mean|what meaning|what)[?!. ]*$",
    )

    def route(self, question: str, user_id: int) -> str:
        query = self._normalize(question)
        if not query:
            return BLOCKED

        if self._is_greeting(query):
            return CONVERSATION

        if any(re.search(rf"\b{word}\b", query) for word in self.DESTRUCTIVE_KEYWORDS):
            return BLOCKED

        if self._mentions_other_user(query, user_id):
            return BLOCKED

        if self._looks_like_farmer_ai_chat(query):
            return TEXT_TO_SQL

        if self._looks_like_account_summary(query):
            return TEXT_TO_SQL

        has_data_intent = any(keyword in query for keyword in self.DATA_KEYWORDS)
        has_rag_intent = any(keyword in query for keyword in self.RAG_KEYWORDS)

        if has_data_intent and has_rag_intent:
            return HYBRID
        if has_rag_intent:
            return RAG
        if has_data_intent:
            return TEXT_TO_SQL
        return BLOCKED

    def _mentions_other_user(self, query: str, user_id: int) -> bool:
        owner_patterns = (
            r"\b(?:owner|user|customer|farmer)\s*(?:id)?\s*#?(\d+)\b",
            r"\b(?:owner_id|user_id|customer_id|farmer_id)\s*=\s*(\d+)\b",
        )
        for pattern in owner_patterns:
            for match in re.findall(pattern, query):
                if int(match) != user_id:
                    return True
        return False

    def _normalize(self, question: str) -> str:
        return normalize_ai_query(question)

    def _is_greeting(self, query: str) -> bool:
        return any(re.match(pattern, query) for pattern in self.GREETING_PATTERNS)

    def _looks_like_account_summary(self, query: str) -> bool:
        if is_broad_summary_query(query):
            return True

        summary_words = ("total", "things", "records", "data", "stuff")
        ownership_words = (
            "my",
            "me",
            "mine",
            "our",
            "us",
            "i have",
            "we have",
            "account",
            "farm",
            "farms",
            "flock",
            "flocks",
        )
        return any(word in query for word in summary_words) and any(
            word in query for word in ownership_words
        )

    def _looks_like_farmer_ai_chat(self, query: str) -> bool:
        # U: NEW: allow conversational farmer questions to reach the intent
        # U: layer instead of being blocked before Groq can understand intent.
        patterns = (
            r"\b(?:who are you|what can you do|how can you help|help me|"
            r"what should i ask|how to use|what do you do)\b",
            r"\bhow\s+(?:am i|are we|is my|is this|is that|is it)\b",
            r"\bwhat\s+do\s+you\s+think\b",
            r"\bwhat\s+should\s+i\b",
            r"\b(?:what next|now what|next steps?|what to do next|tell me what to do)\b",
            r"\b(?:explain|understand)\s+(?:this|that|it)\b",
            r"\b(?:is this enough|is that enough|is it enough)\b",
            r"\b(?:farm|flock|batch|birds?|it|this|that)\b.*"
            r"\b(?:good|bad|better|worse|okay|ok|progressing|performing)\b",
            r"\b(?:good|bad|better|worse|okay|ok|progressing|performing)\b.*"
            r"\b(?:farm|flock|batch|birds?|it|this|that)\b",
        )
        return any(re.search(pattern, query) for pattern in patterns)


class TenantSafeSQLExecutor:
    """
    U: Port of the cloned repo's tenant validation idea. Chikooza must never
    U: trust client-supplied ids; SQL is generated from request.user and then
    U: validated again before execution.
    """

    ALLOWED_VIEWS = {
        "ai_farm_flock_data_view",
        "ai_sale_data_view",
        "ai_purchase_data_view",
        "ai_dailydata_data_view",
    }
    FORBIDDEN_TOKENS = {
        "insert",
        "update",
        "delete",
        "drop",
        "create",
        "alter",
        "truncate",
        "grant",
        "revoke",
        "attach",
        "detach",
    }
    SOURCE_PATTERN = re.compile(r"\b(?:from|join)\s+([`\"\[]?[a-z_][\w.]*[`\"\]]?)")

    def execute(self, plan: SQLPlan) -> list[dict]:
        self._validate(plan)
        with connection.cursor() as cursor:
            cursor.execute(plan.sql, plan.params)
            columns = [column[0] for column in cursor.description]
            rows = cursor.fetchall()
        return [dict(zip(columns, row)) for row in rows]

    def _validate(self, plan: SQLPlan):
        sql_lower = re.sub(r"\s+", " ", plan.sql.lower()).strip()
        sql_comparison_lower = re.sub(r"\s*=\s*", " = ", sql_lower)

        if not sql_lower.startswith("select "):
            raise ValueError("Only SELECT queries are allowed.")

        if ";" in sql_lower.rstrip(";"):
            raise ValueError("Multiple SQL statements are not allowed.")

        if any(
            re.search(rf"\b{token}\b", sql_lower) for token in self.FORBIDDEN_TOKENS
        ):
            raise ValueError("Unsafe SQL token found.")

        placeholder_count = sql_lower.count("%s")
        if placeholder_count != len(plan.params):
            raise ValueError("SQL placeholder count does not match params.")

        # U: OLD validation only confirmed that one safe view appeared anywhere:
        # if not any(view in sql_lower for view in self.ALLOWED_VIEWS):
        #     raise ValueError("Query references an unsupported data source.")
        # U: NEW validation rejects every FROM/JOIN source that is not an
        # U: approved tenant-scoped AI view.
        sources = self._referenced_sources(sql_lower)
        if not sources or any(source not in self.ALLOWED_VIEWS for source in sources):
            raise ValueError("Query references an unsupported data source.")

        view_references = len(sources)
        owner_filters = sql_comparison_lower.count("owner_id = %s")
        if owner_filters < view_references:
            raise ValueError("Tenant filter is missing from one or more data sources.")

        # U: NEW: reject literal owner filters so the authenticated request.user
        # U: remains the only tenant source. LLM-generated SQL must use %s.
        if re.search(r"\bowner_id\s*=\s*(?!%s\b)[^\s)]+", sql_lower):
            raise ValueError(
                "Tenant filter must use parameterized authenticated owner id."
            )
        if re.search(r"\bowner_id\s+in\s*\(", sql_lower):
            raise ValueError("Tenant filter must not use owner_id IN clauses.")

    def _referenced_sources(self, sql_lower: str) -> list[str]:
        sources = []
        for raw_source in self.SOURCE_PATTERN.findall(sql_lower):
            source = raw_source.strip('`"[]').split(".")[-1]
            sources.append(source)
        return sources


class ChikoozaTextToSQLService:
    """
    U: LEGACY / NOT LIVE: this deterministic Text-to-SQL mapper is retained for
    U: safety tests, old intent-agent tests, and rollback reference only.
    U: The active Farmer AI endpoint uses ChikoozaLLMTextToSQLService in
    U: aibot/llm_sql.py through ChikoozaModernAgentService._build_sql_service().

    U: Separate deterministic Text-to-SQL class inspired by the cloned BizBot
    U: pipeline. It uses Chikooza's existing SQL views and parameterized queries.
    """

    def __init__(self, user):
        self.user = user
        self.executor = TenantSafeSQLExecutor()

    def answer(self, question: str, history: list | None = None) -> dict:
        other_entity_response = self._other_entity_response(question, history=history)
        if other_entity_response:
            return other_entity_response

        entity_filter = self.resolve_entity_filters(question, history=history)
        if entity_filter.missing_response:
            return entity_filter.missing_response

        plan = self.build_plan(question, history=history)
        if not plan:
            return {
                "status": "error",
                "message": (
                    "I could not map that question to a safe farm-data query. "
                    "Try asking about sales, purchases, profit, birds, mortality, feed, FCR, farms, or flocks."
                ),
                "route": TEXT_TO_SQL,
            }

        try:
            rows = self.executor.execute(plan)
        except Exception as exc:
            logger.exception("Modern AI SQL execution failed")
            return {
                "status": "error",
                "message": "Query execution failed.",
                "details": str(exc),
                "route": TEXT_TO_SQL,
            }

        value = rows[0] if rows else {}
        answer = self._format_answer(plan, rows)
        return {
            "status": "success",
            "data": self._response_data(plan, rows),
            "answer": answer,
            "message": answer,
            "rows": rows,
            "query": plan.sql,
            "params": plan.params,
            "route": TEXT_TO_SQL,
            "metric": plan.metric,
        }

    def build_plan(self, question: str, history: list | None = None) -> SQLPlan | None:
        query = normalize_ai_query(question)
        if not query:
            return None

        date_range = self._date_range_from_query(query)
        entity_filter = self.resolve_entity_filters(query, history=history)
        if entity_filter.missing_response:
            return None
        farm_id = entity_filter.farm_id
        flock_id = entity_filter.flock_id

        if self._is_summary_query(query):
            if flock_id is not None and self._has_explicit_entity_reference(
                query, "flock"
            ):
                return self._flock_list_plan(farm_id=farm_id, flock_id=flock_id)
            if farm_id is not None and self._has_explicit_entity_reference(
                query, "farm"
            ):
                return self._farm_list_plan(farm_id=farm_id)
            return self._summary_plan(date_range=date_range)

        if self._is_entity_detail_query(query, "flock", entity_filter):
            return self._flock_list_plan(farm_id=farm_id, flock_id=flock_id)

        if self._is_entity_detail_query(query, "farm", entity_filter):
            return self._farm_list_plan(farm_id=farm_id)

        if any(word in query for word in ("profit", "loss", "net", "earning")):
            return self._profit_plan(farm_id, flock_id, date_range=date_range)

        if self._is_count_query(query) and re.search(r"\bfarms?\b", query):
            return self._aggregate_plan(
                view="ai_farm_flock_data_view",
                expression="COUNT(DISTINCT farm_id)",
                metric="farm_count",
                result_type="count",
                farm_id=farm_id,
                flock_id=flock_id,
                extra_conditions=["farm_id IS NOT NULL"],
            )

        if self._is_count_query(query) and re.search(
            r"\b(?:flocks?|batches?)\b", query
        ):
            return self._aggregate_plan(
                view="ai_farm_flock_data_view",
                expression="COUNT(DISTINCT flock_id)",
                metric="flock_count",
                result_type="count",
                farm_id=farm_id,
                flock_id=flock_id,
                extra_conditions=["flock_id IS NOT NULL"],
            )

        if self._is_count_query(query) and "sale" in query:
            return self._aggregate_plan(
                view="ai_sale_data_view",
                expression="COUNT(DISTINCT sale_id)",
                metric="sales_count",
                result_type="count",
                farm_id=farm_id,
                flock_id=flock_id,
                extra_conditions=["sale_id IS NOT NULL"],
                date_column="sale_date",
                date_range=date_range,
            )

        if self._is_count_query(query) and "purchase" in query:
            return self._aggregate_plan(
                view="ai_purchase_data_view",
                expression="COUNT(*)",
                metric="purchase_count",
                result_type="count",
                farm_id=farm_id,
                flock_id=flock_id,
                extra_conditions=["purchase_date IS NOT NULL"],
                date_column="purchase_date",
                date_range=date_range,
            )

        if self._is_list_query(query, "farm"):
            return self._farm_list_plan(farm_id=farm_id)

        if self._is_list_query(query, "flock"):
            return self._flock_list_plan(farm_id=farm_id, flock_id=flock_id)

        metric_map = (
            (
                ("sale", "sales", "revenue", "income", "earning", "sold"),
                "ai_sale_data_view",
                "COALESCE(SUM(sale_amount), 0)",
                "total_sales",
                "money",
                "sale_date",
            ),
            (
                ("flock cost", "initial cost", "chick cost"),
                "ai_purchase_data_view",
                "COALESCE(SUM(DISTINCT flock_cost), 0)",
                "flock_cost",
                "money",
                None,
            ),
            (
                (
                    "purchase",
                    "purchases",
                    "expense",
                    "expenses",
                    "spent",
                    "spend",
                    "cost",
                    "costs",
                ),
                "ai_purchase_data_view",
                "COALESCE(SUM(purchase_amount), 0)",
                "total_purchases",
                "money",
                "purchase_date",
            ),
            (
                (
                    "mortality",
                    "deaths",
                    "death",
                    "dead birds",
                    "birds dead",
                    "birds died",
                    "died",
                ),
                "ai_dailydata_data_view",
                "COALESCE(SUM(birds_died), 0)",
                "mortality",
                "count",
                "record_date",
            ),
            (
                ("average weight", "bird weight", "body weight", "weight"),
                "ai_dailydata_data_view",
                "COALESCE(AVG(average_bird_weight), 0)",
                "average_weight",
                "decimal",
                "record_date",
            ),
            (
                (
                    "current birds",
                    "bird count",
                    "birds left",
                    "birds alive",
                    "chickens alive",
                    "chicks alive",
                    "chickens",
                    "chicks",
                    "birds",
                    "bird",
                ),
                "ai_dailydata_data_view",
                "COALESCE(SUM(birds_current), 0)",
                "current_birds",
                "count",
                "record_date",
            ),
            (
                ("feed consumed", "feed consumption", "feed intake", "feed"),
                "ai_dailydata_data_view",
                "COALESCE(SUM(feed_consumed_kg), 0)",
                "feed_consumed",
                "quantity",
                "record_date",
            ),
            (
                ("fcr", "feed conversion"),
                "ai_dailydata_data_view",
                "COALESCE(AVG(fcr), 0)",
                "fcr",
                "decimal",
                "record_date",
            ),
        )

        for keywords, view, expression, metric, result_type, date_column in metric_map:
            if any(keyword in query for keyword in keywords):
                if metric == "feed_consumed" and "feed conversion" in query:
                    continue
                if metric == "current_birds":
                    return self._current_birds_plan(
                        farm_id,
                        flock_id,
                        date_range=date_range,
                    )
                return self._aggregate_plan(
                    view=view,
                    expression=expression,
                    metric=metric,
                    result_type=result_type,
                    farm_id=farm_id,
                    flock_id=flock_id,
                    date_column=date_column,
                    date_range=date_range,
                )

        return None

    def resolve_entity_filters(
        self, question: str, history: list | None = None
    ) -> EntityFilterResolution:
        query = normalize_ai_query(question)
        farm_resolution = self._resolve_farm_reference(query, history=history)
        flock_resolution = self._resolve_flock_reference(query, history=history)

        if farm_resolution == "not_found":
            return EntityFilterResolution(
                missing_response=self._missing_entity_response("farm", self._farms())
            )
        if farm_resolution == "ambiguous":
            return EntityFilterResolution(
                missing_response=self._ambiguous_entity_response("farm", self._farms())
            )
        if flock_resolution == "not_found":
            return EntityFilterResolution(
                missing_response=self._missing_entity_response("flock", self._flocks())
            )
        if flock_resolution == "ambiguous":
            return EntityFilterResolution(
                missing_response=self._ambiguous_entity_response(
                    "flock", self._flocks()
                )
            )

        farm_id = self._object_id(farm_resolution) if farm_resolution else None
        flock_id = self._object_id(flock_resolution) if flock_resolution else None
        flock_farm_id = self._flock_farm_id(flock_resolution) if flock_resolution else None
        if (
            farm_resolution
            and flock_resolution
            and flock_farm_id is not None
            and flock_farm_id != farm_id
        ):
            # U: NEW: do not silently run an impossible cross-farm filter when
            # U: the farmer names a flock under the wrong owned farm.
            return EntityFilterResolution(
                missing_response=self._conflicting_entity_response(
                    farm_resolution,
                    flock_resolution,
                )
            )
        if flock_resolution and farm_id is None:
            farm_id = self._flock_farm_id(flock_resolution)

        return EntityFilterResolution(farm_id=farm_id, flock_id=flock_id)

    def _aggregate_plan(
        self,
        view: str,
        expression: str,
        metric: str,
        result_type: str,
        farm_id: int | None = None,
        flock_id: int | None = None,
        extra_conditions: list[str] | None = None,
        date_column: str | None = None,
        date_range: DateRange | None = None,
    ) -> SQLPlan:
        where_sql, params = self._where_clause(farm_id=farm_id, flock_id=flock_id)
        conditions = list(extra_conditions or [])
        date_conditions, date_params = self._date_conditions(date_column, date_range)
        conditions.extend(date_conditions)
        params.extend(date_params)
        if conditions:
            where_sql = f"{where_sql} AND {' AND '.join(conditions)}"
        return SQLPlan(
            sql=f"SELECT {expression} AS result FROM {view} WHERE {where_sql}",
            params=params,
            metric=metric,
            result_type=result_type,
            date_range=date_range,
        )

    def _farm_list_plan(self, farm_id: int | None = None) -> SQLPlan:
        where_sql, params = self._where_clause(farm_id=farm_id)
        sql = f"""
            SELECT DISTINCT
                farm_id,
                farm_name,
                farm_city,
                farm_pin,
                shed_count,
                farm_status
            FROM ai_farm_flock_data_view
            WHERE {where_sql}
              AND farm_id IS NOT NULL
            ORDER BY farm_name
            LIMIT 100
        """
        return SQLPlan(
            sql=re.sub(r"\s+", " ", sql).strip(),
            params=params,
            metric="farm_list",
            result_type="table",
        )

    def _flock_list_plan(
        self, farm_id: int | None = None, flock_id: int | None = None
    ) -> SQLPlan:
        where_sql, params = self._where_clause(farm_id=farm_id, flock_id=flock_id)
        sql = f"""
            SELECT DISTINCT
                flock_id,
                flock_name,
                farm_id,
                farm_name,
                hatch_date,
                flock_size,
                actual_birds,
                flock_status,
                breed_name
            FROM ai_farm_flock_data_view
            WHERE {where_sql}
              AND flock_id IS NOT NULL
            ORDER BY farm_name, flock_name
            LIMIT 100
        """
        return SQLPlan(
            sql=re.sub(r"\s+", " ", sql).strip(),
            params=params,
            metric="flock_list",
            result_type="table",
        )

    def _profit_plan(
        self,
        farm_id: int | None,
        flock_id: int | None,
        date_range: DateRange | None = None,
    ) -> SQLPlan:
        sale_where, sale_params = self._where_clause(farm_id=farm_id, flock_id=flock_id)
        sale_where, sale_params = self._apply_date_range(
            sale_where,
            sale_params,
            "sale_date",
            date_range,
        )
        purchase_where, purchase_params = self._where_clause(
            farm_id=farm_id, flock_id=flock_id
        )
        purchase_where, purchase_params = self._apply_date_range(
            purchase_where,
            purchase_params,
            "purchase_date",
            date_range,
        )
        flock_cost_where, flock_cost_params = self._where_clause(
            farm_id=farm_id, flock_id=flock_id
        )

        sql = f"""
            SELECT
                (SELECT COALESCE(SUM(sale_amount), 0) FROM ai_sale_data_view WHERE {sale_where}) AS total_sales,
                (SELECT COALESCE(SUM(purchase_amount), 0) FROM ai_purchase_data_view WHERE {purchase_where}) AS total_purchases,
                (SELECT COALESCE(SUM(DISTINCT flock_cost), 0) FROM ai_purchase_data_view WHERE {flock_cost_where}) AS flock_cost,
                (
                    (SELECT COALESCE(SUM(sale_amount), 0) FROM ai_sale_data_view WHERE {sale_where}) -
                    (SELECT COALESCE(SUM(purchase_amount), 0) FROM ai_purchase_data_view WHERE {purchase_where}) -
                    (SELECT COALESCE(SUM(DISTINCT flock_cost), 0) FROM ai_purchase_data_view WHERE {flock_cost_where})
                ) AS result
        """
        params = (
            sale_params
            + purchase_params
            + flock_cost_params
            + sale_params
            + purchase_params
            + flock_cost_params
        )
        return SQLPlan(
            sql=re.sub(r"\s+", " ", sql).strip(),
            params=params,
            metric="profit_loss",
            result_type="money",
            date_range=date_range,
        )

    def _current_birds_plan(
        self,
        farm_id: int | None,
        flock_id: int | None,
        date_range: DateRange | None = None,
    ) -> SQLPlan:
        # U: OLD code summed birds_current across every daily row, which double
        # U: counted the same flock over time.
        # U: NEW code sums only the latest daily row for each flock.
        current_where, current_params = self._where_clause(
            farm_id=farm_id, flock_id=flock_id, table_alias="current_rows"
        )
        current_where, current_params = self._apply_date_range(
            current_where,
            current_params,
            "current_rows.record_date",
            date_range,
        )
        compare_where = (
            "compare_rows.owner_id = %s "
            "AND compare_rows.flock_id = current_rows.flock_id "
            "AND compare_rows.daily_data_id IS NOT NULL"
        )
        compare_params = [self.user.id]
        compare_where, compare_params = self._apply_date_range(
            compare_where,
            compare_params,
            "compare_rows.record_date",
            date_range,
        )
        sql = f"""
            SELECT COALESCE(SUM(current_rows.birds_current), 0) AS result
            FROM ai_dailydata_data_view current_rows
            WHERE {current_where}
              AND current_rows.daily_data_id IS NOT NULL
              AND current_rows.record_date = (
                  SELECT MAX(compare_rows.record_date)
                  FROM ai_dailydata_data_view compare_rows
                  WHERE {compare_where}
              )
        """
        return SQLPlan(
            sql=re.sub(r"\s+", " ", sql).strip(),
            params=current_params + compare_params,
            metric="current_birds",
            result_type="count",
            date_range=date_range,
        )

    def _summary_plan(self, date_range: DateRange | None = None) -> SQLPlan:
        current_where, current_params = self._apply_date_range(
            "current_rows.owner_id = %s",
            [self.user.id],
            "current_rows.record_date",
            date_range,
        )
        compare_where, compare_params = self._apply_date_range(
            "compare_rows.owner_id = %s AND compare_rows.flock_id = current_rows.flock_id AND compare_rows.daily_data_id IS NOT NULL",
            [self.user.id],
            "compare_rows.record_date",
            date_range,
        )
        sale_where, sale_params = self._apply_date_range(
            "owner_id = %s",
            [self.user.id],
            "sale_date",
            date_range,
        )
        purchase_where, purchase_params = self._apply_date_range(
            "owner_id = %s",
            [self.user.id],
            "purchase_date",
            date_range,
        )
        feed_where, feed_params = self._apply_date_range(
            "owner_id = %s",
            [self.user.id],
            "record_date",
            date_range,
        )
        mortality_where, mortality_params = self._apply_date_range(
            "owner_id = %s",
            [self.user.id],
            "record_date",
            date_range,
        )
        fcr_where, fcr_params = self._apply_date_range(
            "owner_id = %s AND fcr IS NOT NULL",
            [self.user.id],
            "record_date",
            date_range,
        )
        sql = f"""
            SELECT
                (SELECT COUNT(DISTINCT farm_id) FROM ai_farm_flock_data_view WHERE owner_id = %s AND farm_id IS NOT NULL) AS farm_count,
                (SELECT COUNT(DISTINCT flock_id) FROM ai_farm_flock_data_view WHERE owner_id = %s AND flock_id IS NOT NULL) AS flock_count,
                (SELECT COALESCE(SUM(current_rows.birds_current), 0) FROM ai_dailydata_data_view current_rows WHERE {current_where} AND current_rows.daily_data_id IS NOT NULL AND current_rows.record_date = (SELECT MAX(compare_rows.record_date) FROM ai_dailydata_data_view compare_rows WHERE {compare_where})) AS current_birds,
                (SELECT COALESCE(SUM(sale_amount), 0) FROM ai_sale_data_view WHERE {sale_where}) AS total_sales,
                (SELECT COALESCE(SUM(purchase_amount), 0) FROM ai_purchase_data_view WHERE {purchase_where}) AS total_purchases,
                (SELECT COALESCE(SUM(feed_consumed_kg), 0) FROM ai_dailydata_data_view WHERE {feed_where}) AS total_feed_consumed,
                (SELECT COALESCE(SUM(birds_died), 0) FROM ai_dailydata_data_view WHERE {mortality_where}) AS total_mortality,
                (SELECT COALESCE(AVG(fcr), 0) FROM ai_dailydata_data_view WHERE {fcr_where}) AS average_fcr
        """
        params = (
            [self.user.id, self.user.id]
            + current_params
            + compare_params
            + sale_params
            + purchase_params
            + feed_params
            + mortality_params
            + fcr_params
        )
        return SQLPlan(
            sql=re.sub(r"\s+", " ", sql).strip(),
            params=params,
            metric="farm_record_summary",
            result_type="summary",
            date_range=date_range,
        )

    def _where_clause(
        self,
        farm_id: int | None = None,
        flock_id: int | None = None,
        table_alias: str | None = None,
    ) -> tuple[str, list]:
        prefix = f"{table_alias}." if table_alias else ""
        conditions = [f"{prefix}owner_id = %s"]
        params = [self.user.id]
        if farm_id is not None:
            conditions.append(f"{prefix}farm_id = %s")
            params.append(farm_id)
        if flock_id is not None:
            conditions.append(f"{prefix}flock_id = %s")
            params.append(flock_id)
        return " AND ".join(conditions), params

    def _apply_date_range(
        self,
        where_sql: str,
        params: list,
        date_column: str | None,
        date_range: DateRange | None,
    ) -> tuple[str, list]:
        conditions, date_params = self._date_conditions(date_column, date_range)
        if not conditions:
            return where_sql, params
        return f"{where_sql} AND {' AND '.join(conditions)}", params + date_params

    def _date_conditions(
        self,
        date_column: str | None,
        date_range: DateRange | None,
    ) -> tuple[list[str], list]:
        if not date_column or not date_range:
            return [], []
        return [
            f"{date_column} >= %s",
            f"{date_column} <= %s",
        ], [date_range.start, date_range.end]

    def _date_range_from_query(self, query: str) -> DateRange | None:
        today = self._today()
        explicit_range = self._explicit_date_range(query)
        if explicit_range:
            return explicit_range

        if re.search(r"\btoday\b", query):
            return DateRange(today, today, "today")
        if re.search(r"\byesterday\b", query):
            day = today - timedelta(days=1)
            return DateRange(day, day, "yesterday")

        last_days = re.search(r"\blast\s+(\d{1,3})\s+days?\b", query)
        if last_days:
            days = max(1, int(last_days.group(1)))
            return DateRange(today - timedelta(days=days - 1), today, f"last {days} days")

        if re.search(r"\bthis\s+week\b", query):
            start = today - timedelta(days=today.weekday())
            return DateRange(start, today, "this week")
        if re.search(r"\blast\s+week\b", query):
            this_week_start = today - timedelta(days=today.weekday())
            start = this_week_start - timedelta(days=7)
            end = this_week_start - timedelta(days=1)
            return DateRange(start, end, "last week")

        if re.search(r"\bthis\s+month\b", query):
            start = today.replace(day=1)
            end = today.replace(day=calendar.monthrange(today.year, today.month)[1])
            return DateRange(start, end, "this month")
        if re.search(r"\blast\s+month\b", query):
            year = today.year
            month = today.month - 1
            if month == 0:
                month = 12
                year -= 1
            return self._month_range(year, month, "last month")

        if re.search(r"\bthis\s+year\b", query):
            return DateRange(date(today.year, 1, 1), date(today.year, 12, 31), "this year")
        if re.search(r"\blast\s+year\b", query):
            year = today.year - 1
            return DateRange(date(year, 1, 1), date(year, 12, 31), "last year")

        month_range = self._month_name_range(query, today.year)
        if month_range:
            return month_range
        return None

    def _explicit_date_range(self, query: str) -> DateRange | None:
        date_pattern = r"\d{4}-\d{1,2}-\d{1,2}|\d{1,2}[/-]\d{1,2}[/-]\d{4}"
        patterns = (
            rf"\bbetween\s+({date_pattern})\s+(?:and|to)\s+({date_pattern})\b",
            rf"\bfrom\s+({date_pattern})\s+(?:to|till|until|through)\s+({date_pattern})\b",
        )
        for pattern in patterns:
            match = re.search(pattern, query)
            if not match:
                continue
            start = self._parse_date_value(match.group(1))
            end = self._parse_date_value(match.group(2))
            if start and end:
                if start > end:
                    start, end = end, start
                return DateRange(start, end, f"{start.isoformat()} to {end.isoformat()}")
        return None

    def _month_name_range(self, query: str, default_year: int) -> DateRange | None:
        month_names = {
            "jan": 1,
            "january": 1,
            "feb": 2,
            "february": 2,
            "mar": 3,
            "march": 3,
            "apr": 4,
            "april": 4,
            "may": 5,
            "jun": 6,
            "june": 6,
            "jul": 7,
            "july": 7,
            "aug": 8,
            "august": 8,
            "sep": 9,
            "sept": 9,
            "september": 9,
            "oct": 10,
            "october": 10,
            "nov": 11,
            "november": 11,
            "dec": 12,
            "december": 12,
        }
        match = re.search(
            r"\b(?:in|for|during)\s+"
            r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
            r"jul(?:y)?|aug(?:ust)?|sep(?:t|tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
            r"(?:\s+(\d{4}))?\b",
            query,
        )
        if not match:
            return None
        month = month_names[match.group(1)]
        year = int(match.group(2) or default_year)
        return self._month_range(year, month, f"{match.group(1)} {year}")

    def _month_range(self, year: int, month: int, label: str) -> DateRange:
        return DateRange(
            date(year, month, 1),
            date(year, month, calendar.monthrange(year, month)[1]),
            label,
        )

    def _parse_date_value(self, value: str) -> date | None:
        value = value.strip()
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
        return None

    def _today(self) -> date:
        return date.today()

    def _extract_filter_id(self, query: str, label: str) -> int | None:
        match = re.search(rf"\b{label}\s*(?:id)?\s*#?(\d+)\b", query)
        return int(match.group(1)) if match else None

    def _is_count_query(self, query: str) -> bool:
        return bool(
            any(
                phrase in query
                for phrase in (
                    "count",
                    "how many",
                    "number of",
                    "total number",
                    "total no",
                    "no of",
                )
            )
        )

    def _is_list_query(self, query: str, label: str) -> bool:
        plural = f"{label}s"
        if label not in query and plural not in query:
            return False
        list_words = (
            "list",
            "show",
            "display",
            "give",
            "tell",
            "which",
            "what",
            "all",
            "data",
            "info",
            "information",
            "record",
            "records",
            "details",
            "detail",
            "have",
        )
        metric_words = (
            "sale",
            "sales",
            "revenue",
            "purchase",
            "expense",
            "cost",
            "profit",
            "loss",
            "mortality",
            "feed",
            "fcr",
            "weight",
            "bird",
            "birds",
        )
        return any(word in query for word in list_words) and not any(
            word in query for word in metric_words
        )

    def _is_entity_detail_query(
        self, query: str, label: str, entity_filter: EntityFilterResolution
    ) -> bool:
        if self._has_metric_intent(query):
            return False
        if label == "farm" and entity_filter.farm_id is not None:
            return self._has_generic_entity_reference(
                query, "farm"
            ) or self._has_detail_reference(query)
        if label == "flock" and entity_filter.flock_id is not None:
            return self._has_generic_entity_reference(
                query, "flock"
            ) or self._has_detail_reference(query)
        return False

    def _has_metric_intent(self, query: str) -> bool:
        metric_words = (
            "sale",
            "sales",
            "revenue",
            "purchase",
            "purchases",
            "expense",
            "expenses",
            "cost",
            "profit",
            "loss",
            "mortality",
            "dead",
            "died",
            "feed",
            "fcr",
            "weight",
            "bird count",
            "current birds",
            "how many",
            "number of",
            "count",
        )
        return any(word in query for word in metric_words)

    def _is_summary_query(self, query: str) -> bool:
        return is_broad_summary_query(query)

    def _format_answer(self, plan: SQLPlan, rows_or_row) -> str:
        rows = rows_or_row if isinstance(rows_or_row, list) else [rows_or_row]
        row = rows[0] if rows else {}

        if plan.metric == "farm_list":
            return self._format_farm_list(rows)

        if plan.metric == "flock_list":
            return self._format_flock_list(rows)

        if plan.metric == "profit_loss":
            total_sales = float(row.get("total_sales") or 0)
            total_purchases = float(row.get("total_purchases") or 0)
            flock_cost = float(row.get("flock_cost") or 0)
            net = float(row.get("result") or 0)
            status = "profit" if net > 0 else "loss" if net < 0 else "break-even"
            period = self._period_suffix(plan)
            answer = (
                f"Total sales{period}: Rs. {total_sales:,.2f}, total purchases{period}: Rs. {total_purchases:,.2f}, "
                f"flock cost: Rs. {flock_cost:,.2f}. Net result: Rs. {net:,.2f} ({status})."
            )
            return self._append_notes(
                answer,
                self._calculation_explanation(plan.metric),
                self._profit_missing_guidance(
                    total_sales,
                    total_purchases,
                    flock_cost,
                    plan,
                ),
            )

        if plan.metric == "farm_record_summary":
            answer = (
                "Your account summary: "
                f"{row.get('farm_count') or 0} farms, {row.get('flock_count') or 0} flocks, "
                f"{row.get('current_birds') or 0} current birds, "
                f"Rs. {float(row.get('total_sales') or 0):,.2f} sales, "
                f"Rs. {float(row.get('total_purchases') or 0):,.2f} purchases, "
                f"{float(row.get('total_feed_consumed') or 0):,.2f} kg feed consumed, "
                f"{row.get('total_mortality') or 0} total mortality, and "
                f"{float(row.get('average_fcr') or 0):,.2f} average FCR."
            )
            return self._append_guidance(
                answer,
                self._summary_missing_guidance(row, plan),
            )

        value = row.get("result", 0)
        label = plan.metric.replace("_", " ")
        period = self._period_suffix(plan)
        if plan.metric == "feed_consumed":
            answer = f"Total feed consumed{period}: {float(value or 0):,.2f} kg."
            return self._append_guidance(
                answer,
                self._metric_missing_guidance(plan.metric, value, plan),
            )
        if plan.metric == "current_birds":
            answer = f"Current birds{period}: {value or 0}."
            return self._append_notes(
                answer,
                self._calculation_explanation(plan.metric),
                self._metric_missing_guidance(plan.metric, value, plan),
            )
        if plan.metric == "mortality":
            answer = f"Total mortality{period}: {value or 0} birds."
            return self._append_notes(
                answer,
                self._calculation_explanation(plan.metric),
                self._metric_missing_guidance(plan.metric, value, plan),
            )
        if plan.result_type == "money":
            answer = f"{label.title()}{period}: Rs. {float(value or 0):,.2f}."
            return self._append_guidance(
                answer,
                self._metric_missing_guidance(plan.metric, value, plan),
            )
        if plan.result_type == "decimal":
            answer = f"{label.title()}{period}: {float(value or 0):,.2f}."
            return self._append_notes(
                answer,
                self._calculation_explanation(plan.metric),
                self._metric_missing_guidance(plan.metric, value, plan),
            )
        answer = f"{label.title()}{period}: {value or 0}."
        return self._append_guidance(
            answer,
            self._metric_missing_guidance(plan.metric, value, plan),
        )

    def _append_guidance(self, answer: str, guidance: str) -> str:
        return f"{answer} {guidance}" if guidance else answer

    def _append_notes(self, answer: str, *notes: str) -> str:
        return " ".join([answer, *(note for note in notes if note)])

    def _calculation_explanation(self, metric: str) -> str:
        explanations = {
            "profit_loss": (
                "Calculation: net result = recorded sales - recorded purchases - flock cost. "
                "If any sale, purchase, or flock-cost entry is missing, this profit/loss will be incomplete."
            ),
            "current_birds": (
                "Calculation: this adds the latest saved Daily Data current-bird count "
                "for each matching flock, so older daily rows are not counted twice. "
                "It uses daily records, not just the original flock size."
            ),
            "mortality": (
                "Calculation: this adds the birds recorded as mortality in matching "
                "Daily Data entries. If mortality has not been entered for a day, that day contributes zero."
            ),
            "fcr": (
                "Calculation: this is the average of the saved daily FCR values. "
                "Daily FCR is based on cumulative average feed per bird divided by "
                "weight gain above chick weight. If feed or weight is missing, FCR may stay zero."
            ),
        }
        return explanations.get(metric, "")

    def _summary_missing_guidance(self, row: dict, plan: SQLPlan) -> str:
        # U: NEW: zero totals are often missing setup/data-entry, not true
        # U: business performance. Tell the farmer exactly what to enter next.
        farm_count = self._as_float(row.get("farm_count"))
        flock_count = self._as_float(row.get("flock_count"))
        current_birds = self._as_float(row.get("current_birds"))
        total_sales = self._as_float(row.get("total_sales"))
        total_purchases = self._as_float(row.get("total_purchases"))
        feed = self._as_float(row.get("total_feed_consumed"))
        fcr = self._as_float(row.get("average_fcr"))
        mortality = self._as_float(row.get("total_mortality"))
        period = self._period_suffix(plan)

        if farm_count == 0:
            return (
                "Next data to enter: add a Farm first, then add a Flock under that farm. "
                "After that, enter Daily Data, Purchases, and Sales so I can calculate performance."
            )

        guidance = []
        if flock_count == 0:
            guidance.append("add at least one Flock under your Farm")
        if (
            flock_count > 0
            and current_birds == 0
            and feed == 0
            and fcr == 0
            and mortality == 0
        ):
            guidance.append(
                "enter Daily Data with current birds, feed consumed, weight, mortality, and FCR"
            )
        if total_sales == 0:
            guidance.append(f"add Sales records{period}")
        if total_purchases == 0:
            guidance.append(
                f"add Purchase records{period} for feed, medicine, equipment, or flock cost"
            )

        return f"Next data to enter: {'; '.join(guidance)}." if guidance else ""

    def _profit_missing_guidance(
        self,
        total_sales: float,
        total_purchases: float,
        flock_cost: float,
        plan: SQLPlan,
    ) -> str:
        period = self._period_suffix(plan)
        if total_sales == 0 and total_purchases == 0 and flock_cost == 0:
            return (
                f"I cannot judge profit confidently yet because no Sales, Purchase, "
                f"or flock-cost records are saved{period}. Add those records first, then ask again."
            )

        guidance = []
        if total_sales == 0:
            guidance.append(f"Sales records{period}")
        if total_purchases == 0 and flock_cost == 0:
            guidance.append(f"Purchase/flock-cost records{period}")
        if not guidance:
            return ""
        return f"If this profit looks incomplete, add missing {', '.join(guidance)}."

    def _metric_missing_guidance(
        self,
        metric: str,
        value,
        plan: SQLPlan,
    ) -> str:
        if self._as_float(value) != 0:
            return ""

        period = self._period_suffix(plan)
        if metric == "total_sales":
            return (
                f"No Sales records are saved{period}. Add sale/lifting records "
                "under Sales to calculate revenue."
            )
        if metric == "sales_count":
            return (
                f"No Sales records are saved{period}. Add Sales entries before "
                "asking for sale counts."
            )
        if metric == "total_purchases":
            return (
                f"No Purchase records are saved{period}. Add feed, medicine, "
                "equipment, or flock-cost purchases under Purchases."
            )
        if metric == "purchase_count":
            return (
                f"No Purchase records are saved{period}. Add Purchases entries "
                "before asking for purchase counts."
            )
        if metric == "farm_count":
            return "No Farm is saved yet. Add a Farm first, then add Flocks below it."
        if metric == "flock_count":
            return "No Flock is saved yet. Add a Flock under a Farm before asking flock-wise questions."
        if metric == "current_birds":
            return (
                f"The current-bird total is zero or no current-bird value is saved{period}. "
                "Add or update Daily Data for the flock so this number is accurate."
            )
        if metric == "feed_consumed":
            return (
                f"No feed consumption is recorded{period}. Enter Daily Data with "
                "feed consumed in kg."
            )
        if metric == "average_weight":
            return (
                f"No bird-weight data is recorded{period}. Enter Daily Data with "
                "average bird weight."
            )
        if metric == "fcr":
            return (
                f"The saved FCR is zero or not available{period}. Enter Daily Data "
                "with feed and weight values so FCR can be calculated."
            )
        if metric == "mortality":
            return (
                f"No mortality is recorded{period}. If that is correct, no action "
                "is needed. If birds died, enter Daily Data mortality for the correct date."
            )
        return ""

    def _as_float(self, value) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0

    def _period_suffix(self, plan: SQLPlan) -> str:
        if not plan.date_range:
            return ""
        return f" for {plan.date_range.label}"

    def _response_data(self, plan: SQLPlan, rows: list[dict]):
        if plan.result_type == "table":
            return rows
        value = rows[0] if rows else {}
        return value.get("result", value)

    def _other_entity_response(
        self, question: str, history: list | None = None
    ) -> dict | None:
        query = normalize_ai_query(question)
        label = self._other_entity_label(query, history=history)
        if not label:
            return None

        objects = self._flocks() if label == "flock" else self._farms()
        if not objects:
            answer = (
                f"You do not have any {label}s saved yet."
                if label == "flock"
                else "You do not have any farms saved yet."
            )
            return self._direct_entity_answer(label, answer, [], f"other_{label}s")

        referenced = self._latest_entity_from_history(history, label, objects)
        remaining = [
            obj
            for obj in objects
            if not referenced or self._object_id(obj) != self._object_id(referenced)
        ]

        if not remaining:
            name = (
                self._object_name(referenced)
                if referenced
                else self._object_name(objects[0])
            )
            answer = (
                f"No, you only have one {label}: {name}."
                if name
                else f"No, you only have one {label}."
            )
            return self._direct_entity_answer(label, answer, [], f"other_{label}s")

        rows = [
            (
                self._object_to_flock_row(obj)
                if label == "flock"
                else self._object_to_farm_row(obj)
            )
            for obj in remaining
        ]
        answer = (
            self._format_flock_list(rows)
            if label == "flock"
            else self._format_farm_list(rows)
        )
        return self._direct_entity_answer(label, answer, rows, f"other_{label}s")

    def _format_farm_list(self, rows: list[dict]) -> str:
        rows = [row for row in rows if row.get("farm_id")]
        if not rows:
            return "You do not have any farms saved yet. Add a farm first, then I can answer farm-wise questions."

        lines = []
        for index, row in enumerate(rows, start=1):
            location = ", ".join(
                str(part)
                for part in (row.get("farm_city"), row.get("farm_pin"))
                if part not in (None, "")
            )
            shed_text = (
                f", {row.get('shed_count')} sheds"
                if row.get("shed_count") not in (None, "")
                else ""
            )
            status = "active" if row.get("farm_status") else "inactive"
            lines.append(
                f"{index}. {row.get('farm_name') or 'Unnamed farm'}"
                f"{f' ({location})' if location else ''}{shed_text}, {status}"
            )
        return "Your farms:\n" + "\n".join(lines)

    def _format_flock_list(self, rows: list[dict]) -> str:
        rows = [row for row in rows if row.get("flock_id")]
        if not rows:
            return "You do not have any flocks saved yet. Add a flock under a farm first, then I can answer flock-wise questions."

        lines = []
        for index, row in enumerate(rows, start=1):
            details = [
                f"farm: {row.get('farm_name')}" if row.get("farm_name") else "",
                f"size: {row.get('flock_size')}" if row.get("flock_size") else "",
                (
                    f"actual birds: {row.get('actual_birds')}"
                    if row.get("actual_birds") not in (None, "")
                    else ""
                ),
                f"hatch date: {row.get('hatch_date')}" if row.get("hatch_date") else "",
                f"breed: {row.get('breed_name')}" if row.get("breed_name") else "",
            ]
            detail_text = ", ".join(detail for detail in details if detail)
            lines.append(
                f"{index}. {row.get('flock_name') or 'Unnamed flock'}"
                f"{f' ({detail_text})' if detail_text else ''}"
            )
        return "Your flocks:\n" + "\n".join(lines)

    def _other_entity_label(
        self, query: str, history: list | None = None
    ) -> str | None:
        has_other = bool(
            re.search(
                r"\b(?:other|another|any other|more|any more|remaining|rest|left|else|baki|baaki)\b",
                query,
            )
        )
        if not has_other:
            return None
        if re.search(r"\b(?:flocks?|batches?)\b", query):
            return "flock"
        if re.search(r"\bfarms?\b", query):
            return "farm"
        return self._latest_entity_label_from_history(history)

    def _resolve_farm_reference(self, query: str, history: list | None = None):
        farms = self._farms()
        return self._resolve_entity_reference(query, "farm", farms, history=history)

    def _resolve_flock_reference(self, query: str, history: list | None = None):
        flocks = self._flocks()
        return self._resolve_entity_reference(query, "flock", flocks, history=history)

    def _resolve_entity_reference(
        self,
        query: str,
        label: str,
        objects: list,
        history: list | None = None,
    ):
        if not objects and not self._can_query_entity_tables():
            raw_reference = self._raw_entity_reference(query, label)
            if raw_reference:
                return raw_reference

        if not objects and (
            self._has_explicit_entity_reference(query, label)
            or self._requires_existing_entity(query, label)
        ):
            return "not_found"

        numeric_match = re.search(rf"\b{label}\s*(?:id|#)?\s*(\d+)\b", query)
        if numeric_match:
            number = int(numeric_match.group(1))
            exact = self._find_owned_object_by_id(objects, number)
            if exact:
                return exact
            if 1 <= number <= len(objects):
                return objects[number - 1]
            return "not_found"

        ordinal = self._ordinal_for_phrase(query, label)
        if ordinal:
            if 1 <= ordinal <= len(objects):
                return objects[ordinal - 1]
            return "not_found"

        if self._has_last_entity_reference(query, label):
            return objects[-1] if objects else "not_found"

        for obj in objects:
            name = self._object_name(obj)
            if name and len(name) >= 3 and name.lower() in query:
                return obj

        has_context_reference = self._has_generic_entity_reference(query, label) or (
            self._has_detail_pronoun_reference(query)
            and self._history_mentions_label(history, label)
        )
        if has_context_reference:
            history_object = self._latest_entity_from_history(history, label, objects)
            if history_object:
                return history_object
            if self._history_mentions_label(history, label) and len(objects) == 1:
                return objects[0]
            if len(objects) == 1 and self._has_generic_entity_reference(query, label):
                return objects[0]
            if len(objects) > 1:
                return "ambiguous"

        if self._has_named_entity_reference(query, label):
            return "not_found"

        return None

    def _raw_entity_reference(self, query: str, label: str):
        numeric_match = re.search(rf"\b{label}\s*(?:id|#)?\s*(\d+)\b", query)
        if numeric_match:
            number = int(numeric_match.group(1))
            return ResolvedEntityReference(
                id=number, public_id=number, name=f"{label} {number}"
            )

        ordinal = self._ordinal_for_phrase(query, label)
        if ordinal:
            return ResolvedEntityReference(
                id=ordinal, public_id=ordinal, name=f"{label} {ordinal}"
            )
        return None

    def _has_explicit_entity_reference(self, query: str, label: str) -> bool:
        return bool(
            re.search(rf"\b{label}\s*(?:id|#)?\s*\d+\b", query)
            or self._ordinal_for_phrase(query, label)
            or self._has_last_entity_reference(query, label)
        )

    def _has_generic_entity_reference(self, query: str, label: str) -> bool:
        if label == "flock":
            return bool(
                re.search(
                    r"\b(?:the|that|this|same|last|my|our)\s+(?:flock|batch)\b"
                    r"|\bfor\s+(?:the\s+)?(?:flock|batch)\b"
                    r"|\b(?:flock|batch)\s+(?:data|details|information|info|record|records)\b",
                    query,
                )
            )
        if label == "farm":
            return bool(
                re.search(
                    r"\b(?:the|that|this|same|last|my|our)\s+farm\b"
                    r"|\bfor\s+(?:the\s+)?farm\b"
                    r"|\bfarm\s+(?:data|details|information|record|records)\b",
                    query,
                )
            )
        return False

    def _requires_existing_entity(self, query: str, label: str) -> bool:
        entity_words = "flock|batch" if label == "flock" else "farm"
        return bool(
            re.search(
                rf"\b(?:that|this|same|last)\s+(?:{entity_words})\b"
                rf"|\bfor\s+(?:the\s+)?(?:{entity_words})\b",
                query,
            )
        )

    def _has_detail_pronoun_reference(self, query: str) -> bool:
        return bool(
            re.search(
                r"\b(?:it|that|this|same one|that one|this one|last one|one)\b",
                query,
            )
            and re.search(
                r"\b(?:data|details?|info|information|records?|show|tell|give|about|have)\b",
                query,
            )
        )

    def _has_detail_reference(self, query: str) -> bool:
        return bool(
            re.search(
                r"\b(?:data|details?|info|information|records?|show|tell|give|about)\b",
                query,
            )
        )

    def _latest_entity_from_history(
        self, history: list | None, label: str, objects: list
    ):
        if not history:
            return None
        for item in reversed(history[-12:]):
            metadata_id = item.get(f"resolved_{label}_id")
            if metadata_id is not None:
                metadata_object = self._find_owned_object_by_id(objects, metadata_id)
                if metadata_object:
                    return metadata_object
            content = normalize_ai_query(str(item.get("content", "")))
            if not content:
                continue
            matches = []
            for obj in objects:
                name = self._object_name(obj).lower()
                if name and len(name) >= 3 and name in content:
                    matches.append(obj)
            # U: NEW: an assistant list containing multiple names is not a
            # U: selected entity. Ask a clarification instead of picking row 1.
            if len(matches) == 1:
                return matches[0]
            ordinal = self._ordinal_for_phrase(content, label)
            if ordinal and 1 <= ordinal <= len(objects):
                return objects[ordinal - 1]
        return None

    def _history_mentions_label(self, history: list | None, label: str) -> bool:
        if not history:
            return False
        if label == "flock":
            pattern = r"\b(?:flocks?|batches?|broiler batch)\b"
        elif label == "farm":
            pattern = r"\bfarms?\b(?!\s*:)"
        else:
            return False
        return any(
            re.search(pattern, normalize_ai_query(str(item.get("content", ""))))
            for item in history[-12:]
        )

    def _latest_entity_label_from_history(self, history: list | None) -> str | None:
        if not history:
            return None
        for item in reversed(history[-12:]):
            metadata_type = str(item.get("intent_entity_type", "")).strip().lower()
            if metadata_type in {"farm", "flock"}:
                return metadata_type
            content = normalize_ai_query(str(item.get("content", "")))
            if not content:
                continue
            if re.search(
                r"\byour\s+flocks?\b|\bflock count\b|\b(?:flocks?|batches?)\b", content
            ):
                return "flock"
            if re.search(
                r"\byour\s+farms?\b|\bfarm count\b|\bfarms?\b(?!\s*:)", content
            ):
                return "farm"
        return None

    def _has_named_entity_reference(self, query: str, label: str) -> bool:
        if label == "flock":
            return bool(
                re.search(
                    r"\b(?:for|of|in|about)\s+[a-z0-9 ]*(?:flock|batch|broiler)\b",
                    query,
                )
            )
        if label == "farm":
            return bool(re.search(r"\b(?:for|of|in|about)\s+[a-z0-9 ]*farm\b", query))
        return False

    def _find_owned_object_by_id(self, objects: list, number: int):
        for obj in objects:
            if self._object_id(obj) == number or self._object_public_id(obj) == number:
                return obj
        return None

    def _ordinal_for_phrase(self, query: str, label: str) -> int | None:
        ordinals = (
            ("first", "1st", 1),
            ("second", "2nd", 2),
            ("third", "3rd", 3),
            ("fourth", "4th", 4),
            ("fifth", "5th", 5),
        )
        for word, suffix, value in ordinals:
            # U: OLD: entity resolution only understood "second farm".
            # U: NEW: once the caller already knows the entity label from
            # U: conversation context, bare phrases like "details about 2" or
            # U: "2nd one" resolve against that label's numbered list.
            if re.search(
                rf"\b(?:(?:{word}|{suffix})\s+(?:{label}|one)|{label}\s+(?:{word}|{suffix}))\b",
                query,
            ):
                return value
            if re.search(rf"\b(?:number|no\.?|#)\s*{value}\b", query):
                return value
            if re.search(
                rf"\b(?:details?\s+about|about|data\s+for|show|tell|give|for|of|inside|in|under|from)\s+"
                rf"(?:the\s+)?(?:number\s+|no\.?\s*)?{value}(?:st|nd|rd|th)?(?:\s+one)?\b",
                query,
            ):
                return value
        return None

    def _has_last_entity_reference(self, query: str, label: str) -> bool:
        entity_words = "flock|batch" if label == "flock" else "farm"
        return bool(re.search(rf"\blast\s+(?:{entity_words}|one)\b", query))

    def _missing_entity_response(self, label: str, objects: list) -> dict:
        names = [self._object_name(obj) for obj in objects if self._object_name(obj)]
        available = ", ".join(names) if names else "none yet"
        if not names:
            setup_hint = (
                "Add a flock under a farm first, then ask again."
                if label == "flock"
                else "Add a farm first, then ask again."
            )
            answer = (
                f"I cannot answer that {label} question yet because no {label}s are saved "
                f"in your account. Available {label}s: none yet. {setup_hint}"
            )
        else:
            answer = (
                f"I could not find that {label} in your account. "
                f"Available {label}s: {available}. "
                f"Ask using the exact {label} name, or say first/second {label} based on your list."
            )
        return {
            "status": "success",
            "data": {f"available_{label}s": names},
            "answer": answer,
            "message": answer,
            "rows": [],
            "query": None,
            "params": [],
            "route": TEXT_TO_SQL,
            "metric": f"missing_{label}",
            "engine": "entity_filter",
        }

    def _ambiguous_entity_response(self, label: str, objects: list) -> dict:
        names = [self._object_name(obj) for obj in objects if self._object_name(obj)]
        available = ", ".join(names) if names else "none yet"
        answer = (
            f"Which {label} do you mean? Available {label}s: {available}. "
            f"Ask using the exact {label} name, or say first/second {label} from the list."
        )
        return {
            "status": "success",
            "data": {f"available_{label}s": names},
            "answer": answer,
            "message": answer,
            "rows": [],
            "query": None,
            "params": [],
            "route": TEXT_TO_SQL,
            "metric": f"ambiguous_{label}",
            "engine": "entity_filter",
        }

    def _conflicting_entity_response(self, farm, flock) -> dict:
        selected_farm = self._object_name(farm) or "the selected farm"
        flock_name = self._object_name(flock) or "the selected flock"
        flock_farm = getattr(flock, "farm", None)
        actual_farm = self._object_name(flock_farm) or "another farm"
        answer = (
            f"{flock_name} belongs to {actual_farm}, not {selected_farm}. "
            "Ask again using the correct farm and flock, or ask using only the flock name."
        )
        return {
            "status": "success",
            "data": {
                "farm": selected_farm,
                "flock": flock_name,
                "flock_farm": actual_farm,
            },
            "answer": answer,
            "message": answer,
            "rows": [],
            "query": None,
            "params": [],
            "route": TEXT_TO_SQL,
            "metric": "conflicting_farm_flock",
            "engine": "entity_filter",
        }

    def _direct_entity_answer(
        self, label: str, answer: str, rows: list, metric: str
    ) -> dict:
        return {
            "status": "success",
            "data": rows,
            "answer": answer,
            "message": answer,
            "rows": rows,
            "query": None,
            "params": [],
            "route": TEXT_TO_SQL,
            "metric": metric,
            "engine": "entity_filter",
        }

    def _object_to_flock_row(self, flock) -> dict:
        farm = getattr(flock, "farm", None)
        return {
            "flock_id": self._object_id(flock),
            "flock_name": self._object_name(flock),
            "farm_id": self._flock_farm_id(flock),
            "farm_name": self._object_name(farm) if farm else "",
            "hatch_date": getattr(flock, "hatch_date", None),
            "flock_size": getattr(flock, "flock_size", None),
            "actual_birds": getattr(flock, "actual_birds", None),
            "flock_status": getattr(flock, "status", None),
            "breed_name": getattr(getattr(flock, "breed", None), "name", None),
        }

    def _object_to_farm_row(self, farm) -> dict:
        return {
            "farm_id": self._object_id(farm),
            "farm_name": self._object_name(farm),
            "farm_city": getattr(farm, "city", None),
            "farm_pin": getattr(farm, "pin", None),
            "shed_count": getattr(farm, "shed_count", None),
            "farm_status": getattr(farm, "status", None),
        }

    def _farms(self):
        from farm.models import Farm

        if not self._can_query_entity_tables():
            return []
        # U: NEW: ordinal references must follow the same ordering farmers see
        # U: in "Your farms" answers, otherwise "farm 2" selects the wrong row.
        return list(Farm.objects.filter(user_id=self.user.id).order_by("name", "id")[:100])

    def _flocks(self):
        from flocks.models import Flock

        if not self._can_query_entity_tables():
            return []
        return list(
            Flock.objects.filter(user_id=self.user.id)
            .select_related("farm")
            # U: NEW: keep numbered flock follow-ups aligned with the displayed
            # U: "Your flocks" list sorted by farm name and flock name.
            .order_by("farm__name", "name", "id")[:100]
        )

    def _can_query_entity_tables(self) -> bool:
        return (
            hasattr(self.user, "_meta") and getattr(self.user, "id", None) is not None
        )

    def _object_id(self, obj) -> int | None:
        value = getattr(obj, "id", None)
        return int(value) if value is not None else None

    def _object_public_id(self, obj) -> int | None:
        value = getattr(obj, "public_id", None)
        return int(value) if value is not None else None

    def _object_name(self, obj) -> str:
        return str(getattr(obj, "name", "") or "").strip()

    def _flock_farm_id(self, flock) -> int | None:
        farm_id = getattr(flock, "farm_id", None)
        if farm_id is not None:
            return int(farm_id)
        farm = getattr(flock, "farm", None)
        return self._object_id(farm) if farm else None


class ChikoozaModernAgentService:
    """
    U: Chikooza integration of the cloned chatbot design:
    U: route query -> enforce authenticated user -> run tenant-safe Text-to-SQL.
    U: NEW: use the Groq SQL agent as the active Farmer AI data path.
    U: The deterministic mapper remains in the repo for reference/tests, not
    U: as the live fallback. RAG-only questions are still not connected here.
    """

    def __init__(self, user):
        self.user = user
        self.router = ChikoozaQueryRouter()
        self.sql_service = self._build_sql_service()

    def query(
        self,
        query_text: str,
        history: list | None = None,
        active_context: dict | None = None,
    ) -> dict:
        if not self.user or not self.user.is_authenticated:
            return {"status": "error", "message": "Authentication required."}

        compact_answer = self._shorten_previous_answer(query_text, history)
        if compact_answer:
            return {
                "status": "success",
                "data": None,
                "answer": compact_answer,
                "message": compact_answer,
                "rows": [],
                "query": None,
                "route": CONVERSATION,
                "metric": "previous_answer_summary",
            }

        route = self.router.route(query_text, self.user.id)

        if route == BLOCKED:
            return {
                "status": "error",
                "message": (
                    "I can help with your own farm records, such as farms, flocks, sales, purchases, "
                    "daily data, mortality, feed, weight, FCR, and profit. Try asking: "
                    "'show my farm summary' or 'what are my total sales?'"
                ),
                "suggestion": "Ask about your own farms, flocks, purchases, sales, daily data, mortality, feed, weight, FCR, or profit.",
                "route": route,
            }

        if route == CONVERSATION:
            answer = self._conversation_answer(query_text)
            return {
                "status": "success",
                "data": None,
                "answer": answer,
                "message": answer,
                "rows": [],
                "query": None,
                "route": route,
            }

        if route in {TEXT_TO_SQL, HYBRID}:
            result = self.sql_service.answer(
                query_text,
                history=history,
                active_context=active_context,
            )
            result["route"] = route
            return result

        return {
            "status": "error",
            "message": (
                "Farm-specific RAG is not connected yet. The old poultry knowledge chatbot is still available at /chat/, "
                "and this authenticated AI endpoint currently handles tenant-safe farm data questions."
            ),
            "route": route,
        }

    def _conversation_answer(self, query_text: str) -> str:
        query = normalize_ai_query(query_text)
        if re.match(r"^(thanks|thank you|okay thanks|ok thanks|thanks okay)[!. ]*$", query):
            return "You're welcome. Ask me whenever you need farm records."
        if re.match(r"^(ok|okay)[!. ]*$", query):
            return "Okay. Ask your next farm question whenever you want."
        if re.match(r"^(nothing more|no more|that's all|thats all|all good|done|stop|enough)[!. ]*$", query):
            return "Okay, I will stop here. Ask me whenever you need farm records."
        if re.match(r"^(huh|what do you mean|what meaning|what)[?!. ]*$", query):
            return (
                "I mean I can answer questions from your saved farm records: farms, "
                "flocks, sales, purchases, daily data, mortality, feed, weight, FCR, and profit."
            )
        return (
            "Hello. I can help with your own Chikooza farm records, including farms, flocks, "
            "sales, purchases, daily data, mortality, feed, weight, FCR, profit/loss, and "
            "farm-wise or flock-wise reports."
        )

    def _shorten_previous_answer(
        self, query_text: str, history: list | None = None
    ) -> str | None:
        query = normalize_ai_query(query_text)
        if not re.search(
            # U: NEW: only shorten a previous answer when the farmer clearly
            # U: asks for a shorter response. Plain "farm summary" must still
            # U: run the actual farm-summary query.
            r"\b(?:short|shorter|brief|summari[sz]e\s+(?:that|it|this|previous)|"
            r"too big|big ans|big answer|small answer|in short)\b",
            query,
        ):
            return None

        previous_answer = ""
        for item in reversed(history or []):
            if item.get("role") == "assistant":
                previous_answer = str(item.get("content") or "").strip()
                if previous_answer:
                    break
        if not previous_answer:
            return "I do not have a previous farm answer to shorten yet."

        compact_lines = []
        for raw_line in previous_answer.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("Here is "):
                continue
            line = re.sub(r"\s*Calculation:.*", "", line).strip()
            if not line:
                continue
            if line.startswith("- "):
                line = line[2:].strip()
            if line.endswith(":"):
                continue
            compact_lines.append(line)
            if len(compact_lines) >= 6:
                break

        if not compact_lines:
            return previous_answer[:700].strip()

        # U: NEW: farmers can ask "give it in short" after a long report and
        # U: receive a compact version instead of a generic help message.
        return "Short version:\n" + "\n".join(f"- {line}" for line in compact_lines)

    def _build_sql_service(self):
        provider = os.getenv("AIBOT_SQL_LLM_PROVIDER", "groq_sql").strip().lower()
        if provider in {"off", "false", "rule", "rules", "deterministic"}:
            # U: OLD: returning ChikoozaTextToSQLService here made the live
            # U: Farmer AI use brittle rule matching instead of the cloned
            # U: repo-style LLM SQL planner.
            # return ChikoozaTextToSQLService(user=self.user)
            logger.warning(
                "AIBOT_SQL_LLM_PROVIDER=%s requested the disabled rule engine; using Groq SQL path.",
                provider,
            )

        if provider not in {"auto", "groq", "legacy_sql", "groq_sql", "old_sql"}:
            logger.warning(
                "Unknown AIBOT_SQL_LLM_PROVIDER=%s; using Groq SQL path.", provider
            )

        # U: OLD: the intent/rule agent was used by default.
        # try:
        #     from .intent_agent import ChikoozaIntentAgentService
        #     return ChikoozaIntentAgentService(
        #         user=self.user,
        #         deterministic_service=ChikoozaTextToSQLService(user=self.user),
        #     )
        # except Exception:
        #     logger.exception("Could not initialize intent-based Farmer AI agent.")

        try:
            from .llm_sql import ChikoozaLLMTextToSQLService

            service = ChikoozaLLMTextToSQLService(
                user=self.user,
                # U: OLD: fallback_service=ChikoozaTextToSQLService(...) kept
                # U: silently returning the old deterministic answers. The live
                # U: path now fails clearly if Groq SQL cannot run.
                fallback_service=None,
            )
            return service
        except Exception:
            logger.exception("Could not initialize Groq-backed Farmer AI SQL service.")

        return _UnavailableFarmerAIService()


class _UnavailableFarmerAIService:
    def answer(
        self,
        query_text: str,
        history: list | None = None,
        active_context: dict | None = None,
    ) -> dict:
        return {
            "status": "error",
            "message": (
                "Farmer AI SQL planner is not available. Check Groq API key setup "
                "and backend logs."
            ),
            "route": TEXT_TO_SQL,
            "engine": "groq_sql",
        }
