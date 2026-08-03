"""Integration tests for LLM-narrated commander briefs in the analysis workflow.

The narration layer must be invisible to the API contract: the response shape is identical,
every deterministic field is untouched, and only the brief's summary paragraph may change.
When narration is unavailable the workflow behaves exactly as it did before the feature.
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

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Annotated

from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import (
    get_incident_analysis_service,
    get_vision_service,
)
from app.database.base import Base
from app.database.session import get_db_session
from app.engines.allocation_engine import AllocationEngine
from app.engines.decision_engine import DecisionEngine
from app.main import app
from app.models.resource import Resource
from app.repositories import IncidentRepository, ResourceRepository
from app.services.commander_brief import CommanderBriefGenerator
from app.services.commander_brief_llm import CommanderBriefLLMService, NarrationOutcome
from app.services.incident_analysis import IncidentAnalysisService
from app.vision import StaticDetector, VisionService

SCENE = [
    {"class": "fire", "confidence": 0.91, "bbox": [200, 200, 400, 400]},
    {"class": "smoke", "confidence": 0.86, "bbox": [200, 50, 500, 200]},
    {"class": "building", "confidence": 0.95, "bbox": [100, 100, 700, 800]},
    {"class": "person", "confidence": 0.9, "bbox": [10, 600, 60, 750]},
]

IMAGE_BYTES = b"fake-image-payload"

NARRATED_SUMMARY = "Smoke confirmed on the second floor with fire present; deploy suppression and rescue capability."


class ScriptedNarrator(CommanderBriefLLMService):
    """A narration service that always narrates, recording whether it was invoked."""

    def __init__(self) -> None:
        super().__init__(provider=None)
        self.calls = 0
        self._enabled = True

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    def narrate(self, brief, assessment, decision, allocation):
        self.calls += 1
        return NarrationOutcome(
            brief.model_copy(update={"incident_summary": NARRATED_SUMMARY}),
            True,
            "narrated",
        )


class FailingNarrator(ScriptedNarrator):
    """A narration service that always fails, forcing the deterministic fallback."""

    def narrate(self, brief, assessment, decision, allocation):
        self.calls += 1
        return NarrationOutcome(brief, False, "provider_error")


class DisabledNarrator(CommanderBriefLLMService):
    """A narration service that is configured but disabled, as when no key is set."""

    @property
    def is_enabled(self) -> bool:
        return False


@contextmanager
def build_client(narrator) -> Iterator[TestClient]:
    """Assemble the app with an in-memory database and a scripted vision detector."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    seed = factory()
    seed.add(
        Resource(
            resource_type="fire_truck",
            resource_name="Engine 1",
            status="AVAILABLE",
            available=True,
        )
    )
    seed.add(
        Resource(
            resource_type="ambulance",
            resource_name="Ambulance 1",
            status="AVAILABLE",
            available=True,
        )
    )
    seed.commit()
    seed.close()

    def override_session() -> Iterator[Session]:
        session = factory()
        try:
            yield session
        finally:
            session.close()

    def override_analysis_service(session: Annotated[Session, Depends(get_db_session)]):
        return IncidentAnalysisService(
            vision_service=VisionService(
                detector=StaticDetector(detections=SCENE, frame=(1000, 1000))
            ),
            decision_engine=DecisionEngine(),
            allocation_engine=AllocationEngine(),
            brief_generator=CommanderBriefGenerator(),
            brief_narrator=narrator,
            incident_repository=IncidentRepository(session),
            resource_repository=ResourceRepository(session),
        )

    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_vision_service] = lambda: VisionService(
        detector=StaticDetector(detections=SCENE, frame=(1000, 1000))
    )
    app.dependency_overrides[get_incident_analysis_service] = override_analysis_service
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()


class TestNarratedWorkflow:
    def test_response_contract_is_unchanged(self) -> None:
        with build_client(ScriptedNarrator()) as client:
            payload = client.post(
                "/incidents/analyze",
                files={"image": ("scene.jpg", IMAGE_BYTES, "image/jpeg")},
                data={"location": "Mumbai"},
            ).json()

        assert set(payload) == {
            "incident",
            "assessment",
            "decision",
            "resources",
            "commander_brief",
            "scene",
            "timestamp",
        }

    def test_deterministic_fields_are_untouched_by_narration(self) -> None:
        with build_client(ScriptedNarrator()) as client:
            payload = client.post(
                "/incidents/analyze",
                files={"image": ("scene.jpg", IMAGE_BYTES, "image/jpeg")},
            ).json()

        brief = payload["commander_brief"]
        decision = payload["decision"]

        assert brief["incident_summary"] == NARRATED_SUMMARY
        assert decision["severity_level"] is not None
        assert decision["priority_level"] is not None
        assert payload["scene"]["detections"]
        assert payload["resources"]["recommendations"]

    def test_narrator_is_invoked_once_per_analysis(self) -> None:
        narrator = ScriptedNarrator()
        with build_client(narrator) as client:
            client.post(
                "/incidents/analyze",
                files={"image": ("scene.jpg", IMAGE_BYTES, "image/jpeg")},
            )
            client.post(
                "/incidents/analyze",
                files={"image": ("scene2.jpg", IMAGE_BYTES, "image/jpeg")},
            )

        assert narrator.calls == 2

    def test_failing_narration_returns_the_deterministic_brief(self) -> None:
        with build_client(FailingNarrator()) as client:
            payload = client.post(
                "/incidents/analyze",
                files={"image": ("scene.jpg", IMAGE_BYTES, "image/jpeg")},
            ).json()

        brief = payload["commander_brief"]

        assert brief["incident_summary"] != NARRATED_SUMMARY
        assert brief["immediate_actions"]
        assert brief["operational_notes"]
        assert payload["decision"]["severity_level"] is not None

    def test_disabled_narration_returns_the_deterministic_brief(self) -> None:
        with build_client(DisabledNarrator()) as client:
            payload = client.post(
                "/incidents/analyze",
                files={"image": ("scene.jpg", IMAGE_BYTES, "image/jpeg")},
            ).json()

        assert payload["commander_brief"]["incident_summary"]

    def test_shortfall_messages_are_preserved_when_narration_is_disabled(self) -> None:
        with build_client(DisabledNarrator()) as client:
            payload = client.post(
                "/incidents/analyze",
                files={"image": ("scene.jpg", IMAGE_BYTES, "image/jpeg")},
            ).json()

        notes = " ".join(payload["commander_brief"]["operational_notes"])

        assert "shortfall" in notes.lower()
