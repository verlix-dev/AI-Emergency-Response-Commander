"""Normalization of free-text assessment fields into engine enumerations."""

import re

from app.engines.config import DISASTER_TYPE_ALIASES, WEATHER_ALIASES
from app.engines.models import DisasterType, Weather

_TOKEN_PATTERN = re.compile(r"[^a-z0-9]+")


def normalize_token(value: str) -> str:
    """Lower-case a label and collapse punctuation and spacing into single underscores."""
    return _TOKEN_PATTERN.sub("_", value.strip().lower()).strip("_")


def resolve_disaster_type(label: str) -> DisasterType:
    """Map an incident-type label onto the taxonomy.

    Unrecognised labels resolve to ``UNKNOWN`` rather than being forced into the nearest
    neighbour, because selecting the wrong disaster profile silently mis-calibrates every
    downstream score.
    """
    token = normalize_token(label)
    if not token:
        return DisasterType.UNKNOWN
    alias = DISASTER_TYPE_ALIASES.get(token)
    if alias is not None:
        return alias
    try:
        return DisasterType(token.upper())
    except ValueError:
        return DisasterType.UNKNOWN


def resolve_weather(label: str | None) -> Weather:
    """Map a weather label onto the normalized weather enumeration."""
    if label is None:
        return Weather.UNKNOWN
    token = normalize_token(label)
    if not token:
        return Weather.UNKNOWN
    alias = WEATHER_ALIASES.get(token)
    if alias is not None:
        return alias
    try:
        return Weather(token.upper())
    except ValueError:
        return Weather.UNKNOWN
