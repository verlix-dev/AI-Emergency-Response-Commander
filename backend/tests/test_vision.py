"""Unit tests for the vision pipeline and its integration with the assessment contract."""

import pytest

from app.engines.models import IncidentAssessment
from app.vision import (
    AssessmentMapper,
    DetectionClass,
    DetectionParser,
    StaticDetector,
    VisionService,
)

FRAME = (1000, 1000)


def service(detections: list[dict], frame: tuple[int, int] | None = FRAME) -> VisionService:
    return VisionService(detector=StaticDetector(detections=detections, frame=frame))


def box(x1: float, y1: float, x2: float, y2: float) -> list[float]:
    return [x1, y1, x2, y2]


class TestPersonDetection:
    def test_single_person_is_counted(self) -> None:
        result = service([{"class": "person", "confidence": 0.93, "bbox": box(0, 0, 50, 120)}])

        assessment = result.analyze("frame.jpg")

        assert assessment.people_detected == 1

    def test_multiple_people_are_counted(self) -> None:
        detections = [
            {"class": "person", "confidence": 0.93, "bbox": box(0, 0, 50, 120)},
            {"class": "person", "confidence": 0.81, "bbox": box(60, 0, 110, 120)},
            {"class": "person", "confidence": 0.55, "bbox": box(120, 0, 170, 120)},
        ]

        assessment = service(detections).analyze("frame.jpg")

        assert assessment.people_detected == 3

    def test_low_confidence_person_is_discarded(self) -> None:
        detections = [
            {"class": "person", "confidence": 0.93},
            {"class": "person", "confidence": 0.05},
        ]

        frame = service(detections).detect_frame("frame.jpg")

        assert frame.count_of(DetectionClass.PERSON) == 1
        assert len(frame.discarded) == 1
        assert "threshold" in frame.discarded[0].reason

    def test_people_only_leaves_hazards_unreported(self) -> None:
        assessment = service([{"class": "person", "confidence": 0.9}]).analyze("frame.jpg")

        assert assessment.fire_detected is None
        assert assessment.smoke_detected is None
        assert assessment.collapsed_structure is None
        assert assessment.water_level_m is None


class TestFireDetection:
    def test_fire_sets_flag(self) -> None:
        assessment = service([{"class": "fire", "confidence": 0.88}]).analyze("frame.jpg")

        assert assessment.fire_detected is True

    def test_smoke_sets_flag(self) -> None:
        assessment = service([{"class": "smoke", "confidence": 0.81}]).analyze("frame.jpg")

        assert assessment.smoke_detected is True

    def test_fire_with_building_classifies_building_fire(self) -> None:
        detections = [
            {"class": "fire", "confidence": 0.88},
            {"class": "smoke", "confidence": 0.81},
            {"class": "building", "confidence": 0.9},
        ]

        assessment = service(detections).analyze("frame.jpg")

        assert assessment.incident_type == "Building Fire"

    def test_weak_fire_detection_is_not_asserted(self) -> None:
        """A detection above the parse threshold but below the hazard gate stays unreported."""
        assessment = service([{"class": "fire", "confidence": 0.30}]).analyze("frame.jpg")

        assert assessment.fire_detected is None


class TestBuildingCollapse:
    def test_collapse_sets_structure_flags(self) -> None:
        detections = [{"class": "collapsed_building", "confidence": 0.91}]

        assessment = service(detections).analyze("frame.jpg")

        assert assessment.collapsed_structure is True
        assert assessment.structural_damage is True
        assert assessment.road_blocked is True
        assert assessment.incident_type == "Building Collapse"

    def test_weak_collapse_detection_is_not_asserted(self) -> None:
        """Collapse drives a severity floor, so it requires strong evidence."""
        assessment = service([{"class": "collapsed_building", "confidence": 0.45}]).analyze(
            "frame.jpg"
        )

        assert assessment.collapsed_structure is None

    def test_debris_alone_implies_damage_but_not_collapse(self) -> None:
        assessment = service([{"class": "debris", "confidence": 0.7}]).analyze("frame.jpg")

        assert assessment.structural_damage is True
        assert assessment.collapsed_structure is None

    def test_multiple_debris_blocks_road(self) -> None:
        detections = [
            {"class": "debris", "confidence": 0.7},
            {"class": "debris", "confidence": 0.65},
        ]

        assessment = service(detections).analyze("frame.jpg")

        assert assessment.road_blocked is True


