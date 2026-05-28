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
    "farm_progress_insight",
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
        return self._validated_intent(payload, source="groq_intent")

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
- If the farmer says "it", "that", "same one", infer from recent conversation.
- If the farmer asks "other", "more", "remaining", "anything else", use intent "other_entity".
- Count questions like "how many flocks" use count_flocks/count_farms.
- Detail questions like "what data does it have" use flock_details or farm_details based on context.
- Sales/revenue/income/sold use sales_total.
- Purchases/expenses/spent use purchase_total.
- Profit/loss/net/earning use profit_loss.
- Deaths/mortality/died use mortality.
- Feed use feed_consumed. Weight use average_weight. FCR/feed conversion use average_fcr.
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

    def _rule_classify(
        self, question: str, *, history: list | None = None, source: str
    ) -> ChikoozaIntent:
        query = self._normalize(question)
        entity_type = self._entity_type_from_text(query)
        if not entity_type and (
            self._looks_like_other_query(query)
            or (self._is_detail_query(query) and self._has_pronoun_reference(query))
            or (self._is_insight_query(query) and self._has_pronoun_reference(query))
        ):
            entity_type = self._latest_entity_type_from_history(history) or ""
        scope = "other" if self._looks_like_other_query(query) else "current"
        entity_reference = self._entity_reference_from_text(query, scope)

        if self._is_greeting(query):
            return self._intent("greeting", source=source)
        if self._is_capability_query(query):
            return self._intent("capability_help", source=source)
        if self._looks_like_other_query(query):
            return self._intent(
                "other_entity",
                entity_type=entity_type,
                entity_reference=entity_reference,
                scope="other",
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
        if "bird" in query:
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
    ) -> ChikoozaIntent:
        return ChikoozaIntent(
            intent=intent,
            entity_type=entity_type,
            entity_reference=entity_reference,
            scope=scope,
            confidence=0.75 if source.startswith("rule") else 0.0,
            source=source,
        )

    def _owned_context(self) -> str:
        if not hasattr(self.user, "_meta"):
            return "Owned farms/flocks unavailable in this context."
        try:
            from farm.models import Farm
            from flocks.models import Flock

            farms = Farm.objects.filter(user_id=self.user.id).order_by("id")[:50]
            flocks = (
                Flock.objects.filter(user_id=self.user.id)
                .select_related("farm")
                .order_by("id")[:80]
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
        return bool(re.match(r"^(hi|hello|hey|namaste|hii|helo)[!. ]*$", query))

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

    def _is_capability_query(self, query: str) -> bool:
        return bool(
            re.search(
                r"\b(?:who are you|what can you do|how can you help|help me|help|"
                r"what should i ask|how to use|what do you do)\b",
                query,
            )
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

    def _looks_like_list_query(self, query: str) -> bool:
        return any(
            word in query
            for word in ("list", "show", "display", "which", "what", "all", "details")
        )

    def _entity_type_from_text(self, query: str) -> str:
        if re.search(r"\b(?:flocks?|batches?)\b", query):
            return "flock"
        if re.search(r"\bfarms?\b", query):
            return "farm"
        return ""

    def _entity_reference_from_text(self, query: str, scope: str) -> str:
        if scope == "other":
            return "other"
        for phrase in ("same", "that", "this", "it", "first", "second", "third"):
            if re.search(rf"\b{phrase}\b", query):
                return phrase
        return ""

    def _has_pronoun_reference(self, query: str) -> bool:
        return bool(
            re.search(r"\b(?:it|that|this|same one|that one|this one|one)\b", query)
        )

    def _latest_entity_type_from_history(self, history: list | None) -> str | None:
        if not history:
            return None
        for item in reversed(history[-12:]):
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
