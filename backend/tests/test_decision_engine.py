"""Unit tests for the deterministic Decision Intelligence Engine."""

import pytest
from pydantic import ValidationError

from app.engines import (
    ConfidenceEngine,
    ConfidenceLevel,
    DecisionEngine,
    DisasterType,
    IncidentAssessment,
    PriorityEngine,
    PriorityLevel,
    SeverityEngine,
    SeverityLevel,
)

SEVERITY_ORDER = [
    SeverityLevel.MINOR,
    SeverityLevel.MODERATE,
    SeverityLevel.HIGH,
    SeverityLevel.SEVERE,
    SeverityLevel.CRITICAL,
]

PRIORITY_ORDER = [
    PriorityLevel.LOW,
    PriorityLevel.MODERATE,
    PriorityLevel.HIGH,
    PriorityLevel.URGENT,
    PriorityLevel.CRITICAL,
]


def severity_rank(level: SeverityLevel) -> int:
    return SEVERITY_ORDER.index(level)


def priority_rank(level: PriorityLevel) -> int:
    return PRIORITY_ORDER.index(level)


@pytest.fixture
def engine() -> DecisionEngine:
    return DecisionEngine()


BUILDING_FIRE = IncidentAssessment(
    incident_type="Building Fire",
    victims=12,
    children=2,
    elderly=1,
    people_detected=15,
    fire_detected=True,
    smoke_detected=True,
    collapsed_structure=False,
    road_blocked=False,
    hospital_distance_km=4,
    gas_station_nearby=False,
    weather="clear",
)

FLOOD = IncidentAssessment(
    incident_type="Flood",
    victims=8,
    children=3,
    elderly=2,
    trapped_people=4,
    people_detected=20,
    water_level_m=1.8,
    road_blocked=True,
    evacuation_required=True,
    hospital_distance_km=12,
    weather="rain",
)

BUILDING_COLLAPSE = IncidentAssessment(
    incident_type="Building Collapse",
    victims=6,
    trapped_people=5,
    people_detected=9,
    collapsed_structure=True,
    structural_damage=True,
    road_blocked=True,
    hospital_distance_km=7,
    weather="clear",
)

CHEMICAL_LEAK = IncidentAssessment(
    incident_type="Chemical Leak",
    victims=2,
    people_detected=30,
    hazardous_material=True,
    toxic_gas_detected=True,
    explosion_risk=False,
    evacuation_required=True,
    wind_speed_kmh=15,
    hospital_distance_km=6,
    weather="clear",
)

TRAIN_ACCIDENT = IncidentAssessment(
    incident_type="Train Accident",
    victims=35,
    children=4,
    elderly=3,
    trapped_people=8,
    passengers_onboard=180,
    people_detected=150,
    derailment=True,
    structural_damage=True,
    fire_detected=False,
    hazardous_material=False,
    road_blocked=True,
    hospital_distance_km=15,
    weather="clear",
)


class TestBuildingFire:
    def test_severity_is_severe(self, engine: DecisionEngine) -> None:
        result = engine.decide(BUILDING_FIRE)

        assert result.disaster_type is DisasterType.BUILDING_FIRE
        assert result.severity_level is SeverityLevel.SEVERE
        assert result.severity_score >= 65.0

    def test_priority_is_at_least_urgent(self, engine: DecisionEngine) -> None:
        result = engine.decide(BUILDING_FIRE)

        assert priority_rank(result.priority_level) >= priority_rank(PriorityLevel.URGENT)

    def test_mass_casualty_priority_floor_applied(self, engine: DecisionEngine) -> None:
        """Urgency is floored for casualties with fire; severity already clears its floor."""
        result = engine.decide(BUILDING_FIRE)

        assert result.priority_detail.applied_floor == "MASS_CASUALTY_WITH_FIRE"
        assert result.severity_detail.applied_floor is None
        assert result.severity_score > 65.0

    def test_actions_include_fire_attack_and_triage(self, engine: DecisionEngine) -> None:
        result = engine.decide(BUILDING_FIRE)
        actions = " ".join(result.recommended_actions)

        assert "fire crews" in actions
        assert "triage" in actions

    def test_vulnerable_occupants_surfaced(self, engine: DecisionEngine) -> None:
        result = engine.decide(BUILDING_FIRE)

        assert any("children" in factor for factor in result.risk_factors)


