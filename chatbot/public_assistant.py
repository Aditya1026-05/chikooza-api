import os
from dataclasses import dataclass

import httpx

PUBLIC_SITE_CONTEXT = """
Chikooza is a poultry farm management MVP for farmers and farm operators.
It helps users register/login, manage farms and flocks, record daily flock data,
track mortality, feed intake, average weight and FCR, record purchases, record
sales, view summaries, export reports/PDFs, and ask authenticated AI questions
about their own farm data. The public website assistant must explain the product,
guide visitors to register or login, and avoid claiming access to private farmer
records. Private farm-data questions should be answered only after login through
the authenticated AI assistant.
""".strip()


PUBLIC_SYSTEM_PROMPT = f"""
You are ChikBOT, the public assistant for Chikooza.

Use this product context:
{PUBLIC_SITE_CONTEXT}

Rules:
- Explain Chikooza clearly in simple English.
- Keep answers practical and concise.
- If a visitor asks for private farm/flock/sales/purchase data, tell them to log
  in and use the authenticated farmer assistant.
- Do not invent pricing, company claims, medical/veterinary guarantees, or access
  to private user data.
- You can answer general product onboarding questions without login.
""".strip()


@dataclass
class PublicAssistantResponse:
    result: str
    provider: str
    model: str
    fallback: bool = False


class PublicSiteAssistant:
    """
    U: NEW: public website assistant for unauthenticated visitors.
    U: It uses Groq or Ollama when configured, and falls back to a deterministic
    U: product answer so the homepage chatbot remains usable during local setup.
    """

    def __init__(self):
        self.provider = (
            os.getenv("CHIKOOZA_PUBLIC_CHAT_PROVIDER", "auto").strip().lower()
        )
        self.groq_api_key = os.getenv("GROQ_API_KEY", "").strip()
        self.groq_model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant").strip()
        self.groq_base_url = os.getenv(
            "GROQ_API_BASE_URL",
            "https://api.groq.com/openai/v1",
        ).rstrip("/")
        self.ollama_base_url = os.getenv(
            "OLLAMA_BASE_URL", "http://localhost:11434"
        ).rstrip("/")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "gemma3:1b").strip()
        self.timeout = float(os.getenv("CHIKOOZA_PUBLIC_CHAT_TIMEOUT", "20"))

    def answer(self, query_text: str) -> PublicAssistantResponse:
        provider = self._select_provider()

        if provider == "groq":
            try:
                return self._answer_with_groq(query_text)
            except Exception:
                return self._fallback_answer(provider="fallback", model="deterministic")

        if provider == "ollama":
            try:
                return self._answer_with_ollama(query_text)
            except Exception:
                return self._fallback_answer(provider="fallback", model="deterministic")

        return self._fallback_answer(provider="fallback", model="deterministic")

    def _select_provider(self) -> str:
        if self.provider in {"groq", "ollama", "fallback"}:
            return self.provider

        if self.provider != "auto":
            return "fallback"

        if self.groq_api_key:
            return "groq"

        if self.ollama_base_url and self.ollama_model:
            return "ollama"

        return "fallback"

    def _answer_with_groq(self, query_text: str) -> PublicAssistantResponse:
        if not self.groq_api_key:
            raise RuntimeError("GROQ_API_KEY is not configured.")

        payload = {
            "model": self.groq_model,
            "messages": self._messages(query_text),
            "temperature": 0.2,
            "max_tokens": 420,
        }
        response = httpx.post(
            f"{self.groq_base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.groq_api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"].strip()
        return PublicAssistantResponse(
            result=content,
            provider="groq",
            model=self.groq_model,
        )

    def _answer_with_ollama(self, query_text: str) -> PublicAssistantResponse:
        payload = {
            "model": self.ollama_model,
            "messages": self._messages(query_text),
            "stream": False,
            "options": {"temperature": 0.2},
        }
        response = httpx.post(
            f"{self.ollama_base_url}/api/chat",
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        content = response.json()["message"]["content"].strip()
        return PublicAssistantResponse(
            result=content,
            provider="ollama",
            model=self.ollama_model,
        )

    def _messages(self, query_text: str) -> list[dict[str, str]]:
        return [
            {"role": "system", "content": PUBLIC_SYSTEM_PROMPT},
            {"role": "user", "content": query_text},
        ]

    def _fallback_answer(self, provider: str, model: str) -> PublicAssistantResponse:
        return PublicAssistantResponse(
            result=(
                "Chikooza is a poultry farm management MVP for tracking farms, "
                "flocks, daily flock health, mortality, feed, FCR, purchases, "
                "sales, summaries, and reports. Visitors can register or login "
                "to manage their own farm data. For private farm-specific AI "
                "questions, please login first so the authenticated assistant can "
                "answer only from your own data."
            ),
            provider=provider,
            model=model,
            fallback=True,
        )
