"""Orchestration of the deterministic Decision Intelligence Engine pipeline."""

from app.engines.confidence_engine import ConfidenceEngine
from app.engines.explanation_engine import ExplanationEngine
from app.engines.models import DecisionResult, IncidentAssessment
from app.engines.normalization import resolve_disaster_type
from app.engines.priority_engine import PriorityEngine
from app.engines.severity_engine import SeverityEngine


class DecisionEngine:
    """Run an incident assessment through every reasoning stage in a fixed order.

    The pipeline is severity, then priority, then confidence, then explanation. Severity and
    priority are computed independently of one another and of confidence, so the engine is a
    pure function of its input: identical assessments always produce identical decisions.

    Each stage is injected so it can be replaced or tested in isolation.
    """

    def __init__(
        self,
        severity_engine: SeverityEngine | None = None,
        priority_engine: PriorityEngine | None = None,
        confidence_engine: ConfidenceEngine | None = None,
        explanation_engine: ExplanationEngine | None = None,
    ) -> None:
        self._severity_engine = severity_engine or SeverityEngine()
        self._priority_engine = priority_engine or PriorityEngine()
        self._confidence_engine = confidence_engine or ConfidenceEngine()
        self._explanation_engine = explanation_engine or ExplanationEngine()

    def decide(self, assessment: IncidentAssessment) -> DecisionResult:
        """Produce the complete decision for one incident assessment."""
        severity = self._severity_engine.evaluate(assessment)
        priority = self._priority_engine.evaluate(assessment)
        confidence = self._confidence_engine.evaluate(assessment)
        explanation = self._explanation_engine.explain(assessment, severity, priority, confidence)

        return DecisionResult(
            incident_type=assessment.incident_type,
            disaster_type=resolve_disaster_type(assessment.incident_type),
            severity_score=severity.score,
            severity_level=severity.level,
            priority_score=priority.score,
            priority_level=priority.level,
            confidence=confidence.confidence,
            confidence_level=confidence.level,
            recommended_actions=explanation.recommended_immediate_actions,
            risk_factors=explanation.key_risk_factors,
            summary=explanation.reasoning_summary,
            explanation=explanation,
            severity_detail=severity,
            priority_detail=priority,
            confidence_detail=confidence,
        )
