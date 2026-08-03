"""Groq chat-completions adapter.

Implemented against the REST endpoint using the standard library so that the Groq SDK is not a
hard dependency of the application: the commander brief must keep working when the LLM layer is
absent, unconfigured, or unreachable.
"""

import json
import urllib.error
import urllib.request
from collections.abc import Sequence
from typing import Any

from app.core.llm.base import BaseLLMProvider, ChatMessage
from app.core.llm.factory import LLMProviderFactory
from app.exceptions import LLMProviderNotConfiguredError

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

DEFAULT_MODEL = "llama-3.3-70b-versatile"
DEFAULT_TIMEOUT_SECONDS = 8.0
DEFAULT_TEMPERATURE = 0.2
DEFAULT_MAX_TOKENS = 600


class GroqProviderError(RuntimeError):
    """Raised when Groq cannot produce a completion.

    Distinct from the configuration error so callers can tell "not set up" from "set up but
    failing", and fall back on either.
    """


class GroqProvider(BaseLLMProvider):
    """Minimal Groq client covering the single call the commander brief needs."""

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> None:
        if not api_key or not api_key.strip():
            raise LLMProviderNotConfiguredError("A Groq API key is required.")
        self._api_key = api_key.strip()
        self._model = model or DEFAULT_MODEL
        self._timeout_seconds = timeout_seconds
        self._temperature = temperature
        self._max_tokens = max_tokens

    @property
    def model(self) -> str:
        """The model identifier requests are sent to."""
        return self._model

    def generate(self, prompt: str, **options: Any) -> str:
        """Generate text for a single user prompt."""
        return self.chat([ChatMessage(role="user", content=prompt)], **options)

    def chat(self, messages: Sequence[ChatMessage], **options: Any) -> str:
        """Send a chat completion request and return the assistant's text.

        Every failure mode — transport, HTTP status, malformed payload — surfaces as
        ``GroqProviderError`` so a caller can fall back with one except clause.
        """
        payload = {
            "model": options.get("model", self._model),
            "messages": [{"role": item.role, "content": item.content} for item in messages],
            "temperature": options.get("temperature", self._temperature),
            "max_tokens": options.get("max_tokens", self._max_tokens),
        }

        request = urllib.request.Request(
            GROQ_API_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        timeout = float(options.get("timeout_seconds", self._timeout_seconds))
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            # The response body may carry a useful reason; never include the request headers,
            # which hold the API key.
            detail = ""
            try:
                detail = exc.read().decode("utf-8")[:200]
            except Exception:  # noqa: BLE001 - diagnostic only
                detail = ""
            raise GroqProviderError(f"Groq returned HTTP {exc.code}. {detail}".strip()) from exc
        except urllib.error.URLError as exc:
            raise GroqProviderError(f"Groq request failed: {exc.reason}") from exc
        except (TimeoutError, OSError) as exc:
            raise GroqProviderError(f"Groq request failed: {type(exc).__name__}") from exc
        except json.JSONDecodeError as exc:
            raise GroqProviderError("Groq returned a malformed response.") from exc

        try:
            content = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise GroqProviderError("Groq response did not contain a completion.") from exc

        if not isinstance(content, str) or not content.strip():
            raise GroqProviderError("Groq returned an empty completion.")
        return content.strip()


LLMProviderFactory.register("groq", GroqProvider)
