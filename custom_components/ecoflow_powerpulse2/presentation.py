"""Presentation helpers that keep protocol values unchanged internally."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def as_timestamp(value: Any) -> datetime | None:
    """Convert a positive Unix timestamp to an aware UTC datetime."""
    if not isinstance(value, (int, float)) or value <= 0:
        return None
    return datetime.fromtimestamp(value, UTC)


def tenths_to_float(value: Any) -> float | None:
    """Convert a confirmed tenths-scaled protocol value."""
    if not isinstance(value, (int, float)):
        return None
    return round(float(value) / 10, 1)


def watt_hours_to_kwh(value: Any) -> float | None:
    """Convert a confirmed watt-hour protocol value to kilowatt-hours."""
    if not isinstance(value, (int, float)) or value < 0:
        return None
    return round(float(value) / 1000, 3)
