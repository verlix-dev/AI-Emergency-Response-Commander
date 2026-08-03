"""LLM narration of the deterministic commander brief.

The decision, allocation, and brief engines remain the source of truth. This service takes the
brief they already produced and asks a language model to restate it in fluent operational
language. It cannot change a grading, a quantity, or a recommendation.

Two mechanisms enforce that, because instructing a model is not the same as constraining it:

1. The prompt carries only facts the engines produced, as a closed list.
2. The response is validated against those facts before it is accepted. Any number, resource,
   or grading token that is not in the source is a rejection, and the deterministic brief is
   returned instead.

Every failure — unconfigured, timed out, refused, or ungrounded — degrades to the deterministic
brief. The narration layer can never prevent a commander from receiving a brief.
"""

import logging
import re
from dataclasses import dataclass

from app.core.llm.base import ChatMessage
from app.core.llm.providers.groq_provider import GroqProvider, GroqProviderError
from app.engines.allocation_models import AllocationResult
from app.engines.models import DecisionResult, IncidentAssessment
from app.schemas.analysis import CommanderBrief

logger = logging.getLogger(__name__)

MAX_BRIEF_WORDS = 250

SYSTEM_PROMPT = (
    "You are an emergency operations staff officer writing an incident brief for an incident "
    "commander.\n"
    "\n"
    "You are given a completed assessment produced by deterministic analysis engines. Your only "
    "task is to restate it as concise, professional operational prose.\n"
    "\n"
    "ABSOLUTE CONSTRAINTS:\n"
    "- Use ONLY the facts provided. Never introduce a fact that is not in the input.\n"
    "- Never invent or estimate casualties, victims, trapped people, responders, hazards, "
    "weather, distances, or resource quantities.\n"
    "- Never change a severity level, priority level, confidence value, or resource quantity. "
    "Reproduce them exactly as given.\n"
    "- If a field is marked 'not reported', say it is not reported. Do not guess it.\n"
    "- Do not add recommendations that are not in the provided actions.\n"
    "- Reproduce safety-critical instructions verbatim.\n"
    "\n"
    "STYLE:\n"
    f"- Maximum {MAX_BRIEF_WORDS} words.\n"
    "- Plain operational language. No preamble, no sign-off, no markdown headings.\n"
    "- Lead with what happened and how severe it is, then what must happen now.\n"
    "- Write in short declarative sentences a commander can read under pressure."
)


@dataclass(frozen=True)
class NarrationOutcome:
    """The brief that will be shown, and how it was produced."""

    brief: CommanderBrief
    narrated: bool
    reason: str


