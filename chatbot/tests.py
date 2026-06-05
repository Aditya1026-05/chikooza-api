import json
from types import SimpleNamespace
from unittest.mock import patch

from django.test import RequestFactory, TestCase

from .models import ChatLog
from .public_assistant import (
    PublicAssistantResponse,
    PublicRagChunk,
    PublicRagRetriever,
    PublicSiteAssistant,
)
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
            answer=lambda query, history=None: PublicAssistantResponse(
                result=f"site answer for {query}",
                provider="groq",
                model="llama-3.1-8b-instant",
                sources=[{"source": "test-source", "page": 1, "score": 0.9}],
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
        self.assertEqual(body["sources"][0]["source"], "test-source")
        self.assertIn("display", body)
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
    def test_public_retriever_rejects_off_topic_without_loading_faiss(self):
        retriever = PublicRagRetriever()

        with patch.object(retriever, "_retrieve_with_faiss") as retrieve_with_faiss:
            chunks = retriever.retrieve("Who is the prime minister?")

        self.assertEqual(chunks, [])
        retrieve_with_faiss.assert_not_called()

    def test_public_retriever_handles_capability_question_from_product_chunks(self):
        retriever = PublicRagRetriever()

        with patch.object(retriever, "_retrieve_with_faiss") as retrieve_with_faiss:
            chunks = retriever.retrieve("What can you do?")

        self.assertGreater(len(chunks), 0)
        self.assertIn("Chikooza", chunks[0].text)
        retrieve_with_faiss.assert_not_called()

    def test_public_retriever_prioritizes_product_context_for_chikooza_questions(self):
        retriever = PublicRagRetriever()

        with patch.object(retriever, "_retrieve_with_faiss") as retrieve_with_faiss:
            chunks = retriever.retrieve("What does Chikooza do for poultry farm data?")

        self.assertGreater(len(chunks), 0)
        self.assertIn("Chikooza", chunks[0].text)
        retrieve_with_faiss.assert_not_called()

    def test_public_retriever_normalizes_common_query_typos(self):
        retriever = PublicRagRetriever()

        with patch.object(
            retriever,
            "_retrieve_with_faiss",
            return_value=[
                PublicRagChunk(
                    text="FCR is feed conversion ratio for a flock.",
                    source="Broiler guide",
                    page=1,
                    score=0.9,
                )
            ],
        ) as retrieve_with_faiss:
            chunks = retriever.retrieve("how to manage glock feed conversion")

        self.assertGreater(len(chunks), 0)
        retrieve_with_faiss.assert_not_called()

    def test_public_retriever_normalizes_poultry_typo_from_clean_knowledge(self):
        retriever = PublicRagRetriever()

        with patch.object(retriever, "_retrieve_with_faiss") as retrieve_with_faiss:
            chunks = retriever.retrieve("so what is poltry")

        self.assertGreater(len(chunks), 0)
        self.assertIn("Poultry", chunks[0].source)
        retrieve_with_faiss.assert_not_called()

    def test_public_retriever_answers_broad_disease_question_from_clean_knowledge(self):
        retriever = PublicRagRetriever()

        with patch.object(retriever, "_retrieve_with_faiss") as retrieve_with_faiss:
            chunks = retriever.retrieve("so tell all the diseases that can happen")

        self.assertGreater(len(chunks), 0)
        self.assertIn("Disease", chunks[0].source)
        retrieve_with_faiss.assert_not_called()

    def test_public_retriever_keeps_generic_poultry_queries_out_of_product_chunks(self):
        retriever = PublicRagRetriever()
        poultry_chunk = PublicRagChunk(
            text="Stocking density depends on broiler age, ventilation, and available shed space.",
            source="Broiler guide",
            page=8,
            score=0.92,
        )

        with patch.object(
            retriever,
            "_retrieve_with_faiss",
            return_value=[poultry_chunk],
        ):
            chunks = retriever.retrieve("What bird density should I keep in a broiler shed?")

        self.assertGreater(len(chunks), 0)
        self.assertNotIn("Chikooza product overview", chunks[0].source)

    def test_public_display_payload_cleans_markdown_bullets(self):
        assistant = PublicSiteAssistant(
            retriever=SimpleNamespace(retrieve=lambda query, history=None: []),
            groq_client=SimpleNamespace(has_keys=False),
        )

        payload = assistant._display_payload(
            "Keep records daily.\n- **Feed**: Track feed in kg.\n- **Mortality**: Count dead birds.",
            [],
        )

        self.assertEqual(payload["summary"], "Keep records daily.")
        self.assertEqual(payload["items"][0], "Feed: Track feed in kg.")

    def test_public_assistant_uses_retrieved_context_for_groq_prompt(self):
        retriever = SimpleNamespace(
            retrieve=lambda query, history=None: [
                PublicRagChunk(
                    text="Chikooza tracks farms, flocks, daily data, sales, and reports.",
                    source="Chikooza product overview",
                    page=None,
                    score=1.0,
                )
            ]
        )
        groq_client = SimpleNamespace(has_keys=True)
        captured = {}

        def fake_chat(messages, **kwargs):
            captured["messages"] = messages
            captured["kwargs"] = kwargs
            return SimpleNamespace(content="Generated from retrieved context.", model="test-model")

        groq_client.chat = fake_chat

        with patch.dict("os.environ", {"GROQ_MODEL": "test-model"}, clear=True):
            assistant = PublicSiteAssistant(
                retriever=retriever,
                groq_client=groq_client,
            )

        response = assistant.answer(
            "What does Chikooza track?",
            history=[
                {"role": "user", "content": "hello"},
                {"role": "bot", "content": "Hi, ask me about Chikooza."},
            ],
        )

        self.assertEqual(response.provider, "groq-rag")
        self.assertEqual(response.result, "Generated from retrieved context.")
        self.assertIn("Retrieved public knowledge-base snippets", captured["messages"][1]["content"])
        self.assertIn("Recent conversation", captured["messages"][1]["content"])
        self.assertIn("Chikooza tracks farms", captured["messages"][1]["content"])
        self.assertEqual(response.sources[0]["source"], "Chikooza product overview")

    def test_public_assistant_does_not_call_groq_without_retrieved_context(self):
        retriever = SimpleNamespace(retrieve=lambda query, history=None: [])
        groq_client = SimpleNamespace(
            has_keys=True,
            chat=lambda messages, **kwargs: (_ for _ in ()).throw(
                AssertionError("Groq should not be called without RAG context")
            ),
        )

        with patch.dict("os.environ", {}, clear=True):
            assistant = PublicSiteAssistant(
                retriever=retriever,
                groq_client=groq_client,
            )

        response = assistant.answer("Who is the prime minister?")

        self.assertTrue(response.fallback)
        self.assertEqual(response.provider, "rag-no-context")
        self.assertIn("public knowledge base", response.result)
        self.assertEqual(response.display["kind"], "public_answer")

    def test_public_assistant_greeting_uses_chikbot_name(self):
        retriever = SimpleNamespace(retrieve=lambda query, history=None: [])
        groq_client = SimpleNamespace(has_keys=True)

        assistant = PublicSiteAssistant(
            retriever=retriever,
            groq_client=groq_client,
        )

        response = assistant.answer("hello")

        self.assertIn("Chikbot", response.result)
        self.assertEqual(response.display["summary"], response.result)

    def test_public_assistant_uses_retrieval_only_when_groq_is_unavailable(self):
        retriever = SimpleNamespace(
            retrieve=lambda query, history=None: [
                PublicRagChunk(
                    text="Broiler farmers should record feed, mortality, and weight daily.",
                    source="Broiler guide",
                    page=4,
                    score=0.9,
                )
            ]
        )
        groq_client = SimpleNamespace(has_keys=False)

        with patch.dict("os.environ", {}, clear=True):
            assistant = PublicSiteAssistant(
                retriever=retriever,
                groq_client=groq_client,
            )

        response = assistant.answer("How should I track broiler performance?")

        self.assertTrue(response.fallback)
        self.assertEqual(response.provider, "rag-retrieval-only")
        self.assertIn("feed, mortality, and weight", response.result)
        self.assertEqual(response.sources[0]["source"], "Broiler guide")
        self.assertGreater(len(response.display["items"]), 0)
