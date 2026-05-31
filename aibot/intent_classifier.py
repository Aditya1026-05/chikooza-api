import json
import logging
import os
import re
from dataclasses import dataclass, field

import httpx

from common.groq_client import GroqAllKeysFailed, GroqChatClient

logger = logging.getLogger(__name__)


ALLOWED_INTENTS = {
    "farm_summary",
    "list_farms",
    "list_flocks",
    "count_farms",
    "count_flocks",
    "farm_details",
    "flock_details",
    "sales_total",
    "purchase_total",
    "profit_loss",
    "current_birds",
    "mortality",
    "feed_consumed",
    "average_weight",
    "average_fcr",
    "multi_farm_report",
    "comparison_report",
    "trend_report",
    "best_flock_report",
    "farm_progress_insight",
    "field_lookup",
    "capability_help",
    "other_entity",
    "greeting",
    "unsupported",
}

ALLOWED_ENTITY_TYPES = {"", "farm", "flock"}


@dataclass(frozen=True)
class ChikoozaIntent:
    intent: str
    entity_type: str = ""
    entity_reference: str = ""
    scope: str = "current"
    confidence: float = 0.0
    source: str = "rule"
    raw: dict = field(default_factory=dict)

    @property
    def is_supported(self) -> bool:
        return self.intent not in {"unsupported"}


