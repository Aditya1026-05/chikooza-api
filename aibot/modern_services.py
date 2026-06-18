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

COMMON_QUERY_TYPO_REPLACEMENTS = (
    (r"\bglock(s)?\b", r"flock\1"),
    (r"\bflcok(s)?\b", r"flock\1"),
    (r"\bflcoks\b", "flocks"),
    (r"\bfork(s)?\b", r"flock\1"),
    (r"\bfamr(s)?\b", r"farm\1"),
    (r"\bsail(s)?\b", r"sale\1"),
    (r"\bpruchase(s)?\b", r"purchase\1"),
    (r"\bpurchaes\b", "purchase"),
    (r"\bmortilty\b", "mortality"),
    (r"\bmortaltiy\b", "mortality"),
    (r"\bbuggest\b", "biggest"),
    (r"\bperfoming\b", "performing"),
    (r"\bimporve\b", "improve"),
)


def normalize_ai_query(question: str) -> str:
    query = re.sub(r"\s+", " ", (question or "").lower()).strip()
    for pattern, replacement in COMMON_QUERY_TYPO_REPLACEMENTS:
        query = re.sub(pattern, replacement, query)
    return query


@dataclass(frozen=True)
class SQLPlan:
    sql: str
    params: list
    metric: str
    result_type: str
    date_range: object | None = None


class TenantSafeSQLExecutor:
    """Executes only tenant-scoped SELECT queries against approved AI views."""

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
        if any(re.search(rf"\b{token}\b", sql_lower) for token in self.FORBIDDEN_TOKENS):
            raise ValueError("Unsafe SQL token found.")
        if sql_lower.count("%s") != len(plan.params):
            raise ValueError("SQL placeholder count does not match params.")

        sources = self._referenced_sources(sql_lower)
        if not sources or any(source not in self.ALLOWED_VIEWS for source in sources):
            raise ValueError("Query references an unsupported data source.")
        if sql_comparison_lower.count("owner_id = %s") < len(sources):
            raise ValueError("Tenant filter is missing from one or more data sources.")
        if re.search(r"\bowner_id\s*=\s*(?!%s\b)[^\s)]+", sql_lower):
            raise ValueError("Tenant filter must use parameterized authenticated owner id.")
        if re.search(r"\bowner_id\s+in\s*\(", sql_lower):
            raise ValueError("Tenant filter must not use owner_id IN clauses.")

    def _referenced_sources(self, sql_lower: str) -> list[str]:
        return [
            raw_source.strip('`"[]').split(".")[-1]
            for raw_source in self.SOURCE_PATTERN.findall(sql_lower)
        ]


class ChikoozaQueryRouter:
    """Small routing guard before the Groq SQL planner is called."""

    DATA_KEYWORDS = {
        "farm",
        "farms",
        "flock",
        "flocks",
        "bird",
        "birds",
        "sale",
        "sales",
        "revenue",
        "purchase",
        "purchases",
        "cost",
        "costs",
        "expense",
        "profit",
        "loss",
        "feed",
        "fcr",
        "weight",
        "mortality",
        "death",
        "deaths",
        "daily",
        "data",
        "record",
        "records",
        "summary",
        "overview",
        "performance",
        "performing",
        "best",
        "worst",
        "highest",
        "lowest",
        "most",
        "least",
        "count",
        "total",
        "average",
        "avg",
        "breed",
        "hatch",
        "current",
        "active",
        "selected",
        "improve",
        "advice",
    }
    CONVERSATION_PATTERNS = (
        r"^(hi|hello|hey|yo|hii|helo|namaste)\b",
        r"^(ok|okay|thanks|thank you|okay thanks|ok thanks)[!. ]*$",
        r"^(nothing more|no more|that's all|thats all|all good|done|stop|enough)[!. ]*$",
        r"^(huh|what do you mean|what meaning|what)[?!. ]*$",
    )
    FOLLOW_UP_WORDS = {
        "that",
        "this",
        "it",
        "same",
        "other",
        "others",
        "detail",
        "details",
        "more",
        "again",
        "compare",
        "then",
        "now",
    }

    def route(self, query_text: str, user_id: int | None = None) -> str:
        query = normalize_ai_query(query_text)
        if not query:
            return BLOCKED
        if self._is_cross_tenant_request(query):
            return BLOCKED
        if any(re.search(pattern, query) for pattern in self.CONVERSATION_PATTERNS):
            return CONVERSATION
        if self._looks_like_data_query(query):
            return TEXT_TO_SQL
        return BLOCKED

    def is_follow_up(self, query_text: str) -> bool:
        query_words = set(normalize_ai_query(query_text).split())
        return bool(query_words & self.FOLLOW_UP_WORDS)

    def _looks_like_data_query(self, query: str) -> bool:
        if any(keyword in query for keyword in self.DATA_KEYWORDS):
            return True
        return bool(
            re.search(r"\b(?:how many|how much|which|when|where|show|list|tell|give)\b", query)
        )

    def _is_cross_tenant_request(self, query: str) -> bool:
        return bool(
            re.search(
                r"\b(?:other|another|different)\s+(?:farmer|user|customer|owner)\b",
                query,
            )
        )


