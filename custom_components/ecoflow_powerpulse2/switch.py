"""Evidence-gated switch controls for EcoFlow PowerPulse 2."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
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
        PowerPulse2SettingsSwitch(coordinator, serial, description)
        for serial in coordinator.devices
        for description in (
            SwitchEntityDescription(
                key="battery_discharge_control",
                translation_key="battery_discharge_control",
            ),
            SwitchEntityDescription(
                key="continuous_charging_control",
                translation_key="continuous_charging_control",
            ),
        )
    )


class PowerPulse2SettingsSwitch(PowerPulse2Entity, SwitchEntity):
    """One disabled-by-default, acknowledged settings switch."""

    _attr_entity_registry_enabled_default = False

    def __init__(
        self,
        coordinator: PowerPulse2Coordinator,
        serial: str,
        description: SwitchEntityDescription,
    ) -> None:
        super().__init__(coordinator, serial, description.key)
        self.entity_description = description

    @property
    def available(self) -> bool:
        if not self.coordinator.phase_control_available(self.serial):
            return False
        values = self.coordinator.data.get(self.serial, {})
        if self.entity_description.key == "continuous_charging_control":
            return values.get("work_mode") == "solar"
        return "battery_discharge_disabled" in values

    @property
    def is_on(self) -> bool | None:
        key = (
            "battery_discharge_disabled"
            if self.entity_description.key == "battery_discharge_control"
            else "continuous_charging"
        )
        value = self.coordinator.data.get(self.serial, {}).get(key)
        return value if isinstance(value, bool) else None

    async def async_turn_on(self, **kwargs) -> None:
        await self._async_set(True)

    async def async_turn_off(self, **kwargs) -> None:
        await self._async_set(False)

    async def _async_set(self, enabled: bool) -> None:
        setter: Callable[[str, bool], Awaitable[None]] = (
            self.coordinator.async_set_battery_discharge_disabled
            if self.entity_description.key == "battery_discharge_control"
            else self.coordinator.async_set_continuous_charging
        )
        await setter(self.serial, enabled)
