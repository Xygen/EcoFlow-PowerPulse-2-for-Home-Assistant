"""Sensors for EcoFlow PowerPulse 2."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import SENSORS, PowerPulse2SensorDescription
from .coordinator import PowerPulse2Coordinator
from .entity import PowerPulse2Entity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator: PowerPulse2Coordinator = entry.runtime_data
    async_add_entities(
        PowerPulse2Sensor(coordinator, serial, description)
        for serial in coordinator.devices
        for description in SENSORS
    )


class PowerPulse2Sensor(PowerPulse2Entity, SensorEntity):
    """A telemetry or diagnostic sensor."""

    entity_description: PowerPulse2SensorDescription

    def __init__(
        self,
        coordinator: PowerPulse2Coordinator,
        serial: str,
        description: PowerPulse2SensorDescription,
    ) -> None:
        super().__init__(coordinator, serial, description.key)
        self.entity_description = description
        if description.diagnostic:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and self.entity_description.key in self.coordinator.data.get(
            self.serial, {}
        )

    @property
    def native_value(self):
        value = self.coordinator.data.get(self.serial, {}).get(self.entity_description.key)
        if self.entity_description.value_fn is not None:
            return self.entity_description.value_fn(value)
        return value
