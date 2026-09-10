import pytest

from custom_components.ecoflow_powerpulse2.control_readback import (
    matching_readback_source,
    provider_bundle_matches,
    settings_bundle_values,
)
from custom_components.ecoflow_powerpulse2.setting_observation import SettingObservation


def obs(value, at, source="direct_fast_settings_241_44"):
    return SettingObservation(value, source, "2026-09-09T20:00:00Z", at)


@pytest.mark.parametrize("observations,expected", [
    ([], None),
    ([obs(60, 9)], None),
    ([obs(60, 10)], None),
    ([obs(60, 11)], "direct"),
    ([obs(60, 11, "provider_parent_accessory")], "provider"),
    ([obs(60, 11, "provider_device_detail")], "provider"),
    ([obs(160, 9), obs(60, 11, "provider_parent_accessory")], None),
    ([obs(160, 12), obs(60, 11, "provider_parent_accessory")], None),
    ([obs(60, 11), obs(160, 12, "provider_device_detail")], None),
    ([obs(60, 11), obs(160, 11, "direct_settings_2_34")], None),
    ([obs(160, 11), obs(60, 12, "direct_settings_2_34")], "direct"),
    ([obs(160, 9, "provider_device_detail"), obs(60, 11)], "direct"),
])
def test_field_evidence_confirmation(observations, expected):
    assert matching_readback_source(observations=observations, issued_at=10, expected_value=60) == expected


@pytest.mark.parametrize("second_source,second_time,expected", [
    ("provider_parent_accessory", 10, True),
    ("provider_parent_accessory", 11, False),
    ("provider_device_detail", 10, False),
    ("direct_fast_settings_241_44", 10, False),
])
def test_noop_bundle_requires_one_provider_snapshot(second_source, second_time, expected):
    evidence = {"work_mode": [obs("solar", 10, "provider_parent_accessory")],
                "switch_bits_raw": [obs(18, second_time, second_source)]}
    assert provider_bundle_matches(
        evidence=evidence, expected={"work_mode": "solar", "switch_bits_raw": 18},
    ) is expected


def test_noop_rejects_any_fresh_conflict_or_missing_field():
    assert not provider_bundle_matches(evidence={}, expected={"work_mode": "fast"})
    assert not provider_bundle_matches(evidence={}, expected={})
    assert not provider_bundle_matches(
        evidence={"work_mode": [obs("fast", 11, "provider_parent_accessory"), obs("solar", 9)]},
        expected={"work_mode": "fast"},
    )


def test_display_noop_checks_all_companions():
    assert settings_bundle_values({21: bytes((1, 0, 25, 100, 0, 0))}) == {
        "indicator_enabled": True, "screen_enabled": False,
        "indicator_brightness_pct": 25, "screen_brightness_pct": 100,
    }


def test_unknown_or_phase_bundle_cannot_use_generic_noop():
    assert settings_bundle_values({5: 1}) == {}
