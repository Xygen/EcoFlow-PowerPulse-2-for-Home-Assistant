"""Presentation helpers that keep protocol values unchanged internally."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def format_duration(value: Any) -> str | None:
    """Format numeric seconds in a compact human-readable form."""
    if not isinstance(value, (int, float)) or value < 0:
        return None
    total_seconds = int(value)
    if total_seconds < 60:
        return f"{total_seconds} s"

    total_minutes, seconds = divmod(total_seconds, 60)
    if total_minutes < 60:
        return f"{total_minutes} min" + (f" {seconds:02d} s" if seconds else "")

    total_hours, minutes = divmod(total_minutes, 60)
    if total_hours < 24:
        return f"{total_hours} h {minutes:02d} min"

    days, hours = divmod(total_hours, 24)
    return f"{days} d {hours:02d} h"


def as_timestamp(value: Any) -> datetime | None:
    """Convert a positive Unix timestamp to an aware UTC datetime."""
    if not isinstance(value, (int, float)) or value <= 0:
        return None
    return datetime.fromtimestamp(value, UTC)
