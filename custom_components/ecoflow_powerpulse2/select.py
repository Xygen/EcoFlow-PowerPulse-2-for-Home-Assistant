"""Explicitly enabled experimental controls for EcoFlow PowerPulse 2."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import PowerPulse2Coordinator
from .entity import PowerPulse2Entity

PHASE_OPTIONS = ["auto", "one_phase", "three_phase"]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator: PowerPulse2Coordinator = entry.runtime_data
    async_add_entities(
        PowerPulse2PhaseSelect(coordinator, serial) for serial in coordinator.devices
    )


class PowerPulse2PhaseSelect(PowerPulse2Entity, SelectEntity):
    """Evidence-gated phase selection routed through PowerOcean."""

    _attr_translation_key = "phase_control"
    _attr_options = PHASE_OPTIONS
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: PowerPulse2Coordinator, serial: str) -> None:
        super().__init__(coordinator, serial, "phase_control")

    @property
    def available(self) -> bool:
        return (
            self.coordinator.last_update_success
            and self.coordinator.phase_control_available(self.serial)
        )

    @property
    def current_option(self) -> str | None:
        value = self.coordinator.data.get(self.serial, {}).get("phase_mode")
        return value if value in self.options else None

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_set_phase_mode(self.serial, option)