class TestFlood:
    def test_severity_is_critical(self, engine: DecisionEngine) -> None:
        result = engine.decide(FLOOD)

        assert result.disaster_type is DisasterType.FLOOD
        assert result.severity_level is SeverityLevel.CRITICAL

    def test_priority_is_critical(self, engine: DecisionEngine) -> None:
        result = engine.decide(FLOOD)

        assert result.priority_level is PriorityLevel.CRITICAL

    def test_water_depth_drives_risk_factors(self, engine: DecisionEngine) -> None:
        result = engine.decide(FLOOD)

        assert any("1.8 m" in factor for factor in result.risk_factors)

    def test_water_rescue_recommended(self, engine: DecisionEngine) -> None:
        result = engine.decide(FLOOD)

        assert any("water rescue" in action.lower() for action in result.recommended_actions)


class TestBuildingCollapse:
    def test_severity_is_severe_or_critical(self, engine: DecisionEngine) -> None:
        result = engine.decide(BUILDING_COLLAPSE)

        assert result.disaster_type is DisasterType.BUILDING_COLLAPSE
        assert severity_rank(result.severity_level) >= severity_rank(SeverityLevel.SEVERE)

    def test_priority_is_critical(self, engine: DecisionEngine) -> None:
        result = engine.decide(BUILDING_COLLAPSE)

        assert result.priority_level is PriorityLevel.CRITICAL

    def test_entrapment_within_collapse_scored(self, engine: DecisionEngine) -> None:
        result = engine.decide(BUILDING_COLLAPSE)
        codes = {factor.code for factor in result.severity_detail.factors}

        assert "HAZARD_COLLAPSE_ENTRAPMENT" in codes

    def test_structural_assessment_recommended(self, engine: DecisionEngine) -> None:
        result = engine.decide(BUILDING_COLLAPSE)

        assert any("structural engineering" in action for action in result.recommended_actions)


class TestChemicalLeak:
    def test_priority_exceeds_severity(self, engine: DecisionEngine) -> None:
        """A leak harming few people yet is urgent because containment cannot wait."""
        result = engine.decide(CHEMICAL_LEAK)

        assert result.priority_level is PriorityLevel.CRITICAL
        assert priority_rank(result.priority_level) > severity_rank(result.severity_level)
        assert result.priority_score > result.severity_score

    def test_toxic_release_floor_applied(self, engine: DecisionEngine) -> None:
        result = engine.decide(CHEMICAL_LEAK)

        assert result.priority_detail.applied_floor == "ACTIVE_TOXIC_RELEASE"

    def test_severity_is_not_critical(self, engine: DecisionEngine) -> None:
        result = engine.decide(CHEMICAL_LEAK)

        assert severity_rank(result.severity_level) < severity_rank(SeverityLevel.CRITICAL)

    def test_zone_control_recommended(self, engine: DecisionEngine) -> None:
        result = engine.decide(CHEMICAL_LEAK)
        actions = " ".join(result.recommended_actions)

        assert "hot, warm, and cold zones" in actions

    def test_divergence_explained(self, engine: DecisionEngine) -> None:
        result = engine.decide(CHEMICAL_LEAK)

        assert "Urgency exceeds severity" in result.summary


class TestTrainAccident:
    def test_severity_is_critical(self, engine: DecisionEngine) -> None:
        result = engine.decide(TRAIN_ACCIDENT)

        assert result.disaster_type is DisasterType.TRAIN_ACCIDENT
        assert result.severity_level is SeverityLevel.CRITICAL

    def test_priority_is_critical(self, engine: DecisionEngine) -> None:
        result = engine.decide(TRAIN_ACCIDENT)

        assert result.priority_level is PriorityLevel.CRITICAL

    def test_rail_isolation_recommended(self, engine: DecisionEngine) -> None:
        result = engine.decide(TRAIN_ACCIDENT)

        assert any("traction power isolation" in action for action in result.recommended_actions)

    def test_passenger_load_scored(self, engine: DecisionEngine) -> None:
        result = engine.decide(TRAIN_ACCIDENT)
        codes = {factor.code for factor in result.severity_detail.factors}

        assert "LIFE_PASSENGERS" in codes


