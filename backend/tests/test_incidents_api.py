"""HTTP-level tests for the incident analysis API."""

import os

os.environ.setdefault("APP_NAME", "ARES API")
os.environ.setdefault("APP_VERSION", "1.0.0")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("API_V1_PREFIX", "/api/v1")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("UPLOAD_DIRECTORY", "uploads")
os.environ.setdefault("LOG_LEVEL", "INFO")
os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("MAX_UPLOAD_SIZE", "5")
os.environ.setdefault("CORS_ORIGINS", '["http://localhost:3000"]')
os.environ.setdefault("TRUSTED_HOSTS", '["testserver"]')

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_vision_service
from app.database.base import Base
from app.database.session import get_db_session
from app.main import app
from app.models.resource import Resource
from app.vision import StaticDetector, VisionService

SCENE = [
    {"class": "fire", "confidence": 0.91, "bbox": [200, 200, 400, 400]},
    {"class": "smoke", "confidence": 0.86, "bbox": [200, 50, 500, 200]},
    {"class": "building", "confidence": 0.95, "bbox": [100, 100, 700, 800]},
    {"class": "person", "confidence": 0.9, "bbox": [10, 600, 60, 750]},
]

IMAGE_BYTES = b"fake-image-payload"


@pytest.fixture
def client() -> Iterator[TestClient]:
    """Provide a client backed by an in-memory database and a scripted detector."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    seed = factory()
    for index in range(1, 4):
        seed.add(
            Resource(
                resource_type="fire_truck",
                resource_name=f"Engine {index}",
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

    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_vision_service] = lambda: VisionService(
        detector=StaticDetector(detections=SCENE, frame=(1000, 1000))
    )
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()


def post_analyze(client: TestClient, **data: str) -> dict:
    response = client.post(
        "/incidents/analyze",
        files={"image": ("scene.jpg", IMAGE_BYTES, "image/jpeg")},
        data=data or None,
    )
    assert response.status_code == 201, response.text
    return response.json()


class TestAnalyzeEndpoint:
    def test_returns_the_full_response_envelope(self, client: TestClient) -> None:
        payload = post_analyze(client)

        assert set(payload) == {
            "incident",
            "assessment",
            "decision",
            "resources",
            "commander_brief",
            "scene",
            "timestamp",
        }

    def test_incident_is_classified_and_persisted(self, client: TestClient) -> None:
        payload = post_analyze(client)

        assert payload["incident"]["incident_type"] == "BUILDING_FIRE"
        assert payload["incident"]["id"]

    def test_brief_sections_are_present(self, client: TestClient) -> None:
        brief = post_analyze(client)["commander_brief"]

        assert brief["incident_summary"]
        assert brief["immediate_actions"]
        assert brief["recommended_resources"]
        assert brief["operational_notes"]

    def test_resources_are_allocated(self, client: TestClient) -> None:
        resources = post_analyze(client)["resources"]

        assert resources["recommendations"]
        assert resources["total_units_requested"] > 0

    def test_optional_form_fields_are_applied(self, client: TestClient) -> None:
        payload = post_analyze(client, location="12 Dock Road", title="Warehouse blaze")

        assert payload["incident"]["location"] == "12 Dock Road"
        assert payload["incident"]["title"] == "Warehouse blaze"

    def test_non_image_upload_is_rejected(self, client: TestClient) -> None:
        response = client.post(
            "/incidents/analyze",
            files={"image": ("notes.txt", b"not an image", "text/plain")},
        )

        assert response.status_code == 400
        assert response.json()["error"]["code"] == "image_not_readable"

    def test_empty_upload_is_rejected(self, client: TestClient) -> None:
        response = client.post(
            "/incidents/analyze",
            files={"image": ("scene.jpg", b"", "image/jpeg")},
        )

        assert response.status_code == 400

    def test_missing_image_is_a_validation_error(self, client: TestClient) -> None:
        response = client.post("/incidents/analyze")

        assert response.status_code == 422


class TestTimelineEndpoint:
    def test_timeline_returns_the_first_revision(self, client: TestClient) -> None:
        incident_id = post_analyze(client)["incident"]["id"]

        response = client.get(f"/incidents/{incident_id}/timeline")

        assert response.status_code == 200
        body = response.json()
        assert body["incident"]["id"] == incident_id
        assert len(body["revisions"]) == 1
        assert body["revisions"][0]["revision"] == 1

    def test_reanalysis_appends_a_revision(self, client: TestClient) -> None:
        incident_id = post_analyze(client)["incident"]["id"]

        second = client.post(
            f"/incidents/{incident_id}/analyze",
            files={"image": ("scene2.jpg", IMAGE_BYTES, "image/jpeg")},
        )
        assert second.status_code == 201

        revisions = client.get(f"/incidents/{incident_id}/timeline").json()["revisions"]

        assert [item["revision"] for item in revisions] == [1, 2]

    def test_unknown_incident_returns_not_found(self, client: TestClient) -> None:
        response = client.get("/incidents/00000000-0000-0000-0000-000000000000/timeline")

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"

    def test_malformed_incident_id_is_a_validation_error(self, client: TestClient) -> None:
        response = client.get("/incidents/not-a-uuid/timeline")

        assert response.status_code == 422


class TestSceneOverlay:
    def test_scene_exposes_detections_with_boxes(self, client: TestClient) -> None:
        scene = post_analyze(client)["scene"]

        assert scene["frame_width"] == 1000
        assert scene["frame_height"] == 1000
        assert len(scene["detections"]) == len(SCENE)
        first = scene["detections"][0]
        assert first["detection_class"]
        assert 0.0 <= first["confidence"] <= 1.0
        assert first["x1"] is not None

    def test_discarded_detections_are_counted(self, client: TestClient) -> None:
        app.dependency_overrides[get_vision_service] = lambda: VisionService(
            detector=StaticDetector(
                detections=[*SCENE, {"class": "giraffe", "confidence": 0.9}],
                frame=(1000, 1000),
            )
        )

        scene = post_analyze(client)["scene"]

        assert scene["discarded_count"] == 1


class TestIncidentListEndpoint:
    def test_empty_before_any_analysis(self, client: TestClient) -> None:
        response = client.get("/incidents")

        assert response.status_code == 200
        body = response.json()
        assert body["incidents"] == []
        assert body["total"] == 0

    def test_lists_analysed_incidents_with_grading(self, client: TestClient) -> None:
        post_analyze(client, title="First scene")

        body = client.get("/incidents").json()

        assert body["total"] == 1
        row = body["incidents"][0]
        assert row["title"] == "First scene"
        assert row["severity_level"]
        assert row["revision_count"] == 1

    def test_newest_incident_is_listed_first(self, client: TestClient) -> None:
        post_analyze(client, title="Older")
        post_analyze(client, title="Newer")

        titles = [item["title"] for item in client.get("/incidents").json()["incidents"]]

        assert titles[0] == "Newer"

    def test_pagination_limits_results(self, client: TestClient) -> None:
        for index in range(3):
            post_analyze(client, title=f"Scene {index}")

        body = client.get("/incidents", params={"limit": 2}).json()

        assert len(body["incidents"]) == 2
        assert body["total"] == 3

    def test_invalid_limit_is_rejected(self, client: TestClient) -> None:
        assert client.get("/incidents", params={"limit": 0}).status_code == 422


class TestResourceInventoryEndpoint:
    def test_inventory_reflects_seeded_pool(self, client: TestClient) -> None:
        response = client.get("/resources/inventory")

        assert response.status_code == 200
        body = response.json()
        assert body["total_units"] == 4
        assert body["available_units"] == 4
        kinds = {item["resource_kind"]: item for item in body["items"]}
        assert kinds["FIRE_TRUCK"]["total"] == 3
        assert kinds["AMBULANCE"]["total"] == 1

    def test_items_carry_human_labels(self, client: TestClient) -> None:
        items = client.get("/resources/inventory").json()["items"]

        assert any(item["label"] == "Fire Trucks" for item in items)

    def test_available_units_are_named(self, client: TestClient) -> None:
        items = client.get("/resources/inventory").json()["items"]
        fire = next(item for item in items if item["resource_kind"] == "FIRE_TRUCK")

        assert sorted(fire["resource_names"]) == ["Engine 1", "Engine 2", "Engine 3"]


class TestSystemStatusEndpoint:
    def test_status_reports_every_component(self, client: TestClient) -> None:
        response = client.get("/system/status")

        assert response.status_code == 200
        body = response.json()
        components = {item["component"] for item in body["components"]}
        assert components == {"database", "vision", "decision", "resources", "api"}

    def test_database_is_operational(self, client: TestClient) -> None:
        body = client.get("/system/status").json()
        database = next(item for item in body["components"] if item["component"] == "database")

        assert database["status"] == "OPERATIONAL"

    def test_vision_status_reflects_the_configured_detector(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A static detector is reported as not model-backed; a loaded model is operational.

        Readiness is derived from the detector that was actually built, so this assertion is
        pinned to the configured backend rather than to whichever default happens to be set.
        """
        from app.core.config import get_settings

        settings = get_settings()
        monkeypatch.setattr(settings, "vision_detector", "static", raising=False)

        from app.api import dependencies

        dependencies.get_vision_service.cache_clear()
        try:
            body = client.get("/system/status").json()
            vision = next(
                item for item in body["components"] if item["component"] == "vision"
            )

            assert vision["status"] == "DEGRADED"
            assert "no model loaded" in vision["detail"].lower()
        finally:
            dependencies.get_vision_service.cache_clear()

    def test_status_includes_environment_metadata(self, client: TestClient) -> None:
        body = client.get("/system/status").json()

        assert body["version"]
        assert body["environment"]
        assert body["checked_at"]


class TestVisionEndpointStillWorks:
    def test_vision_analyze_returns_an_assessment(self, client: TestClient) -> None:
        response = client.post(
            "/vision/analyze",
            files={"image": ("scene.jpg", IMAGE_BYTES, "image/jpeg")},
        )

        assert response.status_code == 200
        assert response.json()["incident_type"] == "Building Fire"