class ChikoozaModernAgentService:
    """Authenticated Farmer AI service backed by Groq text-to-SQL."""

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
            return self._success(compact_answer, route=CONVERSATION, metric="previous_answer_summary")

        route = self.router.route(query_text, self.user.id)
        if route == BLOCKED and history and self.router.is_follow_up(query_text):
            route = TEXT_TO_SQL

        if route == CONVERSATION:
            return self._success(self._conversation_answer(query_text), route=CONVERSATION)
        if route == TEXT_TO_SQL:
            result = self.sql_service.answer(
                query_text,
                history=history,
                active_context=active_context,
            )
            result["route"] = TEXT_TO_SQL
            return result

        return {
            "status": "error",
            "message": (
                "I can help with your own farm records: farms, flocks, sales, purchases, "
                "daily data, mortality, feed, weight, FCR, and profit."
            ),
            "suggestion": "Ask about your farm summary, flocks, sales, purchases, daily data, FCR, or profit.",
            "route": BLOCKED,
        }

    def _success(self, answer: str, *, route: str, metric: str = "conversation") -> dict:
        return {
            "status": "success",
            "data": None,
            "answer": answer,
            "message": answer,
            "rows": [],
            "query": None,
            "route": route,
            "metric": metric,
        }

    def _conversation_answer(self, query_text: str) -> str:
        query = normalize_ai_query(query_text)
        if re.match(r"^(thanks|thank you|okay thanks|ok thanks)[!. ]*$", query):
            return "You're welcome. Ask me whenever you need farm records."
        if re.match(r"^(ok|okay)[!. ]*$", query):
            return "Okay. Ask your next farm question whenever you want."
        if re.match(r"^(nothing more|no more|that's all|thats all|all good|done|stop|enough)[!. ]*$", query):
            return "Okay, I will stop here. Ask me whenever you need farm records."
        if re.match(r"^(huh|what do you mean|what meaning|what)[?!. ]*$", query):
            return "I can answer from your saved farm records: farms, flocks, sales, purchases, daily data, mortality, feed, weight, FCR, and profit."
        return "Hello. I can help with your own Chikooza farm records."

    def _shorten_previous_answer(self, query_text: str, history: list | None = None) -> str | None:
        query = normalize_ai_query(query_text)
        if not re.search(
            r"\b(?:short|shorter|brief|summari[sz]e\s+(?:that|it|this|previous)|too big|big answer|in short)\b",
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

        lines = []
        for raw_line in previous_answer.splitlines():
            line = raw_line.strip().lstrip("- ").strip()
            if not line or line.lower().startswith("here "):
                continue
            lines.append(line)
            if len(lines) >= 6:
                break
        return "Short version:\n" + "\n".join(f"- {line}" for line in lines) if lines else previous_answer[:700].strip()

    def _build_sql_service(self):
        provider = os.getenv("AIBOT_SQL_LLM_PROVIDER", "groq_sql").strip().lower()
        if provider not in {"auto", "groq", "groq_sql"}:
            logger.warning("Unsupported AIBOT_SQL_LLM_PROVIDER=%s; using Groq SQL.", provider)

        try:
            from .llm_sql import ChikoozaLLMTextToSQLService

            return ChikoozaLLMTextToSQLService(user=self.user)
        except Exception:
            logger.exception("Could not initialize Farmer AI SQL service.")
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
            "message": "Farmer AI SQL planner is not available. Check Groq API key setup and backend logs.",
            "route": TEXT_TO_SQL,
            "engine": "groq_sql",
        }
