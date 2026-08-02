"""Deterministic explanation assembly.

Explanations are rendered from the scores and the reasoning factors that produced them, using
fixed templates. No language model is involved: the same decision always produces the same
words, and every statement traces back to a rule that fired.
"""

from app.engines.config import (
    BASELINE_ACTIONS,
    CONDITIONAL_ACTIONS,
    MAX_LISTED_ACTIONS,
    MAX_LISTED_RISK_FACTORS,
    RISK_FACTOR_FAMILY_PREFIXES,
    RISK_FACTOR_LABELS,
    RISK_SUBJECT_ALIASES,
    ActionTemplate,
)
from app.engines.models import (
    ConfidenceResult,
    DisasterType,
    Explanation,
    IncidentAssessment,
    PriorityResult,
    ReasoningFactor,
    SeverityResult,
)
from app.engines.normalization import resolve_disaster_type, resolve_weather

_DISASTER_LABELS: dict[DisasterType, str] = {
    DisasterType.BUILDING_FIRE: "building fire",
    DisasterType.FLOOD: "flood",
    DisasterType.ROAD_ACCIDENT: "road accident",
    DisasterType.EARTHQUAKE: "earthquake",
    DisasterType.BUILDING_COLLAPSE: "building collapse",
    DisasterType.CHEMICAL_LEAK: "chemical or gas leak",
    DisasterType.TRAIN_ACCIDENT: "train accident",
    DisasterType.CYCLONE_STORM: "cyclone or storm",
    DisasterType.LANDSLIDE: "landslide",
    DisasterType.UNKNOWN: "unclassified emergency",
}

_FLOOR_EXPLANATIONS: dict[str, str] = {
    "TRAPPED_CASUALTIES": "a minimum level applies because people are trapped",
    "COLLAPSE_WITH_CASUALTIES": (
        "a minimum level applies because casualties are involved in a structural collapse"
    ),
    "MASS_CASUALTY_INCIDENT": "a minimum level applies because this is a mass-casualty incident",
    "MAJOR_CASUALTY_INCIDENT": (
        "a minimum level applies because the casualty count is exceptionally high"
    ),
    "SAVABLE_TRAPPED_CASUALTIES": (
        "urgency is raised to its highest band because trapped people remain savable"
    ),
    "ACTIVE_TOXIC_RELEASE": (
        "urgency is raised to its highest band because a toxic release is still active"
    ),
    "IMMINENT_EXPLOSION_RISK": (
        "urgency is raised to its highest band because an explosion risk is live"
    ),
    "HAZARDOUS_MATERIAL_EXPOSURE": (
        "urgency is raised because people are exposed to a hazardous material"
    ),
    "MASS_CASUALTY_WITH_FIRE": (
        "urgency is raised because many casualties are involved alongside an active fire"
    ),
}

_CAP_EXPLANATIONS: dict[str, str] = {
    "UNRECOGNISED_INCIDENT_TYPE": (
        "confidence is capped because the incident type could not be classified"
    ),
    "MISSING_CRITICAL_EVIDENCE": (
        "confidence is capped because decision-critical information was not reported"
    ),
}


