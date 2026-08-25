"""Readback qualification helpers for acknowledged settings writes."""

from __future__ import annotations

from collections.abc import Collection, Mapping
from typing import Any


def fresh_direct_value_available(
    *,
    current_values: Mapping[str, Any],
    direct_reported_at: float,
    now: float,
    max_age: float,
    key: str,
    allowed_values: Collection[Any],
) -> bool:
    """Return whether a recent direct report can confirm one control value."""
    return (
        direct_reported_at > 0
        and now - direct_reported_at <= max_age
        and current_values.get(key) in allowed_values
    )


def provider_readback_attempt_details(
    *,
    polled_values: Mapping[str, Any],
    polled_at: float,
    issued_at: float,
    expected_key: str,
    expected_value: Any,
) -> dict[str, bool]:
    """Return privacy-safe qualification details for one provider attempt."""
    snapshot_after_command = polled_at > issued_at
    expected_key_present = expected_key in polled_values
    return {
        "snapshot_after_command": snapshot_after_command,
        "expected_key_present": expected_key_present,
        "matched": (
            snapshot_after_command
            and expected_key_present
            and polled_values[expected_key] == expected_value
        ),
    }


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
    if provider_readback_attempt_details(
        polled_values=polled_values,
        polled_at=polled_at,
        issued_at=issued_at,
        expected_key=expected_key,
        expected_value=expected_value,
    )["matched"]:
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
