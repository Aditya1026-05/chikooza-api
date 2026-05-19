import json
from types import SimpleNamespace
from unittest.mock import patch

from django.test import RequestFactory, TestCase

from .models import ChatLog
from .public_assistant import PublicAssistantResponse, PublicSiteAssistant
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
            data=json.dumps(
                {"query": "How to manage poultry feed?", "prompt_type": "qa"}
            ),
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

    def test_public_site_mode_uses_public_assistant_without_loading_rag(self):
        assistant = SimpleNamespace(
            answer=lambda query: PublicAssistantResponse(
                result=f"site answer for {query}",
                provider="groq",
                model="llama-3.1-8b-instant",
            )
        )
        request = self.factory.post(
            "/chat/",
            data=json.dumps({"query": "What is Chikooza?", "mode": "site"}),
            content_type="application/json",
        )
        request.user = self.anonymous_user
        request.query_id = "site-query-123"

        with (
            patch("chatbot.views.get_public_site_assistant", return_value=assistant),
            patch("chatbot.views.get_rag_service") as get_rag_service,
        ):
            response = chat_api(request)

        body = json.loads(response.content)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["response"], "site answer for What is Chikooza?")
        self.assertEqual(body["mode"], "site")
        self.assertEqual(body["provider"], "groq")
        self.assertEqual(ChatLog.objects.count(), 1)
        get_rag_service.assert_not_called()

    def test_rejects_unknown_chat_mode_without_loading_rag(self):
        request = self.factory.post(
            "/chat/",
            data=json.dumps({"query": "hello", "mode": "unknown"}),
            content_type="application/json",
        )
        request.user = self.anonymous_user

        with patch("chatbot.views.get_rag_service") as get_rag_service:
            response = chat_api(request)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            json.loads(response.content), {"error": "Unsupported chat mode"}
        )
        get_rag_service.assert_not_called()


class PublicSiteAssistantTests(TestCase):
    def test_auto_prefers_groq_when_api_key_is_configured(self):
        env = {
            "CHIKOOZA_PUBLIC_CHAT_PROVIDER": "auto",
            "GROQ_API_KEY": "test-key",
            "GROQ_MODEL": "llama-3.1-8b-instant",
        }

        with patch.dict("os.environ", env, clear=True):
            assistant = PublicSiteAssistant()

        self.assertEqual(assistant._select_provider(), "groq")

    def test_public_assistant_fallback_keeps_homepage_chat_usable(self):
        env = {
            "CHIKOOZA_PUBLIC_CHAT_PROVIDER": "groq",
            "GROQ_API_KEY": "test-key",
        }

        with patch.dict("os.environ", env, clear=True):
            assistant = PublicSiteAssistant()

        with patch.object(
            assistant, "_answer_with_groq", side_effect=RuntimeError("offline")
        ):
            response = assistant.answer("What does this app do?")

        self.assertTrue(response.fallback)
        self.assertIn("poultry farm management", response.result.lower())
