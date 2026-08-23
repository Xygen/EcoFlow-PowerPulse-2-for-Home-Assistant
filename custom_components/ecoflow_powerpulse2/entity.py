"""Base entity for EcoFlow PowerPulse 2."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PowerPulse2Coordinator


class PowerPulse2Entity(CoordinatorEntity[PowerPulse2Coordinator]):
    """Entity bound to one charger serial."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: PowerPulse2Coordinator, serial: str, key: str) -> None:
        super().__init__(coordinator)
        self.serial = serial
        self._attr_unique_id = f"{serial}_{key}"
        device = coordinator.devices[serial]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, serial)},
            manufacturer="EcoFlow",
            name=device.get("name") or "EcoFlow PowerPulse 2",
            model="PowerPulse 2",
            serial_number=serial,
        )
