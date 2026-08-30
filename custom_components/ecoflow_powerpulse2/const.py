"""Constants for EcoFlow PowerPulse 2."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfLength,
    UnitOfPower,
    UnitOfTime,
)

from .presentation import as_timestamp, tenths_to_float, watt_hours_to_kwh

DOMAIN = "ecoflow_powerpulse2"
CONF_EMAIL = "email"
CONF_PASSWORD = "password"
UPDATE_INTERVAL_SECONDS = 30
SETTINGS_REFRESH_DELAY_SECONDS = 20


@dataclass(frozen=True, kw_only=True)
class PowerPulse2SensorDescription(SensorEntityDescription):
    """PowerPulse sensor metadata."""

    diagnostic: bool = False
    source_key: str | None = None
    value_fn: Callable[[Any], Any] | None = None


SENSORS = (
    PowerPulse2SensorDescription(
        key="charging_power_w",
        translation_key="charging_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    PowerPulse2SensorDescription(
        key="charging_status",
        translation_key="charging_status",
        device_class=SensorDeviceClass.ENUM,
        options=[
            "unknown",
            "unplugged",
            "plugged_in",
            "charging",
            "paused",
            "charge_complete",
            "standby",
            "updating",
        ],
    ),
    PowerPulse2SensorDescription(
        key="work_mode",
        translation_key="work_mode",
        device_class=SensorDeviceClass.ENUM,
        options=["unknown", "fast", "solar", "custom", "smart"],
    ),
    PowerPulse2SensorDescription(
        key="ready_by_timestamp",
        translation_key="ready_by",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=as_timestamp,
    ),
    PowerPulse2SensorDescription(
        key="phase_voltage_v",
        translation_key="phase_voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        entity_registry_enabled_default=False,
    ),
    PowerPulse2SensorDescription(
        key="phase_current_a",
        translation_key="phase_current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
    ),
    PowerPulse2SensorDescription(
        key="session_duration_s",
        translation_key="session_duration",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    PowerPulse2SensorDescription(
        key="smart_charge_target_wh",
        translation_key="smart_charge_target",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        diagnostic=True,
        entity_registry_enabled_default=False,
    ),
    PowerPulse2SensorDescription(
        key="smart_target_type",
        translation_key="smart_target_type",
        device_class=SensorDeviceClass.ENUM,
        options=["energy", "distance"],
    ),
    PowerPulse2SensorDescription(
        key="smart_target_distance_km",
        translation_key="smart_target_distance",
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        device_class=SensorDeviceClass.DISTANCE,
    ),
    PowerPulse2SensorDescription(
        key="smart_calculated_energy_wh",
        translation_key="smart_calculated_energy",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        diagnostic=True,
        entity_registry_enabled_default=False,
    ),
    PowerPulse2SensorDescription(
        key="total_energy_raw",
        translation_key="total_energy_raw",
        diagnostic=True,
        entity_registry_enabled_default=False,
    ),
    PowerPulse2SensorDescription(
        key="total_energy_kwh",
        source_key="total_energy_raw",
        translation_key="total_energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=3,
        value_fn=watt_hours_to_kwh,
    ),
    PowerPulse2SensorDescription(
        key="session_energy_raw",
        translation_key="session_energy_raw",
        diagnostic=True,
        entity_registry_enabled_default=False,
    ),
    PowerPulse2SensorDescription(
        key="session_energy_kwh",
        source_key="session_energy_raw",
        translation_key="session_energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=3,
        value_fn=watt_hours_to_kwh,
    ),
    PowerPulse2SensorDescription(
        key="charge_current_set_raw",
        translation_key="charge_current_set_raw",
        diagnostic=True,
        entity_registry_enabled_default=False,
    ),
    PowerPulse2SensorDescription(
        key="current_limit_raw",
        translation_key="maximum_output_current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        suggested_display_precision=0,
        value_fn=tenths_to_float,
    ),
    PowerPulse2SensorDescription(
        key="suspend_reason_raw",
        translation_key="suspend_reason_raw",
        diagnostic=True,
        entity_registry_enabled_default=False,
    ),
    PowerPulse2SensorDescription(
        key="output_current_max_raw",
        translation_key="output_current_max_raw",
        diagnostic=True,
        entity_registry_enabled_default=False,
    ),
    PowerPulse2SensorDescription(
        key="user_current_set_raw",
        translation_key="user_current_set_raw",
        diagnostic=True,
        entity_registry_enabled_default=False,
    ),
    PowerPulse2SensorDescription(
        key="user_current_set_a",
        source_key="user_current_set_raw",
        translation_key="user_current_set",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        suggested_display_precision=0,
        value_fn=tenths_to_float,
    ),
    PowerPulse2SensorDescription(
        key="solar_current_min_raw",
        translation_key="solar_current_min_raw",
        diagnostic=True,
        entity_registry_enabled_default=False,
    ),
    PowerPulse2SensorDescription(
        key="solar_minimum_current_a",
        source_key="solar_current_min_raw",
        translation_key="solar_minimum_current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        suggested_display_precision=0,
        value_fn=tenths_to_float,
    ),
    PowerPulse2SensorDescription(
        key="switch_bits_raw",
        translation_key="switch_bits_raw",
        diagnostic=True,
        entity_registry_enabled_default=False,
    ),
    PowerPulse2SensorDescription(
        key="phase_specified_raw",
        translation_key="phase_specified_raw",
        diagnostic=True,
        entity_registry_enabled_default=False,
    ),
    PowerPulse2SensorDescription(
        key="phase_mode",
        translation_key="phase_mode",
        device_class=SensorDeviceClass.ENUM,
        options=["unknown", "one_phase", "three_phase", "auto"],
    ),
    PowerPulse2SensorDescription(
        key="screen_brightness_pct",
        translation_key="screen_brightness",
        native_unit_of_measurement=PERCENTAGE,
    ),
    PowerPulse2SensorDescription(
        key="indicator_brightness_pct",
        translation_key="indicator_brightness",
        native_unit_of_measurement=PERCENTAGE,
    ),
    PowerPulse2SensorDescription(
        key="vehicle_consumption_raw",
        translation_key="vehicle_consumption_raw",
        diagnostic=True,
        entity_registry_enabled_default=False,
    ),
)