class TestMultipleDetections:
    def test_mixed_scene_populates_every_supported_field(self) -> None:
        detections = [
            {"class": "person", "confidence": 0.93, "bbox": box(0, 0, 40, 100)},
            {"class": "person", "confidence": 0.88, "bbox": box(50, 0, 90, 100)},
            {"class": "fire", "confidence": 0.9, "bbox": box(200, 200, 300, 300)},
            {"class": "smoke", "confidence": 0.85, "bbox": box(200, 100, 400, 200)},
            {"class": "building", "confidence": 0.95, "bbox": box(150, 150, 500, 600)},
            {"class": "fire_truck", "confidence": 0.8, "bbox": box(600, 600, 800, 750)},
            {"class": "ambulance", "confidence": 0.75, "bbox": box(800, 600, 950, 750)},
            {"class": "power_line", "confidence": 0.6, "bbox": box(0, 900, 1000, 950)},
        ]

        assessment = service(detections).analyze("frame.jpg")

        assert assessment.incident_type == "Building Fire"
        assert assessment.people_detected == 2
        assert assessment.fire_detected is True
        assert assessment.smoke_detected is True
        assert assessment.power_lines_down is True
        assert assessment.responders_on_scene == 2

    def test_flood_scene_estimates_depth_from_coverage(self) -> None:
        detections = [
            {"class": "flood_water", "confidence": 0.9, "bbox": box(0, 0, 1000, 600)},
            {"class": "boat", "confidence": 0.7},
            {"class": "person", "confidence": 0.8},
        ]

        assessment = service(detections).analyze("frame.jpg")

        assert assessment.incident_type == "Flood"
        assert assessment.water_level_m == 1.5

    def test_shallow_flood_coverage_estimates_lower_depth(self) -> None:
        detections = [{"class": "flood_water", "confidence": 0.9, "bbox": box(0, 0, 1000, 150)}]

        assessment = service(detections).analyze("frame.jpg")

        assert assessment.water_level_m == 0.4

    def test_flood_without_frame_geometry_uses_conservative_depth(self) -> None:
        detections = [{"class": "flood_water", "confidence": 0.9, "bbox": box(0, 0, 500, 500)}]

        assessment = service(detections, frame=None).analyze("frame.jpg")

        assert assessment.water_level_m == 0.4

    def test_train_with_debris_classifies_train_accident(self) -> None:
        detections = [
            {"class": "train", "confidence": 0.9},
            {"class": "debris", "confidence": 0.7},
        ]

        assessment = service(detections).analyze("frame.jpg")

        assert assessment.incident_type == "Train Accident"

    def test_collapse_takes_precedence_over_fire(self) -> None:
        detections = [
            {"class": "collapsed_building", "confidence": 0.9},
            {"class": "fire", "confidence": 0.9},
            {"class": "building", "confidence": 0.9},
        ]

        assessment = service(detections).analyze("frame.jpg")

        assert assessment.incident_type == "Building Collapse"
        assert assessment.fire_detected is True


class TestEmptyDetections:
    def test_empty_list_produces_valid_assessment(self) -> None:
        assessment = service([]).analyze("frame.jpg")

        assert isinstance(assessment, IncidentAssessment)
        assert assessment.incident_type == "Unknown"

    def test_empty_list_reports_nothing_as_observed(self) -> None:
        """An empty frame cannot establish absence, so no field is asserted."""
        assessment = service([]).analyze("frame.jpg")

        assert assessment.people_detected is None
        assert assessment.fire_detected is None
        assert assessment.smoke_detected is None
        assert assessment.collapsed_structure is None
        assert assessment.structural_damage is None
        assert assessment.water_level_m is None
        assert assessment.road_blocked is None
        assert assessment.responders_on_scene is None

    def test_detections_present_but_no_people_reports_zero(self) -> None:
        """With something detected, an absence of people is a reportable observation."""
        assessment = service([{"class": "fire", "confidence": 0.9}]).analyze("frame.jpg")

        assert assessment.people_detected == 0

    def test_only_unsupported_classes_behaves_as_empty(self) -> None:
        detections = [
            {"class": "giraffe", "confidence": 0.9},
            {"class": "traffic_cone", "confidence": 0.8},
        ]

        result = service(detections)

        assert result.analyze("frame.jpg").people_detected is None
        assert len(result.detect_frame("frame.jpg").discarded) == 2


