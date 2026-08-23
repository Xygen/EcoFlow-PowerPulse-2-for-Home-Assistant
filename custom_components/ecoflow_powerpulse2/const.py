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
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
)

from .presentation import as_timestamp, format_duration

DOMAIN = "ecoflow_powerpulse2"
CONF_EMAIL = "email"
CONF_PASSWORD = "password"
UPDATE_INTERVAL_SECONDS = 30

# CP307 protocol devices observed by the EcoFlow BLE community. C37x covers
# the European 7/11/22 kW PowerPulse 2 family; the C10x variants use the same
# heartbeat and are retained so discovery remains useful across regions.
POWERPULSE_PREFIXES = (
    "C101",
    "C102",
    "C103",
    "C371",
    "C372",
    "C373",
    "C374",
    "C375",
    "C376",
)


@dataclass(frozen=True, kw_only=True)
class PowerPulse2SensorDescription(SensorEntityDescription):
    """PowerPulse sensor metadata."""

    diagnostic: bool = False
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
        value_fn=format_duration,
        diagnostic=True,
        entity_registry_enabled_default=False,
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
        key="total_energy_raw",
        translation_key="total_energy_raw",
        diagnostic=True,
        entity_registry_enabled_default=False,
    ),
    PowerPulse2SensorDescription(
        key="session_energy_raw",
        translation_key="session_energy_raw",
        diagnostic=True,
        entity_registry_enabled_default=False,
    ),
    PowerPulse2SensorDescription(
        key="charge_current_set_raw",
        translation_key="charge_current_set_raw",
        diagnostic=True,
        entity_registry_enabled_default=False,
    ),
    PowerPulse2SensorDescription(
        key="current_limit_raw",
        translation_key="current_limit_raw",
        diagnostic=True,
        entity_registry_enabled_default=False,
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
        key="solar_current_min_raw",
        translation_key="solar_current_min_raw",
        diagnostic=True,
        entity_registry_enabled_default=False,
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
        key="vehicle_consumption_raw",
        translation_key="vehicle_consumption_raw",
        diagnostic=True,
        entity_registry_enabled_default=False,
    ),
)
