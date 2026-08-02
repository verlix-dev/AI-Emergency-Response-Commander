"""Deterministic confidence estimation from evidence coverage.

Confidence is epistemic: it measures how much of what this decision needs is actually
reported, and whether the reported values are self-consistent. It is explicitly not a
probability that the decision is correct.

Confidence never changes a decision, it only qualifies one. Severity and priority are
computed without reference to confidence, so an incompletely reported incident is never
quietly downgraded; the missing evidence is named instead.
"""

from app.engines.config import (
    CONFIDENCE_BANDS,
    CONFIDENCE_WEIGHTS,
    DISASTER_PROFILES,
    FIELD_EVIDENCE_WEIGHTS,
    ConfidenceWeights,
    DisasterProfile,
)
from app.engines.models import (
    ConfidenceResult,
    DisasterType,
    IncidentAssessment,
    ReasoningFactor,
)
from app.engines.normalization import resolve_disaster_type
from app.engines.scoring import clamp_confidence, resolve_band, round_confidence


class ConfidenceEngine:
    """Convert reported and missing evidence into a single confidence figure."""

    def evaluate(self, assessment: IncidentAssessment) -> ConfidenceResult:
        """Score evidence coverage, apply consistency penalties, and resolve the level."""
        disaster_type = resolve_disaster_type(assessment.incident_type)
        profile = DISASTER_PROFILES[disaster_type]
        weights = CONFIDENCE_WEIGHTS

        observed, missing = self._partition_expected_fields(assessment, profile)
        coverage = self._coverage_score(observed, missing)
        penalties = self._consistency_penalties(assessment, disaster_type, weights)

        penalty_total = sum(penalty.contribution for penalty in penalties)
        confidence = clamp_confidence(coverage + penalty_total)
        confidence, applied_cap = self._apply_caps(
            confidence, assessment, profile, disaster_type, missing, weights
        )

        return ConfidenceResult(
            confidence=round_confidence(confidence),
            level=resolve_band(confidence, CONFIDENCE_BANDS),
            observed_fields=observed,
            missing_fields=missing,
            penalties=penalties,
            applied_cap=applied_cap,
        )

    def _partition_expected_fields(
        self,
        assessment: IncidentAssessment,
        profile: DisasterProfile,
    ) -> tuple[list[str], list[str]]:
        """Split the fields this disaster type expects into reported and unreported.

        ``None`` means unreported. ``0`` and ``False`` are reported values and count as
        evidence, because "no casualties" is information while "not stated" is not.
        """
        observed: list[str] = []
        missing: list[str] = []
        for field in profile.expected_fields:
            if getattr(assessment, field) is None:
                missing.append(field)
            else:
                observed.append(field)
        return observed, missing

    def _coverage_score(self, observed: list[str], missing: list[str]) -> float:
        """Return the evidence-weighted fraction of expected fields that were reported."""
        observed_weight = sum(FIELD_EVIDENCE_WEIGHTS[field] for field in observed)
        total_weight = observed_weight + sum(FIELD_EVIDENCE_WEIGHTS[field] for field in missing)
        if total_weight == 0:
            return 0.0
        return observed_weight / total_weight

    def _consistency_penalties(
        self,
        assessment: IncidentAssessment,
        disaster_type: DisasterType,
        weights: ConfidenceWeights,
    ) -> list[ReasoningFactor]:
        """Penalise reported values that contradict each other or the incident type."""
        penalties: list[ReasoningFactor] = []

        if assessment.collapsed_structure and assessment.structural_damage is False:
            penalties.append(
                ReasoningFactor(
                    code="CONTRADICTION_COLLAPSE_WITHOUT_DAMAGE",
                    description="Collapse reported while structural damage is reported absent",
                    contribution=-weights.contradiction_penalty,
                )
            )
        if disaster_type == DisasterType.BUILDING_FIRE and assessment.fire_detected is False:
            penalties.append(
                ReasoningFactor(
                    code="CONTRADICTION_FIRE_TYPE_WITHOUT_FIRE",
                    description="Incident classified as a fire while fire is reported absent",
                    contribution=-weights.contradiction_penalty,
                )
            )
        if disaster_type == DisasterType.CHEMICAL_LEAK and (
            assessment.toxic_gas_detected is False and assessment.hazardous_material is False
        ):
            penalties.append(
                ReasoningFactor(
                    code="CONTRADICTION_LEAK_WITHOUT_MATERIAL",
                    description="Chemical leak reported with neither gas nor hazardous material",
                    contribution=-weights.contradiction_penalty,
                )
            )
        if (
            assessment.people_detected is not None
            and assessment.victims is not None
            and assessment.victims > assessment.people_detected
        ):
            penalties.append(
                ReasoningFactor(
                    code="INCONSISTENCY_VICTIMS_EXCEED_DETECTED",
                    description="Reported casualties exceed the number of people detected",
                    contribution=-weights.inconsistency_penalty,
                )
            )
        if (
            assessment.trapped_people is not None
            and assessment.victims is not None
            and assessment.trapped_people > assessment.victims
        ):
            penalties.append(
                ReasoningFactor(
                    code="INCONSISTENCY_TRAPPED_EXCEED_VICTIMS",
                    description="Reported trapped people exceed the reported casualty count",
                    contribution=-weights.inconsistency_penalty,
                )
            )
        return penalties

    def _apply_caps(
        self,
        confidence: float,
        assessment: IncidentAssessment,
        profile: DisasterProfile,
        disaster_type: DisasterType,
        missing: list[str],
        weights: ConfidenceWeights,
    ) -> tuple[float, str | None]:
        """Cap confidence where a specific gap makes high confidence indefensible.

        Coverage alone can look healthy while a decision-critical field is absent, so caps
        apply independently of the arithmetic. The lowest applicable cap wins.
        """
        candidates: list[tuple[float, str]] = []

        if disaster_type == DisasterType.UNKNOWN:
            candidates.append((weights.unknown_type_cap, "UNRECOGNISED_INCIDENT_TYPE"))
        missing_critical = [field for field in profile.critical_fields if field in missing]
        if missing_critical:
            candidates.append((weights.missing_critical_cap, "MISSING_CRITICAL_EVIDENCE"))

        applicable = [(cap, code) for cap, code in candidates if cap < confidence]
        if not applicable:
            return confidence, None
        cap, code = min(applicable, key=lambda candidate: candidate[0])
        return cap, code
