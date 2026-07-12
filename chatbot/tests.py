import json
from types import SimpleNamespace
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.test import RequestFactory, TestCase

from .models import ChatLog, ChatMessage, ChatSession, KnowledgeChunk, KnowledgeDocument
from .rag_assistant import (
    EmbeddingService,
    RAGAssistantService,
    RAGChatResponse,
    RAGRetriever,
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

        with patch("chatbot.views.get_rag_assistant") as get_rag_assistant:
            response = chat_api(request)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content), {"error": "Invalid JSON body"})
        get_rag_assistant.assert_not_called()

    def test_rejects_empty_query_without_loading_rag(self):
        request = self.factory.post(
            "/chat/",
            data=json.dumps({"query": "  "}),
            content_type="application/json",
        )
        request.user = self.anonymous_user

        with patch("chatbot.views.get_rag_assistant") as get_rag_assistant:
            response = chat_api(request)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content), {"error": "Query is required"})
        get_rag_assistant.assert_not_called()

    def test_success_logs_chat_without_auth_user(self):
        assistant = SimpleNamespace(
            answer=lambda query, **kwargs: RAGChatResponse(
                result=f"answer for {query}",
                session_id="11111111-1111-1111-1111-111111111111",
                provider="groq-rag",
                model="test-model",
            )
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

        with patch("chatbot.views.get_rag_assistant", return_value=assistant):
            response = chat_api(request)

        self.assertEqual(response.status_code, 200)
        body = json.loads(response.content)
        self.assertEqual(ChatLog.objects.count(), 1)
        self.assertEqual(request.chat_data["model"], "test-model")
        self.assertEqual(body["query_id"], "query-123")
        self.assertEqual(body["session_id"], "11111111-1111-1111-1111-111111111111")

    def test_rag_mode_uses_database_rag_assistant(self):
        assistant = SimpleNamespace(
            answer=lambda query, **kwargs: RAGChatResponse(
                result=f"site answer for {query}",
                session_id="22222222-2222-2222-2222-222222222222",
                provider="groq",
                model="llama-3.1-8b-instant",
                sources=[{"source": "test-source", "page": 1, "score": 0.9}],
            )
        )
        request = self.factory.post(
            "/chat/",
            data=json.dumps({"query": "What is Chikooza?", "mode": "rag"}),
            content_type="application/json",
        )
        request.user = self.anonymous_user
        request.query_id = "site-query-123"

        with patch("chatbot.views.get_rag_assistant", return_value=assistant):
            response = chat_api(request)

        body = json.loads(response.content)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["response"], "site answer for What is Chikooza?")
        self.assertEqual(body["mode"], "rag")
        self.assertEqual(body["provider"], "groq")
        self.assertEqual(body["sources"][0]["source"], "test-source")
        self.assertIn("display", body)
        self.assertEqual(body["session_id"], "22222222-2222-2222-2222-222222222222")
        self.assertEqual(ChatLog.objects.count(), 1)

    def test_rejects_unknown_chat_mode_without_loading_rag(self):
        request = self.factory.post(
            "/chat/",
            data=json.dumps({"query": "hello", "mode": "unknown"}),
            content_type="application/json",
        )
        request.user = self.anonymous_user

        with patch("chatbot.views.get_rag_assistant") as get_rag_assistant:
            response = chat_api(request)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            json.loads(response.content), {"error": "Unsupported chat mode"}
        )
        get_rag_assistant.assert_not_called()


