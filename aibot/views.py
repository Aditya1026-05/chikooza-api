# views.py
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import viewsets, status
from oauth2_provider.contrib.rest_framework import OAuth2Authentication

# U: OLD: from .services import SQLAgentService, AISQLService
# U: NEW: keep legacy services in aibot/services.py, but do not import them into
# U: the active endpoint because that unnecessarily loads the old LangChain stack.
# from .services import SQLAgentService, AISQLService
from .modern_services import ChikoozaModernAgentService
from .preprocessing import QueryPreprocessor
from .log_utils import ChatLogHandler
from .models import AIChatLog
import logging
import json
import os
import uuid
from django.core.serializers.json import DjangoJSONEncoder

logger = logging.getLogger(__name__)


class AIChatViewSet(viewsets.ViewSet):
    authentication_classes = [OAuth2Authentication]
    permission_classes = [IsAuthenticated]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.preprocessor = QueryPreprocessor()
        self.log_handler = ChatLogHandler()

    def create(self, request):
        """Handle natural language queries"""
        try:
            raw_query = request.data.get("query", "").strip()
            if not raw_query:
                return Response(
                    {"error": "Query is required"}, status=status.HTTP_400_BAD_REQUEST
                )

            try:
                query = self.preprocessor.preprocess(raw_query)
            except ValueError as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

            query_id = str(uuid.uuid4())
            request.chat_data = {
                "user_id": request.user.id,
                "raw_query": raw_query,
                "cleaned_query": query,
                "query_id": query_id,
            }

            # U: OLD services kept for reference/rollback:
            # service = SQLAgentService(user=request.user)
            # service = AISQLService(user=request.user)
            # U: NEW service ports the cloned BizBot routing/isolation approach
            # U: into Chikooza and uses request.user as the only tenant source.
            service = ChikoozaModernAgentService(user=request.user)
            history = self._recent_history(request.user)
            result = service.query(query, history=history)

            self._log_interaction(request, result)
            self._save_to_db(request, result)

            if result["status"] == "error":
                return Response(
                    {
                        "error": result["message"],
                        "details": result.get("details"),
                        "suggestion": result.get("suggestion"),
                        "route": result.get("route"),
                        "query_id": query_id,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            return Response(
                {
                    "status": "success",
                    "data": result["data"],
                    "answer": result.get("answer", result.get("message")),
                    "route": result.get("route"),
                    "rows": result.get("rows"),
                    "query": result.get("query"),
                    "query_id": query_id,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.exception("Unexpected Farmer AI error")
            return Response(
                {"error": "Processing failed"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _log_interaction(self, request, result):
        log_data = {
            "user_id": request.user.id,
            "query": request.chat_data["cleaned_query"],
            "response": json.dumps(result, cls=DjangoJSONEncoder),
            "status": result["status"],
            "query_id": request.chat_data["query_id"],
        }
        self.log_handler.log_interaction(log_data)

    def _save_to_db(self, request, result):
        try:
            AIChatLog.objects.create(
                user=request.user,
                query=request.chat_data["cleaned_query"],
                response=json.dumps(result, cls=DjangoJSONEncoder),
                query_id=request.chat_data["query_id"],
            )
        except Exception as e:
            logger.error(f"Database save failed: {str(e)}")

    def _recent_history(self, user):
        # U: OLD: history only carried answer text, so a list containing several
        # U: flocks could be mistaken for one selected flock.
        # U: NEW: keep a bounded number of turns and include safe resolved ids so
        # U: follow-ups such as "same farm" and "last one" reuse explicit context.
        try:
            # U: NEW: keep exactly the last six chat turns by default.
            # U: One turn becomes one user message plus one assistant message,
            # U: so Farmer AI receives up to 12 recent messages as context.
            history_turns = int(os.getenv("AIBOT_HISTORY_TURNS", "6"))
        except ValueError:
            logger.warning("Invalid AIBOT_HISTORY_TURNS value; using 6 turns.")
            history_turns = 6
        history_turns = min(max(history_turns, 1), 6)
        logs = AIChatLog.objects.filter(user=user).order_by("-created_at")[
            :history_turns
        ]
        history = []
        for log in reversed(list(logs)):
            history.append({"role": "user", "content": log.query})
            parsed = self._parse_response(log.response)
            answer = (
                parsed.get("answer") or parsed.get("message") or parsed.get("error")
            )
            if answer:
                assistant_message = {"role": "assistant", "content": answer}
                for key in (
                    "resolved_farm_id",
                    "resolved_flock_id",
                    "intent_entity_type",
                    "intent_entity_reference",
                    "intent_scope",
                    "metric",
                ):
                    if parsed.get(key) is not None:
                        assistant_message[key] = parsed[key]
                history.append(assistant_message)
        return history

    def list(self, request):
        try:
            chat_logs = AIChatLog.objects.filter(user=request.user).order_by(
                "-created_at"
            )[:50]

            history = [
                {
                    "id": log.id,
                    "query": log.query,
                    "response": self._parse_response(log.response),
                    "created_at": log.created_at,
                    "query_id": log.query_id,
                }
                for log in chat_logs
            ]

            return Response({"history": history}, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"History retrieval failed: {str(e)}")
            return Response(
                {"error": "Failed to get history"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _parse_response(self, response_json):
        try:
            return json.loads(response_json)
        except:
            return {"status": "error", "message": "Invalid response format"}
