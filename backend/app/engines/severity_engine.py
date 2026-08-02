"""Deterministic, rule-based severity analysis.

Severity answers a single question: how much harm exists right now. It is deliberately
independent of how fast the incident must be answered, which the priority engine owns.

Rules are grouped into life-safety, hazard, and context families that apply to every disaster
type, plus a registry of disaster-specific rules. Adding a new disaster's rules means
registering a function; no existing rule changes.
"""

from collections.abc import Callable

from app.engines.config import (
    DISASTER_PROFILES,
    HOSPITAL_DISTANCE_SEVERITY_BANDS,
    MAJOR_CASUALTY_VICTIM_THRESHOLD,
    MASS_CASUALTY_VICTIM_THRESHOLD,
    SEVERITY_BANDS,
    SEVERITY_FLOOR_COLLAPSE_WITH_CASUALTIES,
    SEVERITY_FLOOR_MAJOR_CASUALTY,
    SEVERITY_FLOOR_MASS_CASUALTY,
    SEVERITY_FLOOR_TRAPPED,
    SEVERITY_WEIGHTS,
    WATER_DEPTH_SEVERITY_BANDS,
    WEATHER_SEVERITY_POINTS,
    WIND_SPEED_SEVERITY_BANDS,
    DisasterProfile,
)
from app.engines.models import (
    DisasterType,
    IncidentAssessment,
    ReasoningFactor,
    SeverityResult,
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


def _life_safety_rules(
    assessment: IncidentAssessment,
    profile: DisasterProfile,
) -> list[ReasoningFactor]:
    """Score harm to people, which dominates severity for every disaster type."""
    weights = SEVERITY_WEIGHTS
    factors: list[ReasoningFactor] = []

    if assessment.victims:
        factors.append(
            ReasoningFactor(
                code="LIFE_VICTIMS",
                description=f"{assessment.victims} reported casualties",
                contribution=_capped(assessment.victims, weights.victim_points, weights.victim_cap),
            )
        )
    if assessment.trapped_people:
        factors.append(
            ReasoningFactor(
                code="LIFE_TRAPPED",
                description=f"{assessment.trapped_people} people trapped",
                contribution=_capped(
                    assessment.trapped_people, weights.trapped_points, weights.trapped_cap
                ),
            )
        )
    if assessment.children:
        factors.append(
            ReasoningFactor(
                code="LIFE_CHILDREN",
                description=f"{assessment.children} children affected",
                contribution=_capped(assessment.children, weights.child_points, weights.child_cap),
            )
        )
    if assessment.elderly:
        factors.append(
            ReasoningFactor(
                code="LIFE_ELDERLY",
                description=f"{assessment.elderly} elderly people affected",
                contribution=_capped(
                    assessment.elderly, weights.elderly_points, weights.elderly_cap
                ),
            )
        )

    exposed = _exposed_people(assessment)
    if exposed > 0:
        factors.append(
            ReasoningFactor(
                code="LIFE_EXPOSED",
                description=f"{exposed} further people detected in the affected area",
                contribution=_capped(exposed, weights.exposed_points, weights.exposed_cap),
            )
        )
    if assessment.passengers_onboard:
        factors.append(
            ReasoningFactor(
                code="LIFE_PASSENGERS",
                description=f"{assessment.passengers_onboard} passengers onboard",
                contribution=_capped(
                    assessment.passengers_onboard, weights.passenger_points, weights.passenger_cap
                ),
            )
        )
    return factors


def _exposed_people(assessment: IncidentAssessment) -> int:
    """Return people detected beyond those already counted as casualties.

    Detection counts are lower bounds on presence, so they are never allowed to reduce a
    casualty figure: only the surplus above known casualties contributes.
    """
    if assessment.people_detected is None:
        return 0
    return max(0, assessment.people_detected - (assessment.victims or 0))


def _hazard_rules(
    assessment: IncidentAssessment,
    profile: DisasterProfile,
) -> list[ReasoningFactor]:
    """Score the physical hazards present, independent of disaster classification."""
    weights = SEVERITY_WEIGHTS
    factors: list[ReasoningFactor] = []
    flags: tuple[tuple[bool | None, str, str, float], ...] = (
        (assessment.fire_detected, "HAZARD_FIRE", "Active fire", weights.fire),
        (assessment.smoke_detected, "HAZARD_SMOKE", "Smoke present", weights.smoke),
        (
            assessment.collapsed_structure,
            "HAZARD_COLLAPSED_STRUCTURE",
            "Structural collapse",
            weights.collapsed_structure,
        ),
        (
            assessment.structural_damage,
            "HAZARD_STRUCTURAL_DAMAGE",
            "Structural damage",
            weights.structural_damage,
        ),
        (
            assessment.hazardous_material,
            "HAZARD_HAZARDOUS_MATERIAL",
            "Hazardous material involved",
            weights.hazardous_material,
        ),
        (
            assessment.toxic_gas_detected,
            "HAZARD_TOXIC_GAS",
            "Toxic gas detected",
            weights.toxic_gas,
        ),
        (
            assessment.explosion_risk,
            "HAZARD_EXPLOSION_RISK",
            "Explosion risk",
            weights.explosion_risk,
        ),
        (assessment.derailment, "HAZARD_DERAILMENT", "Derailment", weights.derailment),
        (
            assessment.power_lines_down,
            "HAZARD_POWER_LINES",
            "Power lines down",
            weights.power_lines_down,
        ),
    )
    for is_present, code, description, points in flags:
        if is_present:
            factors.append(
                ReasoningFactor(code=code, description=description, contribution=points)
            )

    if assessment.water_level_m:
        points = _banded_points(assessment.water_level_m, WATER_DEPTH_SEVERITY_BANDS)
        if points > 0:
            factors.append(
                ReasoningFactor(
                    code="HAZARD_WATER_DEPTH",
                    description=f"Flood water at {assessment.water_level_m} m",
                    contribution=points,
                )
            )

    if assessment.gas_station_nearby:
        with_fire = bool(assessment.fire_detected or assessment.explosion_risk)
        factors.append(
            ReasoningFactor(
                code="HAZARD_GAS_STATION",
                description=(
                    "Fuel storage adjacent to active fire"
                    if with_fire
                    else "Fuel storage close to the incident"
                ),
                contribution=(
                    weights.gas_station_with_fire if with_fire else weights.gas_station_without_fire
                ),
            )
        )
    return factors


def _context_rules(
    assessment: IncidentAssessment,
    profile: DisasterProfile,
) -> list[ReasoningFactor]:
    """Score environmental and access conditions that worsen the present situation."""
    weights = SEVERITY_WEIGHTS
    factors: list[ReasoningFactor] = []

    if assessment.road_blocked:
        factors.append(
            ReasoningFactor(
                code="CONTEXT_ROAD_BLOCKED",
                description="Access route blocked",
                contribution=weights.road_blocked,
            )
        )
    if assessment.hospital_distance_km is not None:
        points = _banded_points(assessment.hospital_distance_km, HOSPITAL_DISTANCE_SEVERITY_BANDS)
        if points > 0:
            factors.append(
                ReasoningFactor(
                    code="CONTEXT_HOSPITAL_DISTANCE",
                    description=f"Nearest hospital {assessment.hospital_distance_km} km away",
                    contribution=points,
                )
            )
    if assessment.wind_speed_kmh is not None:
        points = _banded_points(assessment.wind_speed_kmh, WIND_SPEED_SEVERITY_BANDS)
        if points > 0:
            factors.append(
                ReasoningFactor(
                    code="CONTEXT_WIND_SPEED",
                    description=f"Wind at {assessment.wind_speed_kmh} km/h",
                    contribution=points,
                )
            )

    weather = resolve_weather(assessment.weather)
    weather_points = WEATHER_SEVERITY_POINTS[weather]
    if weather_points > 0:
        factors.append(
            ReasoningFactor(
                code="CONTEXT_WEATHER",
                description=f"Weather condition: {weather.value}",
                contribution=weather_points,
            )
        )
    if assessment.night_time:
        factors.append(
            ReasoningFactor(
                code="CONTEXT_NIGHT",
                description="Night-time operations",
                contribution=weights.night_time,
            )
        )
    return factors


def _collapse_rules(
    assessment: IncidentAssessment,
    profile: DisasterProfile,
) -> list[ReasoningFactor]:
    """Add the compounding harm of entrapment inside a collapsed structure."""
    if not assessment.collapsed_structure or not assessment.trapped_people:
        return []
    return [
        ReasoningFactor(
            code="HAZARD_COLLAPSE_ENTRAPMENT",
            description=(
                f"{assessment.trapped_people} people trapped within a collapsed structure"
            ),
            contribution=SEVERITY_WEIGHTS.collapse_entrapment,
        )
    ]


def _release_exposure_rules(
    assessment: IncidentAssessment,
    profile: DisasterProfile,
) -> list[ReasoningFactor]:
    """Add downwind exposure harm when a release coincides with people in the area."""
    release_active = bool(assessment.toxic_gas_detected or assessment.hazardous_material)
    if not release_active:
        return []
    exposed = _exposed_people(assessment) + (assessment.victims or 0)
    if exposed <= 0:
        return []
    return [
        ReasoningFactor(
            code="HAZARD_DOWNWIND_EXPOSURE",
            description=f"{exposed} people exposed in the release area",
            contribution=SEVERITY_WEIGHTS.downwind_exposure,
        )
    ]


DISASTER_RULES: dict[DisasterType, tuple[RuleFunction, ...]] = {
    DisasterType.EARTHQUAKE: (_collapse_rules,),
    DisasterType.BUILDING_COLLAPSE: (_collapse_rules,),
    DisasterType.LANDSLIDE: (_collapse_rules,),
    DisasterType.CHEMICAL_LEAK: (_release_exposure_rules,),
    DisasterType.TRAIN_ACCIDENT: (_collapse_rules, _release_exposure_rules),
}

COMMON_RULES: tuple[RuleFunction, ...] = (_life_safety_rules, _hazard_rules, _context_rules)


class SeverityEngine:
    """Convert a structured assessment into a present-tense harm score and level."""

    def evaluate(self, assessment: IncidentAssessment) -> SeverityResult:
        """Score severity, apply life-safety floors, and resolve the severity level."""
        disaster_type = resolve_disaster_type(assessment.incident_type)
        profile = DISASTER_PROFILES[disaster_type]

        factors: list[ReasoningFactor] = [
            ReasoningFactor(
                code="BASELINE",
                description=f"Baseline exposure for {disaster_type.value}",
                contribution=profile.severity_base,
            )
        ]
        for rule in COMMON_RULES + DISASTER_RULES.get(disaster_type, ()):
            factors.extend(rule(assessment, profile))

        factors = self._apply_emphasis(factors, profile)
        raw_score = clamp_score(sum(factor.contribution for factor in factors))
        score, applied_floor = self._apply_floors(raw_score, assessment)

        return SeverityResult(
            score=round_score(score),
            level=resolve_band(score, SEVERITY_BANDS),
            factors=factors,
            applied_floor=applied_floor,
        )

    def _apply_emphasis(
        self,
        factors: list[ReasoningFactor],
        profile: DisasterProfile,
    ) -> list[ReasoningFactor]:
        """Amplify the hazards that define this disaster type.

        A collapse contributes more to an earthquake than the same collapse contributes to a
        road accident, so each profile names the factors it treats as defining.
        """
        if not profile.emphasised_factors:
            return factors
        multiplier = SEVERITY_WEIGHTS.emphasis_multiplier
        return [
            factor.model_copy(update={"contribution": factor.contribution * multiplier})
            if factor.code in profile.emphasised_factors
            else factor
            for factor in factors
        ]

    def _apply_floors(
        self,
        score: float,
        assessment: IncidentAssessment,
    ) -> tuple[float, str | None]:
        """Raise the score to a minimum when a life-safety condition is present.

        Weighted addition alone under-grades a small incident that has trapped or many
        casualties, so floors enforce a minimum level. Floors only ever raise a score, and the
        highest applicable floor wins.
        """
        candidates: list[tuple[float, str]] = []
        if assessment.trapped_people:
            candidates.append((SEVERITY_FLOOR_TRAPPED, "TRAPPED_CASUALTIES"))
        if assessment.collapsed_structure and (assessment.victims or assessment.trapped_people):
            candidates.append(
                (SEVERITY_FLOOR_COLLAPSE_WITH_CASUALTIES, "COLLAPSE_WITH_CASUALTIES")
            )
        victims = assessment.victims or 0
        if victims >= MAJOR_CASUALTY_VICTIM_THRESHOLD:
            candidates.append((SEVERITY_FLOOR_MAJOR_CASUALTY, "MAJOR_CASUALTY_INCIDENT"))
        elif victims >= MASS_CASUALTY_VICTIM_THRESHOLD:
            candidates.append((SEVERITY_FLOOR_MASS_CASUALTY, "MASS_CASUALTY_INCIDENT"))

        applicable = [(floor, code) for floor, code in candidates if floor > score]
        if not applicable:
            return score, None
        floor, code = max(applicable, key=lambda candidate: candidate[0])
        return floor, code
