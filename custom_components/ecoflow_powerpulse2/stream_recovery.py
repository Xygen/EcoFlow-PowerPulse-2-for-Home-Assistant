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
    if last_direct_at is None or last_heartbeat_at is None:
        return False
    if now - last_direct_at < stale_seconds:
        return False
    if now - last_heartbeat_at < stale_seconds:
        return False
    return last_attempt_at is None or now - last_attempt_at >= cooldown_seconds
