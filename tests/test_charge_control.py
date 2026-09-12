from custom_components.ecoflow_powerpulse2.charge_control import (
    charge_action_allowed,
    charge_action_confirm_seconds,
    charge_action_confirmed,
    charge_action_progress_confirm_seconds,
    direct_charging_status,
    fresh_direct_charge_action_confirmed,
    fresh_direct_start_progress_observed,
)


def test_start_requires_a_connected_non_charging_state() -> None:
    for status in ("plugged_in", "paused", "charge_complete", "standby"):
        assert charge_action_allowed("start", status)
    for status in (None, "unknown", "updating", "unplugged", "charging"):
        assert not charge_action_allowed("start", status)


def test_stop_requires_an_active_or_paused_session() -> None:
    for status in ("charging", "paused"):
        assert charge_action_allowed("stop", status)
    for status in (None, "unknown", "updating", "unplugged", "plugged_in", "charge_complete", "standby"):
        assert not charge_action_allowed("stop", status)


def test_action_confirmation_uses_independent_heartbeat_states() -> None:
    assert charge_action_confirmed("start", "charging")
    assert charge_action_confirmed("start", "paused")
    assert not charge_action_confirmed("start", "charge_complete")
    for status in ("plugged_in", "charge_complete", "standby"):
        assert charge_action_confirmed("stop", status)
    assert not charge_action_confirmed("stop", "charging")
    assert not charge_action_confirmed("unknown-action", "charging")


def test_start_and_stop_use_independent_confirmation_windows() -> None:
    assert charge_action_confirm_seconds("start") == 30
    assert charge_action_confirm_seconds("stop") == 15
    assert charge_action_progress_confirm_seconds("start") == 50
    assert charge_action_progress_confirm_seconds("stop") == 15


def test_start_progress_requires_a_new_direct_transition_to_plugged_in() -> None:
    values = {"direct_charging_status": "plugged_in"}

    assert fresh_direct_start_progress_observed(
        "start",
        values,
        heartbeat_reported_at=11,
        issued_at=10,
        pre_direct_state="charge_complete",
    )
    assert not fresh_direct_start_progress_observed(
        "start",
        values,
        heartbeat_reported_at=11,
        issued_at=10,
        pre_direct_state="plugged_in",
    )
    assert not fresh_direct_start_progress_observed(
        "start",
        values,
        heartbeat_reported_at=10,
        issued_at=10,
        pre_direct_state="charge_complete",
    )
    assert not fresh_direct_start_progress_observed(
        "stop",
        values,
        heartbeat_reported_at=11,
        issued_at=10,
        pre_direct_state="charging",
    )
    assert not fresh_direct_start_progress_observed(
        "start",
        {"direct_charging_status": "standby"},
        heartbeat_reported_at=11,
        issued_at=10,
        pre_direct_state="charge_complete",
    )


def test_direct_status_never_falls_back_to_mergeable_canonical_state() -> None:
    assert direct_charging_status({"charging_status": "charging"}) is None
    assert (
        direct_charging_status(
            {
                "charging_status": "charging",
                "direct_charging_status": "charge_complete",
            }
        )
        == "charge_complete"
    )


def test_confirmation_couples_direct_state_to_newer_heartbeat() -> None:
    values = {
        "charging_status": "charging",
        "direct_charging_status": "charge_complete",
    }
    assert fresh_direct_charge_action_confirmed(
        "stop", values, heartbeat_reported_at=11, issued_at=10
    )
    assert not fresh_direct_charge_action_confirmed(
        "start", values, heartbeat_reported_at=11, issued_at=10
    )
    assert not fresh_direct_charge_action_confirmed(
        "stop", values, heartbeat_reported_at=10, issued_at=10
    )
