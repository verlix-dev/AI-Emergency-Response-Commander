"""Integration tests for the end-to-end incident analysis workflow."""

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
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.engines.allocation_engine import AllocationEngine, resolve_resource_kind
from app.engines.allocation_models import AllocationPriority, ResourceKind
from app.engines.decision_engine import DecisionEngine
from app.engines.models import SeverityLevel
from app.models.incident_analysis import IncidentAnalysis
from app.models.resource import Resource
from app.repositories import IncidentRepository, ResourceRepository
from app.services.commander_brief import CommanderBriefGenerator
from app.services.incident_analysis import IncidentAnalysisService
from app.vision import StaticDetector, VisionService

FRAME = (1000, 1000)


def box(x1: float, y1: float, x2: float, y2: float) -> list[float]:
    return [x1, y1, x2, y2]


BUILDING_FIRE_DETECTIONS = [
    {"class": "fire", "confidence": 0.91, "bbox": box(200, 200, 400, 400)},
    {"class": "smoke", "confidence": 0.86, "bbox": box(200, 50, 500, 200)},
    {"class": "building", "confidence": 0.95, "bbox": box(100, 100, 700, 800)},
    {"class": "person", "confidence": 0.9, "bbox": box(10, 600, 60, 750)},
    {"class": "person", "confidence": 0.88, "bbox": box(70, 600, 120, 750)},
]

FLOOD_DETECTIONS = [
    {"class": "flood_water", "confidence": 0.93, "bbox": box(0, 300, 1000, 1000)},
    {"class": "person", "confidence": 0.9, "bbox": box(400, 200, 450, 300)},
    {"class": "person", "confidence": 0.85, "bbox": box(460, 200, 510, 300)},
    {"class": "boat", "confidence": 0.8, "bbox": box(600, 500, 800, 600)},
    {"class": "power_line", "confidence": 0.7, "bbox": box(0, 100, 1000, 140)},
]

BUILDING_COLLAPSE_DETECTIONS = [
    {"class": "collapsed_building", "confidence": 0.94, "bbox": box(100, 100, 800, 700)},
    {"class": "debris", "confidence": 0.88, "bbox": box(50, 600, 900, 800)},
    {"class": "debris", "confidence": 0.81, "bbox": box(200, 700, 700, 900)},
    {"class": "person", "confidence": 0.9, "bbox": box(850, 500, 900, 650)},
]

ROAD_ACCIDENT_DETECTIONS = [
    {"class": "car", "confidence": 0.93, "bbox": box(100, 400, 350, 600)},
    {"class": "truck", "confidence": 0.9, "bbox": box(400, 380, 750, 620)},
    {"class": "debris", "confidence": 0.72, "bbox": box(350, 550, 420, 620)},
    {"class": "person", "confidence": 0.87, "bbox": box(780, 450, 830, 600)},
    {"class": "ambulance", "confidence": 0.8, "bbox": box(850, 380, 990, 560)},
]

CHEMICAL_LEAK_DETECTIONS = [
    {"class": "smoke", "confidence": 0.89, "bbox": box(200, 100, 800, 500)},
    {"class": "truck", "confidence": 0.9, "bbox": box(300, 500, 650, 700)},
    {"class": "person", "confidence": 0.86, "bbox": box(50, 600, 100, 750)},
    {"class": "person", "confidence": 0.84, "bbox": box(110, 600, 160, 750)},
    {"class": "person", "confidence": 0.82, "bbox": box(170, 600, 220, 750)},
]

RESOURCE_POOL = [
    ("fire_truck", "Engine 1"),
    ("fire_truck", "Engine 2"),
    ("fire_truck", "Engine 3"),
    ("fire_truck", "Engine 4"),
    ("ambulance", "Ambulance 1"),
    ("ambulance", "Ambulance 2"),
    ("ambulance", "Ambulance 3"),
    ("police", "Patrol 1"),
    ("police", "Patrol 2"),
    ("police", "Patrol 3"),
    ("search_rescue", "USAR 1"),
    ("search_rescue", "USAR 2"),
    ("boat", "Rescue Boat 1"),
    ("boat", "Rescue Boat 2"),
    ("medical_team", "Medical Team 1"),
    ("medical_team", "Medical Team 2"),
    ("hazmat", "Hazmat 1"),
    ("hazmat", "Hazmat 2"),
    ("heavy_machinery", "Excavator 1"),
    ("heavy_machinery", "Crane 1"),
]


