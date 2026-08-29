from custom_components.ecoflow_powerpulse2.control_safety import (
    CHARGING_LOCKED_SETTING_KEYS,
    control_allowed_for_status,
)


def test_live_confirmed_settings_are_locked_while_charging() -> None:
    assert CHARGING_LOCKED_SETTING_KEYS == {
        "continuous_charging",
        "output_current_max_raw",
        "phase_mode",
        "ready_by_timestamp",
        "solar_current_min_raw",
        "smart_charge_target_wh",
        "smart_target_distance_km",
        "smart_target_type",
        "user_current_set_raw",
        "work_mode",
    }
    for key in CHARGING_LOCKED_SETTING_KEYS:
        assert not control_allowed_for_status(key, "charging")


def test_charging_sensitive_settings_fail_closed_without_known_state() -> None:
    for status in (None, "unknown", "updating", 3):
        assert not control_allowed_for_status("work_mode", status)


def test_charging_sensitive_settings_allow_known_non_charging_states() -> None:
    for status in (
        "unplugged",
        "plugged_in",
        "paused",
        "charge_complete",
        "standby",
    ):
        assert control_allowed_for_status("phase_mode", status)


def test_live_confirmed_allowed_settings_remain_available_while_charging() -> None:
    for key in (
        "battery_discharge_disabled",
        "indicator_brightness_pct",
        "indicator_enabled",
        "plug_and_play",
        "screen_brightness_pct",
        "screen_enabled",
    ):
        assert control_allowed_for_status(key, "charging")
