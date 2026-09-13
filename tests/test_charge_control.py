import pytest

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
        "stop", values, heartbeat_reported_at=11, issued_at=10,
        pre_direct_state="charging",
    )
    assert not fresh_direct_charge_action_confirmed(
        "start", values, heartbeat_reported_at=11, issued_at=10,
        pre_direct_state="plugged_in",
    )
    assert not fresh_direct_charge_action_confirmed(
        "stop", values, heartbeat_reported_at=10, issued_at=10,
        pre_direct_state="charging",
    )


@pytest.mark.parametrize(
    ("action", "pre_state", "current", "confirmed"),
    [
        # The false positive this closes: an ignored Start from paused.
        ("start", "paused", "paused", False),
        # Real transitions, all of which must keep confirming.
        ("start", "charge_complete", "paused", True),
        ("start", "paused", "charging", True),
        ("start", "plugged_in", "paused", True),
        ("start", "plugged_in", "charging", True),
        ("start", "charge_complete", "charging", True),
        ("stop", "charging", "charge_complete", True),
        ("stop", "paused", "plugged_in", True),
        ("stop", "charging", "standby", True),
    ],
)
def test_confirmation_requires_the_state_to_have_changed(
    action, pre_state, current, confirmed
) -> None:
    """A confirmation state is evidence only when the charger reached it.

    The resume case `paused` to `charging` is in this table on purpose: an
    earlier wording of the rule, which rejected any pre-state that was itself a
    confirmation state, would have broken it.
    """
    values = {"direct_charging_status": current}
    assert (
        fresh_direct_charge_action_confirmed(
            action, values,
            heartbeat_reported_at=11, issued_at=10, pre_direct_state=pre_state,
        )
        is confirmed
    )


def test_the_same_state_case_is_reachable_only_where_the_sets_meet() -> None:
    """Pins exactly where an unchanged state could have passed as confirmation.

    If either set changes so that a new state is both a valid pre-state and a
    confirmation state, this fails at the moment of the change rather than on a
    charger.
    """
    from custom_components.ecoflow_powerpulse2 import charge_control as rules

    assert rules._STARTABLE_STATUSES & rules._START_CONFIRMED_STATUSES == {"paused"}
    assert not rules._STOPPABLE_STATUSES & rules._STOP_CONFIRMED_STATUSES


def test_a_stale_heartbeat_still_never_confirms_even_after_a_change() -> None:
    """The change rule adds to the freshness rule; it does not replace it."""
    assert not fresh_direct_charge_action_confirmed(
        "start", {"direct_charging_status": "charging"},
        heartbeat_reported_at=10, issued_at=10, pre_direct_state="paused",
    )
