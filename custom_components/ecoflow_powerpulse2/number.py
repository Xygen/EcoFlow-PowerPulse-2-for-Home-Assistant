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
        return "output_current_max_raw" in values

    @property
    def native_value(self) -> float | None:
        key = (
            "output_current_max_raw"
            if self.entity_description.key == "maximum_output_current_control"
            else "solar_current_min_raw"
        )
        value = self.coordinator.data.get(self.serial, {}).get(key)
        return float(value) / 10 if isinstance(value, (int, float)) else None

    async def async_set_native_value(self, value: float) -> None:
        if self.entity_description.key == "maximum_output_current_control":
            await self.coordinator.async_set_maximum_output_current(self.serial, value)
        else:
            await self.coordinator.async_set_solar_minimum_current(self.serial, value)
