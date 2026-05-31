import re

from .intent_classifier import ChikoozaIntent
from .insight_service import ChikoozaFarmInsightService
from .multi_report_service import ChikoozaMultiReportService
from .trend_service import ChikoozaTrendComparisonService


class ChikoozaSafeQueryExecutor:
    """
    U: NEW: Professional Farmer AI stage 3.
    U: Execute fixed backend queries only. It never accepts SQL from Groq.
    U: For now this delegates to the existing deterministic service so we keep
    U: all tenant-safety validation and already-tested SQL behavior.
    """

    def __init__(self, deterministic_service, entity_resolver):
        self.deterministic_service = deterministic_service
        self.entity_resolver = entity_resolver
        self.insight_service = ChikoozaFarmInsightService(
            getattr(deterministic_service, "user", None),
            deterministic_service=deterministic_service,
        )
        self.multi_report_service = ChikoozaMultiReportService(deterministic_service)
        self.trend_service = ChikoozaTrendComparisonService(deterministic_service)

    def execute(
        self, intent: ChikoozaIntent, question: str, history: list | None = None
    ) -> dict:
        if intent.intent == "greeting":
            return {
                "status": "success",
                "data": None,
                "answer": (
                    "Hello. Ask me about your farm records, for example: "
                    "'show my farm summary', 'what are my total sales?', "
                    "'current birds', 'profit or loss', or 'average FCR'."
                ),
                "message": (
                    "Hello. Ask me about your farm records, for example: "
                    "'show my farm summary', 'what are my total sales?', "
                    "'current birds', 'profit or loss', or 'average FCR'."
                ),
                "rows": [],
                "query": None,
                "params": [],
                "route": "TEXT_TO_SQL",
                "metric": "conversation",
            }

        if intent.intent == "capability_help":
            return self.insight_service.capability_answer()

        vague_target_response = self._vague_target_response(intent, question, history)
        if vague_target_response:
            return vague_target_response

        if intent.intent == "unsupported":
            return {
                "status": "error",
                "message": (
                    "I can answer questions about your own farms, flocks, sales, purchases, "
                    "daily data, mortality, feed, weight, FCR, and profit."
                ),
                "route": "TEXT_TO_SQL",
                "metric": "unsupported",
            }

        if intent.intent == "farm_progress_insight":
            return self.insight_service.answer(
                question,
                history=history,
                intent=intent,
            )

        if intent.intent == "field_lookup":
            entity_resolution = self.entity_resolver.resolve(intent, question, history)
            if entity_resolution.response:
                return entity_resolution.response
            return self._field_lookup_response(intent, entity_resolution)

        if intent.intent == "multi_farm_report":
            entity_resolution = None
            if self._should_resolve_multi_report_target(intent, question):
                entity_resolution = self.entity_resolver.resolve(intent, question, history)
                if entity_resolution.response:
                    return entity_resolution.response
            response = self.multi_report_service.answer(
                question,
                history=history,
                intent=intent,
                entity_resolution=entity_resolution,
            )
            return self._attach_resolution(response, entity_resolution)

        if intent.intent in {"comparison_report", "trend_report", "best_flock_report"}:
            entity_resolution = None
            if self._should_resolve_report_target(intent, question):
                entity_resolution = self.entity_resolver.resolve(intent, question, history)
                if entity_resolution.response:
                    return entity_resolution.response
            response = self.trend_service.answer(
                question,
                intent=intent,
                entity_resolution=entity_resolution,
            )
            return self._attach_resolution(response, entity_resolution)

        if self._should_skip_entity_resolution(intent):
            # U: OLD: account-wide/list intents still went through entity
            # U: resolution, so "farm summary" or "list all flocks" could become
            # U: ambiguous when the account had multiple farms/flocks.
            # U: NEW: keep broad questions broad unless the classifier found an
            # U: explicit entity reference such as first/second/that/exact name.
            canonical_question = self._canonical_question(intent, question)
            response = self.deterministic_service.answer(canonical_question, history=[])
            response["canonical_question"] = canonical_question
            response["resolved_farm_id"] = None
            response["resolved_flock_id"] = None
            return response

        entity_resolution = self.entity_resolver.resolve(intent, question, history)
        if entity_resolution.response:
            return entity_resolution.response

        canonical_question = self._canonical_question(intent, question)
        response = self.deterministic_service.answer(
            canonical_question, history=history
        )
        response["canonical_question"] = canonical_question
        response["resolved_farm_id"] = entity_resolution.farm_id
        response["resolved_flock_id"] = entity_resolution.flock_id
        return response

    def _canonical_question(self, intent: ChikoozaIntent, question: str) -> str:
        target = self._target_phrase(intent)
        if intent.intent == "farm_summary":
            base = f"show summary for {target}" if target else "show my account summary"
            return self._with_time_phrase(base, question)
        if intent.intent == "list_farms":
            return f"list farms for {target}" if target else "list all farms i have"
        if intent.intent == "list_flocks":
            return f"list flocks for {target}" if target else "list all flocks i have"
        if intent.intent == "count_farms":
            return f"how many farms for {target}" if target else "how many farms"
        if intent.intent == "count_flocks":
            return f"how many flocks for {target}" if target else "how many flocks"
        if intent.intent == "farm_details":
            return f"show data for {target or 'the farm'}"
        if intent.intent == "flock_details":
            return f"show data for {target or 'the flock'}"
        if intent.intent == "sales_total":
            base = f"total sales for {target}" if target else "total sales"
            return self._with_time_phrase(base, question)
        if intent.intent == "purchase_total":
            base = f"total purchases for {target}" if target else "total purchases"
            return self._with_time_phrase(base, question)
        if intent.intent == "profit_loss":
            base = f"profit or loss for {target}" if target else "profit or loss"
            return self._with_time_phrase(base, question)
        if intent.intent == "current_birds":
            base = f"current birds for {target}" if target else "current birds"
            return self._with_time_phrase(base, question)
        if intent.intent == "mortality":
            base = f"mortality for {target}" if target else "mortality"
            return self._with_time_phrase(base, question)
        if intent.intent == "feed_consumed":
            base = f"feed consumed for {target}" if target else "feed consumed"
            return self._with_time_phrase(base, question)
        if intent.intent == "average_weight":
            base = f"average weight for {target}" if target else "average weight"
            return self._with_time_phrase(base, question)
        if intent.intent == "average_fcr":
            base = f"average fcr for {target}" if target else "average fcr"
            return self._with_time_phrase(base, question)
        if intent.intent == "other_entity":
            label = intent.entity_type or "flock"
            return f"any other {label} i have"
        return question

    def _with_time_phrase(self, canonical_question: str, original_question: str) -> str:
        # U: NEW: keep safe canonical wording, but do not drop date filters like
        # U: "this month" or "between 2026-01-01 and 2026-01-31".
        time_phrase = self._time_phrase(original_question)
        if not time_phrase:
            return canonical_question
        if time_phrase in canonical_question.lower():
            return canonical_question
        return f"{canonical_question} {time_phrase}"

    def _time_phrase(self, question: str) -> str:
        query = (question or "").lower()
        date_value = r"\d{4}-\d{1,2}-\d{1,2}|\d{1,2}[/-]\d{1,2}[/-]\d{4}"
        month_name = (
            r"jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
            r"jul(?:y)?|aug(?:ust)?|sep(?:t|tember)?|oct(?:ober)?|"
            r"nov(?:ember)?|dec(?:ember)?"
        )
        patterns = (
            rf"\bbetween\s+(?:{date_value})\s+(?:and|to)\s+(?:{date_value})\b",
            rf"\bfrom\s+(?:{date_value})\s+(?:to|till|until|through)\s+(?:{date_value})\b",
            r"\blast\s+\d{1,3}\s+days?\b",
            r"\bthis\s+week\b",
            r"\blast\s+week\b",
            r"\bthis\s+month\b",
            r"\blast\s+month\b",
            r"\bthis\s+year\b",
            r"\blast\s+year\b",
            r"\btoday\b",
            r"\byesterday\b",
            rf"\b(?:in|for|during)\s+(?:{month_name})(?:\s+\d{{4}})?\b",
        )
        for pattern in patterns:
            match = re.search(pattern, query)
            if match:
                return match.group(0)
        return ""

    def _target_phrase(self, intent: ChikoozaIntent) -> str:
        entity_type = intent.entity_type
        reference = (intent.entity_reference or "").strip()
        if not entity_type:
            return ""
        if reference in {"", "current"}:
            return ""
        if reference == "other":
            return f"other {entity_type}"
        if reference in {
            "it",
            "that",
            "this",
            "same",
            "same one",
            "this one",
            "that one",
        }:
            return f"the {entity_type}"
        if reference in {"last", "last one"}:
            return f"last {entity_type}"
        if reference in {"first", "second", "third", "fourth", "fifth"}:
            return f"{reference} {entity_type}"
        return f"{entity_type} {reference}"

    def _should_skip_entity_resolution(self, intent: ChikoozaIntent) -> bool:
        reference = (intent.entity_reference or "").strip()
        if reference and reference != "current":
            return False
        return intent.intent in {
            "farm_summary",
            "list_farms",
            "list_flocks",
            "count_farms",
            "count_flocks",
        }

    def _should_resolve_multi_report_target(
        self, intent: ChikoozaIntent, question: str
    ) -> bool:
        return self._should_resolve_report_target(intent, question)

    def _should_resolve_report_target(
        self, intent: ChikoozaIntent, question: str
    ) -> bool:
        entity_type = intent.entity_type
        reference = (intent.entity_reference or "").strip()
        if entity_type not in {"farm", "flock"}:
            return False
        if reference and reference != "other":
            return True
        entity_words = "flock|batch" if entity_type == "flock" else "farm"
        return bool(
            re.search(
                rf"\b(?:for|inside|about|of|in)\s+(?:the\s+|my\s+|our\s+)?[a-z0-9 ]*\b(?:{entity_words})\b",
                question.lower(),
            )
        )

    def _vague_target_response(
        self, intent: ChikoozaIntent, question: str, history: list | None
    ) -> dict | None:
        if intent.entity_type in {"farm", "flock"}:
            return None
        query = (question or "").lower()
        has_pronoun_reference = bool(
            re.search(r"\b(?:it|that one|this one|same one|last one)\b", query)
        )
        has_generic_data_request = bool(
            re.search(
                r"\b(?:show|tell|give|open|check|see)\s+(?:me\s+)?"
                r"(?:the\s+|my\s+)?(?:data|details?|records?|information|info|status)\b",
                query,
            )
        )
        if not has_pronoun_reference and not has_generic_data_request:
            return None
        latest_label = self.deterministic_service._latest_entity_label_from_history(
            history
        )
        if latest_label:
            return None
        answer = (
            "I need one detail before I answer: do you mean a farm or a flock, "
            "or your whole account? Choose whole account, a farm, or a flock. "
            "For example, ask 'show my farm summary', "
            "'sales for Red Farm', or 'profit for Alpha Batch'."
        )
        return {
            "status": "success",
            "data": {"available_scopes": ["account", "farm", "flock"]},
            "answer": answer,
            "message": answer,
            "rows": [],
            "query": None,
            "params": [],
            "route": "TEXT_TO_SQL",
            "metric": "ambiguous_scope",
            "engine": "entity_filter",
        }

    def _attach_resolution(self, response: dict, entity_resolution) -> dict:
        if entity_resolution:
            response["resolved_farm_id"] = entity_resolution.farm_id
            response["resolved_flock_id"] = entity_resolution.flock_id
        return response

    def _field_lookup_response(self, intent: ChikoozaIntent, entity_resolution) -> dict:
        field = (intent.raw or {}).get("field")
        field_label = (intent.raw or {}).get("field_label") or "Value"
        entity_type = intent.entity_type

        if entity_type == "flock":
            if entity_resolution.flock_id is None:
                return self._clarify_field_target("flock", field_label)
            plan = self.deterministic_service._flock_list_plan(
                farm_id=entity_resolution.farm_id,
                flock_id=entity_resolution.flock_id,
            )
        elif entity_type == "farm":
            if entity_resolution.farm_id is None:
                return self._clarify_field_target("farm", field_label)
            plan = self.deterministic_service._farm_list_plan(
                farm_id=entity_resolution.farm_id,
            )
        else:
            return self._clarify_field_target("farm or flock", field_label)

        rows = self.deterministic_service.executor.execute(plan)
        row = rows[0] if rows else {}
        name = row.get(f"{entity_type}_name") or f"selected {entity_type}"
        value = self._field_value(field, row)
        answer = f"{field_label} for {name}: {value}."
        return {
            "status": "success",
            "data": {"entity": name, "field": field, "value": value},
            "answer": answer,
            "message": answer,
            "rows": rows,
            "query": plan.sql,
            "params": plan.params,
            "route": "TEXT_TO_SQL",
            "metric": f"{entity_type}_{field}",
            "engine": "field_lookup",
            "resolved_farm_id": entity_resolution.farm_id,
            "resolved_flock_id": entity_resolution.flock_id,
        }

    def _field_value(self, field: str, row: dict):
        if field == "location":
            parts = [
                str(part)
                for part in (row.get("farm_city"), row.get("farm_pin"))
                if part not in (None, "")
            ]
            return ", ".join(parts) if parts else "Not added"
        if field == "farm_status":
            return "Active" if row.get("farm_status") else "Inactive"
        value = row.get(field)
        return value if value not in (None, "") else "Not added"

    def _clarify_field_target(self, entity_type: str, field_label: str) -> dict:
        answer = (
            f"Which {entity_type} should I use for {field_label.lower()}? "
            f"Ask with a name or number, for example '{field_label.lower()} for first flock'."
        )
        return {
            "status": "success",
            "data": None,
            "answer": answer,
            "message": answer,
            "rows": [],
            "query": None,
            "params": [],
            "route": "TEXT_TO_SQL",
            "metric": "ambiguous_field_target",
            "engine": "field_lookup",
        }
