"""Vendor-neutral contracts for future LLM integrations."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Sequence


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str


class BaseLLMProvider(ABC):
    """Contract that every LLM provider adapter must satisfy."""

    @abstractmethod
    def generate(self, prompt: str, **options: Any) -> str:
        """Generate text for a prompt."""

    @abstractmethod
    def chat(self, messages: Sequence[ChatMessage], **options: Any) -> str:
        """Generate a chat response from normalized messages."""
