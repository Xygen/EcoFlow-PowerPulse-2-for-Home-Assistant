from pathlib import Path

import pytest

from custom_components.ecoflow_powerpulse2.smart_staging import (
    SmartStaging,
    SmartStagingError,
    validate_smart_bundle,
)

ROOT = Path(__file__).parents[1]


def test_staged_energy_bundle_survives_reload_without_distance() -> None:
    staging = SmartStaging()

    assert staging.update(
        "C376-a",
        {
            "ready_by_timestamp": 1_788_000_000,
            "smart_target_type": "energy",
            "smart_charge_target_wh": 30_000,
        },
    )
    assert not staging.update("C376-a", {"smart_charge_target_wh": 30_000})
    validate_smart_bundle(staging.values("C376-a"))

    restored = SmartStaging()
    restored.load(staging.export())

    assert restored.values("C376-a") == staging.values("C376-a")
    assert restored.value("C376-a", "smart_target_distance_km") is None


def test_staged_distance_bundle_does_not_require_energy_target() -> None:
    staging = SmartStaging()
    staging.update(
        "C376-a",
        {
            "ready_by_timestamp": 1_788_000_000,
            "smart_target_type": "distance",
            "smart_target_distance_km": 200,
        },
    )

    validate_smart_bundle(staging.values("C376-a"))
    assert staging.value("C376-a", "smart_charge_target_wh") is None


def test_target_type_can_be_staged_before_its_target() -> None:
    staging = SmartStaging()
    staging.update("C376-a", {"smart_target_type": "energy"})

    with pytest.raises(SmartStagingError, match="ready-by time"):
        validate_smart_bundle(staging.values("C376-a"))

    staging.update("C376-a", {"ready_by_timestamp": 1_788_000_000})
    with pytest.raises(SmartStagingError, match="energy target"):
        validate_smart_bundle(staging.values("C376-a"))


def test_staging_is_isolated_per_serial() -> None:
    staging = SmartStaging()
    staging.update("C376-a", {"smart_charge_target_wh": 30_000})
    staging.update("C376-b", {"smart_target_distance_km": 200})

    assert staging.values("C376-a") == {"smart_charge_target_wh": 30_000}
    assert staging.values("C376-b") == {"smart_target_distance_km": 200}


def test_load_isolates_malformed_devices_and_fields() -> None:
    staging = SmartStaging()
    staging.load(
        {
            "devices": {
                "C376-good": {
                    "ready_by_timestamp": 1_788_000_000,
                    "smart_target_type": "energy",
                    "smart_charge_target_wh": 30_000,
                    "smart_target_distance_km": True,
                    "vehicle_consumption_raw": 150,
                },
                "C376-bad": "not-a-mapping",
                "C376-partial": {
                    "smart_target_type": "invalid",
                    "smart_target_distance_km": 300,
                },
            }
        }
    )

    assert staging.values("C376-good") == {
        "ready_by_timestamp": 1_788_000_000,
        "smart_target_type": "energy",
        "smart_charge_target_wh": 30_000,
    }
    assert staging.values("C376-bad") == {}
    assert staging.values("C376-partial") == {"smart_target_distance_km": 300}
    assert "vehicle_consumption_raw" not in str(staging.export())


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("ready_by_timestamp", True),
        ("smart_target_type", "automatic"),
        ("smart_charge_target_wh", 30_500),
        ("smart_charge_target_wh", 101_000),
        ("smart_target_distance_km", 9),
        ("smart_target_distance_km", 601),
        ("vehicle_consumption_raw", 150),
    ],
)
def test_invalid_user_owned_stage_values_are_rejected(key: str, value: object) -> None:
    staging = SmartStaging()

    with pytest.raises(SmartStagingError):
        staging.update("C376-a", {key: value})

    assert staging.values("C376-a") == {}


def test_observation_code_does_not_read_staged_smart_values() -> None:
    sensor_source = (
        ROOT / "custom_components/ecoflow_powerpulse2/sensor.py"
    ).read_text(encoding="utf-8")
    coordinator_source = (
        ROOT / "custom_components/ecoflow_powerpulse2/coordinator.py"
    ).read_text(encoding="utf-8")

    assert "staged_smart_setting" not in sensor_source
    assert "setting_observation_value" in sensor_source
    assert "Smart distance target requires vehicle consumption" not in coordinator_source
    assert 'calculated = 0 if target_type == "distance" else None' in coordinator_source
    assert "if (self.data or {}).get(serial, {}).get(\"work_mode\") != \"smart\"" in coordinator_source
    assert "await self._async_update_smart_staging(serial, overrides)" in coordinator_source
