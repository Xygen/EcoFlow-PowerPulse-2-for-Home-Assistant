from custom_components.ecoflow_powerpulse2.setting_observation import (
    SettingObservationTracker,
    SettingSource,
    setting_source_from_headers,
)

FRESH_SECONDS = {
    "direct_heartbeat_2_33": 90,
    "direct_settings_2_34": 90,
    "direct_fast_settings_241_44": 90,
    "provider_parent_accessory": 60,
    "provider_device_detail": 60,
}


def _record(
    tracker: SettingObservationTracker,
    *,
    source: SettingSource,
    value: object,
    observed_monotonic: float,
) -> None:
    tracker.record_snapshot(
        serial="C376-test",
        source=source,
        values={"work_mode": value},
        keys={"work_mode"},
        observed_at="2026-08-30T10:00:00+00:00",
        observed_monotonic=observed_monotonic,
    )


def _value(tracker: SettingObservationTracker, now: float) -> object:
    return tracker.current_value(serial="C376-test", key="work_mode", now=now)


def test_missing_observation_is_unknown() -> None:
    assert _value(SettingObservationTracker(FRESH_SECONDS), 100) is None


def test_direct_report_sources_are_kept_distinct() -> None:
    assert setting_source_from_headers([{"cmd_func": 2, "cmd_id": 33}]) == (
        "direct_heartbeat_2_33"
    )
    assert setting_source_from_headers([{"cmd_func": 2, "cmd_id": 34}]) == (
        "direct_settings_2_34"
    )
    assert setting_source_from_headers([{"cmd_func": 241, "cmd_id": 44}]) == (
        "direct_fast_settings_241_44"
    )
    assert setting_source_from_headers([{"cmd_func": 241, "cmd_id": 3}]) is None


def test_fresh_observation_expires_to_unknown() -> None:
    tracker = SettingObservationTracker(FRESH_SECONDS)
    _record(
        tracker,
        source="provider_device_detail",
        value="solar",
        observed_monotonic=100,
    )

    assert _value(tracker, 160) == "solar"
    assert _value(tracker, 160.1) is None


def test_fresh_direct_observation_precedes_newer_provider_value() -> None:
    tracker = SettingObservationTracker(FRESH_SECONDS)
    _record(
        tracker,
        source="direct_heartbeat_2_33",
        value="solar",
        observed_monotonic=100,
    )
    _record(
        tracker,
        source="provider_parent_accessory",
        value="fast",
        observed_monotonic=120,
    )

    assert _value(tracker, 121) == "solar"


def test_provider_becomes_current_after_direct_expires() -> None:
    tracker = SettingObservationTracker(FRESH_SECONDS)
    _record(
        tracker,
        source="direct_heartbeat_2_33",
        value="solar",
        observed_monotonic=100,
    )
    _record(
        tracker,
        source="provider_parent_accessory",
        value="fast",
        observed_monotonic=150,
    )

    assert _value(tracker, 191) == "fast"


def test_missing_field_in_partial_report_does_not_refresh_previous_value() -> None:
    tracker = SettingObservationTracker(FRESH_SECONDS)
    _record(
        tracker,
        source="direct_settings_2_34",
        value="smart",
        observed_monotonic=100,
    )
    tracker.record_snapshot(
        serial="C376-test",
        source="direct_settings_2_34",
        values={"phase_mode": "auto"},
        keys={"work_mode", "phase_mode"},
        observed_at="2026-08-30T10:01:20+00:00",
        observed_monotonic=180,
    )

    assert _value(tracker, 191) is None
