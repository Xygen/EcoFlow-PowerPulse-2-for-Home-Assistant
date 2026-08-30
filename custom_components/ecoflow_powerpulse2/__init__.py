"""EcoFlow PowerPulse 2 integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

PLATFORMS = [
    "binary_sensor",
    "button",
    "datetime",
    "number",
    "select",
    "sensor",
    "switch",
]
_CANONICAL_SENSOR_DEFAULTS = ("smart_charge_target_wh",)


def _enable_new_canonical_sensor_defaults(
    hass: HomeAssistant, serials: list[str], domain: str
) -> None:
    """Enable entities that changed from diagnostic to canonical defaults."""
    from homeassistant.helpers import entity_registry as er

    registry = er.async_get(hass)
    for serial in serials:
        for key in _CANONICAL_SENSOR_DEFAULTS:
            entity_id = registry.async_get_entity_id("sensor", domain, f"{serial}_{key}")
            if entity_id is None:
                continue
            entity_entry = registry.async_get(entity_id)
            if (
                entity_entry is not None
                and entity_entry.disabled_by == er.RegistryEntryDisabler.INTEGRATION
            ):
                registry.async_update_entity(entity_id, disabled_by=None)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    from .const import DOMAIN
    from .coordinator import PowerPulse2Coordinator

    coordinator = PowerPulse2Coordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    _enable_new_canonical_sensor_defaults(hass, list(coordinator.devices), DOMAIN)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator: Any = entry.runtime_data
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await coordinator.async_shutdown()
    return unloaded
