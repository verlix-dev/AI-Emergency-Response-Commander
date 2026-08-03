"""Tests for the trained-model detector adapter and the demonstration seed data.

Model-backed tests are skipped when the weights file is absent so the suite still runs in a
checkout without the 44 MB artefact.
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
from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.engines.allocation_engine import resolve_resource_kind
from app.exceptions import DetectorNotAvailableError, ImageNotReadableError
from app.models.incident import Incident
from app.models.resource import Resource
from app.services.seed import SEED_CITIES, SEED_INCIDENTS, seed
from app.vision.config import DEFAULT_MODEL_PATH, YoloDetectorConfig
from app.vision.detector import UltralyticsYOLODetector
from app.vision.models import DetectionClass
from app.vision.parser import DetectionParser

WEIGHTS_PRESENT = Path(DEFAULT_MODEL_PATH).is_file()
requires_weights = pytest.mark.skipif(
    not WEIGHTS_PRESENT, reason="Trained weights not present in this checkout."
)


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    db_session = factory()
    try:
        yield db_session
    finally:
        db_session.close()
        engine.dispose()


@pytest.fixture(scope="module")
def scene_image(tmp_path_factory: pytest.TempPathFactory) -> str:
    """Write a small real image so inference has valid pixels to decode."""
    from PIL import Image

    path = tmp_path_factory.mktemp("vision") / "scene.jpg"
    Image.new("RGB", (320, 240), (90, 80, 70)).save(path)
    return str(path)


class TestModelClassVocabulary:
    """Every class the trained model emits must map to a supported detection class."""

    @requires_weights
    def test_all_model_classes_are_mapped(self) -> None:
        detector = UltralyticsYOLODetector()
        assert detector.is_ready, detector.load_error

        parser = DetectionParser()
        raw = [
            {"class": name, "confidence": 0.9, "bbox": [0, 0, 10, 10]}
            for name in detector.class_names().values()
        ]
        frame = parser.parse(raw, frame=(100, 100))

        assert frame.discarded == (), (
            f"Model classes discarded by the parser: "
            f"{[item.raw_class for item in frame.discarded]}"
        )
        assert len(frame.detections) == len(raw)

    def test_model_vocabulary_resolves_to_expected_classes(self) -> None:
        """The four trained classes map onto the pipeline's vocabulary."""
        parser = DetectionParser()
        raw = [
            {"class": name, "confidence": 0.9, "bbox": [0, 0, 10, 10]}
            for name in ("collapsed_building", "fire", "flooded_areas", "traffic_incident")
        ]

        frame = parser.parse(raw, frame=(100, 100))
        resolved = [item.detection_class for item in frame.detections]

        assert resolved == [
            DetectionClass.COLLAPSED_BUILDING,
            DetectionClass.FIRE,
            DetectionClass.FLOOD_WATER,
            DetectionClass.TRAFFIC_INCIDENT,
        ]


class TestDetectorLifecycle:
    @requires_weights
    def test_model_loads_at_construction(self) -> None:
        detector = UltralyticsYOLODetector()

        assert detector.is_ready
        assert detector.load_error is None
        assert detector.class_names()

    @requires_weights
    def test_model_is_loaded_once_per_weights_file(self) -> None:
        import app.vision.detector as detector_module

        UltralyticsYOLODetector()
        cached = len(detector_module._MODEL_CACHE)

        UltralyticsYOLODetector()
        UltralyticsYOLODetector()

        assert len(detector_module._MODEL_CACHE) == cached

    def test_missing_weights_degrade_rather_than_raise(self) -> None:
        """A missing model must not prevent construction, so the app can still start."""
        detector = UltralyticsYOLODetector(model_path="no-such-model.pt")

        assert detector.is_ready is False
        assert detector.load_error is not None
        assert "not found" in detector.load_error

    def test_detect_reports_unavailable_when_model_failed_to_load(
        self, scene_image: str
    ) -> None:
        detector = UltralyticsYOLODetector(model_path="no-such-model.pt")

        with pytest.raises(DetectorNotAvailableError):
            detector.detect(scene_image)

    def test_missing_image_raises_image_error(self) -> None:
        detector = UltralyticsYOLODetector(model_path="no-such-model.pt")

        with pytest.raises(ImageNotReadableError):
            detector.detect("no-such-image.jpg")

    @requires_weights
    def test_undecodable_image_is_reported_as_an_image_error(self, tmp_path: Path) -> None:
        corrupt = tmp_path / "corrupt.jpg"
        corrupt.write_bytes(b"this is not an image")

        detector = UltralyticsYOLODetector()

        with pytest.raises((ImageNotReadableError, DetectorNotAvailableError)):
            detector.detect(str(corrupt))