class TestSeverityEngine:
    def test_minor_incident_scores_low(self) -> None:
        assessment = IncidentAssessment(
            incident_type="Road Accident",
            victims=0,
            trapped_people=0,
            people_detected=2,
            fire_detected=False,
            road_blocked=False,
            hospital_distance_km=3,
            weather="clear",
        )

        result = SeverityEngine().evaluate(assessment)

        assert result.level is SeverityLevel.MINOR
        assert result.applied_floor is None

    def test_floors_only_raise_scores(self) -> None:
        assessment = IncidentAssessment(incident_type="Building Fire", trapped_people=1)

        result = SeverityEngine().evaluate(assessment)
        unfloored = sum(factor.contribution for factor in result.factors)

        assert result.score >= unfloored
        assert result.applied_floor == "TRAPPED_CASUALTIES"

    def test_highest_applicable_floor_wins(self) -> None:
        assessment = IncidentAssessment(
            incident_type="Building Collapse",
            victims=30,
            trapped_people=2,
            collapsed_structure=True,
        )

        result = SeverityEngine().evaluate(assessment)

        assert result.applied_floor == "MAJOR_CASUALTY_INCIDENT"

    def test_mass_casualty_floor_binds_a_low_scoring_incident(self) -> None:
        """Ten casualties reach SEVERE even where no other hazard is reported."""
        assessment = IncidentAssessment(incident_type="Road Accident", victims=10)

        result = SeverityEngine().evaluate(assessment)

        assert result.applied_floor == "MASS_CASUALTY_INCIDENT"
        assert result.level is SeverityLevel.SEVERE

    def test_collapse_with_casualties_floor_binds(self) -> None:
        assessment = IncidentAssessment(
            incident_type="Landslide", victims=1, collapsed_structure=True
        )

        result = SeverityEngine().evaluate(assessment)

        assert result.applied_floor == "COLLAPSE_WITH_CASUALTIES"
        assert result.level is SeverityLevel.SEVERE

    def test_floor_is_not_applied_when_score_already_exceeds_it(self) -> None:
        """Floors raise a score to a minimum; they never pull a higher score down."""
        assessment = IncidentAssessment(
            incident_type="Building Collapse",
            victims=40,
            trapped_people=20,
            collapsed_structure=True,
            structural_damage=True,
            fire_detected=True,
        )

        result = SeverityEngine().evaluate(assessment)

        assert result.applied_floor is None
        assert result.score > 85.0

    def test_score_never_exceeds_maximum(self) -> None:
        assessment = IncidentAssessment(
            incident_type="Earthquake",
            victims=500,
            children=100,
            elderly=100,
            trapped_people=200,
            people_detected=2000,
            passengers_onboard=500,
            fire_detected=True,
            smoke_detected=True,
            collapsed_structure=True,
            structural_damage=True,
            hazardous_material=True,
            toxic_gas_detected=True,
            explosion_risk=True,
            power_lines_down=True,
            road_blocked=True,
            night_time=True,
            water_level_m=5.0,
            wind_speed_kmh=120.0,
            hospital_distance_km=50.0,
            weather="storm",
        )

        result = SeverityEngine().evaluate(assessment)

        assert result.score <= 100.0

    def test_detected_people_never_reduce_casualty_scoring(self) -> None:
        """Detection counts are lower bounds and must not offset reported casualties."""
        with_detection = IncidentAssessment(
            incident_type="Building Fire", victims=10, people_detected=0
        )
        without_detection = IncidentAssessment(incident_type="Building Fire", victims=10)

        assert (
            SeverityEngine().evaluate(with_detection).score
            >= SeverityEngine().evaluate(without_detection).score
        )

    def test_disaster_emphasis_changes_scoring(self) -> None:
        """The same collapse weighs more for an earthquake than for a road accident."""
        earthquake = IncidentAssessment(incident_type="Earthquake", collapsed_structure=True)
        road = IncidentAssessment(incident_type="Road Accident", collapsed_structure=True)

        earthquake_collapse = next(
            factor
            for factor in SeverityEngine().evaluate(earthquake).factors
            if factor.code == "HAZARD_COLLAPSED_STRUCTURE"
        )
        road_collapse = next(
            factor
            for factor in SeverityEngine().evaluate(road).factors
            if factor.code == "HAZARD_COLLAPSED_STRUCTURE"
        )

        assert earthquake_collapse.contribution > road_collapse.contribution


