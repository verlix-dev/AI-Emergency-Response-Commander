"""Deterministic commander-brief generation.

The brief restates a completed analysis in the order a commander reads it: what is happening,
how bad it is, how fast it must be answered, what to do first, what to send, what to watch, and
what constrains the operation.

No language model is involved. Every sentence is composed from values the engines already
produced, so the same analysis always yields the same brief and every statement is traceable.
"""

from app.engines.allocation_models import (
    AllocationPriority,
    AllocationResult,
    ResourceRecommendation,
)
from app.engines.models import DecisionResult, IncidentAssessment
from app.schemas.analysis import CommanderBrief

MAX_BRIEF_ACTIONS = 8
MAX_BRIEF_RISKS = 8

_RESOURCE_LABELS: dict[str, str] = {
    "FIRE_TRUCK": "Fire truck",
    "AMBULANCE": "Ambulance",
    "POLICE": "Police unit",
    "SEARCH_RESCUE": "Search & rescue team",
    "BOAT": "Rescue boat",
    "MEDICAL_TEAM": "Medical team",
    "HAZMAT": "Hazmat unit",
    "HEAVY_MACHINERY": "Heavy machinery",
}


class CommanderBriefGenerator:
    """Compose a structured operational briefing from a decision and its allocation."""

    def generate(
        self,
        assessment: IncidentAssessment,
        decision: DecisionResult,
        allocation: AllocationResult,
    ) -> CommanderBrief:
        """Build every brief section from the analysis outputs."""
        return CommanderBrief(
            incident_summary=decision.explanation.current_situation,
            severity=self._severity_line(decision),
            priority=self._priority_line(decision),
            immediate_actions=decision.recommended_actions[:MAX_BRIEF_ACTIONS],
            recommended_resources=self._resource_lines(allocation),
            risk_factors=decision.risk_factors[:MAX_BRIEF_RISKS],
            operational_notes=self._operational_notes(assessment, decision, allocation),
        )

    def _severity_line(self, decision: DecisionResult) -> str:
        """State the severity band, score, and dominant reason."""
        return (
            f"{decision.severity_level.value} ({decision.severity_score}/100). "
            f"{decision.explanation.severity}"
        )

    def _priority_line(self, decision: DecisionResult) -> str:
        """State the urgency band, score, and what is driving the clock."""
        return (
            f"{decision.priority_level.value} ({decision.priority_score}/100). "
            f"{decision.explanation.priority}"
        )

    def _resource_lines(self, allocation: AllocationResult) -> list[str]:
        """Render each requirement with its quantity, urgency, and availability."""
        lines: list[str] = []
        for item in allocation.recommendations:
            label = _RESOURCE_LABELS.get(item.resource_kind.value, item.resource_kind.value)
            line = f"{item.quantity} x {label} [{item.priority.value}] - {item.reason}"
            if item.shortfall > 0:
                line = (
                    f"{line} SHORTFALL: only {item.fulfilled_quantity} of {item.quantity} "
                    f"available."
                )
            lines.append(line)
        return lines

    def _operational_notes(
        self,
        assessment: IncidentAssessment,
        decision: DecisionResult,
        allocation: AllocationResult,
    ) -> list[str]:
        """Collect the constraints and caveats a commander must know before acting."""
        notes: list[str] = []

        notes.append(
            f"Assessment confidence is {decision.confidence_level.value} "
            f"({decision.confidence}). "
            f"{'Verify on arrival before committing crews.' if decision.confidence < 0.6 else 'Confirm on arrival.'}"
        )

        missing = decision.confidence_detail.missing_fields
        if missing:
            notes.append(
                f"Unreported and required for a firmer picture: {', '.join(missing)}."
            )

        if allocation.unmet_requirements:
            notes.append(
                f"Resource shortfall: {'; '.join(allocation.unmet_requirements)}. "
                f"Request mutual aid before committing to the full plan."
            )

        critical = [
            item
            for item in allocation.recommendations
            if item.priority is AllocationPriority.CRITICAL
        ]
        if critical:
            notes.append(
                f"Non-negotiable capabilities: {self._kind_list(critical)}. "
                f"Do not reduce these below the stated quantity."
            )

        if decision.severity_detail.applied_floor is not None:
            notes.append(
                f"Severity was raised to a minimum by rule "
                f"{decision.severity_detail.applied_floor}."
            )
        if decision.priority_detail.applied_floor is not None:
            notes.append(
                f"Urgency was raised to a minimum by rule "
                f"{decision.priority_detail.applied_floor}."
            )

        if assessment.responders_on_scene:
            notes.append(
                f"{assessment.responders_on_scene} responder units already on scene; "
                f"confirm tasking with the incident commander before adding resources."
            )

        notes.append(
            "This brief is generated deterministically from structured detections. "
            "It supports the commander's decision and does not replace it."
        )
        return notes

    def _kind_list(self, recommendations: list[ResourceRecommendation]) -> str:
        """Render a comma-separated list of resource labels."""
        return ", ".join(
            _RESOURCE_LABELS.get(item.resource_kind.value, item.resource_kind.value)
            for item in recommendations
        )