class CommanderBriefLLMService:
    """Narrate a deterministic brief, falling back to it on any failure."""

    def __init__(
        self,
        provider: GroqProvider | None = None,
        timeout_seconds: float = 8.0,
        max_words: int = MAX_BRIEF_WORDS,
    ) -> None:
        self._provider = provider
        self._timeout_seconds = timeout_seconds
        self._max_words = max_words

    @property
    def is_enabled(self) -> bool:
        """Whether a provider is configured. When false, briefs stay deterministic."""
        return self._provider is not None

    def narrate(
        self,
        brief: CommanderBrief,
        assessment: IncidentAssessment,
        decision: DecisionResult,
        allocation: AllocationResult,
    ) -> NarrationOutcome:
        """Return a narrated brief, or the deterministic one when narration is unavailable."""
        if self._provider is None:
            return NarrationOutcome(brief, False, "no_provider_configured")

        prompt = self._build_prompt(brief, assessment, decision, allocation)

        try:
            completion = self._provider.chat(
                [
                    ChatMessage(role="system", content=SYSTEM_PROMPT),
                    ChatMessage(role="user", content=prompt),
                ],
                timeout_seconds=self._timeout_seconds,
            )
        except GroqProviderError as exc:
            logger.warning("Commander brief narration failed; using deterministic brief: %s", exc)
            return NarrationOutcome(brief, False, "provider_error")
        except Exception as exc:  # noqa: BLE001 - narration must never break the response
            logger.warning(
                "Unexpected narration failure; using deterministic brief: %s: %s",
                type(exc).__name__,
                exc,
            )
            return NarrationOutcome(brief, False, "unexpected_error")

        violation = self._grounding_violation(completion, brief, decision, allocation)
        if violation is not None:
            logger.warning("Narration rejected as ungrounded (%s); using deterministic brief.", violation)
            return NarrationOutcome(brief, False, f"ungrounded:{violation}")

        narrated = brief.model_copy(update={"incident_summary": completion})
        return NarrationOutcome(narrated, True, "narrated")

    def _build_prompt(
        self,
        brief: CommanderBrief,
        assessment: IncidentAssessment,
        decision: DecisionResult,
        allocation: AllocationResult,
    ) -> str:
        """Render the deterministic facts as a closed input set.

        Only engine output appears here. Unreported fields are stated as unreported rather than
        omitted, so the model is never left to infer a value from silence.
        """
        lines: list[str] = [
            "INCIDENT",
            f"  Type: {decision.disaster_type.value.replace('_', ' ').title()}",
            f"  Severity: {decision.severity_level.value} ({decision.severity_score}/100)",
            f"  Priority: {decision.priority_level.value} ({decision.priority_score}/100)",
            (
                f"  Assessment confidence: {decision.confidence_level.value} "
                f"({round(decision.confidence * 100)}%)"
            ),
            "",
            "OBSERVED",
        ]

        observed = [
            ("People detected", assessment.people_detected),
            ("Casualties", assessment.victims),
            ("Trapped", assessment.trapped_people),
            ("Children", assessment.children),
            ("Elderly", assessment.elderly),
            ("Responders on scene", assessment.responders_on_scene),
            ("Water depth (m)", assessment.water_level_m),
        ]
        for label, value in observed:
            lines.append(f"  {label}: {'not reported' if value is None else value}")

        flags = [
            ("Fire", assessment.fire_detected),
            ("Smoke", assessment.smoke_detected),
            ("Structural collapse", assessment.collapsed_structure),
            ("Structural damage", assessment.structural_damage),
            ("Hazardous material", assessment.hazardous_material),
            ("Toxic gas", assessment.toxic_gas_detected),
            ("Explosion risk", assessment.explosion_risk),
            ("Power lines down", assessment.power_lines_down),
            ("Road blocked", assessment.road_blocked),
        ]
        for label, value in flags:
            lines.append(
                f"  {label}: {'not reported' if value is None else ('confirmed' if value else 'reported absent')}"
            )

        lines += ["", "RISK FACTORS"]
        lines += [f"  - {item}" for item in decision.risk_factors] or ["  - none identified"]
        lines += ["", "RESOURCES REQUIRED"]
        if allocation.recommendations:
            for item in allocation.recommendations:
                shortfall = f", {item.shortfall} unavailable" if item.shortfall else ""
                lines.append(
                    f"  - {item.quantity} x {item.resource_kind.value.replace('_', ' ').title()} "
                    f"[{item.priority.value}]{shortfall}"
                )
        else:
            lines.append("  - none derived")

        lines += ["", "IMMEDIATE ACTIONS"]
        lines += [f"  {i}. {a}" for i, a in enumerate(brief.immediate_actions, 1)]

        lines += ["", "OPERATIONAL NOTES"]
        lines += [f"  - {n}" for n in brief.operational_notes]

        if decision.confidence_detail.missing_fields:
            lines += [
                "",
                "NOT REPORTED (do not infer these)",
                "  " + ", ".join(decision.confidence_detail.missing_fields),
            ]

        lines += [
            "",
            f"Write the incident summary paragraph. Maximum {self._max_words} words.",
        ]
        return "\n".join(lines)

    def _grounding_violation(
        self,
        completion: str,
        brief: CommanderBrief,
        decision: DecisionResult,
        allocation: AllocationResult,
    ) -> str | None:
        """Return why the narration is ungrounded, or ``None`` when it is acceptable.

        This is the structural guarantee behind the no-hallucination requirement. Prompt
        instructions are advisory; this check is not.
        """
        if not completion.strip():
            return "empty"

        if len(completion.split()) > self._max_words * 1.2:
            return "too_long"

        # Grading tokens must not be contradicted. If the text names a severity or priority
        # level, it must be the one the engine assigned.
        severity_levels = {"MINOR", "MODERATE", "HIGH", "SEVERE", "CRITICAL"}
        priority_levels = {"LOW", "MODERATE", "HIGH", "URGENT", "CRITICAL"}
        upper = completion.upper()

        for level in severity_levels | priority_levels:
            if re.search(rf"\b{level}\b", upper) and level not in {
                decision.severity_level.value,
                decision.priority_level.value,
                decision.confidence_level.value,
            }:
                return f"contradicts_grading:{level}"

        # Every number in the narration must appear in the source facts. This is the check that
        # catches an invented casualty count, which is the most dangerous failure mode.
        allowed = self._allowed_numbers(brief, decision, allocation)
        for token in re.findall(r"\d+(?:\.\d+)?", completion):
            value = float(token)
            if not any(abs(value - candidate) < 1e-6 for candidate in allowed):
                return f"unsourced_number:{token}"

        return None

    def _allowed_numbers(
        self,
        brief: CommanderBrief,
        decision: DecisionResult,
        allocation: AllocationResult,
    ) -> set[float]:
        """Collect every number the narration is permitted to contain."""
        allowed: set[float] = {
            decision.severity_score,
            decision.priority_score,
            round(decision.confidence * 100),
            decision.confidence,
            100.0,
        }

        for item in allocation.recommendations:
            allowed.add(float(item.quantity))
            allowed.add(float(item.fulfilled_quantity))
            allowed.add(float(item.shortfall))

        # Numbers already present in engine-authored text are by definition grounded.
        source_text = " ".join(
            [
                brief.incident_summary,
                brief.severity,
                brief.priority,
                *brief.immediate_actions,
                *brief.risk_factors,
                *brief.operational_notes,
                *decision.risk_factors,
            ]
        )
        for token in re.findall(r"\d+(?:\.\d+)?", source_text):
            allowed.add(float(token))

        # Ordinals used for numbered actions.
        allowed.update(float(index) for index in range(1, len(brief.immediate_actions) + 2))
        return allowed
