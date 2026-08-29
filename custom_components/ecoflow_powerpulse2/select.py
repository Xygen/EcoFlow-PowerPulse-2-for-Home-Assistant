"""Evidence-gated select controls for EcoFlow PowerPulse 2."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import PowerPulse2Coordinator
from .entity import PowerPulse2Entity

PHASE_OPTIONS = ["auto", "one_phase", "three_phase"]
MODE_OPTIONS = ["fast", "solar", "custom", "smart"]
SMART_TARGET_OPTIONS = ["energy", "distance"]


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
            PowerPulse2PhaseSelect(coordinator, serial),
            PowerPulse2ModeSelect(coordinator, serial),
            PowerPulse2SmartTargetSelect(coordinator, serial),
        )
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


class PowerPulse2ModeSelect(PowerPulse2Entity, SelectEntity):
    """Select one of the four captured operating modes."""

    _attr_translation_key = "work_mode_control"
    _attr_options = MODE_OPTIONS
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: PowerPulse2Coordinator, serial: str) -> None:
        super().__init__(coordinator, serial, "work_mode_control")

    @property
    def available(self) -> bool:
        return self.coordinator.charging_sensitive_control_available(
            self.serial, "work_mode"
        )

    @property
    def current_option(self) -> str | None:
        value = self.coordinator.data.get(self.serial, {}).get("work_mode")
        return value if value in self.options else None

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_set_work_mode(self.serial, option)


class PowerPulse2SmartTargetSelect(PowerPulse2Entity, SelectEntity):
    """Select the active Smart target type."""

    _attr_translation_key = "smart_target_type_control"
    _attr_options = SMART_TARGET_OPTIONS
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: PowerPulse2Coordinator, serial: str) -> None:
        super().__init__(coordinator, serial, "smart_target_type_control")

    @property
    def available(self) -> bool:
        values = self.coordinator.data.get(self.serial, {})
        return (
            self.coordinator.settings_control_available(self.serial)
            and values.get("work_mode") == "smart"
            and self.coordinator.smart_target_type_control_available(self.serial)
            and self.coordinator.charging_sensitive_control_available(
                self.serial, "smart_target_type"
            )
        )

    @property
    def current_option(self) -> str | None:
        value = self.coordinator.data.get(self.serial, {}).get("smart_target_type")
        return value if value in self.options else None

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_set_smart_target_type(self.serial, option)
