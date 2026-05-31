import json
import logging
import os
from datetime import date, datetime
from decimal import Decimal

import httpx

from common.groq_client import GroqAllKeysFailed, GroqChatClient

logger = logging.getLogger(__name__)


class ChikoozaFarmInsightService:
    """
    U: NEW: Safe conversational insight layer for Farmer AI.
    U: Groq receives only tenant-scoped answers already produced by the backend,
    U: never raw SQL authority or another farmer's records.
    """

    SNAPSHOT_QUESTIONS = (
        ("summary", "show my farm summary"),
        ("farms", "list all farms i have"),
        ("flocks", "list all flocks i have"),
        ("sales", "total sales"),
        ("purchases", "total purchases"),
        ("profit", "profit or loss"),
        ("current_birds", "current birds"),
        ("mortality", "mortality"),
        ("feed", "feed consumed"),
        ("weight", "average weight"),
        ("fcr", "average fcr"),
    )

    TARGET_METRICS = (
        ("details", "show data for {target}"),
        ("sales", "total sales for {target}"),
        ("purchases", "total purchases for {target}"),
        ("profit", "profit or loss for {target}"),
        ("current_birds", "current birds for {target}"),
        ("mortality", "mortality for {target}"),
        ("feed", "feed consumed for {target}"),
        ("weight", "average weight for {target}"),
        ("fcr", "average fcr for {target}"),
    )

    def __init__(
        self,
        user,
        *,
        deterministic_service,
        groq_client: GroqChatClient | None = None,
    ):
        self.user = user
        self.deterministic_service = deterministic_service
        self.client = groq_client or GroqChatClient(
            model=os.getenv("AIBOT_INSIGHT_MODEL", "llama-3.1-8b-instant"),
            fallback_model=os.getenv(
                "AIBOT_INSIGHT_FALLBACK_MODEL", "llama-3.1-8b-instant"
            ),
            timeout=float(os.getenv("AIBOT_INSIGHT_TIMEOUT", "25")),
        )

    def answer(self, question: str, history: list | None = None, intent=None) -> dict:
        snapshot = self._build_snapshot(question, history=history, intent=intent)
        answer = self._fallback_answer(snapshot)
        engine = "safe_insight_fallback"

        provider = os.getenv("AIBOT_INSIGHT_PROVIDER", "auto").strip().lower()
        if (
            provider not in {"off", "false", "rule", "rules", "deterministic"}
            and self.client.has_keys
            and hasattr(self.user, "_meta")
        ):
            try:
                answer = self._groq_answer(question, history=history, snapshot=snapshot)
                engine = "safe_insight_groq"
            except (GroqAllKeysFailed, KeyError, ValueError, httpx.HTTPError):
                logger.warning(
                    "Groq insight answer failed; using deterministic fallback.",
                    exc_info=True,
                )

        return {
            "status": "success",
            "data": snapshot,
            "answer": answer,
            "message": answer,
            "rows": [snapshot],
            "query": None,
            "params": [],
            "route": "TEXT_TO_SQL",
            "metric": "farm_progress_insight",
            "engine": engine,
        }

    def capability_answer(self) -> dict:
        answer = (
            "I am Chikooza Farmer AI. I can explain your own farm records, compare farms or flocks, "
            "summarize sales, purchases, profit/loss, current birds, mortality, feed, weight, and FCR, "
            "and tell you what data is missing before I can judge performance properly."
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
            "metric": "capability_help",
            "engine": "safe_static",
        }

    def _build_snapshot(
        self, question: str, *, history: list | None = None, intent=None
    ) -> dict:
        snapshot = {
            "scope": "account",
            "question": question,
            "account": {},
            "target": {},
        }

        for key, safe_question in self.SNAPSHOT_QUESTIONS:
            snapshot["account"][key] = self._safe_response(safe_question, history)

        target = self._target_phrase(intent)
        if target:
            snapshot["scope"] = target
            for key, template in self.TARGET_METRICS:
                snapshot["target"][key] = self._safe_response(
                    template.format(target=target),
                    history,
                )

        return snapshot

    def _safe_response(self, safe_question: str, history: list | None) -> dict:
        response = self.deterministic_service.answer(safe_question, history=history)
        rows = response.get("rows") or []
        return {
            "question": safe_question,
            "metric": response.get("metric"),
            "answer": response.get("answer") or response.get("message"),
            "data": self._json_safe(response.get("data")),
            "rows": self._json_safe(rows[:10] if isinstance(rows, list) else rows),
            "status": response.get("status"),
        }

    def _groq_answer(
        self, question: str, *, history: list | None, snapshot: dict
    ) -> str:
        result = self.client.chat(
            self._messages(question, history=history, snapshot=snapshot),
            model=os.getenv("AIBOT_INSIGHT_MODEL", "llama-3.1-8b-instant"),
            fallback_model=os.getenv(
                "AIBOT_INSIGHT_FALLBACK_MODEL", "llama-3.1-8b-instant"
            ),
            temperature=float(os.getenv("AIBOT_INSIGHT_TEMPERATURE", "0.2")),
            max_tokens=int(os.getenv("AIBOT_INSIGHT_MAX_TOKENS", "650")),
            timeout=float(os.getenv("AIBOT_INSIGHT_TIMEOUT", "25")),
        )
        return result.content.strip()

    def _messages(
        self, question: str, *, history: list | None, snapshot: dict
    ) -> list[dict[str, str]]:
        prompt = f"""
You are Chikooza Farmer AI. Answer like a practical farm assistant.

Rules:
- Use only the safe tenant-scoped snapshot below.
- Do not invent records, totals, dates, or benchmarks that are not in the snapshot.
- If data is too thin to judge progress, say that clearly and explain what to record next.
- Be conversational, but stay focused on Chikooza farm records.
- Do not mention SQL, database tables, prompts, tenant isolation, or implementation details.
- Keep the answer short: 2 to 5 concise paragraphs or bullets.

Recent conversation:
{self._history_text(history or []) or "No previous conversation."}

Safe farm snapshot:
{json.dumps(snapshot, ensure_ascii=True)}

Farmer message:
{question}
""".strip()
        return [
            {
                "role": "system",
                "content": "You turn safe Chikooza farm metrics into clear farmer-facing advice.",
            },
            {"role": "user", "content": prompt},
        ]

    def _fallback_answer(self, snapshot: dict) -> str:
        account = snapshot.get("account", {})
        summary_answer = self._answer_text(account.get("summary"))
        profit_answer = self._answer_text(self._target_or_account(snapshot, "profit"))
        birds_answer = self._answer_text(
            self._target_or_account(snapshot, "current_birds")
        )
        feed_answer = self._answer_text(self._target_or_account(snapshot, "feed"))
        fcr_answer = self._answer_text(self._target_or_account(snapshot, "fcr"))
        mortality_answer = self._answer_text(
            self._target_or_account(snapshot, "mortality")
        )

        missing = []
        if self._looks_zero(birds_answer):
            missing.append("current bird count")
        if self._looks_zero(feed_answer):
            missing.append("feed consumed")
        if self._looks_zero(fcr_answer):
            missing.append("FCR")
        if self._looks_zero(mortality_answer):
            missing.append("daily mortality")

        scope_text = "this farm/flock" if snapshot.get("target") else "your farm"
        lines = [
            f"Based on the records I can see, {summary_answer.lower() if summary_answer else 'your Chikooza account has limited recorded data.'}",
            f"For progress, the key signal right now is: {profit_answer or 'profit/loss is not available from the recorded sales and costs yet.'}",
        ]

        if missing:
            lines.append(
                f"I cannot judge {scope_text} performance confidently yet because these records are missing or still zero: "
                f"{', '.join(missing)}."
            )
        else:
            lines.append(
                f"The useful checks for {scope_text} are current birds, mortality trend, feed consumed, average weight, FCR, sales, purchases, and net profit/loss."
            )

        lines.append(
            "Add daily data, purchases, and sales consistently; then I can give a stronger progress review instead of only a partial snapshot."
        )
        return " ".join(lines)

    def _target_or_account(self, snapshot: dict, key: str):
        return (snapshot.get("target") or {}).get(key) or (
            snapshot.get("account") or {}
        ).get(key)

    def _answer_text(self, response: dict | None) -> str:
        return str((response or {}).get("answer") or "").strip()

    def _looks_zero(self, answer: str) -> bool:
        text = answer.lower()
        return any(
            phrase in text
            for phrase in (
                ": 0",
                "0.00",
                "0 kg",
                "0 birds",
                "current birds: 0",
                "average fcr: 0",
            )
        )

    def _target_phrase(self, intent) -> str:
        if not intent:
            return ""
        entity_type = getattr(intent, "entity_type", "") or ""
        reference = (getattr(intent, "entity_reference", "") or "").strip()
        if not entity_type:
            return ""
        if reference in {"", "current"}:
            return f"the {entity_type}"
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
        if reference == "other":
            return f"other {entity_type}"
        if reference in {"first", "second", "third", "fourth", "fifth"}:
            return f"{reference} {entity_type}"
        return f"{entity_type} {reference}"

    def _history_text(self, history: list[dict]) -> str:
        parts = []
        for item in history[-10:]:
            role = item.get("role", "user")
            content = str(item.get("content", "")).strip()
            if content:
                parts.append(f"{role.title()}: {content}")
        return "\n".join(parts)

    def _json_safe(self, value):
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, dict):
            return {key: self._json_safe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [self._json_safe(item) for item in value]
        return value