class TestDetectionParser:
    def test_unsupported_class_is_discarded_with_reason(self) -> None:
        frame = DetectionParser().parse([{"class": "giraffe", "confidence": 0.9}])

        assert frame.detections == ()
        assert frame.discarded[0].raw_class == "giraffe"
        assert frame.discarded[0].reason == "class not in supported vocabulary"

    def test_class_aliases_are_normalized(self) -> None:
        raw = [
            {"class": "Person", "confidence": 0.9},
            {"class": "FLAMES", "confidence": 0.9},
            {"class": "fire truck", "confidence": 0.9},
            {"class": "collapsed-building", "confidence": 0.9},
        ]

        frame = DetectionParser().parse(raw)
        classes = [item.detection_class for item in frame.detections]

        assert classes == [
            DetectionClass.PERSON,
            DetectionClass.FIRE,
            DetectionClass.FIRE_TRUCK,
            DetectionClass.COLLAPSED_BUILDING,
        ]

    def test_alternative_field_names_are_accepted(self) -> None:
        raw = [{"name": "person", "conf": 0.9, "xyxy": [0, 0, 10, 10]}]

        frame = DetectionParser().parse(raw)

        assert frame.count_of(DetectionClass.PERSON) == 1
        assert frame.detections[0].bbox is not None

    def test_nested_bbox_is_flattened(self) -> None:
        """Ultralytics reports xyxy as a nested sequence per box."""
        raw = [{"class": "person", "confidence": 0.9, "bbox": [[10.0, 20.0, 30.0, 40.0]]}]

        frame = DetectionParser().parse(raw)

        assert frame.detections[0].bbox is not None
        assert frame.detections[0].bbox.x1 == 10.0
        assert frame.detections[0].bbox.x2 == 30.0

    def test_dict_bbox_is_accepted(self) -> None:
        raw = [{"class": "person", "confidence": 0.9, "bbox": {"x1": 1, "y1": 2, "x2": 3, "y2": 4}}]

        frame = DetectionParser().parse(raw)

        assert frame.detections[0].bbox is not None

    def test_inverted_bbox_coordinates_are_ordered(self) -> None:
        raw = [{"class": "person", "confidence": 0.9, "bbox": [30, 40, 10, 20]}]

        bbox = DetectionParser().parse(raw).detections[0].bbox

        assert bbox is not None
        assert (bbox.x1, bbox.y1, bbox.x2, bbox.y2) == (10.0, 20.0, 30.0, 40.0)

    def test_malformed_bbox_keeps_detection(self) -> None:
        """Class and confidence remain trustworthy when only the box is unusable."""
        raw = [{"class": "person", "confidence": 0.9, "bbox": [1, 2]}]

        frame = DetectionParser().parse(raw)

        assert frame.count_of(DetectionClass.PERSON) == 1
        assert frame.detections[0].bbox is None

    def test_missing_confidence_is_discarded(self) -> None:
        frame = DetectionParser().parse([{"class": "person"}])

        assert frame.detections == ()
        assert frame.discarded[0].reason == "confidence missing or unparseable"

    def test_out_of_range_confidence_is_discarded(self) -> None:
        frame = DetectionParser().parse([{"class": "person", "confidence": 1.4}])

        assert frame.detections == ()
        assert frame.discarded[0].reason == "confidence outside 0.0-1.0"

    def test_missing_class_is_discarded(self) -> None:
        frame = DetectionParser().parse([{"confidence": 0.9}])

        assert frame.detections == ()
        assert frame.discarded[0].reason == "class label missing"

    def test_parsing_is_deterministic(self) -> None:
        raw = [
            {"class": "person", "confidence": 0.9},
            {"class": "fire", "confidence": 0.8},
            {"class": "giraffe", "confidence": 0.7},
        ]

        first = DetectionParser().parse(raw)
        second = DetectionParser().parse(raw)

        assert first.model_dump() == second.model_dump()


