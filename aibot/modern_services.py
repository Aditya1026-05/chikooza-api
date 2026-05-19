import logging
import re
from dataclasses import dataclass

from django.db import connection

logger = logging.getLogger(__name__)


TEXT_TO_SQL = "TEXT_TO_SQL"
RAG = "RAG"
HYBRID = "HYBRID"
BLOCKED = "BLOCKED"


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
        "sale", "sales", "revenue", "purchase", "purchases", "expense",
        "expenses", "cost", "costs", "farm", "farms", "flock", "flocks",
        "bird", "birds", "mortality", "death", "deaths", "feed", "fcr",
        "weight", "profit", "loss", "net", "count", "total", "average",
        "avg", "how many", "number of",
    }
    RAG_KEYWORDS = {
        "overview", "summary", "summarize", "trend", "trends", "pattern",
        "patterns", "insight", "insights", "analysis", "analyze", "why",
        "recommend", "suggest",
    }
    DESTRUCTIVE_KEYWORDS = {
        "drop", "delete", "truncate", "update", "insert", "alter", "create",
        "replace", "grant", "revoke",
    }

    def route(self, question: str, user_id: int) -> str:
        query = self._normalize(question)
        if not query:
            return BLOCKED

        if any(re.search(rf"\b{word}\b", query) for word in self.DESTRUCTIVE_KEYWORDS):
            return BLOCKED

        if self._mentions_other_user(query, user_id):
            return BLOCKED

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
        return re.sub(r"\s+", " ", (question or "").lower()).strip()


