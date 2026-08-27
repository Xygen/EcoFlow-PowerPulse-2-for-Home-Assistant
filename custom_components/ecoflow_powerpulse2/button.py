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
        entity
        for serial in coordinator.devices
        for entity in (
            PowerPulse2StartChargingButton(coordinator, serial),
            PowerPulse2StopChargingButton(coordinator, serial),
            PowerPulse2ReactivateDirectStreamButton(coordinator, serial),
            PowerPulse2ReconnectDirectStreamButton(coordinator, serial),
        )
    )


class PowerPulse2StartChargingButton(PowerPulse2Entity, ButtonEntity):
    """Start or resume a connected charging session."""

    _attr_translation_key = "start_charging"
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: PowerPulse2Coordinator, serial: str) -> None:
        super().__init__(coordinator, serial, "start_charging")

    @property
    def available(self) -> bool:
        return self.coordinator.charge_action_available(self.serial, "start")

    async def async_press(self) -> None:
        await self.coordinator.async_start_charging(self.serial)


class PowerPulse2StopChargingButton(PowerPulse2Entity, ButtonEntity):
    """Stop an active or paused charging session."""

    _attr_translation_key = "stop_charging"
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: PowerPulse2Coordinator, serial: str) -> None:
        super().__init__(coordinator, serial, "stop_charging")

    @property
    def available(self) -> bool:
        return self.coordinator.charge_action_available(self.serial, "stop")

    async def async_press(self) -> None:
        await self.coordinator.async_stop_charging(self.serial)


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


class PowerPulse2ReconnectDirectStreamButton(PowerPulse2Entity, ButtonEntity):
    """Rebuild the listen-only C376 WSS client without publishing."""

    _attr_translation_key = "reconnect_direct_data_stream"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: PowerPulse2Coordinator, serial: str) -> None:
        super().__init__(coordinator, serial, "reconnect_direct_data_stream")

    @property
    def available(self) -> bool:
        return self.coordinator.direct_reconnect_available(self.serial)

    @property
    def extra_state_attributes(self) -> dict:
        return self.coordinator.direct_stream_diagnostics(self.serial)

    async def async_press(self) -> None:
        await self.coordinator.async_reconnect_direct_stream(self.serial)
