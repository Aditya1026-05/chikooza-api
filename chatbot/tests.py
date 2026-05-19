import json
from types import SimpleNamespace
from unittest.mock import patch

from django.test import RequestFactory, TestCase

from .models import ChatLog
from .views import chat_api


class ChatApiValidationTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.anonymous_user = SimpleNamespace(is_authenticated=False)

    def test_rejects_invalid_json_without_loading_rag(self):
        request = self.factory.post(
            "/chat/",
            data="not-json",
            content_type="application/json",
        )
        request.user = self.anonymous_user

        with patch("chatbot.views.get_rag_service") as get_rag_service:
            response = chat_api(request)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content), {"error": "Invalid JSON body"})
        get_rag_service.assert_not_called()

    def test_rejects_empty_query_without_loading_rag(self):
        request = self.factory.post(
            "/chat/",
            data=json.dumps({"query": "  "}),
            content_type="application/json",
        )
        request.user = self.anonymous_user

        with patch("chatbot.views.get_rag_service") as get_rag_service:
            response = chat_api(request)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content), {"error": "Query is required"})
        get_rag_service.assert_not_called()

    def test_success_logs_chat_without_auth_user(self):
        rag = SimpleNamespace(
            ollama_model="test-ollama-model",
            query=lambda query, prompt_type: {
                "result": f"answer for {query}",
                "source_documents": [],
            },
        )
        request = self.factory.post(
            "/chat/",
            data=json.dumps({"query": "How to manage poultry feed?", "prompt_type": "qa"}),
            content_type="application/json",
        )
        request.user = self.anonymous_user
        request.query_id = "query-123"

        with patch("chatbot.views.get_rag_service", return_value=rag):
            response = chat_api(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(ChatLog.objects.count(), 1)
        self.assertEqual(request.chat_data["model"], "test-ollama-model")
        self.assertEqual(json.loads(response.content)["query_id"], "query-123")
