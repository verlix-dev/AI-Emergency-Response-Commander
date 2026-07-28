"""Registry-backed creation of vendor-neutral LLM provider adapters."""

from typing import Type

from app.core.llm.base import BaseLLMProvider
from app.exceptions import LLMProviderNotConfiguredError


class LLMProviderFactory:
    """Keep provider selection isolated from application modules."""

    _providers: dict[str, Type[BaseLLMProvider]] = {}

    @classmethod
    def register(cls, name: str, provider: Type[BaseLLMProvider]) -> None:
        cls._providers[name.lower()] = provider

    @classmethod
    def create(cls, name: str, **options: object) -> BaseLLMProvider:
        provider = cls._providers.get(name.lower())
        if provider is None:
            raise LLMProviderNotConfiguredError("The requested LLM provider is not configured.")
        return provider(**options)