class TestPriorityEngine:
    def test_urgency_is_independent_of_severity(self) -> None:
        """Moderate harm with an active release still demands the highest urgency."""
        assessment = IncidentAssessment(
            incident_type="Chemical Leak",
            victims=0,
            people_detected=5,
            toxic_gas_detected=True,
            hazardous_material=True,
        )

        severity = SeverityEngine().evaluate(assessment)
        priority = PriorityEngine().evaluate(assessment)

        assert severity_rank(severity.level) < severity_rank(SeverityLevel.SEVERE)
        assert priority.level is PriorityLevel.CRITICAL

    def test_trapped_floor_binds_a_low_scoring_incident(self) -> None:
        """A single trapped person makes the response immediate on its own."""
        assessment = IncidentAssessment(incident_type="Road Accident", trapped_people=1)

        result = PriorityEngine().evaluate(assessment)

        assert result.applied_floor == "SAVABLE_TRAPPED_CASUALTIES"
        assert result.level is PriorityLevel.CRITICAL

    def test_responders_on_scene_reduce_urgency(self) -> None:
        base = IncidentAssessment(incident_type="Flood", victims=4, water_level_m=0.6)
        crewed = base.model_copy(update={"responders_on_scene": 6})

        assert PriorityEngine().evaluate(crewed).score < PriorityEngine().evaluate(base).score

    def test_stable_incident_ranks_below_developing_incident(self) -> None:
        stable = IncidentAssessment(
            incident_type="Road Accident", victims=6, fire_detected=False, road_blocked=False
        )
        developing = IncidentAssessment(
            incident_type="Road Accident", victims=6, fire_detected=True, explosion_risk=True
        )

        assert (
            PriorityEngine().evaluate(developing).score
            > PriorityEngine().evaluate(stable).score
        )

    def test_score_never_exceeds_maximum(self) -> None:
        assessment = IncidentAssessment(
            incident_type="Chemical Leak",
            victims=200,
            children=50,
            elderly=50,
            trapped_people=60,
            people_detected=900,
            toxic_gas_detected=True,
            explosion_risk=True,
            hazardous_material=True,
            collapsed_structure=True,
            fire_detected=True,
            smoke_detected=True,
            derailment=True,
            power_lines_down=True,
            evacuation_required=True,
            road_blocked=True,
            night_time=True,
            water_level_m=3.0,
            hospital_distance_km=40.0,
            weather="storm",
        )

        assert PriorityEngine().evaluate(assessment).score <= 100.0