class DatabaseRAGAssistantTests(TestCase):
    def setUp(self):
        self.anonymous_user = SimpleNamespace(is_authenticated=False)
        self.embedding_service = EmbeddingService(provider="hash")

    def _create_chunk(self, content, *, title="Test Knowledge", category=None):
        document = KnowledgeDocument.objects.create(
            title=title,
            category=category or KnowledgeDocument.CATEGORY_GENERAL,
            source_label=title,
            status=KnowledgeDocument.STATUS_READY,
            chunk_count=1,
        )
        return KnowledgeChunk.objects.create(
            document=document,
            chunk_index=1,
            content=content,
            token_count=len(content.split()),
            embedding=self.embedding_service.embed_text(content),
        )

    def test_database_rag_uses_retrieved_context_for_groq_answer(self):
        chunk = self._create_chunk(
            "Chikooza tracks farms, flocks, daily data, purchases, sales, and reports for poultry farmers.",
            title="Chikooza product overview",
            category=KnowledgeDocument.CATEGORY_PRODUCT,
        )
        captured = {}
        calls = []

        def fake_chat(messages, **kwargs):
            calls.append(messages)
            captured["messages"] = messages
            captured["kwargs"] = kwargs
            if len(calls) == 1:
                return SimpleNamespace(
                    content='{"answerable": true, "reason": "Product context matches."}',
                    model="test-groq-model",
                )
            return SimpleNamespace(
                content="Chikooza tracks farm, flock, daily, purchase, sale, and report records.",
                model="test-groq-model",
            )

        service = RAGAssistantService(
            retriever=RAGRetriever(
                embedding_service=self.embedding_service,
                require_pgvector=False,
            ),
            groq_client=SimpleNamespace(has_keys=True, chat=fake_chat),
        )

        response = service.answer(
            "What does Chikooza track?",
            user=self.anonymous_user,
        )

        self.assertEqual(response.provider, "groq-rag")
        self.assertEqual(response.model, "test-groq-model")
        self.assertEqual(response.sources[0]["chunk_id"], chunk.id)
        self.assertEqual(len(calls), 2)
        self.assertIn(
            "Retrieved Chikooza knowledge-base context",
            calls[1][1]["content"],
        )
        self.assertIn("Chikooza tracks farms", calls[1][1]["content"])
        self.assertEqual(ChatSession.objects.count(), 1)
        self.assertEqual(ChatMessage.objects.count(), 2)

    def test_off_topic_question_does_not_call_groq(self):
        self._create_chunk(
            "Chikooza helps poultry farmers manage flock records and reports.",
            title="Chikooza product overview",
            category=KnowledgeDocument.CATEGORY_PRODUCT,
        )
        groq_client = SimpleNamespace(
            has_keys=True,
            chat=lambda messages, **kwargs: (_ for _ in ()).throw(
                AssertionError("Groq should not be called for off-topic questions")
            ),
        )
        service = RAGAssistantService(
            retriever=RAGRetriever(
                embedding_service=self.embedding_service,
                require_pgvector=False,
            ),
            groq_client=groq_client,
        )

        response = service.answer(
            "Who is the prime minister?", user=self.anonymous_user
        )

        self.assertTrue(response.fallback)
        self.assertEqual(response.provider, "rag-no-context")
        self.assertIn("Chikooza", response.result)
        self.assertNotIn("knowledge base", response.result.lower())
        self.assertEqual(ChatMessage.objects.count(), 2)

    def test_short_control_messages_do_not_search_or_call_groq(self):
        self._create_chunk(
            "Poultry farm setup requires training, record keeping, feed management, and bird health checks.",
            title="Poultry farm setup",
            category=KnowledgeDocument.CATEGORY_FARM_SETUP,
        )
        groq_client = SimpleNamespace(
            has_keys=True,
            chat=lambda messages, **kwargs: (_ for _ in ()).throw(
                AssertionError("Groq should not be called for control messages")
            ),
        )
        service = RAGAssistantService(
            retriever=RAGRetriever(
                embedding_service=self.embedding_service,
                require_pgvector=False,
            ),
            groq_client=groq_client,
        )

        hello = service.answer("hello", user=self.anonymous_user)
        unclear = service.answer("m", user=self.anonymous_user)
        okay = service.answer("okay", user=self.anonymous_user)
        identity = service.answer("what are you", user=self.anonymous_user)
        small_talk = service.answer("how are you", user=self.anonymous_user)
        gibberish = service.answer("xqzrt", user=self.anonymous_user)

        self.assertEqual(hello.provider, "chat-control")
        self.assertIn("Chikbot", hello.result)
        self.assertNotIn("knowledge base", hello.result.lower())
        self.assertEqual(unclear.provider, "chat-control")
        self.assertIn("could not understand", unclear.result)
        self.assertEqual(okay.provider, "chat-control")
        self.assertIn("Ask me a question", okay.result)
        self.assertNotIn("knowledge base", okay.result.lower())
        self.assertEqual(identity.provider, "chat-control")
        self.assertIn("Chikooza and poultry farming", identity.result)
        self.assertEqual(small_talk.provider, "chat-control")
        self.assertIn("ready to help", small_talk.result)
        self.assertEqual(gibberish.provider, "chat-control")
        self.assertIn("rephrase", gibberish.result)
        self.assertFalse(hello.sources)
        self.assertFalse(unclear.sources)
        self.assertFalse(okay.sources)
        self.assertFalse(identity.sources)
        self.assertFalse(small_talk.sources)
        self.assertFalse(gibberish.sources)

    def test_clear_questions_ignore_previous_control_history(self):
        self._create_chunk(
            "Chikooza is a poultry farm records and operations platform. It helps "
            "farmers keep farm, flock, daily data, purchase, sale, and report "
            "records in one workspace.",
            title="Chikooza product overview",
            category=KnowledgeDocument.CATEGORY_PRODUCT,
        )
        self._create_chunk(
            "Poultry farming means raising domesticated birds such as chickens for "
            "meat or eggs. It needs planning, housing, feed, water, health checks, "
            "biosecurity, vaccination planning, and daily records.",
            title="Poultry basics",
            category=KnowledgeDocument.CATEGORY_FARM_SETUP,
        )
        calls = []

        def fake_chat(messages, **kwargs):
            calls.append(messages)
            content = messages[1]["content"]
            if "Can the question be answered directly" in content:
                return SimpleNamespace(
                    content='{"answerable": true, "reason": "Direct context matches."}',
                    model="test-groq-model",
                )
            if "Farmer question: what is chikooza" in content:
                return SimpleNamespace(
                    content="Chikooza is a poultry farm records and operations platform.",
                    model="test-groq-model",
                )
            return SimpleNamespace(
                content=(
                    "Poultry farming means raising domesticated birds such as "
                    "chickens for meat or eggs."
                ),
                model="test-groq-model",
            )

        service = RAGAssistantService(
            retriever=RAGRetriever(
                embedding_service=self.embedding_service,
                require_pgvector=False,
            ),
            groq_client=SimpleNamespace(has_keys=True, chat=fake_chat),
        )

        session_id = None
        for query in ("hello", "how are you", "what are you"):
            response = service.answer(
                query,
                user=self.anonymous_user,
                session_id=session_id,
            )
            session_id = response.session_id
            self.assertEqual(response.provider, "chat-control")

        product_response = service.answer(
            "what is chikooza",
            user=self.anonymous_user,
            session_id=session_id,
        )
        poultry_response = service.answer(
            "what is poultry farming",
            user=self.anonymous_user,
            session_id=session_id,
        )

        self.assertEqual(product_response.provider, "groq-rag")
        self.assertIn("poultry farm records", product_response.result)
        self.assertEqual(poultry_response.provider, "groq-rag")
        self.assertIn("raising domesticated birds", poultry_response.result)
        self.assertEqual(len(calls), 4)
        self.assertTrue(
            all("No recent conversation." in call[1]["content"] for call in calls)
        )
        self.assertTrue(
            all("how are you" not in call[1]["content"].lower() for call in calls)
        )

    def test_acknowledged_farming_steps_question_uses_rag_context(self):
        self._create_chunk(
            "A broiler setup usually needs a clean shed, dry litter, feeders, "
            "drinkers, brooding heat, ventilation, lighting, water supply, feed "
            "storage, disinfectants, vaccination planning, and daily checks.",
            title="Broiler setup and management",
            category=KnowledgeDocument.CATEGORY_FARM_SETUP,
        )
        calls = []

        def fake_chat(messages, **kwargs):
            calls.append(messages)
            if len(calls) == 1:
                return SimpleNamespace(
                    content='{"answerable": true, "reason": "Setup context matches."}',
                    model="test-groq-model",
                )
            return SimpleNamespace(
                content=(
                    "Based on the retrieved Chikooza knowledge-base context, for "
                    "poultry farm setup, start with a clean shed, dry litter, "
                    "feeders, drinkers, brooding heat, ventilation, water, feed "
                    "storage, vaccination planning, and daily checks."
                ),
                model="test-groq-model",
            )

        service = RAGAssistantService(
            retriever=RAGRetriever(
                embedding_service=self.embedding_service,
                require_pgvector=False,
            ),
            groq_client=SimpleNamespace(has_keys=True, chat=fake_chat),
        )

        response = service.answer(
            "okay what are the steps involve in farming",
            user=self.anonymous_user,
        )

        self.assertEqual(response.provider, "groq-rag")
        self.assertIn("clean shed", response.result)
        self.assertNotIn("knowledge base", response.result.lower())
        self.assertEqual(len(calls), 2)
        self.assertIn("Interpreted search question", calls[0][1]["content"])
        self.assertIn("poultry broiler farm setup", calls[0][1]["content"])
        self.assertIn("Broiler setup", calls[1][1]["content"])

    def test_groq_relevance_check_can_reject_weak_context(self):
        self._create_chunk(
            "Feed should be clean and available according to bird age and farm management plan.",
            title="Broiler feed basics",
            category=KnowledgeDocument.CATEGORY_FEED,
        )
        calls = []

        def fake_chat(messages, **kwargs):
            calls.append(messages)
            if len(calls) == 1:
                return SimpleNamespace(
                    content='{"answerable": false, "reason": "Context is only loosely related."}',
                    model="test-groq-model",
                )
            raise AssertionError(
                "Final answer should not be generated from weak context"
            )

        service = RAGAssistantService(
            retriever=RAGRetriever(
                embedding_service=self.embedding_service,
                require_pgvector=False,
            ),
            groq_client=SimpleNamespace(has_keys=True, chat=fake_chat),
        )

        response = service.answer(
            "What feed formula should I use for day old chicks?",
            user=self.anonymous_user,
        )

        self.assertEqual(response.provider, "rag-context-not-relevant")
        self.assertTrue(response.fallback)
        self.assertIn("could not find a clear answer", response.result)
        self.assertNotIn("knowledge base", response.result.lower())
        self.assertEqual(len(calls), 1)

    def test_product_question_prioritizes_product_knowledge(self):
        self._create_chunk(
            "Chikooza tracks farms, flocks, daily data, purchases, sales, and reports.",
            title="Chikooza product overview",
            category=KnowledgeDocument.CATEGORY_PRODUCT,
        )
        self._create_chunk(
            "Hatchery teams track flock hatchability, basket refilling, and egg candling results.",
            title="Hatchery guide",
            category=KnowledgeDocument.CATEGORY_BROILER,
        )
        retriever = RAGRetriever(
            embedding_service=self.embedding_service,
            require_pgvector=False,
        )

        chunks = retriever.retrieve("What does Chikooza track?")

        self.assertGreater(len(chunks), 0)
        self.assertEqual(chunks[0].source, "Chikooza product overview")

    def test_require_pgvector_rejects_sqlite(self):
        self._create_chunk(
            "Chikooza tracks farm records and poultry reports.",
            title="Chikooza product overview",
            category=KnowledgeDocument.CATEGORY_PRODUCT,
        )
        retriever = RAGRetriever(
            embedding_service=self.embedding_service,
            require_pgvector=True,
        )

        with self.assertRaisesMessage(
            ImproperlyConfigured,
            "CHIKOOZA_RAG_REQUIRE_PGVECTOR is enabled",
        ):
            retriever.retrieve("What does Chikooza track?")

    def test_session_id_keeps_follow_up_in_same_conversation(self):
        self._create_chunk(
            "Broiler farmers should keep feed and clean water available according to bird age and farm management plan.",
            title="Broiler feed and water",
            category=KnowledgeDocument.CATEGORY_FEED,
        )
        service = RAGAssistantService(
            retriever=RAGRetriever(
                embedding_service=self.embedding_service,
                require_pgvector=False,
            ),
            groq_client=SimpleNamespace(
                has_keys=True,
                chat=lambda messages, **kwargs: SimpleNamespace(
                    content=(
                        '{"answerable": true, "reason": "Context matches."}'
                        if "Can the question be answered directly"
                        in messages[1]["content"]
                        else "Broiler farmers should keep feed and clean water available."
                    ),
                    model="test-groq-model",
                ),
            ),
        )

        first = service.answer("Tell me about broiler feed", user=self.anonymous_user)
        second = service.answer(
            "what about water",
            user=self.anonymous_user,
            session_id=first.session_id,
        )

        self.assertEqual(first.session_id, second.session_id)
        self.assertEqual(ChatSession.objects.count(), 1)
        self.assertEqual(ChatMessage.objects.count(), 4)
        self.assertIn("water", second.result.lower())