class TestDetectionFrame:
    def test_coverage_is_clamped_for_overlapping_boxes(self) -> None:
        raw = [
            {"class": "flood_water", "confidence": 0.9, "bbox": box(0, 0, 1000, 1000)},
            {"class": "flood_water", "confidence": 0.9, "bbox": box(0, 0, 1000, 1000)},
        ]

        frame = DetectionParser().parse(raw, frame=FRAME)

        assert frame.coverage_fraction(DetectionClass.FLOOD_WATER) == 1.0

    def test_coverage_is_none_without_geometry(self) -> None:
        raw = [{"class": "flood_water", "confidence": 0.9, "bbox": box(0, 0, 10, 10)}]

        frame = DetectionParser().parse(raw)

        assert frame.coverage_fraction(DetectionClass.FLOOD_WATER) is None

    def test_max_confidence_returns_strongest(self) -> None:
        raw = [
            {"class": "fire", "confidence": 0.4},
            {"class": "fire", "confidence": 0.92},
        ]

        frame = DetectionParser().parse(raw)

        assert frame.max_confidence(DetectionClass.FIRE) == 0.92


class TestAssessmentMapper:
    def test_mapper_is_independent_of_detector(self) -> None:
        frame = DetectionParser().parse(
            [{"class": "fire", "confidence": 0.9}, {"class": "person", "confidence": 0.9}],
            frame=FRAME,
        )

        assessment = AssessmentMapper().map(frame)

        assert assessment.fire_detected is True
        assert assessment.people_detected == 1

    def test_mapping_is_deterministic(self) -> None:
        frame = DetectionParser().parse(
            [
                {"class": "collapsed_building", "confidence": 0.9},
                {"class": "person", "confidence": 0.9},
                {"class": "debris", "confidence": 0.8},
            ],
            frame=FRAME,
        )

        assert AssessmentMapper().map(frame).model_dump() == AssessmentMapper().map(
            frame
        ).model_dump()

    def test_output_is_accepted_by_the_assessment_contract(self) -> None:
        """The mapper must never emit a field the decision engine would reject."""
        frame = DetectionParser().parse(
            [
                {"class": "flood_water", "confidence": 0.9, "bbox": box(0, 0, 1000, 800)},
                {"class": "person", "confidence": 0.9},
                {"class": "boat", "confidence": 0.8},
                {"class": "power_line", "confidence": 0.7},
            ],
            frame=FRAME,
        )

        assessment = AssessmentMapper().map(frame)

        assert IncidentAssessment.model_validate(assessment.model_dump()) == assessment


class TestVisionServiceContract:
    def test_analyze_exposes_a_single_entry_point(self) -> None:
        assert callable(VisionService(detector=StaticDetector([])).analyze)

    def test_detector_is_replaceable(self) -> None:
        """A custom detector needs only the base contract, not YOLO."""

        class ScriptedDetector(StaticDetector):
            def __init__(self) -> None:
                super().__init__(detections=[{"class": "fire", "confidence": 0.99}])

        assessment = VisionService(detector=ScriptedDetector()).analyze("frame.jpg")

        assert assessment.fire_detected is True

    def test_parser_and_mapper_are_injectable(self) -> None:
        instance = VisionService(
            detector=StaticDetector([{"class": "fire", "confidence": 0.5}]),
            parser=DetectionParser(min_confidence=0.9),
            mapper=AssessmentMapper(),
        )

        assert instance.analyze("frame.jpg").fire_detected is None

    def test_detect_frame_exposes_discarded_detections(self) -> None:
        frame = service([{"class": "unicorn", "confidence": 0.9}]).detect_frame("frame.jpg")

        assert frame.discarded[0].raw_class == "unicorn"


