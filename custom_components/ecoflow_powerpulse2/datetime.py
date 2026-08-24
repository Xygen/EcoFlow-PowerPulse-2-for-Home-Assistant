"""Evidence-gated Smart ready-by control for EcoFlow PowerPulse 2."""

from __future__ import annotations

from datetime import UTC, datetime

from homeassistant.components.datetime import DateTimeEntity
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
    async_add_entities(
        PowerPulse2ReadyByDateTime(coordinator, serial)
        for serial in coordinator.devices
    )


class PowerPulse2ReadyByDateTime(PowerPulse2Entity, DateTimeEntity):
    """Set the complete Smart ready-by date and time."""

    _attr_translation_key = "smart_ready_by_control"
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: PowerPulse2Coordinator, serial: str) -> None:
        super().__init__(coordinator, serial, "smart_ready_by_control")

    @property
    def available(self) -> bool:
        values = self.coordinator.data.get(self.serial, {})
        return (
            self.coordinator.phase_control_available(self.serial)
            and values.get("work_mode") == "smart"
            and isinstance(values.get("ready_by_timestamp"), int)
        )

    @property
    def native_value(self) -> datetime | None:
        value = self.coordinator.data.get(self.serial, {}).get("ready_by_timestamp")
        return datetime.fromtimestamp(value, UTC) if isinstance(value, int) else None

    async def async_set_value(self, value: datetime) -> None:
        if value.tzinfo is None:
            raise ValueError("Smart ready-by time must include a timezone")
        await self.coordinator.async_set_smart_ready_by(self.serial, int(value.timestamp()))
