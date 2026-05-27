import logging
import os
import re
from dataclasses import dataclass

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


def normalize_ai_query(question: str) -> str:
    return re.sub(r"\s+", " ", (question or "").lower()).strip()


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
class SQLPlan:
    sql: str
    params: list
    metric: str
    result_type: str


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
        r"^(hi|hello|hey|namaste|hii|helo|good morning|good afternoon|good evening)[!. ]*$",
        r"^(thanks|thank you|ok|okay)[!. ]*$",
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
    U: Separate deterministic Text-to-SQL class inspired by the cloned BizBot
    U: pipeline. It uses Chikooza's existing SQL views and parameterized queries.
    """

    def __init__(self, user):
        self.user = user
        self.executor = TenantSafeSQLExecutor()

    def answer(self, question: str, history: list | None = None) -> dict:
        plan = self.build_plan(question)
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
        answer = self._format_answer(plan, value)
        return {
            "status": "success",
            "data": value.get("result", value),
            "answer": answer,
            "message": answer,
            "rows": rows,
            "query": plan.sql,
            "params": plan.params,
            "route": TEXT_TO_SQL,
            "metric": plan.metric,
        }

    def build_plan(self, question: str) -> SQLPlan | None:
        query = normalize_ai_query(question)
        if not query:
            return None

        farm_id = self._extract_filter_id(query, "farm")
        flock_id = self._extract_filter_id(query, "flock")

        if self._is_summary_query(query):
            return self._summary_plan()

        if any(word in query for word in ("profit", "loss", "net")):
            return self._profit_plan(farm_id, flock_id)

        if self._is_count_query(query) and "farm" in query:
            return self._aggregate_plan(
                view="ai_farm_flock_data_view",
                expression="COUNT(DISTINCT farm_id)",
                metric="farm_count",
                result_type="count",
                farm_id=farm_id,
                flock_id=flock_id,
                extra_conditions=["farm_id IS NOT NULL"],
            )

        if self._is_count_query(query) and "flock" in query:
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
            )

        metric_map = (
            (
                ("sale", "sales", "revenue"),
                "ai_sale_data_view",
                "COALESCE(SUM(sale_amount), 0)",
                "total_sales",
                "money",
            ),
            (
                ("purchase", "purchases", "expense", "expenses"),
                "ai_purchase_data_view",
                "COALESCE(SUM(purchase_amount), 0)",
                "total_purchases",
                "money",
            ),
            (
                ("flock cost", "initial cost", "chick cost"),
                "ai_purchase_data_view",
                "COALESCE(SUM(DISTINCT flock_cost), 0)",
                "flock_cost",
                "money",
            ),
            (
                ("mortality", "deaths", "dead birds", "birds died"),
                "ai_dailydata_data_view",
                "COALESCE(SUM(birds_died), 0)",
                "mortality",
                "count",
            ),
            (
                ("average weight", "bird weight", "weight"),
                "ai_dailydata_data_view",
                "COALESCE(AVG(average_bird_weight), 0)",
                "average_weight",
                "decimal",
            ),
            (
                ("current birds", "bird count", "birds", "bird"),
                "ai_dailydata_data_view",
                "COALESCE(SUM(birds_current), 0)",
                "current_birds",
                "count",
            ),
            (
                ("feed consumed", "feed consumption", "feed intake", "feed"),
                "ai_dailydata_data_view",
                "COALESCE(SUM(feed_consumed_kg), 0)",
                "feed_consumed",
                "quantity",
            ),
            (
                ("fcr", "feed conversion"),
                "ai_dailydata_data_view",
                "COALESCE(AVG(fcr), 0)",
                "fcr",
                "decimal",
            ),
        )

        for keywords, view, expression, metric, result_type in metric_map:
            if any(keyword in query for keyword in keywords):
                if metric == "current_birds":
                    return self._current_birds_plan(farm_id, flock_id)
                return self._aggregate_plan(
                    view=view,
                    expression=expression,
                    metric=metric,
                    result_type=result_type,
                    farm_id=farm_id,
                    flock_id=flock_id,
                )

        return None

    def _aggregate_plan(
        self,
        view: str,
        expression: str,
        metric: str,
        result_type: str,
        farm_id: int | None = None,
        flock_id: int | None = None,
        extra_conditions: list[str] | None = None,
    ) -> SQLPlan:
        where_sql, params = self._where_clause(farm_id=farm_id, flock_id=flock_id)
        conditions = list(extra_conditions or [])
        if conditions:
            where_sql = f"{where_sql} AND {' AND '.join(conditions)}"
        return SQLPlan(
            sql=f"SELECT {expression} AS result FROM {view} WHERE {where_sql}",
            params=params,
            metric=metric,
            result_type=result_type,
        )

    def _profit_plan(self, farm_id: int | None, flock_id: int | None) -> SQLPlan:
        sale_where, sale_params = self._where_clause(farm_id=farm_id, flock_id=flock_id)
        purchase_where, purchase_params = self._where_clause(
            farm_id=farm_id, flock_id=flock_id
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
        )

    def _current_birds_plan(self, farm_id: int | None, flock_id: int | None) -> SQLPlan:
        # U: OLD code summed birds_current across every daily row, which double
        # U: counted the same flock over time.
        # U: NEW code sums only the latest daily row for each flock.
        current_where, current_params = self._where_clause(
            farm_id=farm_id, flock_id=flock_id, table_alias="current_rows"
        )
        sql = f"""
            SELECT COALESCE(SUM(current_rows.birds_current), 0) AS result
            FROM ai_dailydata_data_view current_rows
            WHERE {current_where}
              AND current_rows.daily_data_id IS NOT NULL
              AND current_rows.record_date = (
                  SELECT MAX(compare_rows.record_date)
                  FROM ai_dailydata_data_view compare_rows
                  WHERE compare_rows.owner_id = %s
                    AND compare_rows.flock_id = current_rows.flock_id
                    AND compare_rows.daily_data_id IS NOT NULL
              )
        """
        return SQLPlan(
            sql=re.sub(r"\s+", " ", sql).strip(),
            params=current_params + [self.user.id],
            metric="current_birds",
            result_type="count",
        )

    def _summary_plan(self) -> SQLPlan:
        sql = """
            SELECT
                (SELECT COUNT(DISTINCT farm_id) FROM ai_farm_flock_data_view WHERE owner_id = %s AND farm_id IS NOT NULL) AS farm_count,
                (SELECT COUNT(DISTINCT flock_id) FROM ai_farm_flock_data_view WHERE owner_id = %s AND flock_id IS NOT NULL) AS flock_count,
                (SELECT COALESCE(SUM(current_rows.birds_current), 0) FROM ai_dailydata_data_view current_rows WHERE current_rows.owner_id = %s AND current_rows.daily_data_id IS NOT NULL AND current_rows.record_date = (SELECT MAX(compare_rows.record_date) FROM ai_dailydata_data_view compare_rows WHERE compare_rows.owner_id = %s AND compare_rows.flock_id = current_rows.flock_id AND compare_rows.daily_data_id IS NOT NULL)) AS current_birds,
                (SELECT COALESCE(SUM(sale_amount), 0) FROM ai_sale_data_view WHERE owner_id = %s) AS total_sales,
                (SELECT COALESCE(SUM(purchase_amount), 0) FROM ai_purchase_data_view WHERE owner_id = %s) AS total_purchases,
                (SELECT COALESCE(SUM(feed_consumed_kg), 0) FROM ai_dailydata_data_view WHERE owner_id = %s) AS total_feed_consumed,
                (SELECT COALESCE(SUM(birds_died), 0) FROM ai_dailydata_data_view WHERE owner_id = %s) AS total_mortality,
                (SELECT COALESCE(AVG(fcr), 0) FROM ai_dailydata_data_view WHERE owner_id = %s AND fcr IS NOT NULL) AS average_fcr
        """
        return SQLPlan(
            sql=re.sub(r"\s+", " ", sql).strip(),
            params=[self.user.id] * 9,
            metric="farm_record_summary",
            result_type="summary",
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

    def _extract_filter_id(self, query: str, label: str) -> int | None:
        match = re.search(rf"\b{label}\s*(?:id)?\s*#?(\d+)\b", query)
        return int(match.group(1)) if match else None

    def _is_count_query(self, query: str) -> bool:
        return any(phrase in query for phrase in ("count", "how many", "number of"))

    def _is_summary_query(self, query: str) -> bool:
        return is_broad_summary_query(query)

    def _format_answer(self, plan: SQLPlan, row: dict) -> str:
        if plan.metric == "profit_loss":
            total_sales = float(row.get("total_sales") or 0)
            total_purchases = float(row.get("total_purchases") or 0)
            flock_cost = float(row.get("flock_cost") or 0)
            net = float(row.get("result") or 0)
            status = "profit" if net > 0 else "loss" if net < 0 else "break-even"
            return (
                f"Total sales: Rs. {total_sales:,.2f}, total purchases: Rs. {total_purchases:,.2f}, "
                f"flock cost: Rs. {flock_cost:,.2f}. Net result: Rs. {net:,.2f} ({status})."
            )

        if plan.metric == "farm_record_summary":
            return (
                "Your account summary: "
                f"{row.get('farm_count') or 0} farms, {row.get('flock_count') or 0} flocks, "
                f"{row.get('current_birds') or 0} current birds, "
                f"Rs. {float(row.get('total_sales') or 0):,.2f} sales, "
                f"Rs. {float(row.get('total_purchases') or 0):,.2f} purchases, "
                f"{float(row.get('total_feed_consumed') or 0):,.2f} kg feed consumed, "
                f"{row.get('total_mortality') or 0} total mortality, and "
                f"{float(row.get('average_fcr') or 0):,.2f} average FCR."
            )

        value = row.get("result", 0)
        label = plan.metric.replace("_", " ")
        if plan.metric == "feed_consumed":
            return f"Total feed consumed: {float(value or 0):,.2f} kg."
        if plan.metric == "current_birds":
            return f"Current birds: {value or 0}."
        if plan.metric == "mortality":
            return f"Total mortality: {value or 0} birds."
        if plan.result_type == "money":
            return f"{label.title()}: Rs. {float(value or 0):,.2f}."
        if plan.result_type == "decimal":
            return f"{label.title()}: {float(value or 0):,.2f}."
        return f"{label.title()}: {value or 0}."


class ChikoozaModernAgentService:
    """
    U: Chikooza integration of the cloned chatbot design:
    U: route query -> enforce authenticated user -> run tenant-safe Text-to-SQL.
    U: NEW: use the Groq SQL agent when configured and keep the deterministic
    U: mapper as fallback. RAG-only questions are still not connected here.
    """

    def __init__(self, user):
        self.user = user
        self.router = ChikoozaQueryRouter()
        self.sql_service = self._build_sql_service()

    def query(self, query_text: str, history: list | None = None) -> dict:
        if not self.user or not self.user.is_authenticated:
            return {"status": "error", "message": "Authentication required."}

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
            return {
                "status": "success",
                "data": None,
                "answer": (
                    "Hello. Ask me about your farm records, for example: 'show my farm summary', "
                    "'what are my total sales?', 'current birds', 'profit or loss', or 'average FCR'."
                ),
                "message": (
                    "Hello. Ask me about your farm records, for example: 'show my farm summary', "
                    "'what are my total sales?', 'current birds', 'profit or loss', or 'average FCR'."
                ),
                "rows": [],
                "query": None,
                "route": route,
            }

        if route in {TEXT_TO_SQL, HYBRID}:
            result = self.sql_service.answer(query_text, history=history)
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

    def _build_sql_service(self):
        fallback = ChikoozaTextToSQLService(user=self.user)
        provider = os.getenv("AIBOT_SQL_LLM_PROVIDER", "auto").strip().lower()
        if provider in {"off", "false", "rule", "rules", "deterministic"}:
            return fallback

        try:
            from .llm_sql import ChikoozaLLMTextToSQLService

            service = ChikoozaLLMTextToSQLService(
                user=self.user,
                fallback_service=fallback,
            )
            if service.is_available:
                return service
        except Exception:
            logger.exception("Could not initialize Groq-backed Farmer AI SQL service.")

        return fallback
