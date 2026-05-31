from dataclasses import dataclass

from .intent_classifier import ChikoozaIntent


@dataclass(frozen=True)
class ChikoozaEntityResolution:
    farm_id: int | None = None
    flock_id: int | None = None
    response: dict | None = None


class ChikoozaEntityResolver:
    """
    U: NEW: Professional Farmer AI stage 2.
    U: Resolve farms/flocks only from the authenticated farmer's own records.
    U: The LLM may identify "first flock" or "that batch", but this class is
    U: responsible for converting that intent into safe tenant-scoped ids.
    """

    def __init__(self, deterministic_service):
        self.deterministic_service = deterministic_service

    def resolve(
        self, intent: ChikoozaIntent, question: str, history: list | None = None
    ) -> ChikoozaEntityResolution:
        canonical_question = self._question_for_resolution(intent, question)
        resolution = self.deterministic_service.resolve_entity_filters(
            canonical_question,
            history=history,
        )
        return ChikoozaEntityResolution(
            farm_id=resolution.farm_id,
            flock_id=resolution.flock_id,
            response=resolution.missing_response,
        )

    def _question_for_resolution(self, intent: ChikoozaIntent, question: str) -> str:
        reference = (intent.entity_reference or "").strip()
        entity_type = intent.entity_type
        if not entity_type or not reference:
            return question

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
            return f"that {entity_type}"
        if reference in {"last", "last one"}:
            return f"last {entity_type}"
        if reference in {"first", "second", "third", "fourth", "fifth"}:
            return f"{reference} {entity_type}"
        if entity_type in {"farm", "flock"}:
            return f"{question} {reference}"
        return question
