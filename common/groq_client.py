import logging
import os
import threading
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)


class GroqAllKeysFailed(RuntimeError):
    """Raised when every configured Groq key fails for a retryable reason."""


@dataclass(frozen=True)
class GroqChatResult:
    content: str
    model: str


class GroqChatClient:
    """
    Shared Groq client with key rotation and optional model fallback.

    Keys rotate when a request is rate-limited, invalid, timed out, or the API
    is temporarily unavailable.
    """

    RETRYABLE_STATUS_CODES = {401, 403, 408, 409, 425, 429, 500, 502, 503, 504}
    LEGACY_KEY_NAMES = (
        "GROQ_API_KEY",
        "GROQ_API_KEY_ONE",
        "GROQ_API_KEY_TWO",
        "GROQ_API_KEY_THREE",
        "GROQ_API_KEY_FOUR",
    )

    def __init__(
        self,
        *,
        api_keys: list[str] | None = None,
        base_url: str | None = None,
        model: str | None = None,
        fallback_model: str | None = None,
        timeout: float | None = None,
    ):
        self.api_keys = self._dedupe(
            api_keys if api_keys is not None else self._load_api_keys()
        )
        self.base_url = (
            base_url
            or os.getenv("GROQ_API_BASE_URL")
            or "https://api.groq.com/openai/v1"
        ).rstrip("/")
        self.model = model or os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        self.fallback_model = fallback_model or os.getenv("GROQ_FALLBACK_MODEL", "")
        self.timeout = float(timeout or os.getenv("GROQ_TIMEOUT", "30"))
        self._next_key_index = 0
        self._lock = threading.Lock()

    @property
    def has_keys(self) -> bool:
        return bool(self.api_keys)

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        fallback_model: str | None = None,
        temperature: float = 0,
        max_tokens: int = 1024,
        timeout: float | None = None,
    ) -> GroqChatResult:
        if not self.api_keys:
            raise GroqAllKeysFailed("No Groq API keys are configured.")

        primary_model = model or self.model
        secondary_model = fallback_model or self.fallback_model

        try:
            return self._chat_with_model(
                messages,
                model=primary_model,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
            )
        except GroqAllKeysFailed:
            if secondary_model and secondary_model != primary_model:
                return self._chat_with_model(
                    messages,
                    model=secondary_model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=timeout,
                )
            raise

    def _chat_with_model(
        self,
        messages: list[dict[str, str]],
        *,
        model: str,
        temperature: float,
        max_tokens: int,
        timeout: float | None,
    ) -> GroqChatResult:
        last_error: Exception | None = None
        start_index = self._claim_start_index()

        for offset in range(len(self.api_keys)):
            key_index = (start_index + offset) % len(self.api_keys)
            api_key = self.api_keys[key_index]

            try:
                response = httpx.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    },
                    timeout=timeout or self.timeout,
                )

                if response.status_code in self.RETRYABLE_STATUS_CODES:
                    last_error = httpx.HTTPStatusError(
                        "Retryable Groq response",
                        request=response.request,
                        response=response,
                    )
                    logger.warning(
                        "Groq key #%s failed with retryable status %s; rotating.",
                        key_index + 1,
                        response.status_code,
                    )
                    continue

                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"].strip()
                self._advance_after_success(key_index)
                return GroqChatResult(content=content, model=model)
            except (httpx.TimeoutException, httpx.RequestError) as exc:
                last_error = exc
                logger.warning("Groq key #%s request failed; rotating.", key_index + 1)
                continue

        raise GroqAllKeysFailed("All configured Groq keys failed.") from last_error

    def _claim_start_index(self) -> int:
        with self._lock:
            if not self.api_keys:
                return 0
            return self._next_key_index % len(self.api_keys)

    def _advance_after_success(self, key_index: int):
        with self._lock:
            self._next_key_index = (key_index + 1) % len(self.api_keys)

    def _load_api_keys(self) -> list[str]:
        keys = []
        keys.extend(self._split_keys(os.getenv("GROQ_API_KEYS", "")))
        for name in self.LEGACY_KEY_NAMES:
            value = os.getenv(name, "").strip()
            if value:
                keys.append(value)
        return keys

    def _split_keys(self, value: str) -> list[str]:
        return [item.strip() for item in value.split(",") if item.strip()]

    def _dedupe(self, keys: list[str]) -> list[str]:
        deduped = []
        for key in keys:
            if key and key not in deduped:
                deduped.append(key)
        return deduped
