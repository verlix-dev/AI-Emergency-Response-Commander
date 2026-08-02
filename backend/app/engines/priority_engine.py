"""Deterministic response-urgency analysis, computed independently of severity.

Severity measures harm that already exists. Urgency measures whether the clock is
load-bearing: how quickly the situation deteriorates, how much worse it becomes if the
response is late, and how much friction stands between responders and the scene.

The two are computed from the same assessment but by separate rules, so a moderate-harm
incident with a fast-closing window outranks a higher-harm incident that has stabilised.
"""

from collections.abc import Callable

from app.engines.config import (
    DISASTER_PROFILES,
    HOSPITAL_DISTANCE_PRIORITY_BANDS,
    MASS_CASUALTY_VICTIM_THRESHOLD,
    PRIORITY_BANDS,
    PRIORITY_FLOOR_EXPLOSION_RISK,
    PRIORITY_FLOOR_HAZMAT_EXPOSURE,
    PRIORITY_FLOOR_MASS_CASUALTY_FIRE,
    PRIORITY_FLOOR_TOXIC_GAS,
    PRIORITY_FLOOR_TRAPPED,
    PRIORITY_WEIGHTS,
    RISING_WATER_THRESHOLD_M,
    WEATHER_PRIORITY_POINTS,
    DisasterProfile,
)
from app.engines.models import (
    IncidentAssessment,
    PriorityResult,
    ReasoningFactor,
)
from app.engines.normalization import resolve_disaster_type, resolve_weather
from app.engines.scoring import clamp_score, resolve_band, round_score

RuleFunction = Callable[[IncidentAssessment, DisasterProfile], list[ReasoningFactor]]


def _banded_points(value: float, bands: tuple[tuple[float, float], ...]) -> float:
    """Return the points for the first band whose lower bound the value meets."""
    for threshold, points in bands:
        if value >= threshold:
            return points
    return 0.0


def _capped(count: int, points_each: float, cap: float) -> float:
    """Scale a count by its per-unit points without exceeding the rule's cap."""
    return min(count * points_each, cap)


def _savable_life_rules(
    assessment: IncidentAssessment,
    profile: DisasterProfile,
) -> list[ReasoningFactor]:
    """Score the people whose outcome still depends on how fast the response arrives."""
    weights = PRIORITY_WEIGHTS
    factors: list[ReasoningFactor] = []

    if assessment.trapped_people:
        factors.append(
            ReasoningFactor(
                code="URGENCY_TRAPPED",
                description=f"{assessment.trapped_people} trapped and awaiting rescue",
                contribution=_capped(
                    assessment.trapped_people, weights.trapped_points, weights.trapped_cap
                ),
            )
        )
    if assessment.victims:
        factors.append(
            ReasoningFactor(
                code="URGENCY_VICTIMS",
                description=f"{assessment.victims} casualties needing treatment",
                contribution=_capped(assessment.victims, weights.victim_points, weights.victim_cap),
            )
        )
    if assessment.children:
        factors.append(
            ReasoningFactor(
                code="URGENCY_CHILDREN",
                description=f"{assessment.children} children requiring assisted rescue",
                contribution=_capped(assessment.children, weights.child_points, weights.child_cap),
            )
        )
    if assessment.elderly:
        factors.append(
            ReasoningFactor(
                code="URGENCY_ELDERLY",
                description=f"{assessment.elderly} elderly requiring assisted rescue",
                contribution=_capped(
                    assessment.elderly, weights.elderly_points, weights.elderly_cap
                ),
            )
        )
    return factors


def _escalation_rules(
    assessment: IncidentAssessment,
    profile: DisasterProfile,
) -> list[ReasoningFactor]:
    """Score hazards that make the situation worse the longer the response takes."""
    weights = PRIORITY_WEIGHTS
    factors: list[ReasoningFactor] = []
    flags: tuple[tuple[bool | None, str, str, float], ...] = (
        (
            assessment.toxic_gas_detected,
            "ESCALATION_TOXIC_GAS",
            "Toxic gas spreading from the source",
            weights.toxic_gas,
        ),
        (
            assessment.explosion_risk,
            "ESCALATION_EXPLOSION_RISK",
            "Explosion risk that worsens with time",
            weights.explosion_risk,
        ),
        (
            assessment.hazardous_material,
            "ESCALATION_HAZARDOUS_MATERIAL",
            "Hazardous material release",
            weights.hazardous_material,
        ),
        (
            assessment.collapsed_structure,
            "ESCALATION_COLLAPSE",
            "Collapse with a closing survivability window",
            weights.collapsed_structure,
        ),
        (assessment.fire_detected, "ESCALATION_FIRE", "Fire growth over time", weights.fire),
        (assessment.smoke_detected, "ESCALATION_SMOKE", "Spreading smoke", weights.smoke),
        (
            assessment.derailment,
            "ESCALATION_DERAILMENT",
            "Derailment blocking the line",
            weights.derailment,
        ),
        (
            assessment.power_lines_down,
            "ESCALATION_POWER_LINES",
            "Live power infrastructure down",
            weights.power_lines_down,
        ),
        (
            assessment.evacuation_required,
            "ESCALATION_EVACUATION",
            "Evacuation still to be completed",
            weights.evacuation_required,
        ),
    )
    for is_present, code, description, points in flags:
        if is_present:
            factors.append(
                ReasoningFactor(code=code, description=description, contribution=points)
            )

    if assessment.water_level_m and assessment.water_level_m >= RISING_WATER_THRESHOLD_M:
        factors.append(
            ReasoningFactor(
                code="ESCALATION_WATER_LEVEL",
                description=f"Flood water at {assessment.water_level_m} m limiting refuge",
                contribution=weights.rising_water,
            )
        )
    return factors


