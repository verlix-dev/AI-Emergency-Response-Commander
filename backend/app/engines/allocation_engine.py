"""Deterministic resource allocation from a completed decision.

Requirements are derived from the incident's own facts first and only then confronted with what
is actually available. Reversing that order would hide a shortfall behind whatever happened to
be free, so unmet demand is reported explicitly rather than silently reduced.

Like the decision engine, this stage recommends but never dispatches: committing a resource
remains a human act, which keeps the engine pure and safe to re-run.
"""

from collections.abc import Sequence

from app.engines.allocation_config import (
    ALLOCATION_RULES,
    MAX_TOTAL_UNITS,
    MAX_UNITS_PER_KIND,
    PRIORITY_ORDER,
    RESOURCE_KIND_ORDER,
    RESOURCE_TYPE_ALIASES,
    AllocationRule,
)
from app.engines.allocation_models import (
    AllocationPriority,
    AllocationResult,
    ResourceKind,
    ResourceRecommendation,
)
from app.engines.models import DecisionResult, IncidentAssessment
from app.engines.normalization import normalize_token


class AvailableResource:
    """A resource offered to the allocator, decoupled from its persistence model."""

    def __init__(self, resource_kind: ResourceKind, resource_name: str) -> None:
        self.resource_kind = resource_kind
        self.resource_name = resource_name


def resolve_resource_kind(resource_type: str) -> ResourceKind | None:
    """Map a stored resource-type label onto a known kind, or ``None`` when unrecognised."""
    token = normalize_token(resource_type)
    if not token:
        return None
    alias = RESOURCE_TYPE_ALIASES.get(token)
    if alias is not None:
        return alias
    try:
        return ResourceKind(token.upper())
    except ValueError:
        return None


class AllocationEngine:
    """Convert a decision into a prioritised, quantified resource requirement."""

    def __init__(self, rules: Sequence[AllocationRule] = ALLOCATION_RULES) -> None:
        self._rules = tuple(rules)

    def allocate(
        self,
        assessment: IncidentAssessment,
        decision: DecisionResult,
        available: Sequence[AvailableResource] = (),
    ) -> AllocationResult:
        """Derive requirements from the decision, then match them against availability."""
        requirements = self._derive_requirements(assessment, decision)
        recommendations = self._match_availability(requirements, available)
        return self._summarise(recommendations)

    def _derive_requirements(
        self,
        assessment: IncidentAssessment,
        decision: DecisionResult,
    ) -> list[ResourceRecommendation]:
        """Evaluate every rule and merge the results per resource kind.

        Where several rules ask for the same kind, the largest quantity wins rather than the
        sum: two rules each needing two ambulances need two, not four. The strongest priority
        and every contributing reason are retained so the requirement stays explainable.
        """
        merged: dict[ResourceKind, ResourceRecommendation] = {}

        for rule in self._rules:
            if not rule.applies(assessment, decision.severity_level):
                continue
            quantity = min(MAX_UNITS_PER_KIND, rule.quantity(assessment, decision.severity_level))
            if quantity <= 0:
                continue

            existing = merged.get(rule.resource_kind)
            if existing is None:
                merged[rule.resource_kind] = ResourceRecommendation(
                    resource_kind=rule.resource_kind,
                    quantity=quantity,
                    priority=rule.priority,
                    reason=rule.reason,
                    rule_ids=[rule.rule_id],
                )
                continue

            merged[rule.resource_kind] = existing.model_copy(
                update={
                    "quantity": max(existing.quantity, quantity),
                    "priority": self._strongest_priority(existing.priority, rule.priority),
                    "reason": self._merge_reasons(existing.reason, rule.reason),
                    "rule_ids": [*existing.rule_ids, rule.rule_id],
                }
            )

        return self._apply_total_cap(sorted(merged.values(), key=self._ordering_key))

    def _strongest_priority(
        self,
        first: AllocationPriority,
        second: AllocationPriority,
    ) -> AllocationPriority:
        """Return whichever priority is more urgent."""
        return min(first, second, key=PRIORITY_ORDER.index)

    def _merge_reasons(self, existing: str, addition: str) -> str:
        """Append a distinct reason to an existing justification."""
        if addition in existing:
            return existing
        return f"{existing} {addition}"

    def _ordering_key(self, recommendation: ResourceRecommendation) -> tuple[int, int]:
        """Order recommendations by urgency, then by a fixed operational sequence."""
        return (
            PRIORITY_ORDER.index(recommendation.priority),
            RESOURCE_KIND_ORDER.index(recommendation.resource_kind),
        )

    def _apply_total_cap(
        self,
        recommendations: list[ResourceRecommendation],
    ) -> list[ResourceRecommendation]:
        """Trim the tail of the request when the total exceeds the fleet ceiling.

        Trimming runs from the least urgent requirement upward, and never reduces a CRITICAL
        requirement below one unit, so the cap can never remove a safety-critical capability
        entirely.
        """
        total = sum(item.quantity for item in recommendations)
        if total <= MAX_TOTAL_UNITS:
            return recommendations

        trimmed = list(recommendations)
        excess = total - MAX_TOTAL_UNITS
        for index in range(len(trimmed) - 1, -1, -1):
            if excess <= 0:
                break
            item = trimmed[index]
            floor = 1 if item.priority is AllocationPriority.CRITICAL else 0
            reducible = max(0, item.quantity - floor)
            reduction = min(reducible, excess)
            if reduction == 0:
                continue
            trimmed[index] = item.model_copy(update={"quantity": item.quantity - reduction})
            excess -= reduction
        return [item for item in trimmed if item.quantity > 0]

    def _match_availability(
        self,
        requirements: list[ResourceRecommendation],
        available: Sequence[AvailableResource],
    ) -> list[ResourceRecommendation]:
        """Assign available units to requirements without double-assigning any unit."""
        pool: dict[ResourceKind, list[str]] = {}
        for resource in available:
            pool.setdefault(resource.resource_kind, []).append(resource.resource_name)
        for names in pool.values():
            names.sort()

        matched: list[ResourceRecommendation] = []
        for requirement in requirements:
            candidates = pool.get(requirement.resource_kind, [])
            assigned = candidates[: requirement.quantity]
            del candidates[: requirement.quantity]
            matched.append(
                requirement.model_copy(
                    update={
                        "fulfilled_quantity": len(assigned),
                        "shortfall": requirement.quantity - len(assigned),
                        "assigned_resource_names": assigned,
                    }
                )
            )
        return matched

    def _summarise(self, recommendations: list[ResourceRecommendation]) -> AllocationResult:
        """Roll recommendations up into totals and a list of unmet requirements."""
        unmet = [
            f"{item.resource_kind.value}: {item.shortfall} of {item.quantity} unavailable"
            for item in recommendations
            if item.shortfall > 0
        ]
        return AllocationResult(
            recommendations=recommendations,
            total_units_requested=sum(item.quantity for item in recommendations),
            total_units_fulfilled=sum(item.fulfilled_quantity for item in recommendations),
            unmet_requirements=unmet,
        )