class ExplanationEngine:
    """Render a structured, human-readable account of a completed decision."""

    def explain(
        self,
        assessment: IncidentAssessment,
        severity: SeverityResult,
        priority: PriorityResult,
        confidence: ConfidenceResult,
    ) -> Explanation:
        """Assemble every explanation section from the decision and its reasoning factors."""
        disaster_type = resolve_disaster_type(assessment.incident_type)
        context = self._render_context(assessment)

        return Explanation(
            current_situation=self._current_situation(assessment, disaster_type),
            severity=self._severity_statement(severity),
            priority=self._priority_statement(priority),
            key_risk_factors=self._risk_factors(severity, priority, context),
            recommended_immediate_actions=self._actions(assessment, disaster_type, context),
            reasoning_summary=self._reasoning_summary(
                assessment, disaster_type, severity, priority, confidence
            ),
        )

    def _render_context(self, assessment: IncidentAssessment) -> dict[str, str]:
        """Build the substitution values used by risk-factor and action templates."""
        return {
            "victims": str(assessment.victims or 0),
            "children": str(assessment.children or 0),
            "elderly": str(assessment.elderly or 0),
            "trapped_people": str(assessment.trapped_people or 0),
            "people_detected": str(assessment.people_detected or 0),
            "passengers_onboard": str(assessment.passengers_onboard or 0),
            "exposed": str(
                max(0, (assessment.people_detected or 0) - (assessment.victims or 0))
            ),
            "water_level_m": str(assessment.water_level_m or 0),
            "wind_speed_kmh": str(assessment.wind_speed_kmh or 0),
            "hospital_distance_km": str(assessment.hospital_distance_km or 0),
            "weather": resolve_weather(assessment.weather).value,
        }

    def _current_situation(
        self,
        assessment: IncidentAssessment,
        disaster_type: DisasterType,
    ) -> str:
        """State what is happening, where the people are, and what is present."""
        label = _DISASTER_LABELS[disaster_type]
        parts = [f"Reported {label}"]

        people: list[str] = []
        if assessment.victims:
            people.append(f"{assessment.victims} casualties")
        if assessment.trapped_people:
            people.append(f"{assessment.trapped_people} trapped")
        if assessment.children:
            people.append(f"{assessment.children} children")
        if assessment.elderly:
            people.append(f"{assessment.elderly} elderly")
        if assessment.passengers_onboard:
            people.append(f"{assessment.passengers_onboard} passengers onboard")
        if assessment.people_detected is not None:
            people.append(f"{assessment.people_detected} people detected in the area")
        parts.append(f"involving {', '.join(people)}" if people else "with no casualty detail reported")

        hazards = self._present_hazards(assessment)
        if hazards:
            parts.append(f"Hazards present: {', '.join(hazards)}")

        access = "blocked" if assessment.road_blocked else "reported clear"
        if assessment.hospital_distance_km is not None:
            parts.append(
                f"Access is {access} and the nearest hospital is "
                f"{assessment.hospital_distance_km} km away"
            )
        else:
            parts.append(f"Access is {access}")
        return f"{parts[0]} {parts[1]}. {'. '.join(parts[2:])}."

    def _present_hazards(self, assessment: IncidentAssessment) -> list[str]:
        """List the hazard flags reported as present, in a fixed order."""
        flags: tuple[tuple[bool | None, str], ...] = (
            (assessment.fire_detected, "active fire"),
            (assessment.smoke_detected, "smoke"),
            (assessment.toxic_gas_detected, "toxic gas"),
            (assessment.hazardous_material, "hazardous material"),
            (assessment.explosion_risk, "explosion risk"),
            (assessment.collapsed_structure, "structural collapse"),
            (assessment.structural_damage, "structural damage"),
            (assessment.derailment, "derailment"),
            (assessment.power_lines_down, "downed power lines"),
            (assessment.gas_station_nearby, "nearby fuel storage"),
        )
        hazards = [label for is_present, label in flags if is_present]
        if assessment.water_level_m:
            hazards.append(f"flood water at {assessment.water_level_m} m")
        return hazards

    def _severity_statement(self, severity: SeverityResult) -> str:
        """State the severity level, score, and the largest contributing factor."""
        statement = f"{severity.level.value} ({severity.score}/100)"
        dominant = self._dominant_factor(severity.factors)
        if dominant is not None:
            statement = f"{statement}. Largest contributor: {dominant.description}"
        if severity.applied_floor is not None:
            statement = f"{statement}. Note that {_FLOOR_EXPLANATIONS[severity.applied_floor]}"
        return f"{statement}."

    def _priority_statement(self, priority: PriorityResult) -> str:
        """State the urgency level, score, and why the response cannot wait."""
        statement = f"{priority.level.value} ({priority.score}/100)"
        dominant = self._dominant_factor(priority.factors)
        if dominant is not None:
            statement = f"{statement}. Largest contributor: {dominant.description}"
        if priority.applied_floor is not None:
            statement = f"{statement}. Note that {_FLOOR_EXPLANATIONS[priority.applied_floor]}"
        return f"{statement}."

    def _dominant_factor(self, factors: list[ReasoningFactor]) -> ReasoningFactor | None:
        """Return the highest-contributing factor, excluding the disaster baseline."""
        scored = [
            factor
            for factor in factors
            if factor.contribution > 0 and not factor.code.endswith("BASELINE")
        ]
        if not scored:
            return None
        return max(scored, key=lambda factor: factor.contribution)

    def _risk_factors(
        self,
        severity: SeverityResult,
        priority: PriorityResult,
        context: dict[str, str],
    ) -> list[str]:
        """List the distinct risks that drove either score, strongest first.

        Where severity and priority fire rules for the same underlying hazard (e.g.
        HAZARD_TOXIC_GAS vs ESCALATION_TOXIC_GAS), keep only the highest-contributing one.
        """
        contributions_by_subject: dict[str, tuple[str, float]] = {}

        for factor in list(severity.factors) + list(priority.factors):
            if factor.contribution <= 0 or factor.code.endswith("BASELINE"):
                continue

            subject = factor.code
            for prefix in RISK_FACTOR_FAMILY_PREFIXES:
                if factor.code.startswith(prefix):
                    subject = factor.code[len(prefix) :]
                    break

            subject = RISK_SUBJECT_ALIASES.get(subject, subject)

            label = RISK_FACTOR_LABELS.get(factor.code, factor.description)
            rendered = label.format(**context)

            existing = contributions_by_subject.get(subject)
            if existing is None or factor.contribution > existing[1]:
                contributions_by_subject[subject] = (rendered, factor.contribution)

        ranked = sorted(
            contributions_by_subject.values(), key=lambda item: (-item[1], item[0])
        )
        return [label for label, _ in ranked[:MAX_LISTED_RISK_FACTORS]]

    def _actions(
        self,
        assessment: IncidentAssessment,
        disaster_type: DisasterType,
        context: dict[str, str],
    ) -> list[str]:
        """Select and render the actions whose triggering conditions are satisfied."""
        triggered = {
            code
            for code, is_triggered in self._action_triggers(assessment, disaster_type).items()
            if is_triggered
        }
        selected: list[ActionTemplate] = list(BASELINE_ACTIONS)
        selected.extend(action for action in CONDITIONAL_ACTIONS if action.code in triggered)
        ordered = sorted(selected, key=lambda action: (action.rank, action.code))
        return [action.template.format(**context) for action in ordered[:MAX_LISTED_ACTIONS]]

    def _action_triggers(
        self,
        assessment: IncidentAssessment,
        disaster_type: DisasterType,
    ) -> dict[str, bool]:
        """Map each conditional action onto the condition that justifies recommending it."""
        water_present = bool(assessment.water_level_m)
        structural = bool(assessment.collapsed_structure or assessment.structural_damage)
        return {
            "TECHNICAL_RESCUE": bool(assessment.trapped_people),
            "TOXIC_ZONE_CONTROL": bool(assessment.toxic_gas_detected),
            "EXPLOSION_WITHDRAWAL": bool(assessment.explosion_risk),
            "HAZMAT_IDENTIFY": bool(
                assessment.hazardous_material or disaster_type == DisasterType.CHEMICAL_LEAK
            ),
            "FIRE_ATTACK": bool(assessment.fire_detected),
            "STRUCTURAL_ASSESSMENT": structural,
            "WATER_RESCUE": water_present and disaster_type != DisasterType.CHEMICAL_LEAK,
            "RAIL_ISOLATION": disaster_type == DisasterType.TRAIN_ACCIDENT,
            "MASS_CASUALTY_TRIAGE": (assessment.victims or 0) > 0,
            "MEDICAL_TRANSPORT": assessment.hospital_distance_km is not None
            and bool(assessment.victims or assessment.trapped_people),
            "VULNERABLE_OCCUPANTS": bool(assessment.children or assessment.elderly),
            "EVACUATION": bool(assessment.evacuation_required),
            "ACCESS_ROUTE": bool(assessment.road_blocked),
            "UTILITY_ISOLATION": bool(assessment.power_lines_down),
            "IGNITION_CONTROL": bool(
                assessment.gas_station_nearby
                and (assessment.fire_detected or assessment.explosion_risk)
            ),
            "WEATHER_MITIGATION": resolve_weather(assessment.weather).value
            not in {"CLEAR", "UNKNOWN"},
            "VERIFY_INFORMATION": True,
        }

    def _reasoning_summary(
        self,
        assessment: IncidentAssessment,
        disaster_type: DisasterType,
        severity: SeverityResult,
        priority: PriorityResult,
        confidence: ConfidenceResult,
    ) -> str:
        """Explain how the scores were reached and how far apart severity and urgency are."""
        label = _DISASTER_LABELS[disaster_type]
        sentences = [
            f"Classified as {label} from the reported incident type.",
            (
                f"Severity is {severity.level.value} at {severity.score}/100, reflecting harm "
                f"already present."
            ),
            (
                f"Priority is {priority.level.value} at {priority.score}/100, reflecting how "
                f"quickly the situation worsens and how long the response will take to arrive."
            ),
        ]
        divergence = self._divergence_sentence(severity, priority)
        if divergence is not None:
            sentences.append(divergence)
        sentences.append(
            f"Confidence is {confidence.level.value} at {confidence.confidence}, based on "
            f"{len(confidence.observed_fields)} reported and {len(confidence.missing_fields)} "
            f"unreported fields."
        )
        if confidence.applied_cap is not None:
            sentences.append(f"{_CAP_EXPLANATIONS[confidence.applied_cap].capitalize()}.")
        if confidence.missing_fields:
            sentences.append(
                f"Unreported: {', '.join(confidence.missing_fields)}. Severity and priority were "
                f"not reduced because of these gaps."
            )
        return " ".join(sentences)

    def _divergence_sentence(
        self,
        severity: SeverityResult,
        priority: PriorityResult,
    ) -> str | None:
        """State explicitly when urgency and severity disagree, and why that is expected."""
        gap = priority.score - severity.score
        if gap >= 15.0:
            return (
                "Urgency exceeds severity because the hazard is still developing: acting early "
                "changes the outcome even though present harm is lower."
            )
        if gap <= -15.0:
            return (
                "Severity exceeds urgency because the harm is largely already realised: speed "
                "changes the outcome less than the harm level alone would suggest."
            )
        return None
