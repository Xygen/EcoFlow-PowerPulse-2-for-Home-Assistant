"""Diagnostic actions for EcoFlow PowerPulse 2."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
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
        PowerPulse2ReactivateDirectStreamButton(coordinator, serial)
        for serial in coordinator.devices
    )


class PowerPulse2ReactivateDirectStreamButton(PowerPulse2Entity, ButtonEntity):
    """Renew direct MQTT subscriptions without publishing to the device."""

    _attr_translation_key = "reactivate_direct_data_stream"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: PowerPulse2Coordinator, serial: str) -> None:
        super().__init__(coordinator, serial, "reactivate_direct_data_stream")

    @property
    def available(self) -> bool:
        return self.coordinator.direct_stream_available(self.serial)

    @property
    def extra_state_attributes(self) -> dict:
        return self.coordinator.direct_stream_diagnostics(self.serial)

    async def async_press(self) -> None:
        await self.coordinator.async_reactivate_direct_stream(self.serial)
