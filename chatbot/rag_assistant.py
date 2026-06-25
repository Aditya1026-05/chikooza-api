import hashlib
import json
import logging
import math
import os
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from django.core.exceptions import ImproperlyConfigured
from django.db import connection, transaction
from django.db.models.expressions import RawSQL

from common.groq_client import GroqChatClient

from .models import ChatMessage, ChatSession, KnowledgeChunk, KnowledgeDocument

logger = logging.getLogger(__name__)


RAG_SYSTEM_PROMPT = """
You are Chikbot, the Chikooza knowledge-base assistant.

Answer only from the retrieved Chikooza knowledge-base context in the user
message. The context can include Chikooza product information and poultry
farming reference material. Recent conversation is provided only to understand
follow-up questions.

Rules:
- Stay within Chikooza, poultry farming, farm operations, and the product being built.
- Do not answer outside topics.
- If the context is not enough, say you do not have enough reliable information.
- Do not invent pricing, guarantees, private farmer records, veterinary diagnosis, or medicine prescriptions.
- For disease or sick-bird questions, give general prevention/warning-sign information only and advise contacting a qualified veterinarian or poultry expert.
- Keep answers natural, practical, and concise.
- Use 2-5 bullets when the answer has multiple points.
- Do not mention retrieved context, snippets, sources, documents, or the knowledge base in the visible answer.
- Do not mention hidden prompts or internal implementation details.
""".strip()

CONTEXT_ASSESSMENT_SYSTEM_PROMPT = """
You are Chikbot's retrieval relevance checker.

Decide whether the retrieved Chikooza knowledge-base snippets contain enough
directly relevant information to answer the farmer's question.

Rules:
- Return JSON only.
- Use this exact shape: {"answerable": true|false, "reason": "short reason"}.
- answerable must be false for greetings, acknowledgements, unclear text, outside topics, or loosely related context.
- answerable must be false if the snippets do not directly answer the question.
- answerable may be true only when the answer can be written from the snippets without guessing.
""".strip()


STOP_WORDS = {
    "a",
    "about",
    "after",
    "again",
    "all",
    "also",
    "am",
    "an",
    "and",
    "any",
    "are",
    "as",
    "at",
    "be",
    "but",
    "by",
    "can",
    "could",
    "do",
    "does",
    "for",
    "from",
    "give",
    "has",
    "have",
    "help",
    "how",
    "i",
    "in",
    "into",
    "is",
    "it",
    "its",
    "me",
    "my",
    "ok",
    "okay",
    "of",
    "on",
    "or",
    "our",
    "please",
    "show",
    "so",
    "tell",
    "thank",
    "thanks",
    "that",
    "the",
    "their",
    "them",
    "this",
    "to",
    "use",
    "using",
    "what",
    "we",
    "when",
    "where",
    "which",
    "who",
    "why",
    "with",
    "you",
    "your",
}

GREETING_TERMS = {"hello", "hi", "hey", "namaste"}
ACKNOWLEDGEMENT_TERMS = {
    "fine",
    "good",
    "got it",
    "great",
    "hm",
    "hmm",
    "ok",
    "okay",
    "sure",
    "thank",
    "thanks",
    "thank you",
    "yes",
    "yeah",
    "yep",
}

IDENTITY_CONTROL_TEXTS = {
    "how can you help",
    "tell me about yourself",
    "what are you",
    "what can you do",
    "what is chikbot",
    "what is this",
    "who are you",
}

SMALL_TALK_CONTROL_TEXTS = {
    "how are you",
    "how are you doing",
    "how is it going",
    "how r u",
    "what s up",
    "whats up",
}

GENERIC_FARMING_QUERY_TERMS = {
    "begin",
    "business",
    "farm",
    "farmer",
    "farming",
    "get",
    "involve",
    "involved",
    "manage",
    "management",
    "need",
    "process",
    "require",
    "required",
    "setup",
    "start",
    "step",
    "steps",
}

POULTRY_CONTEXT_TERMS = {
    "bird",
    "breeder",
    "broiler",
    "chicken",
    "chick",
    "egg",
    "fcr",
    "feed",
    "flock",
    "hatchery",
    "layer",
    "mortality",
    "poultry",
}

OUT_OF_SCOPE_TERMS = {
    "bank",
    "bitcoin",
    "code",
    "coding",
    "crypto",
    "election",
    "forex",
    "football",
    "hotel",
    "iphone",
    "minister",
    "movie",
    "politic",
    "prime",
    "programming",
    "recipe",
    "recipes",
    "stock",
    "trading",
    "travel",
    "weather",
}