class TestConfidenceEngine:
    def test_complete_report_scores_high(self) -> None:
        result = ConfidenceEngine().evaluate(BUILDING_FIRE)

        assert result.level in {ConfidenceLevel.MODERATE, ConfidenceLevel.HIGH}
        assert result.missing_fields != []

    def test_missing_information_reduces_confidence(self) -> None:
        sparse = IncidentAssessment(incident_type="Building Fire")
        rich = BUILDING_FIRE

        assert (
            ConfidenceEngine().evaluate(sparse).confidence
            < ConfidenceEngine().evaluate(rich).confidence
        )

    def test_reported_zero_counts_as_evidence(self) -> None:
        """A reported zero is information; an omitted field is not."""
        reported = IncidentAssessment(incident_type="Building Fire", victims=0)
        omitted = IncidentAssessment(incident_type="Building Fire")

        assert (
            ConfidenceEngine().evaluate(reported).confidence
            > ConfidenceEngine().evaluate(omitted).confidence
        )
        assert "victims" in ConfidenceEngine().evaluate(reported).observed_fields
        assert "victims" in ConfidenceEngine().evaluate(omitted).missing_fields

    def test_unknown_incident_type_caps_confidence(self) -> None:
        assessment = IncidentAssessment(
            incident_type="Something Unrecognised",
            victims=3,
            trapped_people=1,
            people_detected=5,
            road_blocked=False,
            hospital_distance_km=2,
            weather="clear",
            night_time=False,
            responders_on_scene=2,
            children=0,
            elderly=0,
        )

        result = ConfidenceEngine().evaluate(assessment)

        assert result.applied_cap == "UNRECOGNISED_INCIDENT_TYPE"
        assert result.confidence <= 0.55

    def test_missing_critical_evidence_caps_confidence(self) -> None:
        assessment = IncidentAssessment(
            incident_type="Chemical Leak",
            victims=1,
            trapped_people=0,
            children=0,
            elderly=0,
            people_detected=4,
            hazardous_material=True,
            explosion_risk=False,
            evacuation_required=True,
            wind_speed_kmh=10,
            road_blocked=False,
            hospital_distance_km=3,
            weather="clear",
            night_time=False,
            responders_on_scene=1,
        )

        result = ConfidenceEngine().evaluate(assessment)

        assert "toxic_gas_detected" in result.missing_fields
        assert result.applied_cap == "MISSING_CRITICAL_EVIDENCE"

    def test_contradiction_penalised(self) -> None:
        contradictory = IncidentAssessment(
            incident_type="Building Collapse", collapsed_structure=True, structural_damage=False
        )

        result = ConfidenceEngine().evaluate(contradictory)
        codes = {penalty.code for penalty in result.penalties}

        assert "CONTRADICTION_COLLAPSE_WITHOUT_DAMAGE" in codes

    def test_inconsistent_counts_penalised(self) -> None:
        inconsistent = IncidentAssessment(
            incident_type="Flood", victims=10, people_detected=4, trapped_people=12
        )

        codes = {penalty.code for penalty in ConfidenceEngine().evaluate(inconsistent).penalties}

        assert "INCONSISTENCY_VICTIMS_EXCEED_DETECTED" in codes
        assert "INCONSISTENCY_TRAPPED_EXCEED_VICTIMS" in codes

    def test_confidence_stays_within_bounds(self) -> None:
        result = ConfidenceEngine().evaluate(
            IncidentAssessment(
                incident_type="Flood", victims=10, people_detected=1, trapped_people=99
            )
        )

        assert 0.0 <= result.confidence <= 1.0


class TestConfidenceDoesNotAlterDecisions:
    def test_severity_and_priority_ignore_confidence(self) -> None:
        """Adding low-value context must not move severity or priority scores."""
        core = IncidentAssessment(
            incident_type="Building Fire", victims=5, fire_detected=True, trapped_people=1
        )
        annotated = core.model_copy(update={"responders_on_scene": None, "weather": None})

        assert SeverityEngine().evaluate(core).score == SeverityEngine().evaluate(annotated).score
        assert PriorityEngine().evaluate(core).score == PriorityEngine().evaluate(annotated).score

    def test_sparse_report_is_not_downgraded(self) -> None:
        """An incompletely reported entrapment keeps its severity floor."""
        sparse = IncidentAssessment(incident_type="Building Fire", trapped_people=2)

        result = DecisionEngine().decide(sparse)

        assert result.severity_level is SeverityLevel.SEVERE
        assert result.priority_level is PriorityLevel.CRITICAL
        assert result.confidence_level in {ConfidenceLevel.VERY_LOW, ConfidenceLevel.LOW}


