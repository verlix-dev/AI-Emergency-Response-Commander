"""Tests for the Groq provider and the LLM commander-brief narration layer.

The narration layer is optional by design: these tests assert that it improves the brief when
it works and is invisible when it does not. No test contacts Groq; the provider is faked at the
transport boundary so the whole matrix is deterministic and offline.
"""

import os

os.environ.setdefault("APP_NAME", "ARES API")
os.environ.setdefault("APP_VERSION", "1.0.0")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("API_V1_PREFIX", "/api/v1")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("UPLOAD_DIRECTORY", "uploads")
os.environ.setdefault("LOG_LEVEL", "INFO")
os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("MAX_UPLOAD_SIZE", "10")
os.environ.setdefault("CORS_ORIGINS", '["http://localhost:3000"]')
os.environ.setdefault("TRUSTED_HOSTS", '["testserver"]')

import pytest

from app.core.llm import LLMProviderFactory
from app.core.llm.base import ChatMessage
from app.core.llm.providers.groq_provider import GroqProvider, GroqProviderError
from app.engines.allocation_engine import AllocationEngine
from app.engines.decision_engine import DecisionEngine
from app.engines.models import IncidentAssessment
from app.exceptions import LLMProviderNotConfiguredError
from app.services.commander_brief import CommanderBriefGenerator
from app.services.commander_brief_llm import CommanderBriefLLMService

ASSESSMENT = IncidentAssessment(
    incident_type="Building Fire",
    victims=4,
    trapped_people=1,
    people_detected=9,
    fire_detected=True,
    smoke_detected=True,
    hospital_distance_km=6,
    weather="clear",
)


@pytest.fixture(scope="module")
def analysis() -> tuple:
    """A real decision, allocation, and deterministic brief to narrate."""
    decision = DecisionEngine().decide(ASSESSMENT)
    allocation = AllocationEngine().allocate(ASSESSMENT, decision)
    brief = CommanderBriefGenerator().generate(ASSESSMENT, decision, allocation)
    return decision, allocation, brief


class FakeProvider:
    """Stands in for GroqProvider, returning scripted text or raising."""

    def __init__(self, response: str | None = None, error: Exception | None = None) -> None:
        self._response = response
        self._error = error
        self.calls: list[list[ChatMessage]] = []

    def chat(self, messages, **options):
        self.calls.append(list(messages))
        if self._error is not None:
            raise self._error
        return self._response


class TestGroqProviderConfiguration:
    def test_missing_api_key_is_rejected(self) -> None:
        with pytest.raises(LLMProviderNotConfiguredError):
            GroqProvider(api_key="")

    def test_whitespace_api_key_is_rejected(self) -> None:
        with pytest.raises(LLMProviderNotConfiguredError):
            GroqProvider(api_key="   ")

    def test_provider_is_registered_with_the_factory(self) -> None:
        assert "groq" in LLMProviderFactory._providers

    def test_default_model_is_applied(self) -> None:
        assert GroqProvider(api_key="test-key").model

    def test_explicit_model_overrides_the_default(self) -> None:
        assert GroqProvider(api_key="test-key", model="custom-model").model == "custom-model"