class TenantSafeSQLExecutor:
    """
    U: Port of the cloned repo's tenant validation idea. Chikooza must never
    U: trust client-supplied ids; SQL is generated from request.user and then
    U: validated again before execution.
    """

    ALLOWED_VIEWS = {
        "ai_sale_data_view",
        "ai_purchase_data_view",
        "ai_dailydata_data_view",
    }
    FORBIDDEN_TOKENS = {
        "insert", "update", "delete", "drop", "create", "alter", "truncate",
        "grant", "revoke", "attach", "detach",
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

        if not sql_lower.startswith("select "):
            raise ValueError("Only SELECT queries are allowed.")

        if ";" in sql_lower.rstrip(";"):
            raise ValueError("Multiple SQL statements are not allowed.")

        if any(re.search(rf"\b{token}\b", sql_lower) for token in self.FORBIDDEN_TOKENS):
            raise ValueError("Unsafe SQL token found.")

        # U: OLD validation only confirmed that one safe view appeared anywhere:
        # if not any(view in sql_lower for view in self.ALLOWED_VIEWS):
        #     raise ValueError("Query references an unsupported data source.")
        # U: NEW validation rejects every FROM/JOIN source that is not an
        # U: approved tenant-scoped AI view.
        sources = self._referenced_sources(sql_lower)
        if not sources or any(source not in self.ALLOWED_VIEWS for source in sources):
            raise ValueError("Query references an unsupported data source.")

        view_references = len(sources)
        owner_filters = sql_lower.count("owner_id = %s")
        if owner_filters < view_references:
            raise ValueError("Tenant filter is missing from one or more data sources.")

    def _referenced_sources(self, sql_lower: str) -> list[str]:
        sources = []
        for raw_source in self.SOURCE_PATTERN.findall(sql_lower):
            source = raw_source.strip("`\"[]").split(".")[-1]
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

    def answer(self, question: str) -> dict:
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
        query = re.sub(r"\s+", " ", (question or "").lower()).strip()
        if not query:
            return None

        farm_id = self._extract_filter_id(query, "farm")
        flock_id = self._extract_filter_id(query, "flock")

        if any(word in query for word in ("profit", "loss", "net")):
            return self._profit_plan(farm_id, flock_id)

        if self._is_count_query(query) and "farm" in query:
            return self._aggregate_plan(
                view="ai_dailydata_data_view",
                expression="COUNT(DISTINCT farm_id)",
                metric="farm_count",
                result_type="count",
                farm_id=farm_id,
                flock_id=flock_id,
                extra_conditions=["farm_id IS NOT NULL"],
            )

        if self._is_count_query(query) and "flock" in query:
            return self._aggregate_plan(
                view="ai_dailydata_data_view",
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
                expression="COUNT(DISTINCT purchase_date)",
                metric="purchase_count",
                result_type="count",
                farm_id=farm_id,
                flock_id=flock_id,
                extra_conditions=["purchase_amount IS NOT NULL"],
            )

        metric_map = (
            (("sale", "sales", "revenue"), "ai_sale_data_view", "COALESCE(SUM(sale_amount), 0)", "total_sales", "money"),
            (("purchase", "purchases", "expense", "expenses"), "ai_purchase_data_view", "COALESCE(SUM(purchase_amount), 0)", "total_purchases", "money"),
            (("flock cost", "initial cost", "chick cost"), "ai_purchase_data_view", "COALESCE(SUM(DISTINCT flock_cost), 0)", "flock_cost", "money"),
            (("current birds", "bird count", "birds", "bird"), "ai_dailydata_data_view", "COALESCE(SUM(birds_current), 0)", "current_birds", "count"),
            (("mortality", "deaths", "dead birds", "birds died"), "ai_dailydata_data_view", "COALESCE(SUM(birds_died), 0)", "mortality", "count"),
            (("feed consumed", "feed consumption", "feed intake", "feed"), "ai_dailydata_data_view", "COALESCE(SUM(feed_consumed_kg), 0)", "feed_consumed", "quantity"),
            (("average weight", "bird weight", "weight"), "ai_dailydata_data_view", "COALESCE(AVG(average_bird_weight), 0)", "average_weight", "decimal"),
            (("fcr", "feed conversion"), "ai_dailydata_data_view", "COALESCE(AVG(fcr), 0)", "fcr", "decimal"),
        )

        for keywords, view, expression, metric, result_type in metric_map:
            if any(keyword in query for keyword in keywords):
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
        purchase_where, purchase_params = self._where_clause(farm_id=farm_id, flock_id=flock_id)
        flock_cost_where, flock_cost_params = self._where_clause(farm_id=farm_id, flock_id=flock_id)

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

    def _where_clause(self, farm_id: int | None = None, flock_id: int | None = None) -> tuple[str, list]:
        conditions = ["owner_id = %s"]
        params = [self.user.id]
        if farm_id is not None:
            conditions.append("farm_id = %s")
            params.append(farm_id)
        if flock_id is not None:
            conditions.append("flock_id = %s")
            params.append(flock_id)
        return " AND ".join(conditions), params

    def _extract_filter_id(self, query: str, label: str) -> int | None:
        match = re.search(rf"\b{label}\s*(?:id)?\s*#?(\d+)\b", query)
        return int(match.group(1)) if match else None

    def _is_count_query(self, query: str) -> bool:
        return any(phrase in query for phrase in ("count", "how many", "number of"))

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

        value = row.get("result", 0)
        label = plan.metric.replace("_", " ")
        if plan.result_type == "money":
            return f"{label.title()}: Rs. {float(value or 0):,.2f}."
        if plan.result_type == "decimal":
            return f"{label.title()}: {float(value or 0):,.2f}."
        return f"{label.title()}: {value or 0}."


class ChikoozaModernAgentService:
    """
    U: First Chikooza integration of the cloned chatbot design:
    U: route query -> enforce authenticated user -> run tenant-safe Text-to-SQL.
    U: RAG/HYBRID routes are identified now; farm-specific RAG documents can be
    U: connected in a later step without removing the old chatbot app.
    """

    def __init__(self, user):
        self.user = user
        self.router = ChikoozaQueryRouter()
        self.sql_service = ChikoozaTextToSQLService(user=user)

    def query(self, query_text: str, history: list | None = None) -> dict:
        if not self.user or not self.user.is_authenticated:
            return {"status": "error", "message": "Authentication required."}

        route = self.router.route(query_text, self.user.id)

        if route == BLOCKED:
            return {
                "status": "error",
                "message": "I can only answer safe questions about your own Chikooza farm data.",
                "route": route,
            }

        if route in {TEXT_TO_SQL, HYBRID}:
            result = self.sql_service.answer(query_text)
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
