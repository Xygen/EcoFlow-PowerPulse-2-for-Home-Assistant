"""Evidence-gated current controls for EcoFlow PowerPulse 2."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfElectricCurrent
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
            ),
            NumberEntityDescription(
                key="solar_minimum_current_control",
                translation_key="solar_minimum_current_control",
                native_min_value=6,
                native_max_value=16,
                native_step=1,
                native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
            ),
            NumberEntityDescription(
                key="custom_current_control",
                translation_key="custom_current_control",
                native_min_value=6,
                native_max_value=16,
                native_step=1,
                native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
            ),
            NumberEntityDescription(
                key="smart_energy_target_control",
                translation_key="smart_energy_target_control",
                native_min_value=1,
                native_max_value=100,
                native_step=1,
                native_unit_of_measurement="kWh",
            ),
            NumberEntityDescription(
                key="smart_distance_target_control",
                translation_key="smart_distance_target_control",
                native_min_value=10,
                native_max_value=600,
                native_step=1,
                native_unit_of_measurement="km",
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
        if not self.coordinator.phase_control_available(self.serial):
            return False
        values = self.coordinator.data.get(self.serial, {})
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
        return "output_current_max_raw" in values

    @property
    def native_value(self) -> float | None:
        key = {
            "maximum_output_current_control": "output_current_max_raw",
            "solar_minimum_current_control": "solar_current_min_raw",
            "custom_current_control": "user_current_set_raw",
            "smart_energy_target_control": "smart_charge_target_wh",
            "smart_distance_target_control": "smart_target_distance_km",
        }[self.entity_description.key]
        value = self.coordinator.data.get(self.serial, {}).get(key)
        if value is None and self.entity_description.key.startswith("smart_"):
            value = self.coordinator.remembered_smart_setting(self.serial, key)
        if not isinstance(value, (int, float)):
            return None
        if self.entity_description.key == "smart_energy_target_control":
            return float(value) / 1000
        if self.entity_description.key == "smart_distance_target_control":
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
        else:
            await self.coordinator.async_set_smart_distance_target(self.serial, value)
