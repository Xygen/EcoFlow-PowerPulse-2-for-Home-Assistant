"""Readback qualification helpers for acknowledged settings writes."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def matching_readback_source(
    *,
    current_values: Mapping[str, Any],
    direct_reported_at: float,
    polled_values: Mapping[str, Any],
    polled_at: float,
    issued_at: float,
    expected_key: str,
    expected_value: Any,
) -> str | None:
    """Return the fresh source that independently confirms a write."""
    if (
        direct_reported_at > issued_at
        and current_values.get(expected_key) == expected_value
    ):
        return "direct"
    if (
        polled_at > issued_at
        and expected_key in polled_values
        and polled_values[expected_key] == expected_value
    ):
        return "provider"
    return None


def fresh_polled_value_matches(
    *,
    polled_values: Mapping[str, Any],
    polled_at: float,
    now: float,
    max_age: float,
    expected_key: str,
    expected_value: Any,
) -> bool:
    """Return whether a recent raw poll already confirms the requested value."""
    return (
        polled_at > 0
        and now - polled_at <= max_age
        and expected_key in polled_values
        and polled_values[expected_key] == expected_value
    )
