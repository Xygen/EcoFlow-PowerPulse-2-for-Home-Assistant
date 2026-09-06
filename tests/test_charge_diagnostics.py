from custom_components.ecoflow_powerpulse2.charge_diagnostics import (
    ChargeActionDiagnostics,
)


def _begin(
    tracker: ChargeActionDiagnostics,
    serial: str = "C376SECRET",
    *,
    issued_monotonic: float = 100,
) -> None:
    tracker.begin(
        serial,
        action="start",
        issued_at="2026-09-06T10:00:00+00:00",
        issued_monotonic=issued_monotonic,
        pre_direct_state="plugged_in",
        pre_direct_reported_at=98.7654,
    )


def test_attempt_records_source_specific_first_states_and_timings() -> None:
    tracker = ChargeActionDiagnostics(2)
    _begin(tracker)

    tracker.record_direct("C376SECRET", "charging", observed_monotonic=99)
    tracker.record_direct("C376SECRET", "paused", observed_monotonic=101.2345)
    tracker.record_direct("C376SECRET", "charging", observed_monotonic=102)
    tracker.record_powerocean(
        "C376SECRET", "preparing", observed_monotonic=101.9876
    )
    tracker.record_publish("C376SECRET", "accepted")
    tracker.record_set_reply(
        "C376SECRET", result="received", observed_monotonic=100.4567
    )
    tracker.finish(
        "C376SECRET",
        outcome="confirmed",
        confirmation_source="direct",
        completed_monotonic=102.3456,
    )

    record = tracker.snapshot()["recent_attempts"][0]
    assert record == {
        "device_prefix": "C376",
        "action": "start",
        "issued_at": "2026-09-06T10:00:00+00:00",
        "pre_direct_state": "plugged_in",
        "pre_direct_age_seconds": 1.235,
        "publish_result": "accepted",
        "set_reply_result": "received",
        "set_reply_latency_seconds": 0.457,
        "first_post_command_direct_state": "paused",
        "first_post_command_direct_latency_seconds": 1.234,
        "first_post_command_powerocean_state": "preparing",
        "first_post_command_powerocean_latency_seconds": 1.988,
        "confirmation_source": "direct",
        "progress_extension_granted": False,
        "outcome": "confirmed",
        "elapsed_seconds": 2.346,
    }


def test_attempt_diagnostics_are_bounded_and_identifier_free() -> None:
    tracker = ChargeActionDiagnostics(2)
    for index, serial in enumerate(("C376FIRST", "C376SECOND", "C376THIRD")):
        _begin(tracker, serial, issued_monotonic=float(index + 1))
        tracker.finish(
            serial,
            outcome="readback_timeout",
            completed_monotonic=float(index + 2),
        )

    snapshot = tracker.snapshot()
    assert snapshot["max_completed_attempts"] == 2
    assert len(snapshot["recent_attempts"]) == 2
    assert all(record["device_prefix"] == "C376" for record in snapshot["recent_attempts"])
    assert "C376SECOND" not in repr(snapshot)
    assert "C376THIRD" not in repr(snapshot)


def test_unknown_states_and_inactive_observations_are_not_retained() -> None:
    tracker = ChargeActionDiagnostics(1)
    tracker.record_direct("C376SECRET", "charging", observed_monotonic=101)
    _begin(tracker)
    tracker.record_powerocean(
        "C376SECRET", "vehicle-secret-value", observed_monotonic=101
    )

    assert tracker.snapshot()["active_attempts"][0][
        "first_post_command_powerocean_state"
    ] is None