class ChikoozaIntentClassifier:
    """
    U: NEW: Professional Farmer AI stage 1.
    U: Groq is used only to understand language and return a safe JSON intent.
    U: It is not allowed to generate SQL or decide private data access.
    """

    def __init__(self, user, groq_client: GroqChatClient | None = None):
        self.user = user
        self.client = groq_client or GroqChatClient(
            model=os.getenv("AIBOT_INTENT_MODEL", "llama-3.1-8b-instant"),
            fallback_model=os.getenv(
                "AIBOT_INTENT_FALLBACK_MODEL", "llama-3.1-8b-instant"
            ),
            timeout=float(os.getenv("AIBOT_INTENT_TIMEOUT", "20")),
        )

    def classify(self, question: str, history: list | None = None) -> ChikoozaIntent:
        query = self._normalize(question)
        if self._is_account_summary_detail_followup(query, history):
            # U: NEW: after "show my farm summary", follow-ups like
            # U: "now tell this in detail" mean expand the whole account
            # U: summary into farm-wise and flock-wise detail, not "this flock".
            return self._intent(
                "multi_farm_report",
                source="rule_summary_detail_followup",
            )
        field_lookup = self._field_lookup(query)
        if field_lookup:
            # U: NEW: deterministic metric catalog for direct record fields.
            # U: This handles questions such as "species in flock 1" without
            # U: falling back to a broad flock-list answer.
            return self._intent(
                "field_lookup",
                entity_type=field_lookup["entity_type"],
                entity_reference=self._entity_reference_from_text(query, "current"),
                source="rule_field_lookup",
                raw=field_lookup,
            )
        context_entity_type = self._contextual_entity_type(query, history)
        context_reference = self._entity_reference_from_text(query, "current")
        if self._is_complete_data_query(query):
            # U: OLD: broad "show all my data" wording collapsed into one account summary.
            # U: NEW: route it to the safe multi-report path so farmers get account totals
            # U: plus farm/flock-wise details from fixed backend queries.
            return self._intent(
                "multi_farm_report",
                entity_type=context_entity_type,
                entity_reference=context_reference,
                source="rule_complete_data",
            )
        if self._is_multi_query(query):
            return self._intent(
                "multi_farm_report",
                entity_type=context_entity_type,
                entity_reference=context_reference,
                source="rule_multi",
            )

        early_entity_type = context_entity_type
        early_reference = context_reference
        if self._is_count_query(query) and early_entity_type == "farm":
            return self._intent("count_farms", entity_type="farm", source="rule_core")
        if self._is_count_query(query) and early_entity_type == "flock":
            return self._intent("count_flocks", entity_type="flock", source="rule_core")
        if self._is_best_flock_query(query):
            # U: NEW: do not let "which flock is best" fall through to the
            # U: broad "list flocks" shortcut.
            return self._intent(
                "best_flock_report",
                entity_type="flock",
                entity_reference=early_reference,
                source="rule_core",
            )
        if self._is_broad_list_query(query, "farm"):
            return self._intent("list_farms", entity_type="farm", source="rule_core")
        if self._is_broad_list_query(query, "flock"):
            return self._intent("list_flocks", entity_type="flock", source="rule_core")
        if self._is_summary_query(query) and not early_reference:
            # U: OLD: Groq could classify "show my farm summary" as one farm's
            # U: details, especially after farm names existed in history.
            # U: NEW: core account summary/list/count intents are deterministic.
            return self._intent("farm_summary", source="rule_core")

        provider = os.getenv("AIBOT_INTENT_PROVIDER", "auto").strip().lower()
        if provider in {"off", "false", "rule", "rules", "deterministic"}:
            return self._rule_classify(question, history=history, source="rule")

        if self.client.has_keys and hasattr(self.user, "_meta"):
            try:
                return self._groq_classify(question, history=history)
            except (GroqAllKeysFailed, KeyError, ValueError, httpx.HTTPError):
                logger.warning(
                    "Groq intent classification failed; using rule classifier.",
                    exc_info=True,
                )

        return self._rule_classify(question, history=history, source="rule_fallback")

    def _groq_classify(self, question: str, history: list | None) -> ChikoozaIntent:
        result = self.client.chat(
            self._messages(question, history),
            model=os.getenv("AIBOT_INTENT_MODEL", "llama-3.1-8b-instant"),
            fallback_model=os.getenv(
                "AIBOT_INTENT_FALLBACK_MODEL", "llama-3.1-8b-instant"
            ),
            temperature=0,
            max_tokens=350,
            timeout=float(os.getenv("AIBOT_INTENT_TIMEOUT", "20")),
        )
        payload = self._parse_json(result.content)
        intent = self._validated_intent(payload, source="groq_intent")
        return self._repair_contextual_intent(intent, self._normalize(question), history)

    def _messages(self, question: str, history: list | None) -> list[dict[str, str]]:
        owned_context = self._owned_context()
        prompt = f"""
Classify the farmer's message into one JSON intent. Do not write SQL.

Allowed intents:
{", ".join(sorted(ALLOWED_INTENTS))}

JSON shape:
{{
  "intent": "one_allowed_intent",
  "entity_type": "farm|flock|",
  "entity_reference": "exact name, first, second, that, same, other, or empty",
  "scope": "current|other|all",
  "confidence": 0.0
}}

Rules:
- Use only the owned farms/flocks listed below for entity names.
- If the farmer says "it", "that", "same one", or "last one", infer from recent conversation.
- If the farmer says "details about 2", "2nd one", or another numbered follow-up
  after a numbered farm/flock list, infer the matching farm/flock from recent conversation.
- If the farmer asks for "flocks for 2nd one" after a farm list, the "2nd one" is
  the farm being filtered, not the flock.
- If the farmer asks "other", "more", "remaining", "anything else", use intent "other_entity".
- Count questions like "how many flocks" use count_flocks/count_farms.
- Detail questions like "what data does it have" use flock_details or farm_details based on context.
- Sales/revenue/income/sold use sales_total.
- Purchases/expenses/spent use purchase_total.
- Profit/loss/net/earning use profit_loss.
- Deaths/mortality/died use mortality.
- Feed use feed_consumed. Weight use average_weight. FCR/feed conversion use average_fcr.
- If the farmer asks for multiple categories/metrics in one message, such as
  counts plus sales plus farm/flock-wise details, use multi_farm_report.
- Compare/versus questions such as this month vs last month use comparison_report.
- Trend/increasing/decreasing questions use trend_report.
- Best/worst/top flock performance questions use best_flock_report.
- Progress, performance, health, advice, "how am I doing", "is this good",
  "what should I improve", or similar farm-record interpretation uses farm_progress_insight.
- "Who are you", "what can you do", "help", or usage questions use capability_help.
- If not related to farm records, use unsupported.

Owned context:
{owned_context}

Recent conversation:
{self._history_text(history or []) or "No previous conversation."}

Current farmer message:
{question}

Return JSON only.
""".strip()
        return [
            {
                "role": "system",
                "content": "You classify Chikooza Farmer AI questions into safe JSON intents only.",
            },
            {"role": "user", "content": prompt},
        ]

    def _parse_json(self, content: str) -> dict:
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        return json.loads(cleaned)

    def _validated_intent(self, payload: dict, source: str) -> ChikoozaIntent:
        intent = str(payload.get("intent") or "unsupported").strip().lower()
        entity_type = str(payload.get("entity_type") or "").strip().lower()
        entity_reference = str(payload.get("entity_reference") or "").strip()
        scope = str(payload.get("scope") or "current").strip().lower()

        if intent not in ALLOWED_INTENTS:
            intent = "unsupported"
        if entity_type not in ALLOWED_ENTITY_TYPES:
            entity_type = ""
        if scope not in {"current", "other", "all"}:
            scope = "current"

        try:
            confidence = float(payload.get("confidence") or 0)
        except (TypeError, ValueError):
            confidence = 0.0

        return ChikoozaIntent(
            intent=intent,
            entity_type=entity_type,
            entity_reference=entity_reference,
            scope=scope,
            confidence=max(0.0, min(confidence, 1.0)),
            source=source,
            raw=payload,
        )

    def _repair_contextual_intent(
        self, intent: ChikoozaIntent, query: str, history: list | None
    ) -> ChikoozaIntent:
        context_type = self._contextual_entity_type(query, history)
        context_reference = self._entity_reference_from_text(query, intent.scope)
        has_followup_reference = (
            self._has_bare_ordinal_reference(query)
            or self._has_pronoun_reference(query)
            or self._looks_like_other_query(query)
        )

        entity_type = intent.entity_type
        entity_reference = intent.entity_reference
        repaired_intent = intent.intent

        # U: NEW: Groq may classify "show flocks for 2nd one" as a flock
        # U: reference because "flocks" appears in the sentence. If recent
        # U: context was a farm list, the ordinal belongs to the farm filter.
        if context_type and (not entity_type or has_followup_reference):
            entity_type = context_type
        if context_reference and (not entity_reference or has_followup_reference):
            entity_reference = context_reference

        if repaired_intent == "unsupported" and entity_type in {"farm", "flock"}:
            if self._is_detail_query(query):
                repaired_intent = f"{entity_type}_details"
            elif self._looks_like_list_query(query) and entity_type == "farm":
                repaired_intent = (
                    "list_flocks"
                    if re.search(r"\b(?:flocks?|batches?)\b", query)
                    else "list_farms"
                )

        if (
            repaired_intent == intent.intent
            and entity_type == intent.entity_type
            and entity_reference == intent.entity_reference
        ):
            return intent

        return ChikoozaIntent(
            intent=repaired_intent,
            entity_type=entity_type,
            entity_reference=entity_reference,
            scope=intent.scope,
            confidence=intent.confidence,
            source=f"{intent.source}_context_repaired",
            raw=intent.raw,
        )

    def _rule_classify(
        self, question: str, *, history: list | None = None, source: str
    ) -> ChikoozaIntent:
        query = self._normalize(question)
        entity_type = self._contextual_entity_type(query, history)
        if not entity_type and (
            self._looks_like_other_query(query)
            or self._has_pronoun_reference(query)
            or self._has_bare_ordinal_reference(query)
        ):
            # U: NEW: metric follow-ups such as "sales for that one" and
            # U: "profit for last one" reuse the recent farm/flock context too.
            entity_type = self._latest_entity_type_from_history(history) or ""
        scope = "other" if self._looks_like_other_query(query) else "current"
        entity_reference = self._entity_reference_from_text(query, scope)

        if self._is_greeting(query):
            return self._intent("greeting", source=source)
        if self._is_capability_query(query):
            return self._intent("capability_help", source=source)
        if self._is_complete_data_query(query):
            return self._intent(
                "multi_farm_report",
                entity_type=entity_type,
                entity_reference=entity_reference,
                source=source,
            )
        if self._looks_like_other_query(query):
            return self._intent(
                "other_entity",
                entity_type=entity_type,
                entity_reference=entity_reference,
                scope="other",
                source=source,
            )
        if self._is_multi_query(query):
            return self._intent(
                "multi_farm_report",
                entity_type=entity_type,
                entity_reference=entity_reference,
                source=source,
            )
        if self._is_best_flock_query(query):
            return self._intent(
                "best_flock_report",
                entity_type="flock",
                entity_reference=entity_reference,
                source=source,
            )
        if self._is_comparison_query(query):
            return self._intent(
                "comparison_report",
                entity_type=entity_type,
                entity_reference=entity_reference,
                source=source,
            )
        if self._is_trend_query(query):
            return self._intent(
                "trend_report",
                entity_type=entity_type,
                entity_reference=entity_reference,
                source=source,
            )
        if self._is_insight_query(query):
            return self._intent(
                "farm_progress_insight",
                entity_type=entity_type,
                entity_reference=entity_reference,
                source=source,
            )
        if self._is_summary_query(query):
            return self._intent(
                "farm_summary",
                entity_type=entity_type,
                entity_reference=entity_reference,
                source=source,
            )
        if self._is_count_query(query) and entity_type == "flock":
            return self._intent("count_flocks", entity_type="flock", source=source)
        if self._is_count_query(query) and entity_type == "farm":
            return self._intent("count_farms", entity_type="farm", source=source)
        if self._is_detail_query(query) and entity_type == "flock":
            return self._intent(
                "flock_details",
                entity_type="flock",
                entity_reference=entity_reference,
                source=source,
            )
        if self._is_detail_query(query) and entity_type == "farm":
            return self._intent(
                "farm_details",
                entity_type="farm",
                entity_reference=entity_reference,
                source=source,
            )
        if any(word in query for word in ("profit", "loss", "net", "earning")):
            return self._intent(
                "profit_loss",
                entity_type=entity_type,
                entity_reference=entity_reference,
                source=source,
            )
        if any(
            word in query for word in ("sale", "sales", "revenue", "income", "sold")
        ):
            return self._intent(
                "sales_total",
                entity_type=entity_type,
                entity_reference=entity_reference,
                source=source,
            )
        if any(
            word in query
            for word in (
                "purchase",
                "purchases",
                "expense",
                "expenses",
                "spent",
                "spend",
                "cost",
                "costs",
            )
        ):
            return self._intent(
                "purchase_total",
                entity_type=entity_type,
                entity_reference=entity_reference,
                source=source,
            )
        if any(
            word in query for word in ("mortality", "death", "deaths", "died", "dead")
        ):
            return self._intent(
                "mortality",
                entity_type=entity_type,
                entity_reference=entity_reference,
                source=source,
            )
        if "feed" in query and "conversion" not in query:
            return self._intent(
                "feed_consumed",
                entity_type=entity_type,
                entity_reference=entity_reference,
                source=source,
            )
        if "fcr" in query or "feed conversion" in query:
            return self._intent(
                "average_fcr",
                entity_type=entity_type,
                entity_reference=entity_reference,
                source=source,
            )
        if "weight" in query:
            return self._intent(
                "average_weight",
                entity_type=entity_type,
                entity_reference=entity_reference,
                source=source,
            )
        if re.search(r"\b(?:birds?|chickens?|chicks?)\b", query):
            return self._intent(
                "current_birds",
                entity_type=entity_type,
                entity_reference=entity_reference,
                source=source,
            )
        if self._looks_like_list_query(query) and entity_type == "flock":
            return self._intent("list_flocks", entity_type="flock", source=source)
        if self._looks_like_list_query(query) and entity_type == "farm":
            return self._intent("list_farms", entity_type="farm", source=source)

        return self._intent("unsupported", source=source)

    def _intent(
        self,
        intent: str,
        *,
        entity_type: str = "",
        entity_reference: str = "",
        scope: str = "current",
        source: str = "rule",
        raw: dict | None = None,
    ) -> ChikoozaIntent:
        return ChikoozaIntent(
            intent=intent,
            entity_type=entity_type,
            entity_reference=entity_reference,
            scope=scope,
            confidence=0.75 if source.startswith("rule") else 0.0,
            source=source,
            raw=raw or {},
        )

    def _owned_context(self) -> str:
        if not hasattr(self.user, "_meta"):
            return "Owned farms/flocks unavailable in this context."
        try:
            from farm.models import Farm
            from flocks.models import Flock

            # U: NEW: prompt numbering must match the safe executor's displayed
            # U: farm/flock ordering so "2nd one" means the same row everywhere.
            farms = Farm.objects.filter(user_id=self.user.id).order_by("name", "id")[:50]
            flocks = (
                Flock.objects.filter(user_id=self.user.id)
                .select_related("farm")
                .order_by("farm__name", "name", "id")[:80]
            )
            farm_text = "; ".join(
                f"{index}. {farm.name}" for index, farm in enumerate(farms, start=1)
            )
            flock_text = "; ".join(
                f"{index}. {flock.name} (farm: {flock.farm.name})"
                for index, flock in enumerate(flocks, start=1)
            )
            return f"Farms: {farm_text or 'none'}.\n" f"Flocks: {flock_text or 'none'}."
        except Exception:
            logger.warning("Could not build owned context for intent classifier.")
            return "Owned farms/flocks unavailable."

    def _history_text(self, history: list[dict]) -> str:
        parts = []
        for item in history[-12:]:
            role = item.get("role", "user")
            content = str(item.get("content", "")).strip()
            if content:
                parts.append(f"{role.title()}: {content}")
        return "\n".join(parts)

    def _normalize(self, question: str) -> str:
        return re.sub(r"\s+", " ", (question or "").lower()).strip()

    def _is_greeting(self, query: str) -> bool:
        return bool(re.match(r"^(hi|hello|hey|namaste|hii|helo)(?:[!. ]+.*)?$", query))

    def _looks_like_other_query(self, query: str) -> bool:
        return bool(
            re.search(
                r"\b(?:other|another|any other|more|any more|remaining|rest|left|else|baki|baaki)\b",
                query,
            )
        )

    def _is_summary_query(self, query: str) -> bool:
        return any(
            phrase in query
            for phrase in (
                "summary",
                "overview",
                "all data",
                "all the data",
                "my data",
                "my records",
                "total things",
                "what all i have",
                "what do i have",
            )
        )

    def _is_complete_data_query(self, query: str) -> bool:
        """
        U: Treat farmer wording that asks for complete records as a report request,
        U: not a single summary metric. Keep plain "summary"/"overview" separate.
        """
        if not query:
            return False
        explicit_phrases = (
            "everything",
            "all data",
            "all the data",
            "all my data",
            "my all data",
            "total data",
            "full data",
            "complete data",
            "all records",
            "all my records",
            "complete records",
            "all details",
            "all information",
            "all their stuff",
            "all the stuff",
            "all stuff",
            "all things",
            "all my stuff",
            "complete report",
            "full report",
        )
        if any(phrase in query for phrase in explicit_phrases):
            return True
        if re.search(
            r"\b(?:show|give|tell|display|list)\s+"
            r"(?:me\s+)?(?:my\s+|our\s+)?(?:all|complete|full)\s+"
            r"(?:my\s+|our\s+)?(?:farms?|flocks?|batches?)\s+"
            r"(?:data|records|details|information|stuff|things)\b",
            query,
        ):
            return True
        return bool(
            re.search(
                r"\b(?:show|give|tell|display|list)\s+"
                r"(?:me\s+)?(?:my\s+|our\s+)?(?:all|complete|full)\s+"
                r"(?:the\s+)?(?:data|records|details|information|stuff|things)\b",
                query,
            )
        )

    def _field_lookup(self, query: str) -> dict | None:
        flock_fields = (
            (
                r"\b(?:species|breed|strain|bird type|chick type|chicken type)\b",
                "breed_name",
                "Breed/species",
            ),
            (r"\b(?:hatch date|hatching date|hatched)\b", "hatch_date", "Hatch date"),
            (r"\b(?:flock size|batch size|initial birds?)\b", "flock_size", "Flock size"),
            (r"\b(?:actual birds?|started birds?)\b", "actual_birds", "Actual birds"),
        )
        for pattern, field, label in flock_fields:
            if re.search(pattern, query):
                return {
                    "entity_type": "flock",
                    "field": field,
                    "field_label": label,
                }

        farm_fields = (
            (r"\b(?:location|city|village|address|place)\b", "location", "Location"),
            (r"\b(?:sheds?|shed count|number of sheds)\b", "shed_count", "Sheds"),
            (r"\b(?:pin|pincode|postal code)\b", "farm_pin", "Pincode"),
            (r"\b(?:status|active|inactive)\b", "farm_status", "Status"),
        )
        for pattern, field, label in farm_fields:
            if re.search(pattern, query) and re.search(r"\bfarm\b", query):
                return {
                    "entity_type": "farm",
                    "field": field,
                    "field_label": label,
                }
        return None

    def _is_capability_query(self, query: str) -> bool:
        return bool(
            re.search(
                r"\b(?:who are you|what can you do|how can you help|help me|help|"
                r"what should i ask|how to use|what do you do)\b",
                query,
            )
        )

    def _is_multi_query(self, query: str) -> bool:
        if not query:
            return False

        task_hits = 0
        if self._is_count_query(query) and re.search(r"\bfarms?\b", query):
            task_hits += 1
        if self._is_count_query(query) and re.search(
            r"\b(?:flocks?|batches?)\b", query
        ):
            task_hits += 1

        task_patterns = (
            r"\b(?:sale|sales|revenue|income|sold)\b",
            r"\b(?:purchase|purchases|expense|expenses|spent|spend|costs?)\b",
            r"\b(?:profit|loss|net|earning|earnings)\b",
            r"\b(?:current birds?|birds? left|bird count)\b",
            r"\b(?:mortality|deaths?|died|dead birds?)\b",
            r"\bfeed\b",
            r"\b(?:weight|body weight)\b",
            r"\b(?:fcr|feed conversion)\b",
        )
        task_hits += sum(1 for pattern in task_patterns if re.search(pattern, query))

        breakdown_hint = bool(
            re.search(
                r"\b(?:inside each|inside every|each of the|every farm|every flock|"
                r"individually|individual|farm-wise|flock-wise|per farm|per flock|"
                r"all their stuff|all details|complete report|full report)\b",
                query,
            )
        )
        connector_hint = bool(
            re.search(r"\b(?:and|also|then|plus|along with)\b|,", query)
        )
        has_multiple_entities = bool(re.search(r"\bfarms?\b", query)) and bool(
            re.search(r"\b(?:flocks?|batches?)\b", query)
        )

        return task_hits >= 2 and (
            connector_hint or breakdown_hint or has_multiple_entities
        )

    def _is_insight_query(self, query: str) -> bool:
        insight_patterns = (
            r"\b(?:progress|progressing|performance|performing|doing|improve|"
            r"improvement|advice|advise|suggest|recommend|recommendation|"
            r"analyse|analyze|analysis|insight|insights|assess|evaluate|"
            r"review|risk|risks|problem|problems|issue|issues|healthy|health)\b",
            r"\b(?:good|bad|better|worse|okay|ok)\b.*\b(?:farm|flock|batch|birds?|it|this|that)\b",
            r"\b(?:farm|flock|batch|birds?|it|this|that)\b.*\b(?:good|bad|better|worse|okay|ok)\b",
            r"\bhow\s+(?:am i|are we|is my|is this|is that|is it)\b",
            r"\bwhat\s+do\s+you\s+think\b",
            r"\bwhat\s+should\s+i\b",
            r"\b(?:what next|now what|next steps?|what to do next|tell me what to do)\b",
            r"\b(?:explain|understand)\s+(?:this|that|it)\b",
            r"\b(?:is this enough|is that enough|is it enough)\b",
            r"\bwhat\s+is\s+wrong\b",
            r"\banything\s+(?:wrong|bad|to improve)\b",
        )
        return any(re.search(pattern, query) for pattern in insight_patterns)

    def _is_comparison_query(self, query: str) -> bool:
        return bool(
            re.search(
                r"\b(?:compare|comparison|versus|vs\.?|against|better than|worse than)\b",
                query,
            )
        )

    def _is_trend_query(self, query: str) -> bool:
        return bool(
            re.search(
                r"\b(?:trend|trends|increasing|decreasing|increase|decrease|rising|falling|going up|going down)\b",
                query,
            )
        )

    def _is_best_flock_query(self, query: str) -> bool:
        return bool(
            re.search(
                r"\b(?:best|top|worst|lowest|highest)\b.*\b(?:flock|flocks|batch|batches|performance|performing)\b"
                r"|\b(?:which|what)\s+(?:flock|batch)\b.*\b(?:best|top|worst|perform)\b",
                query,
            )
        )

    def _is_count_query(self, query: str) -> bool:
        return any(
            phrase in query
            for phrase in ("how many", "number of", "total number", "count", "no of")
        )

    def _is_detail_query(self, query: str) -> bool:
        return bool(
            re.search(
                r"\b(?:data|details?|info|information|records?|show|tell|give|about|have)\b",
                query,
            )
        )

    def _is_account_summary_detail_followup(
        self, query: str, history: list | None
    ) -> bool:
        if not history:
            return False
        if not re.search(
            r"\b(?:detail|details|detailed|in detail|more detail|full detail|expand|explain this|tell this)\b",
            query,
        ):
            return False
        if re.search(r"\b(?:farm|flock|batch)\b", query):
            return False

        for item in reversed(history[-12:]):
            metric = str(item.get("metric", "")).strip().lower()
            intent = str(item.get("intent", "")).strip().lower()
            content = self._normalize(str(item.get("content", "")))
            if metric in {"farm_record_summary", "multi_farm_report"}:
                return True
            if intent in {"farm_summary", "multi_farm_report"}:
                return True
            if "your account summary" in content:
                return True
            if "combined report from your chikooza records" in content:
                return True
        return False

    def _looks_like_list_query(self, query: str) -> bool:
        return any(
            word in query
            for word in ("list", "show", "display", "which", "what", "all", "details")
        )

    def _is_broad_list_query(self, query: str, label: str) -> bool:
        entity_pattern = r"\b(?:flocks?|batches?)\b" if label == "flock" else r"\bfarms?\b"
        if not re.search(entity_pattern, query):
            return False
        if self._entity_reference_from_text(query, "current"):
            return False
        if re.search(r"\b(?:summary|overview)\b", query):
            return False
        return bool(
            re.search(
                r"\b(?:list|display|which)\b.*\b(?:all|my|our)?\b",
                query,
            )
            or re.search(r"\b(?:show|give|tell|what)\b.*\b(?:all|every)\b", query)
            or re.search(r"\b(?:show|give|tell|what)\b.*\b(?:my|our)\s+(?:farms?|flocks?|batches?)\b", query)
            or re.search(r"\b(?:what|which)\s+(?:farms?|flocks?|batches?)\b", query)
            or re.search(r"\b(?:all|every)\b.*\b(?:farms?|flocks?|batches?)\b", query)
        )

    def _entity_type_from_text(self, query: str) -> str:
        if re.search(r"\b(?:flocks?|batches?)\b", query):
            return "flock"
        if re.search(r"\bfarms?\b", query):
            return "farm"
        return ""

    def _contextual_entity_type(self, query: str, history: list | None) -> str:
        explicit_type = self._entity_type_from_text(query)
        latest_type = self._latest_entity_type_from_history(history)

        # U: NEW: "show flocks for 2nd one" after a farm list means "second
        # U: farm", even though the word "flocks" appears in the query.
        if (
            latest_type == "farm"
            and explicit_type == "flock"
            and self._has_bare_ordinal_reference(query)
            and re.search(r"\b(?:for|of|inside|in|under|from)\b", query)
        ):
            return "farm"

        if explicit_type:
            return explicit_type

        if latest_type and (
            self._has_pronoun_reference(query)
            or self._has_bare_ordinal_reference(query)
            or self._is_detail_query(query)
        ):
            return latest_type

        return ""

    def _entity_reference_from_text(self, query: str, scope: str) -> str:
        if scope == "other":
            return "other"
        bare_ordinal = self._bare_ordinal_reference(query)
        if bare_ordinal:
            return bare_ordinal
        reference_patterns = (
            ("last one", r"\blast\s+one\b"),
            ("same one", r"\bsame\s+one\b"),
            ("that one", r"\bthat\s+one\b"),
            ("this one", r"\bthis\s+one\b"),
            ("last", r"\blast\s+(?:farm|flock|batch)\b"),
            ("same", r"\bsame\s+(?:farm|flock|batch)\b"),
            ("that", r"\bthat\s+(?:farm|flock|batch)\b"),
            ("this", r"\bthis\s+(?:farm|flock|batch)\b"),
            ("it", r"\bit\b"),
            (
                "first",
                r"\b(?:(?:first|1st)\s+(?:farm|flock|batch|one)|(?:farm|flock|batch)\s+(?:first|1st))\b",
            ),
            (
                "second",
                r"\b(?:(?:second|2nd)\s+(?:farm|flock|batch|one)|(?:farm|flock|batch)\s+(?:second|2nd))\b",
            ),
            (
                "third",
                r"\b(?:(?:third|3rd)\s+(?:farm|flock|batch|one)|(?:farm|flock|batch)\s+(?:third|3rd))\b",
            ),
            (
                "fourth",
                r"\b(?:(?:fourth|4th)\s+(?:farm|flock|batch|one)|(?:farm|flock|batch)\s+(?:fourth|4th))\b",
            ),
            (
                "fifth",
                r"\b(?:(?:fifth|5th)\s+(?:farm|flock|batch|one)|(?:farm|flock|batch)\s+(?:fifth|5th))\b",
            ),
        )
        for phrase, pattern in reference_patterns:
            if re.search(pattern, query):
                return phrase
        return ""

    def _bare_ordinal_reference(self, query: str) -> str:
        ordinals = (
            ("first", 1, "1st"),
            ("second", 2, "2nd"),
            ("third", 3, "3rd"),
            ("fourth", 4, "4th"),
            ("fifth", 5, "5th"),
        )
        for word, number, suffix in ordinals:
            if re.search(rf"\b(?:{word}|{suffix})\s+one\b", query):
                return word
            if re.search(rf"\b(?:number|no\.?|#)\s*{number}\b", query):
                return word
            if re.search(
                rf"\b(?:details?\s+about|about|data\s+for|show|tell|give|for|of|inside|in|under|from)\s+"
                rf"(?:the\s+)?(?:number\s+|no\.?\s*)?{number}(?:st|nd|rd|th)?(?:\s+one)?\b",
                query,
            ):
                return word
        return ""

    def _has_bare_ordinal_reference(self, query: str) -> bool:
        return bool(self._bare_ordinal_reference(query))

    def _has_pronoun_reference(self, query: str) -> bool:
        return bool(
            re.search(
                r"\b(?:it|that|this|same one|that one|this one|last one|one)\b",
                query,
            )
        )

    def _latest_entity_type_from_history(self, history: list | None) -> str | None:
        if not history:
            return None
        for item in reversed(history[-12:]):
            metadata_type = str(item.get("intent_entity_type", "")).strip().lower()
            if metadata_type in {"farm", "flock"}:
                return metadata_type
            content = self._normalize(str(item.get("content", "")))
            if re.search(
                r"\byour\s+flocks?\b|\bflock count\b|\b(?:flocks?|batches?)\b", content
            ):
                return "flock"
            if re.search(
                r"\byour\s+farms?\b|\bfarm count\b|\bfarms?\b(?!\s*:)", content
            ):
                return "farm"
        return None
