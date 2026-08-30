"""Evidence-gated current controls for EcoFlow PowerPulse 2."""

from __future__ import annotations

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfEnergy,
    UnitOfLength,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import PowerPulse2Coordinator
from .entity import PowerPulse2Entity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator: PowerPulse2Coordinator = entry.runtime_data
    async_add_entities(
        PowerPulse2CurrentNumber(coordinator, serial, description)
        for serial in coordinator.devices
        for description in (
            NumberEntityDescription(
                key="maximum_output_current_control",
                translation_key="maximum_output_current_control",
                native_min_value=6,
                native_max_value=16,
                native_step=1,
                native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
                device_class=NumberDeviceClass.CURRENT,
            ),
            NumberEntityDescription(
                key="solar_minimum_current_control",
                translation_key="solar_minimum_current_control",
                native_min_value=6,
                native_max_value=16,
                native_step=1,
                native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
                device_class=NumberDeviceClass.CURRENT,
            ),
            NumberEntityDescription(
                key="custom_current_control",
                translation_key="custom_current_control",
                native_min_value=6,
                native_max_value=16,
                native_step=1,
                native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
                device_class=NumberDeviceClass.CURRENT,
            ),
            NumberEntityDescription(
                key="smart_energy_target_control",
                translation_key="smart_energy_target_control",
                native_min_value=1,
                native_max_value=100,
                native_step=1,
                native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
                device_class=NumberDeviceClass.ENERGY,
            ),
            NumberEntityDescription(
                key="smart_distance_target_control",
                translation_key="smart_distance_target_control",
                native_min_value=10,
                native_max_value=600,
                native_step=1,
                native_unit_of_measurement=UnitOfLength.KILOMETERS,
                device_class=NumberDeviceClass.DISTANCE,
            ),
            NumberEntityDescription(
                key="screen_brightness_control",
                translation_key="screen_brightness_control",
                native_min_value=25,
                native_max_value=100,
                native_step=25,
                native_unit_of_measurement=PERCENTAGE,
                entity_category=EntityCategory.CONFIG,
            ),
            NumberEntityDescription(
                key="indicator_brightness_control",
                translation_key="indicator_brightness_control",
                native_min_value=25,
                native_max_value=100,
                native_step=25,
                native_unit_of_measurement=PERCENTAGE,
                entity_category=EntityCategory.CONFIG,
            ),
        )
    )


class PowerPulse2CurrentNumber(PowerPulse2Entity, NumberEntity):
    """One disabled-by-default whole-ampere current control."""

    _attr_entity_registry_enabled_default = False

    def __init__(
        self,
        coordinator: PowerPulse2Coordinator,
        serial: str,
        description: NumberEntityDescription,
    ) -> None:
        super().__init__(coordinator, serial, description.key)
        self.entity_description = description

    @property
    def available(self) -> bool:
        if not self.coordinator.settings_control_available(self.serial):
            return False
        values = self.coordinator.data.get(self.serial, {})
        locked_key = {
            "maximum_output_current_control": "output_current_max_raw",
            "solar_minimum_current_control": "solar_current_min_raw",
            "custom_current_control": "user_current_set_raw",
            "smart_energy_target_control": "smart_charge_target_wh",
            "smart_distance_target_control": "smart_target_distance_km",
        }.get(self.entity_description.key)
        if locked_key and not self.coordinator.charging_sensitive_control_available(
            self.serial, locked_key
        ):
            return False
        if self.entity_description.key == "solar_minimum_current_control":
            return values.get("work_mode") == "solar" and bool(
                values.get("continuous_charging")
            )
        if self.entity_description.key == "custom_current_control":
            return values.get("work_mode") == "custom"
        if self.entity_description.key == "smart_energy_target_control":
            return values.get("work_mode") == "smart"
        if self.entity_description.key == "smart_distance_target_control":
            return values.get("work_mode") == "smart"
        if self.entity_description.key == "screen_brightness_control":
            return values.get("screen_enabled") is True
        if self.entity_description.key == "indicator_brightness_control":
            return values.get("indicator_enabled") is True
        return "output_current_max_raw" in values

    @property
    def native_value(self) -> float | None:
        key = {
            "maximum_output_current_control": "output_current_max_raw",
            "solar_minimum_current_control": "solar_current_min_raw",
            "custom_current_control": "user_current_set_raw",
            "smart_energy_target_control": "smart_charge_target_wh",
            "smart_distance_target_control": "smart_target_distance_km",
            "screen_brightness_control": "screen_brightness_pct",
            "indicator_brightness_control": "indicator_brightness_pct",
        }[self.entity_description.key]
        value = self.coordinator.data.get(self.serial, {}).get(key)
        if value is None and self.entity_description.key.startswith("smart_"):
            value = self.coordinator.remembered_smart_setting(self.serial, key)
        if not isinstance(value, (int, float)):
            return None
        if self.entity_description.key == "smart_energy_target_control":
            return float(value) / 1000
        if self.entity_description.key in (
            "smart_distance_target_control", "screen_brightness_control",
            "indicator_brightness_control",
        ):
            return float(value)
        return float(value) / 10

    async def async_set_native_value(self, value: float) -> None:
        if self.entity_description.key == "maximum_output_current_control":
            await self.coordinator.async_set_maximum_output_current(self.serial, value)
        elif self.entity_description.key == "solar_minimum_current_control":
            await self.coordinator.async_set_solar_minimum_current(self.serial, value)
        elif self.entity_description.key == "custom_current_control":
            await self.coordinator.async_set_custom_current(self.serial, value)
        elif self.entity_description.key == "smart_energy_target_control":
            await self.coordinator.async_set_smart_energy_target(self.serial, value)
        elif self.entity_description.key == "screen_brightness_control":
            await self.coordinator.async_set_screen_brightness(self.serial, value)
        elif self.entity_description.key == "indicator_brightness_control":
            await self.coordinator.async_set_indicator_brightness(self.serial, value)
        else:
            await self.coordinator.async_set_smart_distance_target(self.serial, value)
