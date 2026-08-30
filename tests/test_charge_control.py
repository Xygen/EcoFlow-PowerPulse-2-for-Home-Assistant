from custom_components.ecoflow_powerpulse2.charge_control import (
    charge_action_allowed,
    charge_action_confirm_seconds,
    charge_action_confirmed,
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