DOMAIN_TERMS = {
    "account",
    "ai",
    "ammonia",
    "app",
    "biosecurity",
    "bird",
    "breeder",
    "broiler",
    "brooding",
    "chicken",
    "chick",
    "chikbot",
    "chikooza",
    "cost",
    "daily",
    "dashboard",
    "data",
    "disease",
    "egg",
    "farm",
    "farmer",
    "fcr",
    "feed",
    "flock",
    "hatch",
    "hatchability",
    "hatchery",
    "health",
    "housing",
    "layer",
    "litter",
    "meat",
    "mortality",
    "performance",
    "platform",
    "poultry",
    "processing",
    "product",
    "purchase",
    "record",
    "register",
    "report",
    "revenue",
    "sale",
    "sanitation",
    "shed",
    "space",
    "stocking",
    "stress",
    "summary",
    "temperature",
    "vaccine",
    "vaccination",
    "ventilation",
    "water",
    "weight",
}

PRODUCT_INTENT_TERMS = {
    "account",
    "ai",
    "app",
    "chikbot",
    "chikooza",
    "dashboard",
    "feature",
    "login",
    "platform",
    "product",
    "register",
}

POULTRY_SPECIFIC_TERMS = (
    DOMAIN_TERMS - PRODUCT_INTENT_TERMS - {"data", "record", "report", "summary"}
)

QUERY_NORMALIZATIONS = (
    (re.compile(r"\bpoltry\b", re.IGNORECASE), "poultry"),
    (re.compile(r"\bpolutry\b", re.IGNORECASE), "poultry"),
    (re.compile(r"\bpoultary\b", re.IGNORECASE), "poultry"),
    (re.compile(r"\bdiesease(s)?\b", re.IGNORECASE), r"disease\1"),
    (re.compile(r"\bdesiese(s)?\b", re.IGNORECASE), r"disease\1"),
    (re.compile(r"\bglock(s)?\b", re.IGNORECASE), r"flock\1"),
    (re.compile(r"\bflcok(s)?\b", re.IGNORECASE), r"flock\1"),
    (re.compile(r"\bfamr(s)?\b", re.IGNORECASE), r"farm\1"),
    (re.compile(r"\bsail(s)?\b", re.IGNORECASE), r"sale\1"),
    (re.compile(r"\bpruchase(s)?\b", re.IGNORECASE), r"purchase\1"),
    (re.compile(r"\bpurchaes\b", re.IGNORECASE), "purchase"),
    (re.compile(r"\bfeed\s+conversion\b", re.IGNORECASE), "fcr feed conversion"),
    (re.compile(r"\bbird\s+density\b", re.IGNORECASE), "stocking density space"),
    (re.compile(r"\bsteps?\s+involve\b", re.IGNORECASE), "steps involved"),
)


@dataclass(frozen=True)
class TextUnit:
    text: str
    page: str = ""


@dataclass(frozen=True)
class RetrievedChunk:
    id: int
    content: str
    source: str
    page: str = ""
    score: float = 0
    category: str = ""

    @property
    def source_label(self):
        if self.page:
            return f"{self.source}, page {self.page}"
        return self.source

    def as_source(self):
        return {
            "chunk_id": self.id,
            "source": self.source,
            "page": self.page or None,
            "category": self.category,
            "score": round(float(self.score), 4),
        }


@dataclass
class RAGChatResponse:
    result: str
    session_id: str
    provider: str
    model: str
    fallback: bool = False
    sources: list[dict] = field(default_factory=list)
    display: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ContextAssessment:
    answerable: bool
    reason: str = ""


