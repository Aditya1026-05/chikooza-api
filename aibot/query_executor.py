from .intent_classifier import ChikoozaIntent
from .insight_service import ChikoozaFarmInsightService
from .multi_report_service import ChikoozaMultiReportService


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

    def execute(
        self, intent: ChikoozaIntent, question: str, history: list | None = None
    ) -> dict:
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

        if intent.intent == "farm_progress_insight":
            return self.insight_service.answer(
                question,
                history=history,
                intent=intent,
            )

        if intent.intent == "multi_farm_report":
            return self.multi_report_service.answer(
                question,
                history=history,
                intent=intent,
            )

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
            return "show my farm summary"
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
            return f"total sales for {target}" if target else "total sales"
        if intent.intent == "purchase_total":
            return f"total purchases for {target}" if target else "total purchases"
        if intent.intent == "profit_loss":
            return f"profit or loss for {target}" if target else "profit or loss"
        if intent.intent == "current_birds":
            return f"current birds for {target}" if target else "current birds"
        if intent.intent == "mortality":
            return f"mortality for {target}" if target else "mortality"
        if intent.intent == "feed_consumed":
            return f"feed consumed for {target}" if target else "feed consumed"
        if intent.intent == "average_weight":
            return f"average weight for {target}" if target else "average weight"
        if intent.intent == "average_fcr":
            return f"average fcr for {target}" if target else "average fcr"
        if intent.intent == "other_entity":
            label = intent.entity_type or "flock"
            return f"any other {label} i have"
        return question

    def _target_phrase(self, intent: ChikoozaIntent) -> str:
        entity_type = intent.entity_type
        reference = (intent.entity_reference or "").strip()
        if not entity_type:
            return ""
        if reference in {"", "current"}:
            return f"the {entity_type}"
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
        if reference in {"first", "second", "third", "fourth", "fifth"}:
            return f"{reference} {entity_type}"
        return f"{entity_type} {reference}"