class TestDecisionEngineCompatibility:
    def test_assessment_flows_into_the_decision_engine(self) -> None:
        """Vision output must be consumable by the existing engine without adaptation."""
        from app.engines import DecisionEngine

        detections = [
            {"class": "collapsed_building", "confidence": 0.92},
            {"class": "person", "confidence": 0.9},
            {"class": "person", "confidence": 0.88},
            {"class": "debris", "confidence": 0.8},
        ]

        assessment = service(detections).analyze("frame.jpg")
        decision = DecisionEngine().decide(assessment)

        assert decision.severity_level is not None
        assert decision.priority_level is not None
        assert decision.recommended_actions

    def test_empty_frame_still_yields_a_decision(self) -> None:
        from app.engines import DecisionEngine

        decision = DecisionEngine().decide(service([]).analyze("frame.jpg"))

        assert decision.summary
        assert decision.confidence_level.value in {"VERY_LOW", "LOW", "MODERATE", "HIGH"}


class TestUltralyticsAdapter:
    def test_missing_image_raises_domain_error(self) -> None:
        from app.exceptions import ImageNotReadableError
        from app.vision import UltralyticsYOLODetector

        detector = UltralyticsYOLODetector(model_path="model.pt")

        with pytest.raises(ImageNotReadableError):
            detector.detect("does-not-exist.jpg")

    def test_result_flattening_handles_ultralytics_shapes(self) -> None:
        """Boxes arrive as tensor-like objects with nested coordinates and index classes."""
        from app.vision import UltralyticsYOLODetector

        class FakeTensor:
            def __init__(self, value: list) -> None:
                self._value = value

            def tolist(self) -> list:
                return self._value

            def item(self) -> float:
                return float(self._value[0])

        class FakeBox:
            def __init__(self, cls: int, conf: float, xyxy: list) -> None:
                self.cls = FakeTensor([cls])
                self.conf = FakeTensor([conf])
                self.xyxy = FakeTensor([xyxy])

        class FakeResult:
            def __init__(self) -> None:
                self.names = {0: "person", 1: "fire"}
                self.boxes = [
                    FakeBox(0, 0.93, [1.0, 2.0, 3.0, 4.0]),
                    FakeBox(1, 0.88, [5.0, 6.0, 7.0, 8.0]),
                ]

        detector = UltralyticsYOLODetector(model_path="model.pt")
        raw = detector._flatten_result(FakeResult())

        assert raw == [
            {"class": "person", "confidence": 0.93, "bbox": [1.0, 2.0, 3.0, 4.0]},
            {"class": "fire", "confidence": 0.88, "bbox": [5.0, 6.0, 7.0, 8.0]},
        ]

    def test_flattened_output_parses_end_to_end(self) -> None:
        raw = [
            {"class": "person", "confidence": 0.93, "bbox": [1.0, 2.0, 3.0, 4.0]},
            {"class": "fire", "confidence": 0.88, "bbox": [5.0, 6.0, 7.0, 8.0]},
        ]

        assessment = AssessmentMapper().map(DetectionParser().parse(raw, frame=FRAME))

        assert assessment.people_detected == 1
        assert assessment.fire_detected is True

    def test_unmapped_class_index_is_discarded(self) -> None:
        """A class index absent from the model's name map must not become a detection."""
        from app.vision import UltralyticsYOLODetector

        class FakeTensor:
            def __init__(self, value: list) -> None:
                self._value = value

            def tolist(self) -> list:
                return self._value

            def item(self) -> float:
                return float(self._value[0])

        class FakeBox:
            def __init__(self) -> None:
                self.cls = FakeTensor([7])
                self.conf = FakeTensor([0.9])
                self.xyxy = FakeTensor([[1.0, 2.0, 3.0, 4.0]])

        class FakeResult:
            def __init__(self) -> None:
                self.names = {0: "person"}
                self.boxes = [FakeBox()]

        raw = UltralyticsYOLODetector(model_path="model.pt")._flatten_result(FakeResult())
        frame = DetectionParser().parse(raw)

        assert raw[0]["class"] == "7"
        assert frame.detections == ()