class EmbeddingService:
    def __init__(
        self,
        *,
        dimensions: int | None = None,
        provider: str | None = None,
        model_name: str | None = None,
    ):
        self.dimensions = dimensions or int(
            os.getenv("CHIKOOZA_RAG_VECTOR_DIMENSIONS", "384")
        )
        self.provider = (
            (provider or os.getenv("CHIKOOZA_RAG_EMBEDDING_PROVIDER", "hash"))
            .strip()
            .lower()
        )
        self.model_name = model_name or os.getenv(
            "CHIKOOZA_RAG_EMBEDDING_MODEL",
            "sentence-transformers/all-MiniLM-L6-v2",
        )
        self._model = None

    def embed_text(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        clean_texts = [self._clean_text(text) for text in texts]
        if self.provider in {"sentence_transformers", "sentence-transformer"}:
            return self._sentence_transformer_embeddings(clean_texts)
        if self.provider == "auto":
            try:
                return self._sentence_transformer_embeddings(clean_texts)
            except Exception as exc:
                logger.warning("Falling back to hash embeddings: %s", exc)
        return [self._hash_embedding(text) for text in clean_texts]

    def _sentence_transformer_embeddings(self, texts: list[str]) -> list[list[float]]:
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        vectors = self._model.encode(texts, normalize_embeddings=True)
        return [
            [float(value) for value in vector[: self.dimensions]]
            for vector in vectors.tolist()
        ]

    def _hash_embedding(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        tokens = _tokens(text)
        if not tokens:
            tokens = ["empty"]

        for token in tokens:
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            number = int.from_bytes(digest, "big")
            index = number % self.dimensions
            sign = 1 if (number >> 8) % 2 == 0 else -1
            vector[index] += sign

        norm = math.sqrt(sum(value * value for value in vector)) or 1
        return [value / norm for value in vector]

    def _clean_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", str(text or "")).strip()


class KnowledgeIngestionService:
    def __init__(self, embedding_service: EmbeddingService | None = None):
        self.embedding_service = embedding_service or EmbeddingService()
        self.chunk_size = int(os.getenv("CHIKOOZA_RAG_CHUNK_SIZE", "1200"))
        self.chunk_overlap = int(os.getenv("CHIKOOZA_RAG_CHUNK_OVERLAP", "180"))

    def process_document(self, document: KnowledgeDocument) -> int:
        document.mark_processing()
        try:
            units = self._extract_text_units(document)
            chunk_payloads = self._chunk_units(units)
            if not chunk_payloads:
                raise ValueError("No readable text was found in this document.")

            embeddings = self.embedding_service.embed_texts(
                [payload["content"] for payload in chunk_payloads]
            )

            with transaction.atomic():
                KnowledgeChunk.objects.filter(document=document).delete()
                chunks = [
                    KnowledgeChunk(
                        document=document,
                        chunk_index=index + 1,
                        content=payload["content"],
                        page=payload["page"],
                        token_count=payload["token_count"],
                        embedding=embeddings[index],
                        metadata=payload["metadata"],
                    )
                    for index, payload in enumerate(chunk_payloads)
                ]
                KnowledgeChunk.objects.bulk_create(chunks, batch_size=100)
                if not document.checksum:
                    document.checksum = self._checksum_document(document)
                    document.save(update_fields=["checksum", "updated_at"])

            document.mark_ready(len(chunk_payloads))
            return len(chunk_payloads)
        except Exception as exc:
            document.mark_failed(exc)
            raise

    def _extract_text_units(self, document: KnowledgeDocument) -> list[TextUnit]:
        if document.content.strip():
            return [TextUnit(text=document.content, page="")]

        if not document.file:
            return []

        path = Path(document.file.path)
        suffix = path.suffix.lower()
        if suffix in {".txt", ".md"}:
            return [TextUnit(text=path.read_text(encoding="utf-8"), page="")]
        if suffix == ".pdf":
            return self._extract_pdf_units(path)
        raise ValueError(f"Unsupported knowledge document type: {suffix}")

    def _extract_pdf_units(self, path: Path) -> list[TextUnit]:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        units = []
        for index, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            if text.strip():
                units.append(TextUnit(text=text, page=str(index)))
        return units

    def _chunk_units(self, units: list[TextUnit]) -> list[dict]:
        payloads = []
        for unit in units:
            for piece in self._split_text(unit.text):
                payloads.append(
                    {
                        "content": piece,
                        "page": unit.page,
                        "token_count": len(_tokens(piece)),
                        "metadata": {},
                    }
                )
        return payloads

    def _split_text(self, text: str) -> list[str]:
        clean_text = re.sub(r"\s+", " ", text or "").strip()
        if not clean_text:
            return []
        if len(clean_text) <= self.chunk_size:
            return [clean_text]

        chunks = []
        start = 0
        while start < len(clean_text):
            end = min(start + self.chunk_size, len(clean_text))
            if end < len(clean_text):
                boundary = max(
                    clean_text.rfind(". ", start, end),
                    clean_text.rfind("? ", start, end),
                    clean_text.rfind("! ", start, end),
                    clean_text.rfind("; ", start, end),
                )
                if boundary > start + int(self.chunk_size * 0.55):
                    end = boundary + 1

            piece = clean_text[start:end].strip()
            if piece:
                chunks.append(piece)
            if end >= len(clean_text):
                break
            start = max(end - self.chunk_overlap, start + 1)
        return chunks

    def _checksum_document(self, document: KnowledgeDocument) -> str:
        digest = hashlib.sha256()
        if document.content:
            digest.update(document.content.encode("utf-8"))
        if document.file:
            with open(document.file.path, "rb") as file_obj:
                for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
                    digest.update(chunk)
        return digest.hexdigest()


class RAGRetriever:
    def __init__(
        self,
        embedding_service: EmbeddingService | None = None,
        *,
        require_pgvector: bool | None = None,
    ):
        self.embedding_service = embedding_service or EmbeddingService()
        self.top_k = int(os.getenv("CHIKOOZA_RAG_TOP_K", "5"))
        self.candidate_limit = int(os.getenv("CHIKOOZA_RAG_CANDIDATE_LIMIT", "50"))
        self.local_scan_limit = int(os.getenv("CHIKOOZA_RAG_LOCAL_SCAN_LIMIT", "10000"))
        self.min_score = float(os.getenv("CHIKOOZA_RAG_MIN_SCORE", "0.18"))
        self.require_pgvector = (
            require_pgvector
            if require_pgvector is not None
            else _env_bool("CHIKOOZA_RAG_REQUIRE_PGVECTOR", False)
        )

    def retrieve(
        self,
        query_text: str,
        history: list[dict[str, str]] | None = None,
    ) -> list[RetrievedChunk]:
        self._validate_database_backend()
        search_text = self._search_text(query_text, history or [])
        if not self._is_allowed_topic(search_text):
            return []

        query_vector = self.embedding_service.embed_text(search_text)
        if connection.vendor == "postgresql":
            chunks = self._retrieve_postgres(search_text, query_vector)
        else:
            chunks = self._retrieve_python(search_text, query_vector)

        return self._dedupe(chunks)[: self.top_k]

    def should_use_history(self, query_text: str) -> bool:
        search_text = _question_for_retrieval(query_text)
        query_terms = [
            token for token in _tokens(search_text) if token not in STOP_WORDS
        ]
        return self._is_followup_query(search_text, query_terms)

    def _retrieve_postgres(
        self,
        search_text: str,
        query_vector: list[float],
    ) -> list[RetrievedChunk]:
        vector_literal = _vector_literal(query_vector)
        query_terms = set(_tokens(search_text))
        rows = (
            KnowledgeChunk.objects.filter(
                document__status=KnowledgeDocument.STATUS_READY,
                embedding__isnull=False,
            )
            .select_related("document")
            .annotate(distance=RawSQL("embedding <=> %s::vector", [vector_literal]))
            .order_by("distance")[: self.candidate_limit]
        )

        chunks = []
        for chunk in rows:
            distance = float(getattr(chunk, "distance", 1.0) or 1.0)
            vector_score = max(0.0, 1.0 - distance)
            score = (
                vector_score
                + min(_lexical_score(query_terms, chunk.content), 0.25)
                + self._category_boost(query_terms, chunk.document)
            )
            if score >= self.min_score:
                chunks.append(self._to_retrieved_chunk(chunk, score))
        return chunks

    def _retrieve_python(
        self,
        search_text: str,
        query_vector: list[float],
    ) -> list[RetrievedChunk]:
        query_terms = set(_tokens(search_text))
        chunks = []
        queryset = (
            KnowledgeChunk.objects.filter(
                document__status=KnowledgeDocument.STATUS_READY,
                embedding__isnull=False,
            )
            .select_related("document")
            .order_by("id")[: self.local_scan_limit]
        )
        for chunk in queryset:
            vector_score = _cosine_similarity(query_vector, chunk.embedding or [])
            lexical = _lexical_score(query_terms, chunk.content)
            score = (
                (0.8 * vector_score)
                + min(lexical, 0.3)
                + self._category_boost(query_terms, chunk.document)
            )
            if score >= self.min_score or lexical >= 0.5:
                chunks.append(self._to_retrieved_chunk(chunk, score))

        chunks.sort(key=lambda item: item.score, reverse=True)
        return chunks[: self.candidate_limit]

    def _to_retrieved_chunk(
        self, chunk: KnowledgeChunk, score: float
    ) -> RetrievedChunk:
        return RetrievedChunk(
            id=chunk.id,
            content=chunk.content,
            source=chunk.document.display_source,
            page=chunk.page,
            score=score,
            category=chunk.document.category,
        )

    def _dedupe(self, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
        unique = {}
        for chunk in sorted(chunks, key=lambda item: item.score, reverse=True):
            key = (chunk.source, chunk.page, chunk.content[:180])
            if key not in unique:
                unique[key] = chunk
        return list(unique.values())

    def _search_text(self, query_text: str, history: list[dict[str, str]]) -> str:
        query_text = _question_for_retrieval(query_text)
        query_terms = [
            token for token in _tokens(query_text) if token not in STOP_WORDS
        ]
        if not history or not self._is_followup_query(query_text, query_terms):
            return query_text
        recent = " ".join(item["content"][:280] for item in history[-6:])
        return f"{recent} {query_text}".strip()

    def _is_followup_query(self, query_text: str, query_terms: list[str]) -> bool:
        normalized = _normalize_text(query_text)
        followup_markers = (
            "also",
            "and then",
            "continue",
            "explain more",
            "in detail",
            "it",
            "same",
            "that",
            "them",
            "those",
            "what about",
        )
        if any(marker in normalized for marker in followup_markers):
            return True

        terms = set(query_terms)
        if terms & (PRODUCT_INTENT_TERMS | POULTRY_CONTEXT_TERMS):
            return False
        if terms & (DOMAIN_TERMS - {"farm", "farmer"}):
            return False
        return len(query_terms) <= 3

    def _is_allowed_topic(self, text: str) -> bool:
        terms = {token for token in _tokens(text) if token not in STOP_WORDS}
        if not terms or terms <= GREETING_TERMS:
            return False
        if terms & _out_of_scope_terms():
            return False
        domain_terms = terms & DOMAIN_TERMS
        if not domain_terms:
            return False
        if domain_terms <= {"farm", "farmer"} and not terms <= (
            _generic_farming_terms() | {"poultry"}
        ):
            return False
        return True

    def _validate_database_backend(self):
        if self.require_pgvector and connection.vendor != "postgresql":
            raise ImproperlyConfigured(
                "CHIKOOZA_RAG_REQUIRE_PGVECTOR is enabled, but Django is not using "
                "PostgreSQL. Set DATABASE_URL to a PostgreSQL database with the "
                "pgvector extension before using chatbot RAG."
            )

    def _category_boost(
        self,
        query_terms: set[str],
        document: KnowledgeDocument,
    ) -> float:
        if not self._is_product_question(query_terms):
            return 0
        if document.category == KnowledgeDocument.CATEGORY_PRODUCT:
            return 0.75
        return -0.2

    def _is_product_question(self, query_terms: set[str]) -> bool:
        if not query_terms & PRODUCT_INTENT_TERMS:
            return False
        return not bool(query_terms & POULTRY_SPECIFIC_TERMS)


class RAGAssistantService:
    def __init__(
        self,
        *,
        retriever: RAGRetriever | None = None,
        groq_client: GroqChatClient | None = None,
    ):
        self.retriever = retriever or RAGRetriever()
        self.groq_client = groq_client or GroqChatClient(
            model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
            fallback_model=os.getenv("GROQ_FALLBACK_MODEL", ""),
            timeout=float(os.getenv("CHIKOOZA_PUBLIC_CHAT_TIMEOUT", "25")),
        )
        self.groq_model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        self.timeout = float(os.getenv("CHIKOOZA_PUBLIC_CHAT_TIMEOUT", "25"))

    def answer(
        self,
        query_text: str,
        *,
        user=None,
        session_id: str | None = None,
        client_history: list[dict[str, str]] | None = None,
    ) -> RAGChatResponse:
        query_text = query_text.strip()
        session = self._resolve_session(session_id, user)
        control_response = self._control_answer(query_text, session)
        if control_response:
            self._store_exchange(session, query_text, control_response)
            return control_response

        history = self._session_history(session)
        if not history and client_history:
            history = self._sanitize_client_history(client_history)

        retrieval_query = _question_for_retrieval(query_text)
        history_for_answer = (
            history if self.retriever.should_use_history(query_text) else []
        )
        chunks = self.retriever.retrieve(retrieval_query, history=history_for_answer)
        if not chunks:
            response = self._no_context_answer(query_text, session)
        elif not self.groq_client.has_keys:
            response = self._groq_unavailable_answer(session)
        else:
            try:
                assessment = self._assess_context(
                    query_text,
                    retrieval_query,
                    chunks,
                    history_for_answer,
                )
                if assessment.answerable:
                    response = self._answer_with_groq(
                        query_text,
                        retrieval_query,
                        chunks,
                        history_for_answer,
                        session,
                    )
                else:
                    response = self._not_enough_matching_context_answer(
                        session,
                        assessment.reason,
                    )
            except Exception as exc:
                logger.warning("Groq RAG answer failed: %s", exc)
                response = self._groq_unavailable_answer(session)

        self._store_exchange(session, query_text, response)
        return response

    def _answer_with_groq(
        self,
        query_text: str,
        retrieval_query: str,
        chunks: list[RetrievedChunk],
        history: list[dict[str, str]],
        session: ChatSession,
    ) -> RAGChatResponse:
        result = self.groq_client.chat(
            self._messages(query_text, retrieval_query, chunks, history),
            model=self.groq_model,
            temperature=0.12,
            max_tokens=620,
            timeout=self.timeout,
        )
        answer = _clean_public_answer(result.content)
        sources = self._sources(chunks)
        return RAGChatResponse(
            result=answer,
            session_id=str(session.session_id),
            provider="groq-rag",
            model=result.model,
            sources=sources,
            display=self._display_payload(answer, sources),
        )

    def _assess_context(
        self,
        query_text: str,
        retrieval_query: str,
        chunks: list[RetrievedChunk],
        history: list[dict[str, str]],
    ) -> ContextAssessment:
        result = self.groq_client.chat(
            self._assessment_messages(query_text, retrieval_query, chunks, history),
            model=self.groq_model,
            temperature=0,
            max_tokens=140,
            timeout=self.timeout,
        )
        payload = _json_object(result.content)
        return ContextAssessment(
            answerable=bool(payload.get("answerable")),
            reason=_clip(str(payload.get("reason", "")), 240),
        )

    def _assessment_messages(
        self,
        query_text: str,
        retrieval_query: str,
        chunks: list[RetrievedChunk],
        history: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        interpreted_text = ""
        if retrieval_query != query_text:
            interpreted_text = f"\nInterpreted search question: {retrieval_query}"
        return [
            {"role": "system", "content": CONTEXT_ASSESSMENT_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "Retrieved Chikooza knowledge-base snippets:\n"
                    f"{self._context_text(chunks, limit=900)}\n\n"
                    f"Recent conversation:\n{self._history_prompt_text(history)}\n\n"
                    f"Farmer question: {query_text}{interpreted_text}\n\n"
                    "Can the question be answered directly from these snippets?"
                ),
            },
        ]

    def _messages(
        self,
        query_text: str,
        retrieval_query: str,
        chunks: list[RetrievedChunk],
        history: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        context = self._context_text(chunks, limit=1600)
        history_text = self._history_prompt_text(history)
        interpreted_text = ""
        if retrieval_query != query_text:
            interpreted_text = f"\nInterpreted search question: {retrieval_query}"
        return [
            {"role": "system", "content": RAG_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "Retrieved Chikooza knowledge-base context:\n"
                    f"{context}\n\n"
                    f"Recent conversation for follow-up context:\n{history_text}\n\n"
                    f"Farmer question: {query_text}{interpreted_text}\n\n"
                    "Write the answer using only the retrieved context."
                ),
            },
        ]

    def _no_context_answer(
        self, query_text: str, session: ChatSession
    ) -> RAGChatResponse:
        if _is_greeting(query_text):
            answer = "Hi, I am Chikbot. I can answer questions about Chikooza and poultry farming."
        else:
            answer = (
                "I could not find a clear answer for that. Please ask about Chikooza, "
                "poultry farming, broiler setup, feed, mortality, FCR, disease "
                "prevention, records, purchases, sales, or reports."
            )
        return RAGChatResponse(
            result=answer,
            session_id=str(session.session_id),
            provider="rag-no-context",
            model="knowledge-base",
            fallback=True,
            display=self._display_payload(answer, []),
        )

    def _not_enough_matching_context_answer(
        self,
        session: ChatSession,
        reason: str = "",
    ) -> RAGChatResponse:
        answer = (
            "I could not find a clear answer for that. Please rephrase your question "
            "or ask about Chikooza or poultry farming."
        )
        return RAGChatResponse(
            result=answer,
            session_id=str(session.session_id),
            provider="rag-context-not-relevant",
            model=self.groq_model,
            fallback=True,
            display=self._display_payload(answer, []),
        )

    def _groq_unavailable_answer(self, session: ChatSession) -> RAGChatResponse:
        answer = "I could not verify an answer right now. Please try again in a moment."
        return RAGChatResponse(
            result=answer,
            session_id=str(session.session_id),
            provider="groq-unavailable",
            model=self.groq_model,
            fallback=True,
            display=self._display_payload(answer, []),
        )

    def _control_answer(
        self,
        query_text: str,
        session: ChatSession,
    ) -> RAGChatResponse | None:
        normalized = _control_text(query_text)
        if not normalized:
            return None

        if len(normalized) <= 1:
            answer = (
                "I could not understand that. Please ask a specific question about "
                "Chikooza or poultry farming."
            )
        elif _is_greeting(query_text):
            answer = "Hi, I am Chikbot. I can answer questions about Chikooza and poultry farming."
        elif _is_identity_question(normalized):
            answer = (
                "I am Chikbot, Chikooza's assistant for Chikooza and poultry farming "
                "questions."
            )
        elif _is_small_talk(normalized):
            answer = (
                "I am here and ready to help with Chikooza or poultry farming "
                "questions."
            )
        elif normalized in ACKNOWLEDGEMENT_TERMS:
            answer = "Okay. Ask me a question about Chikooza or poultry farming."
        elif _looks_like_gibberish(normalized):
            answer = (
                "I could not understand that clearly. Please rephrase your question "
                "about Chikooza or poultry farming."
            )
        else:
            return None

        return RAGChatResponse(
            result=answer,
            session_id=str(session.session_id),
            provider="chat-control",
            model="knowledge-base",
            fallback=False,
            display=self._display_payload(answer, []),
        )

    def _resolve_session(self, session_id: str | None, user) -> ChatSession:
        authenticated_user = user if getattr(user, "is_authenticated", False) else None
        session = None
        parsed_session_id = self._parse_session_id(session_id)
        if parsed_session_id:
            session = ChatSession.objects.filter(session_id=parsed_session_id).first()
            if (
                session
                and session.user_id
                and authenticated_user
                and session.user_id != authenticated_user.id
            ):
                session = None
            if session and session.user_id and not authenticated_user:
                session = None

        if session is None:
            session = ChatSession.objects.create(
                session_id=uuid.uuid4(),
                user=authenticated_user,
                is_public=not bool(authenticated_user),
            )
        elif authenticated_user and session.user_id is None:
            session.user = authenticated_user
            session.is_public = False
            session.save(update_fields=["user", "is_public", "updated_at"])
        return session

    def _parse_session_id(self, session_id: str | None):
        if not session_id:
            return None
        try:
            return uuid.UUID(str(session_id))
        except (TypeError, ValueError):
            return None

    def _session_history(self, session: ChatSession) -> list[dict[str, str]]:
        messages = list(session.messages.order_by("-created_at", "-id")[:8])
        return [
            {
                "role": message.role,
                "content": _clip(message.content, 400),
            }
            for message in reversed(messages)
        ]

    def _sanitize_client_history(
        self,
        history: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        clean_history = []
        for message in history[-6:]:
            role = str(message.get("role", "")).strip().lower()
            if role == "bot":
                role = ChatMessage.ROLE_ASSISTANT
            if role not in {ChatMessage.ROLE_USER, ChatMessage.ROLE_ASSISTANT}:
                continue
            content = _clip(str(message.get("content", "")).strip(), 400)
            if content:
                clean_history.append({"role": role, "content": content})
        return clean_history

    def _store_exchange(
        self,
        session: ChatSession,
        query_text: str,
        response: RAGChatResponse,
    ):
        with transaction.atomic():
            ChatMessage.objects.create(
                session=session,
                role=ChatMessage.ROLE_USER,
                content=query_text,
            )
            ChatMessage.objects.create(
                session=session,
                role=ChatMessage.ROLE_ASSISTANT,
                content=response.result,
                sources=response.sources,
                provider=response.provider,
                model=response.model,
                fallback=response.fallback,
            )
            if not session.title:
                session.title = _clip(query_text, 150)
                session.save(update_fields=["title", "updated_at"])
            else:
                session.save(update_fields=["updated_at"])

    def _history_prompt_text(self, history: list[dict[str, str]]) -> str:
        if not history:
            return "No recent conversation."
        return "\n".join(
            f"- {message['role']}: {_clip(message['content'], 320)}"
            for message in history[-8:]
        )

    def _context_text(self, chunks: list[RetrievedChunk], *, limit: int) -> str:
        return "\n\n".join(
            f"[{index}] Source: {chunk.source_label}\n{_clip(chunk.content, limit)}"
            for index, chunk in enumerate(chunks, start=1)
        )

    def _sources(self, chunks: list[RetrievedChunk]) -> list[dict]:
        sources = []
        seen = set()
        for chunk in chunks:
            payload = chunk.as_source()
            key = (payload["source"], payload["page"], payload["chunk_id"])
            if key not in seen:
                seen.add(key)
                sources.append(payload)
        return sources

    def _display_payload(self, answer: str, sources: list[dict]) -> dict:
        lines = [
            line.strip() for line in str(answer or "").splitlines() if line.strip()
        ]
        summary = []
        items = []
        for line in lines:
            bullet = re.match(r"^(?:[-*•]|\d+[.)])\s*(.+)$", line)
            if bullet:
                items.append(self._clean_display_text(bullet.group(1)))
            elif items:
                items[-1] = f"{items[-1]} {self._clean_display_text(line)}".strip()
            else:
                summary.append(self._clean_display_text(line))
        return {
            "kind": "public_answer",
            "summary": " ".join(summary) or self._clean_display_text(answer),
            "items": items,
            "sources": sources,
        }

    def _clean_display_text(self, text: str) -> str:
        return re.sub(r"\*\*(.*?)\*\*", r"\1", str(text or "")).strip()


def _normalize_query(query_text: str) -> str:
    normalized = query_text.strip()
    for pattern, replacement in QUERY_NORMALIZATIONS:
        normalized = pattern.sub(replacement, normalized)
    return normalized


def _question_for_retrieval(query_text: str) -> str:
    normalized = _strip_leading_acknowledgement(_normalize_query(query_text))
    terms = set(_tokens(normalized))
    if _should_expand_generic_farming_question(terms):
        normalized = (
            f"{normalized} poultry broiler farm setup shed litter feeders drinkers "
            "brooding ventilation feed water vaccination daily checks"
        )
    return normalized


def _strip_leading_acknowledgement(text: str) -> str:
    clean = str(text or "").strip()
    if not clean:
        return clean

    while True:
        for term in sorted(ACKNOWLEDGEMENT_TERMS, key=len, reverse=True):
            match = re.match(
                rf"^\s*{re.escape(term)}(?:[\s,.!?]+)(.+)$",
                clean,
                flags=re.IGNORECASE,
            )
            if match and match.group(1).strip():
                clean = match.group(1).strip()
                break
        else:
            return clean


def _should_expand_generic_farming_question(terms: set[str]) -> bool:
    if terms & _out_of_scope_terms():
        return False
    if terms & POULTRY_CONTEXT_TERMS:
        return False
    domain_terms = terms & DOMAIN_TERMS
    if not domain_terms or not domain_terms <= {"farm", "farmer"}:
        return False
    return terms <= _generic_farming_terms()


def _generic_farming_terms() -> set[str]:
    return {_stem_token(term) for term in GENERIC_FARMING_QUERY_TERMS}


def _out_of_scope_terms() -> set[str]:
    return {_stem_token(term) for term in OUT_OF_SCOPE_TERMS}


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").lower()).strip()


def _tokens(text: str) -> list[str]:
    tokens = []
    for token in re.findall(r"[a-zA-Z][a-zA-Z0-9]+", _normalize_text(text)):
        if token in STOP_WORDS:
            continue
        tokens.append(_stem_token(token))
    return tokens


def _stem_token(token: str) -> str:
    known_terms = DOMAIN_TERMS
    singular = token[:-1]
    if singular in known_terms:
        return singular
    for suffix in ("ies", "ing", "ed", "es", "s"):
        if len(token) > len(suffix) + 3 and token.endswith(suffix):
            if suffix == "ies":
                return token[: -len(suffix)] + "y"
            return token[: -len(suffix)]
    return token


def _lexical_score(query_terms: set[str], text: str) -> float:
    if not query_terms:
        return 0
    text_terms = set(_tokens(text))
    if not text_terms:
        return 0
    matches = query_terms & text_terms
    if not matches:
        return 0
    return len(matches) / max(len(query_terms), 1)


def _cosine_similarity(left: Iterable[float], right: Iterable[float]) -> float:
    left_values = [float(value) for value in left or []]
    right_values = [float(value) for value in right or []]
    if not left_values or not right_values or len(left_values) != len(right_values):
        return 0
    dot_product = sum(a * b for a, b in zip(left_values, right_values))
    left_norm = math.sqrt(sum(value * value for value in left_values))
    right_norm = math.sqrt(sum(value * value for value in right_values))
    if not left_norm or not right_norm:
        return 0
    return dot_product / (left_norm * right_norm)


def _vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(f"{float(value):.8f}" for value in vector) + "]"


def _clip(text: str, limit: int = 500) -> str:
    clean = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(clean) <= limit:
        return clean
    return clean[: limit - 1].rstrip() + "..."


def _clean_public_answer(text: str) -> str:
    clean = str(text or "").strip()
    clean = re.sub(
        r"(?is)^\s*(?:based on|according to)\s+(?:the\s+)?(?:retrieved\s+)?"
        r"(?:chikooza\s+)?(?:knowledge[-\s]?base\s+)?"
        r"(?:context|snippets|documents|sources)\s*,?\s*",
        "",
        clean,
    )
    clean = re.sub(
        r"(?i)\s+from\s+the\s+Chikooza\s+knowledge[-\s]?base\b",
        "",
        clean,
    )
    return clean.strip()


def _is_greeting(query_text: str) -> bool:
    normalized = _control_text(query_text)
    if normalized in GREETING_TERMS:
        return True
    terms = set(_tokens(query_text))
    return bool(terms) and terms <= GREETING_TERMS


def _is_identity_question(normalized: str) -> bool:
    if normalized in IDENTITY_CONTROL_TEXTS:
        return True
    return bool(
        re.search(r"\b(?:what|who)\s+(?:are|is)\s+(?:you|chikbot)\b", normalized)
        or re.search(r"\b(?:what|how)\s+can\s+you\s+(?:do|help)\b", normalized)
    )


def _is_small_talk(normalized: str) -> bool:
    return normalized in SMALL_TALK_CONTROL_TEXTS


def _json_object(text: str) -> dict:
    raw_text = str(text or "").strip()
    if not raw_text:
        return {}
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw_text, flags=re.DOTALL)
        if not match:
            return {}
        try:
            payload = json.loads(match.group(0))
        except json.JSONDecodeError:
            return {}
    return payload if isinstance(payload, dict) else {}


def _control_text(text: str) -> str:
    clean = re.sub(r"[^a-zA-Z0-9\s]", " ", str(text or "").lower())
    return re.sub(r"\s+", " ", clean).strip()


def _looks_like_gibberish(text: str) -> bool:
    tokens = re.findall(r"[a-zA-Z0-9]+", text)
    if not tokens:
        return True
    if len(tokens) == 1 and len(tokens[0]) <= 2:
        return True

    alpha_tokens = [token for token in tokens if re.search(r"[a-zA-Z]", token)]
    if not alpha_tokens:
        return True

    letters = "".join(alpha_tokens)
    if len(letters) <= 4 and not (
        {_stem_token(token) for token in alpha_tokens} & DOMAIN_TERMS
    ):
        return True

    vowel_count = sum(1 for char in letters.lower() if char in "aeiou")
    return len(letters) >= 5 and vowel_count == 0


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}
