from .intent_classifier import ChikoozaIntent

# U: LEGACY / NOT LIVE: this formatter belongs to the old deterministic
# U: intent-agent path. It remains for tests/reference only.


class ChikoozaAnswerFormatter:
    """
    U: NEW: Professional Farmer AI stage 4.
    U: Keep final response shaping separate from intent and query execution.
    U: Current deterministic answers are already farmer-facing, so this class
    U: adds trace metadata and leaves wording unchanged.
    """

    def format(self, response: dict, intent: ChikoozaIntent) -> dict:
        response["intent"] = intent.intent
        response["intent_source"] = intent.source
        response["intent_entity_type"] = intent.entity_type
        response["intent_entity_reference"] = intent.entity_reference
        response["intent_scope"] = intent.scope
        return response
