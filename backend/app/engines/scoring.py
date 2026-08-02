"""Shared numeric helpers for deterministic score handling."""

from typing import TypeVar

from app.engines.config import (
    CONFIDENCE_MAX,
    CONFIDENCE_MIN,
    CONFIDENCE_PRECISION,
    SCORE_MAX,
    SCORE_MIN,
    SCORE_PRECISION,
)

BandT = TypeVar("BandT")


def clamp_score(value: float) -> float:
    """Constrain a raw score to the engine's 0-100 domain."""
    return max(SCORE_MIN, min(SCORE_MAX, value))


def round_score(value: float) -> float:
    """Round a score at the single output boundary, keeping runs reproducible."""
    return round(value, SCORE_PRECISION)


def clamp_confidence(value: float) -> float:
    """Constrain a raw confidence to the engine's 0-1 domain."""
    return max(CONFIDENCE_MIN, min(CONFIDENCE_MAX, value))


def round_confidence(value: float) -> float:
    """Round a confidence at the single output boundary."""
    return round(value, CONFIDENCE_PRECISION)


def resolve_band(value: float, bands: tuple[tuple[float, BandT], ...]) -> BandT:
    """Return the band whose inclusive lower bound the value first satisfies.

    Bands must be ordered from the highest threshold down; the final entry acts as the
    default so that every value in the domain resolves to exactly one band.
    """
    for threshold, band in bands:
        if value >= threshold:
            return band
    return bands[-1][1]
