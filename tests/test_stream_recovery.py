from custom_components.ecoflow_powerpulse2.stream_recovery import (
    automatic_recovery_due,
)


def _due(
    *,
    now: float = 1_000,
    direct: float | None = 600,
    heartbeat: float | None = 600,
    attempt: float | None = None,
) -> bool:
    return automatic_recovery_due(
        now=now,
        last_direct_at=direct,
        last_heartbeat_at=heartbeat,
        last_attempt_at=attempt,
        stale_seconds=300,
        cooldown_seconds=1_800,
    )


def test_recovery_requires_both_streams_to_have_been_observed() -> None:
    assert not _due(direct=None)
    assert not _due(heartbeat=None)


def test_recovery_waits_until_both_streams_are_sustainably_stale() -> None:
    assert not _due(direct=701)
    assert not _due(heartbeat=701)
    assert _due(direct=700, heartbeat=700)


def test_recovery_enforces_cooldown_after_attempt() -> None:
    assert not _due(attempt=-799)
    assert _due(attempt=-800)
