"""Charging binary sensor for EcoFlow PowerPulse 2."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
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
    async_add_entities(PowerPulse2ChargingSensor(coordinator, serial) for serial in coordinator.devices)


class PowerPulse2ChargingSensor(PowerPulse2Entity, BinarySensorEntity):
    """Whether the charger reports an active charging session."""

    _attr_translation_key = "charging"
    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(self, coordinator: PowerPulse2Coordinator, serial: str) -> None:
        super().__init__(coordinator, serial, "charging")

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and "charging_status" in self.coordinator.data.get(
            self.serial, {}
        )

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.get(self.serial, {}).get("charging_status") == "charging"
