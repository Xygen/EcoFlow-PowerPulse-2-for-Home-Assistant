"""Eligibility rules for bounded direct-stream recovery."""

from __future__ import annotations


def automatic_recovery_due(
    *,
    now: float,
    last_direct_at: float | None,
    last_heartbeat_at: float | None,
    last_attempt_at: float | None,
    stale_seconds: float,
    cooldown_seconds: float,
) -> bool:
    """Return whether both proven streams are stale and cooldown has elapsed."""
    return recovery_reason(
        now=now, last_direct_at=last_direct_at,
        last_heartbeat_at=last_heartbeat_at, last_attempt_at=last_attempt_at,
        stale_seconds=stale_seconds, cooldown_seconds=cooldown_seconds,
    ) == "due"


def recovery_reason(
    *, now: float, last_direct_at: float | None,
    last_heartbeat_at: float | None, last_attempt_at: float | None,
    stale_seconds: float, cooldown_seconds: float,
) -> str:
    """Explain the existing policy without changing its eligibility rules."""
    if last_direct_at is None or last_heartbeat_at is None:
        return "streams_not_started"
    if now - last_direct_at < stale_seconds:
        return "settings_within_stale_limit"
    if now - last_heartbeat_at < stale_seconds:
        return "heartbeat_within_stale_limit"
    if last_attempt_at is not None and now - last_attempt_at < cooldown_seconds:
        return "cooldown"
    return "due"