@pytest.fixture
def session() -> Iterator[Session]:
    """Provide an isolated in-memory database with the full schema applied."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    db_session = factory()
    for resource_type, resource_name in RESOURCE_POOL:
        db_session.add(
            Resource(
                resource_type=resource_type,
                resource_name=resource_name,
                status="AVAILABLE",
                available=True,
            )
        )
    db_session.commit()
    try:
        yield db_session
    finally:
        db_session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def build_service(session: Session, detections: list[dict]) -> IncidentAnalysisService:
    """Assemble the workflow against a scripted detector and the test database."""
    return IncidentAnalysisService(
        vision_service=VisionService(
            detector=StaticDetector(detections=detections, frame=FRAME)
        ),
        decision_engine=DecisionEngine(),
        allocation_engine=AllocationEngine(),
        brief_generator=CommanderBriefGenerator(),
        incident_repository=IncidentRepository(session),
        resource_repository=ResourceRepository(session),
    )


def kinds_of(response) -> set[ResourceKind]:
    """Return the set of resource kinds recommended in a response."""
    return {item.resource_kind for item in response.resources.recommendations}


class TestBuildingFireWorkflow:
    def test_end_to_end_produces_complete_response(self, session: Session) -> None:
        response = build_service(session, BUILDING_FIRE_DETECTIONS).analyze_image("scene.jpg")

        assert response.incident.incident_type == "BUILDING_FIRE"
        assert response.assessment.fire_detected is True
        assert response.assessment.smoke_detected is True
        assert response.assessment.people_detected == 2
        assert response.decision.severity_level is not None
        assert response.commander_brief.incident_summary
        assert response.timestamp is not None

    def test_fire_trucks_are_recommended(self, session: Session) -> None:
        response = build_service(session, BUILDING_FIRE_DETECTIONS).analyze_image("scene.jpg")

        assert ResourceKind.FIRE_TRUCK in kinds_of(response)

    def test_incident_is_persisted(self, session: Session) -> None:
        response = build_service(session, BUILDING_FIRE_DETECTIONS).analyze_image("scene.jpg")
        session.commit()

        stored = IncidentRepository(session).get_incident(response.incident.id)

        assert stored is not None
        assert stored.priority == response.decision.priority_level.value


class TestFloodWorkflow:
    def test_flood_classified_and_boats_recommended(self, session: Session) -> None:
        response = build_service(session, FLOOD_DETECTIONS).analyze_image("scene.jpg")

        assert response.incident.incident_type == "FLOOD"
        assert response.assessment.water_level_m is not None
        assert ResourceKind.BOAT in kinds_of(response)

    def test_power_lines_drive_police_presence(self, session: Session) -> None:
        response = build_service(session, FLOOD_DETECTIONS).analyze_image("scene.jpg")

        assert response.assessment.power_lines_down is True
        assert ResourceKind.POLICE in kinds_of(response)


class TestBuildingCollapseWorkflow:
    def test_collapse_recommends_rescue_and_machinery(self, session: Session) -> None:
        response = build_service(session, BUILDING_COLLAPSE_DETECTIONS).analyze_image("scene.jpg")

        assert response.incident.incident_type == "BUILDING_COLLAPSE"
        assert response.assessment.collapsed_structure is True
        recommended = kinds_of(response)
        assert ResourceKind.SEARCH_RESCUE in recommended
        assert ResourceKind.HEAVY_MACHINERY in recommended

    def test_severity_is_elevated(self, session: Session) -> None:
        response = build_service(session, BUILDING_COLLAPSE_DETECTIONS).analyze_image("scene.jpg")

        order = list(SeverityLevel)
        assert order.index(response.decision.severity_level) >= order.index(SeverityLevel.MODERATE)


class TestRoadAccidentWorkflow:
    def test_road_accident_produces_medical_response(self, session: Session) -> None:
        response = build_service(session, ROAD_ACCIDENT_DETECTIONS).analyze_image("scene.jpg")

        assert response.assessment.people_detected == 1
        assert response.assessment.responders_on_scene == 1
        assert response.commander_brief.recommended_resources

    def test_responders_already_present_are_noted(self, session: Session) -> None:
        response = build_service(session, ROAD_ACCIDENT_DETECTIONS).analyze_image("scene.jpg")
        notes = " ".join(response.commander_brief.operational_notes)

        assert "already on scene" in notes


class TestChemicalLeakWorkflow:
    def test_leak_scene_produces_actionable_brief(self, session: Session) -> None:
        response = build_service(session, CHEMICAL_LEAK_DETECTIONS).analyze_image("scene.jpg")

        assert response.assessment.people_detected == 3
        assert response.assessment.smoke_detected is True
        assert response.commander_brief.immediate_actions
        assert response.commander_brief.risk_factors

    def test_all_brief_sections_populated(self, session: Session) -> None:
        brief = build_service(session, CHEMICAL_LEAK_DETECTIONS).analyze_image(
            "scene.jpg"
        ).commander_brief

        assert brief.incident_summary
        assert brief.severity
        assert brief.priority
        assert brief.immediate_actions
        assert brief.recommended_resources
        assert brief.risk_factors
        assert brief.operational_notes


class TestAllocationBehaviour:
    def test_available_resources_are_assigned(self, session: Session) -> None:
        response = build_service(session, BUILDING_FIRE_DETECTIONS).analyze_image("scene.jpg")
        fire = next(
            item
            for item in response.resources.recommendations
            if item.resource_kind is ResourceKind.FIRE_TRUCK
        )

        assert fire.fulfilled_quantity > 0
        assert len(fire.assigned_resource_names) == fire.fulfilled_quantity

    def test_no_resource_is_assigned_twice(self, session: Session) -> None:
        response = build_service(session, BUILDING_COLLAPSE_DETECTIONS).analyze_image("scene.jpg")
        assigned = [
            name
            for item in response.resources.recommendations
            for name in item.assigned_resource_names
        ]

        assert len(assigned) == len(set(assigned))

    def test_shortfall_is_reported_when_pool_is_empty(self, session: Session) -> None:
        for resource in session.query(Resource).all():
            resource.available = False
        session.commit()

        response = build_service(session, BUILDING_FIRE_DETECTIONS).analyze_image("scene.jpg")

        assert response.resources.total_units_fulfilled == 0
        assert response.resources.unmet_requirements
        assert any(item.shortfall > 0 for item in response.resources.recommendations)

    def test_shortfall_surfaces_in_the_brief(self, session: Session) -> None:
        for resource in session.query(Resource).all():
            resource.available = False
        session.commit()

        response = build_service(session, BUILDING_FIRE_DETECTIONS).analyze_image("scene.jpg")
        notes = " ".join(response.commander_brief.operational_notes)

        assert "shortfall" in notes.lower()

    def test_duplicate_requirements_are_merged(self, session: Session) -> None:
        response = build_service(session, BUILDING_COLLAPSE_DETECTIONS).analyze_image("scene.jpg")
        kinds = [item.resource_kind for item in response.resources.recommendations]

        assert len(kinds) == len(set(kinds))

    def test_critical_requirements_lead_the_list(self, session: Session) -> None:
        response = build_service(session, BUILDING_COLLAPSE_DETECTIONS).analyze_image("scene.jpg")
        priorities = [item.priority for item in response.resources.recommendations]
        order = [AllocationPriority.CRITICAL, AllocationPriority.HIGH, AllocationPriority.MEDIUM,
                 AllocationPriority.LOW]

        assert priorities == sorted(priorities, key=order.index)

    def test_allocation_is_deterministic(self, session: Session) -> None:
        first = build_service(session, FLOOD_DETECTIONS).analyze_image("scene.jpg")
        second = build_service(session, FLOOD_DETECTIONS).analyze_image("scene.jpg")

        assert first.resources.model_dump() == second.resources.model_dump()

    def test_unknown_resource_types_are_ignored(self, session: Session) -> None:
        session.add(
            Resource(
                resource_type="teleporter",
                resource_name="Teleporter 1",
                status="AVAILABLE",
                available=True,
            )
        )
        session.commit()

        response = build_service(session, BUILDING_FIRE_DETECTIONS).analyze_image("scene.jpg")
        assigned = [
            name
            for item in response.resources.recommendations
            for name in item.assigned_resource_names
        ]

        assert "Teleporter 1" not in assigned
        assert resolve_resource_kind("teleporter") is None


class TestTimeline:
    def test_first_analysis_creates_revision_one(self, session: Session) -> None:
        response = build_service(session, BUILDING_FIRE_DETECTIONS).analyze_image("scene.jpg")
        session.commit()

        timeline = build_service(session, []).get_timeline(response.incident.id)

        assert len(timeline.revisions) == 1
        assert timeline.revisions[0].revision == 1

    def test_reanalysis_appends_a_revision(self, session: Session) -> None:
        first = build_service(session, BUILDING_FIRE_DETECTIONS).analyze_image("scene.jpg")
        session.commit()

        build_service(session, BUILDING_COLLAPSE_DETECTIONS).reanalyze_incident(
            first.incident.id, "scene2.jpg"
        )
        session.commit()

        timeline = build_service(session, []).get_timeline(first.incident.id)

        assert [item.revision for item in timeline.revisions] == [1, 2]

    def test_revisions_record_the_full_snapshot(self, session: Session) -> None:
        response = build_service(session, FLOOD_DETECTIONS).analyze_image("scene.jpg")
        session.commit()

        record = build_service(session, []).get_timeline(response.incident.id).revisions[0]

        assert record.assessment["incident_type"]
        assert record.decision["severity_level"]
        assert record.resources["recommendations"]
        assert record.commander_brief["incident_summary"]
        assert record.severity_level == response.decision.severity_level.value

    def test_history_is_ordered_oldest_first(self, session: Session) -> None:
        first = build_service(session, BUILDING_FIRE_DETECTIONS).analyze_image("scene.jpg")
        session.commit()
        for detections in (FLOOD_DETECTIONS, BUILDING_COLLAPSE_DETECTIONS):
            build_service(session, detections).reanalyze_incident(first.incident.id, "s.jpg")
            session.commit()

        revisions = build_service(session, []).get_timeline(first.incident.id).revisions

        assert [item.revision for item in revisions] == [1, 2, 3]

    def test_reanalysis_updates_the_incident_classification(self, session: Session) -> None:
        first = build_service(session, BUILDING_FIRE_DETECTIONS).analyze_image("scene.jpg")
        session.commit()

        second = build_service(session, BUILDING_COLLAPSE_DETECTIONS).reanalyze_incident(
            first.incident.id, "scene2.jpg"
        )
        session.commit()

        assert second.incident.incident_type == "BUILDING_COLLAPSE"
        assert second.incident.id == first.incident.id

    def test_timeline_for_unknown_incident_raises(self, session: Session) -> None:
        from uuid import uuid4

        from app.exceptions import NotFoundError

        with pytest.raises(NotFoundError):
            build_service(session, []).get_timeline(uuid4())


class TestPersistenceSideEffects:
    def test_vision_result_is_recorded(self, session: Session) -> None:
        response = build_service(session, FLOOD_DETECTIONS).analyze_image("scene.jpg")
        session.commit()

        incident = IncidentRepository(session).get_incident(response.incident.id)

        assert incident is not None
        assert len(incident.vision_results) == 1
        assert incident.vision_results[0].people_detected == 2
        assert incident.vision_results[0].boats_detected == 1

    def test_commander_brief_is_stored_as_the_action_plan(self, session: Session) -> None:
        response = build_service(session, BUILDING_FIRE_DETECTIONS).analyze_image("scene.jpg")
        session.commit()

        incident = IncidentRepository(session).get_incident(response.incident.id)

        assert incident is not None
        assert len(incident.action_plans) == 1
        assert "INCIDENT SUMMARY" in incident.action_plans[0].generated_plan

    def test_empty_detections_still_persist_a_complete_analysis(self, session: Session) -> None:
        response = build_service(session, []).analyze_image("scene.jpg")
        session.commit()

        stored = session.query(IncidentAnalysis).all()

        assert len(stored) == 1
        assert response.incident.incident_type == "UNKNOWN"
        assert response.commander_brief.operational_notes

    def test_location_defaults_when_not_supplied(self, session: Session) -> None:
        response = build_service(session, BUILDING_FIRE_DETECTIONS).analyze_image("scene.jpg")

        assert response.incident.location == "Unknown"

    def test_supplied_location_is_used(self, session: Session) -> None:
        response = build_service(session, BUILDING_FIRE_DETECTIONS).analyze_image(
            "scene.jpg", location="42 Mill Road", latitude=51.5, longitude=-0.12
        )

        assert response.incident.location == "42 Mill Road"
        assert response.incident.latitude == 51.5

    def test_title_is_derived_when_not_supplied(self, session: Session) -> None:
        response = build_service(session, BUILDING_FIRE_DETECTIONS).analyze_image("scene.jpg")

        assert "Building Fire" in response.incident.title

    def test_supplied_title_is_used(self, session: Session) -> None:
        response = build_service(session, BUILDING_FIRE_DETECTIONS).analyze_image(
            "scene.jpg", title="Warehouse blaze, Dock Road"
        )

        assert response.incident.title == "Warehouse blaze, Dock Road"


class TestWorkflowDeterminism:
    def test_same_detections_yield_the_same_decision(self, session: Session) -> None:
        first = build_service(session, CHEMICAL_LEAK_DETECTIONS).analyze_image("scene.jpg")
        second = build_service(session, CHEMICAL_LEAK_DETECTIONS).analyze_image("scene.jpg")

        assert first.decision.model_dump() == second.decision.model_dump()
        assert first.commander_brief.model_dump() == second.commander_brief.model_dump()

    def test_brief_contains_no_generated_prose_markers(self, session: Session) -> None:
        """The brief must be template-composed, never model-generated."""
        brief = build_service(session, BUILDING_FIRE_DETECTIONS).analyze_image(
            "scene.jpg"
        ).commander_brief

        assert "deterministically" in " ".join(brief.operational_notes)