def _response_friction_rules(
    assessment: IncidentAssessment,
    profile: DisasterProfile,
) -> list[ReasoningFactor]:
    """Score the delay between tasking and arrival, which must be started against."""
    weights = PRIORITY_WEIGHTS
    factors: list[ReasoningFactor] = []

    if assessment.road_blocked:
        factors.append(
            ReasoningFactor(
                code="FRICTION_ROAD_BLOCKED",
                description="Blocked access delays arrival",
                contribution=weights.road_blocked,
            )
        )
    if assessment.hospital_distance_km is not None:
        points = _banded_points(assessment.hospital_distance_km, HOSPITAL_DISTANCE_PRIORITY_BANDS)
        if points > 0:
            factors.append(
                ReasoningFactor(
                    code="FRICTION_HOSPITAL_DISTANCE",
                    description=(
                        f"Casualty transport of {assessment.hospital_distance_km} km to hospital"
                    ),
                    contribution=points,
                )
            )
    weather = resolve_weather(assessment.weather)
    weather_points = WEATHER_PRIORITY_POINTS[weather]
    if weather_points > 0:
        factors.append(
            ReasoningFactor(
                code="FRICTION_WEATHER",
                description=f"{weather.value} conditions slow the response",
                contribution=weather_points,
            )
        )
    if assessment.night_time:
        factors.append(
            ReasoningFactor(
                code="FRICTION_NIGHT",
                description="Night-time conditions slow search and access",
                contribution=weights.night_time,
            )
        )
    if assessment.responders_on_scene:
        factors.append(
            ReasoningFactor(
                code="MITIGATION_RESPONDERS_ON_SCENE",
                description=(
                    f"{assessment.responders_on_scene} responders already committed on scene"
                ),
                contribution=weights.responders_present_relief,
            )
        )
    return factors


COMMON_RULES: tuple[RuleFunction, ...] = (
    _savable_life_rules,
    _escalation_rules,
    _response_friction_rules,
)


class PriorityEngine:
    """Convert a structured assessment into a response-urgency score and level."""

    def evaluate(self, assessment: IncidentAssessment) -> PriorityResult:
        """Score urgency, apply time-critical floors, and resolve the priority level."""
        disaster_type = resolve_disaster_type(assessment.incident_type)
        profile = DISASTER_PROFILES[disaster_type]

        factors: list[ReasoningFactor] = [
            ReasoningFactor(
                code="URGENCY_BASELINE",
                description=f"Baseline response urgency for {disaster_type.value}",
                contribution=profile.urgency_bias,
            )
        ]
        for rule in COMMON_RULES:
            factors.extend(rule(assessment, profile))

        raw_score = clamp_score(sum(factor.contribution for factor in factors))
        score, applied_floor = self._apply_floors(raw_score, assessment)

        return PriorityResult(
            score=round_score(score),
            level=resolve_band(score, PRIORITY_BANDS),
            factors=factors,
            applied_floor=applied_floor,
        )

    def _apply_floors(
        self,
        score: float,
        assessment: IncidentAssessment,
    ) -> tuple[float, str | None]:
        """Raise urgency to a minimum where delay changes the outcome irreversibly.

        These floors are what separate urgency from severity: a contained release harming
        nobody yet still demands an immediate response, because the window to contain it
        closes whether or not harm has occurred.
        """
        exposed = (assessment.people_detected or 0) + (assessment.victims or 0)
        candidates: list[tuple[float, str]] = []

        if assessment.trapped_people:
            candidates.append((PRIORITY_FLOOR_TRAPPED, "SAVABLE_TRAPPED_CASUALTIES"))
        if assessment.toxic_gas_detected:
            candidates.append((PRIORITY_FLOOR_TOXIC_GAS, "ACTIVE_TOXIC_RELEASE"))
        if assessment.explosion_risk:
            candidates.append((PRIORITY_FLOOR_EXPLOSION_RISK, "IMMINENT_EXPLOSION_RISK"))
        if assessment.hazardous_material and exposed > 0:
            candidates.append((PRIORITY_FLOOR_HAZMAT_EXPOSURE, "HAZARDOUS_MATERIAL_EXPOSURE"))
        if assessment.fire_detected and (assessment.victims or 0) >= MASS_CASUALTY_VICTIM_THRESHOLD:
            candidates.append((PRIORITY_FLOOR_MASS_CASUALTY_FIRE, "MASS_CASUALTY_WITH_FIRE"))

        applicable = [(floor, code) for floor, code in candidates if floor > score]
        if not applicable:
            return score, None
        floor, code = max(applicable, key=lambda candidate: candidate[0])
        return floor, code