class TestExplanation:
    def test_all_sections_populated(self, engine: DecisionEngine) -> None:
        explanation = engine.decide(BUILDING_FIRE).explanation

        assert explanation.current_situation
        assert explanation.severity
        assert explanation.priority
        assert explanation.key_risk_factors
        assert explanation.recommended_immediate_actions
        assert explanation.reasoning_summary

    def test_levels_appear_in_statements(self, engine: DecisionEngine) -> None:
        result = engine.decide(FLOOD)

        assert result.severity_level.value in result.explanation.severity
        assert result.priority_level.value in result.explanation.priority

    def test_missing_fields_named_in_summary(self, engine: DecisionEngine) -> None:
        result = engine.decide(IncidentAssessment(incident_type="Flood", victims=2))

        assert "Unreported" in result.summary
        assert "not reduced because of these gaps" in result.summary

    def test_baseline_actions_always_present(self, engine: DecisionEngine) -> None:
        actions = engine.decide(IncidentAssessment(incident_type="Flood")).recommended_actions

        assert any("incident command" in action for action in actions)

    def test_risk_factors_are_unique(self, engine: DecisionEngine) -> None:
        factors = engine.decide(TRAIN_ACCIDENT).risk_factors

        assert len(factors) == len(set(factors))

    def test_same_hazard_is_not_listed_twice(self, engine: DecisionEngine) -> None:
        """Severity and priority both score toxic gas; the risk list mentions it once."""
        result = engine.decide(CHEMICAL_LEAK)

        gas_mentions = [factor for factor in result.risk_factors if "Toxic gas" in factor]

        assert len(gas_mentions) == 1

    def test_situation_reads_as_complete_sentences(self, engine: DecisionEngine) -> None:
        situation = engine.decide(CHEMICAL_LEAK).explanation.current_situation

        for sentence in (part.strip() for part in situation.split(".") if part.strip()):
            assert sentence[0].isupper() or sentence[0].isdigit()

    def test_severity_dominant_incident_explains_divergence(self, engine: DecisionEngine) -> None:
        stabilised = IncidentAssessment(
            incident_type="Building Collapse",
            victims=20,
            trapped_people=0,
            collapsed_structure=True,
            structural_damage=True,
            responders_on_scene=12,
            road_blocked=False,
            weather="clear",
        )

        result = engine.decide(stabilised)

        assert result.severity_score > result.priority_score
        assert "Severity exceeds urgency" in result.summary


class TestDecisionEngine:
    def test_pipeline_is_deterministic(self, engine: DecisionEngine) -> None:
        first = engine.decide(TRAIN_ACCIDENT)
        second = DecisionEngine().decide(TRAIN_ACCIDENT)

        assert first.model_dump() == second.model_dump()

    def test_result_exposes_every_required_output(self, engine: DecisionEngine) -> None:
        result = engine.decide(CHEMICAL_LEAK)

        assert 0.0 <= result.severity_score <= 100.0
        assert 0.0 <= result.priority_score <= 100.0
        assert 0.0 <= result.confidence <= 1.0
        assert isinstance(result.severity_level, SeverityLevel)
        assert isinstance(result.priority_level, PriorityLevel)
        assert isinstance(result.confidence_level, ConfidenceLevel)
        assert result.recommended_actions
        assert result.risk_factors
        assert result.summary

    def test_minimal_input_produces_complete_decision(self, engine: DecisionEngine) -> None:
        result = engine.decide(IncidentAssessment(incident_type="Flood"))

        assert result.severity_level in SEVERITY_ORDER
        assert result.priority_level in PRIORITY_ORDER
        assert result.recommended_actions
        assert result.summary

    def test_incident_type_aliases_resolve(self, engine: DecisionEngine) -> None:
        for label in ("Building Fire", "building_fire", "BUILDING FIRE", "house fire"):
            assert engine.decide(IncidentAssessment(incident_type=label)).disaster_type is (
                DisasterType.BUILDING_FIRE
            )

    def test_unknown_type_is_not_forced_into_taxonomy(self, engine: DecisionEngine) -> None:
        result = engine.decide(IncidentAssessment(incident_type="Alien Invasion"))

        assert result.disaster_type is DisasterType.UNKNOWN

    def test_unknown_fields_are_rejected(self) -> None:
        with pytest.raises(ValidationError):
            IncidentAssessment(incident_type="Building Fire", victim_count=4)

    def test_negative_counts_are_rejected(self) -> None:
        with pytest.raises(ValidationError):
            IncidentAssessment(incident_type="Building Fire", victims=-1)

    def test_example_payload_from_specification(self, engine: DecisionEngine) -> None:
        payload = {
            "incident_type": "Building Fire",
            "victims": 12,
            "children": 2,
            "elderly": 1,
            "people_detected": 15,
            "fire_detected": True,
            "smoke_detected": True,
            "collapsed_structure": False,
            "road_blocked": False,
            "hospital_distance_km": 4,
            "gas_station_nearby": False,
            "weather": "clear",
        }

        result = engine.decide(IncidentAssessment.model_validate(payload))

        assert result.severity_level is SeverityLevel.SEVERE
        assert priority_rank(result.priority_level) >= priority_rank(PriorityLevel.URGENT)
        assert result.confidence > 0.0