class TestGroqProviderTransport:
    def test_http_error_becomes_a_provider_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import urllib.error

        def raise_http(*args, **kwargs):
            raise urllib.error.HTTPError("url", 429, "Too Many Requests", {}, None)

        monkeypatch.setattr("urllib.request.urlopen", raise_http)

        with pytest.raises(GroqProviderError):
            GroqProvider(api_key="k").generate("hello")

    def test_timeout_becomes_a_provider_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def raise_timeout(*args, **kwargs):
            raise TimeoutError("timed out")

        monkeypatch.setattr("urllib.request.urlopen", raise_timeout)

        with pytest.raises(GroqProviderError):
            GroqProvider(api_key="k").generate("hello")

    def test_malformed_response_becomes_a_provider_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        class FakeResponse:
            def read(self):
                return b'{"unexpected": true}'

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        monkeypatch.setattr("urllib.request.urlopen", lambda *a, **k: FakeResponse())

        with pytest.raises(GroqProviderError):
            GroqProvider(api_key="k").generate("hello")

    def test_api_key_is_never_included_in_an_error_message(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A leaked key in a log line or error response would be a credential disclosure."""
        import urllib.error

        secret = "gsk-super-secret-key-value"

        def raise_http(*args, **kwargs):
            raise urllib.error.HTTPError("url", 401, "Unauthorized", {}, None)

        monkeypatch.setattr("urllib.request.urlopen", raise_http)

        with pytest.raises(GroqProviderError) as exc_info:
            GroqProvider(api_key=secret).generate("hello")

        assert secret not in str(exc_info.value)


class TestNarrationDisabled:
    def test_no_provider_returns_the_deterministic_brief(self, analysis: tuple) -> None:
        decision, allocation, brief = analysis

        outcome = CommanderBriefLLMService(provider=None).narrate(
            brief, ASSESSMENT, decision, allocation
        )

        assert outcome.narrated is False
        assert outcome.reason == "no_provider_configured"
        assert outcome.brief == brief

    def test_service_reports_disabled(self) -> None:
        assert CommanderBriefLLMService(provider=None).is_enabled is False


class TestNarrationFallback:
    def test_provider_error_falls_back(self, analysis: tuple) -> None:
        decision, allocation, brief = analysis
        service = CommanderBriefLLMService(provider=FakeProvider(error=GroqProviderError("down")))

        outcome = service.narrate(brief, ASSESSMENT, decision, allocation)

        assert outcome.narrated is False
        assert outcome.reason == "provider_error"
        assert outcome.brief.incident_summary == brief.incident_summary

    def test_unexpected_error_falls_back(self, analysis: tuple) -> None:
        decision, allocation, brief = analysis
        service = CommanderBriefLLMService(provider=FakeProvider(error=RuntimeError("boom")))

        outcome = service.narrate(brief, ASSESSMENT, decision, allocation)

        assert outcome.narrated is False
        assert outcome.brief == brief

    def test_empty_completion_falls_back(self, analysis: tuple) -> None:
        decision, allocation, brief = analysis
        service = CommanderBriefLLMService(provider=FakeProvider(response="   "))

        outcome = service.narrate(brief, ASSESSMENT, decision, allocation)

        assert outcome.narrated is False
        assert outcome.brief == brief


class TestGroundingValidator:
    """The structural guarantee: ungrounded narration is rejected, not displayed."""

    def test_grounded_narration_is_accepted(self, analysis: tuple) -> None:
        decision, allocation, brief = analysis
        text = (
            f"Building fire in progress. Severity is {decision.severity_level.value}. "
            "Fire and smoke are confirmed on scene. Commit suppression crews and "
            "establish a rescue team before entry."
        )
        service = CommanderBriefLLMService(provider=FakeProvider(response=text))

        outcome = service.narrate(brief, ASSESSMENT, decision, allocation)

        assert outcome.narrated is True
        assert outcome.brief.incident_summary == text

    def test_invented_casualty_count_is_rejected(self, analysis: tuple) -> None:
        """The most dangerous failure mode: a number the engines never produced."""
        decision, allocation, brief = analysis
        service = CommanderBriefLLMService(
            provider=FakeProvider(response="Fire with 47 casualties reported on scene.")
        )

        outcome = service.narrate(brief, ASSESSMENT, decision, allocation)

        assert outcome.narrated is False
        assert outcome.reason.startswith("ungrounded:unsourced_number")
        assert outcome.brief == brief

    def test_contradicting_the_severity_grading_is_rejected(self, analysis: tuple) -> None:
        decision, allocation, brief = analysis
        assigned = {
            decision.severity_level.value,
            decision.priority_level.value,
            decision.confidence_level.value,
        }
        wrong = next(
            level
            for level in ("MINOR", "MODERATE", "HIGH", "SEVERE", "CRITICAL")
            if level not in assigned
        )
        service = CommanderBriefLLMService(
            provider=FakeProvider(response=f"This incident is graded {wrong} and needs response.")
        )

        outcome = service.narrate(brief, ASSESSMENT, decision, allocation)

        assert outcome.narrated is False
        assert "contradicts_grading" in outcome.reason

    def test_overlong_narration_is_rejected(self, analysis: tuple) -> None:
        decision, allocation, brief = analysis
        service = CommanderBriefLLMService(
            provider=FakeProvider(response="word " * 400), max_words=250
        )

        outcome = service.narrate(brief, ASSESSMENT, decision, allocation)

        assert outcome.narrated is False
        assert outcome.reason == "ungrounded:too_long"

    def test_engine_supplied_numbers_are_permitted(self, analysis: tuple) -> None:
        decision, allocation, brief = analysis
        text = (
            f"Severity {decision.severity_score} of 100. "
            f"Confidence {round(decision.confidence * 100)} percent."
        )
        service = CommanderBriefLLMService(provider=FakeProvider(response=text))

        outcome = service.narrate(brief, ASSESSMENT, decision, allocation)

        assert outcome.narrated is True

    def test_resource_quantities_from_the_allocation_are_permitted(
        self, analysis: tuple
    ) -> None:
        decision, allocation, brief = analysis
        quantity = allocation.recommendations[0].quantity
        service = CommanderBriefLLMService(
            provider=FakeProvider(response=f"Dispatch {quantity} units immediately.")
        )

        outcome = service.narrate(brief, ASSESSMENT, decision, allocation)

        assert outcome.narrated is True


class TestPromptConstruction:
    def test_prompt_contains_only_engine_facts(self, analysis: tuple) -> None:
        decision, allocation, brief = analysis
        provider = FakeProvider(response="Grounded summary.")

        CommanderBriefLLMService(provider=provider).narrate(
            brief, ASSESSMENT, decision, allocation
        )

        prompt = provider.calls[0][1].content
        assert decision.severity_level.value in prompt
        assert decision.priority_level.value in prompt
        assert "not reported" in prompt

    def test_system_prompt_forbids_invention(self, analysis: tuple) -> None:
        decision, allocation, brief = analysis
        provider = FakeProvider(response="Grounded summary.")

        CommanderBriefLLMService(provider=provider).narrate(
            brief, ASSESSMENT, decision, allocation
        )

        system = provider.calls[0][0].content.lower()
        assert "never invent" in system
        assert "250 words" in system

    def test_unreported_fields_are_marked_rather_than_omitted(self) -> None:
        """Silence invites the model to guess; explicit 'not reported' does not."""
        sparse = IncidentAssessment(incident_type="Flood")
        sparse_decision = DecisionEngine().decide(sparse)
        sparse_allocation = AllocationEngine().allocate(sparse, sparse_decision)
        sparse_brief = CommanderBriefGenerator().generate(
            sparse, sparse_decision, sparse_allocation
        )
        provider = FakeProvider(response="Flood reported.")

        CommanderBriefLLMService(provider=provider).narrate(
            sparse_brief, sparse, sparse_decision, sparse_allocation
        )

        prompt = provider.calls[0][1].content
        assert prompt.count("not reported") >= 5


class TestDeterministicFieldsSurviveNarration:
    """Narration may only rewrite prose. Every decided value must pass through untouched."""

    def test_only_the_summary_is_replaced(self, analysis: tuple) -> None:
        decision, allocation, brief = analysis
        service = CommanderBriefLLMService(provider=FakeProvider(response="New prose summary."))

        outcome = service.narrate(brief, ASSESSMENT, decision, allocation)

        assert outcome.brief.incident_summary == "New prose summary."
        assert outcome.brief.severity == brief.severity
        assert outcome.brief.priority == brief.priority
        assert outcome.brief.immediate_actions == brief.immediate_actions
        assert outcome.brief.recommended_resources == brief.recommended_resources
        assert outcome.brief.risk_factors == brief.risk_factors
        assert outcome.brief.operational_notes == brief.operational_notes
