from custom_components.ecoflow_powerpulse2.sensor_availability import (
    telemetry_sensor_available,
    telemetry_sensor_value,
)


def test_healthy_sensor_with_present_value_is_available() -> None:
    values = {"charging_power_w": 1234}

    assert telemetry_sensor_available(
        coordinator_available=True,
        device_present=True,
        source_available=True,
    )
    assert telemetry_sensor_value(values, "charging_power_w") == 1234


def test_healthy_sensor_with_missing_value_is_unknown_not_unavailable() -> None:
    assert telemetry_sensor_available(
        coordinator_available=True,
        device_present=True,
        source_available=True,
    )
    assert telemetry_sensor_value({}, "charging_power_w") is None


def test_failed_coordinator_or_missing_device_is_unavailable() -> None:
    assert not telemetry_sensor_available(
        coordinator_available=False,
        device_present=True,
        source_available=True,
    )
    assert not telemetry_sensor_available(
        coordinator_available=True,
        device_present=False,
        source_available=True,
    )


def test_genuinely_unavailable_source_is_unavailable_even_with_cached_value() -> None:
    values = {"charging_power_w": 1234}

    assert not telemetry_sensor_available(
        coordinator_available=True,
        device_present=True,
        source_available=False,
    )
    assert telemetry_sensor_value(values, "charging_power_w") == 1234
