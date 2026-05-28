import logging

from .answer_formatter import ChikoozaAnswerFormatter
from .entity_resolver import ChikoozaEntityResolver
from .intent_classifier import ChikoozaIntentClassifier
from .query_executor import ChikoozaSafeQueryExecutor

logger = logging.getLogger(__name__)


class ChikoozaIntentAgentService:
    """
    U: NEW: Professional Farmer AI orchestration:
    U: classify intent -> resolve owned farm/flock -> execute fixed safe query
    U: -> format response. Groq can classify language, but SQL remains backend-owned.
    """

    def __init__(
        self,
        user,
        *,
        deterministic_service,
        classifier: ChikoozaIntentClassifier | None = None,
        formatter: ChikoozaAnswerFormatter | None = None,
    ):
        self.user = user
        self.deterministic_service = deterministic_service
        self.classifier = classifier or ChikoozaIntentClassifier(user=user)
        self.entity_resolver = ChikoozaEntityResolver(deterministic_service)
        self.executor = ChikoozaSafeQueryExecutor(
            deterministic_service,
            self.entity_resolver,
        )
        self.formatter = formatter or ChikoozaAnswerFormatter()

    def answer(self, question: str, history: list | None = None) -> dict:
        intent = self.classifier.classify(question, history=history)
        response = self.executor.execute(intent, question, history=history)
        return self.formatter.format(response, intent)