class TestInference:
    @requires_weights
    def test_inference_returns_wellformed_raw_detections(self, scene_image: str) -> None:
        """Whatever the model returns must match the shape the parser expects."""
        detector = UltralyticsYOLODetector(
            config=YoloDetectorConfig(confidence_threshold=0.01)
        )

        raw = detector.detect(scene_image)

        assert isinstance(raw, list)
        for item in raw:
            assert isinstance(item["class"], str)
            assert 0.0 <= item["confidence"] <= 1.0
            assert len(item["bbox"]) == 4

    @requires_weights
    def test_raw_detections_survive_the_parser(self, scene_image: str) -> None:
        detector = UltralyticsYOLODetector(
            config=YoloDetectorConfig(confidence_threshold=0.01)
        )

        frame = DetectionParser(min_confidence=0.01).parse(
            detector.detect(scene_image), frame=detector.frame_size(scene_image)
        )

        assert frame.discarded == ()

    @requires_weights
    def test_no_detections_is_a_valid_result(self, scene_image: str) -> None:
        """A high threshold suppresses every detection without raising."""
        detector = UltralyticsYOLODetector(
            config=YoloDetectorConfig(confidence_threshold=0.99)
        )

        assert detector.detect(scene_image) == []

    @requires_weights
    def test_frame_size_is_reported_from_the_image(self, scene_image: str) -> None:
        detector = UltralyticsYOLODetector()

        assert detector.frame_size(scene_image) == (320, 240)

    @requires_weights
    def test_confidence_threshold_is_configurable(self, scene_image: str) -> None:
        permissive = UltralyticsYOLODetector(
            config=YoloDetectorConfig(confidence_threshold=0.01)
        ).detect(scene_image)
        strict = UltralyticsYOLODetector(
            config=YoloDetectorConfig(confidence_threshold=0.95)
        ).detect(scene_image)

        assert len(strict) <= len(permissive)


class TestSeedData:
    def test_seed_populates_resources_and_incidents(self, session: Session) -> None:
        seed(session)
        session.commit()

        assert session.scalar(select(func.count()).select_from(Resource)) > 0
        assert session.scalar(select(func.count()).select_from(Incident)) == len(SEED_INCIDENTS)

    def test_every_city_receives_resources(self, session: Session) -> None:
        seed(session)
        session.commit()

        for city in SEED_CITIES:
            name = str(city["name"])
            count = session.scalar(
                select(func.count()).select_from(Resource).where(Resource.current_location == name)
            )
            assert count and count > 0, f"{name} has no resources"

    def test_cities_have_distinct_resource_profiles(self, session: Session) -> None:
        """Seeded cities must differ, so demonstrations show varied capacity."""
        seed(session)
        session.commit()

        totals = {
            str(city["name"]): session.scalar(
                select(func.count())
                .select_from(Resource)
                .where(Resource.current_location == str(city["name"]))
            )
            for city in SEED_CITIES
        }

        assert len(set(totals.values())) > 1

    def test_seeded_resource_types_are_allocatable(self, session: Session) -> None:
        """Every seeded type must resolve to a kind the allocation engine understands."""
        seed(session)
        session.commit()

        types = session.execute(select(Resource.resource_type).distinct()).scalars().all()

        for resource_type in types:
            assert resolve_resource_kind(resource_type) is not None, (
                f"Seeded resource type '{resource_type}' is not allocatable"
            )

    def test_seeded_resources_are_available(self, session: Session) -> None:
        seed(session)
        session.commit()

        unavailable = session.scalar(
            select(func.count()).select_from(Resource).where(Resource.available.is_(False))
        )

        assert unavailable == 0

    def test_incidents_carry_realistic_detail(self, session: Session) -> None:
        seed(session)
        session.commit()

        for incident in session.execute(select(Incident)).scalars().all():
            assert incident.title
            assert incident.description
            assert incident.location
            assert incident.incident_type
            assert incident.priority
            assert incident.latitude is not None
            assert incident.longitude is not None

    def test_incidents_span_multiple_statuses(self, session: Session) -> None:
        seed(session)
        session.commit()

        statuses = {
            incident.status for incident in session.execute(select(Incident)).scalars().all()
        }

        assert len(statuses) > 1

    def test_incidents_are_backdated_across_a_range(self, session: Session) -> None:
        seed(session)
        session.commit()

        timestamps = [
            incident.created_at for incident in session.execute(select(Incident)).scalars().all()
        ]

        assert len(set(timestamps)) == len(timestamps)

    def test_seeding_is_idempotent(self, session: Session) -> None:
        seed(session)
        session.commit()
        resources = session.scalar(select(func.count()).select_from(Resource))
        incidents = session.scalar(select(func.count()).select_from(Incident))

        seed(session)
        session.commit()

        assert session.scalar(select(func.count()).select_from(Resource)) == resources
        assert session.scalar(select(func.count()).select_from(Incident)) == incidents
