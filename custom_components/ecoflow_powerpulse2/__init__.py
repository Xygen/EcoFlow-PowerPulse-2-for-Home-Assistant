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


def _config_entry_only_schema(config: dict[str, Any]) -> dict[str, Any]:
    """Use HA's standard schema while keeping pure protocol imports independent."""
    from homeassistant.helpers import config_validation as cv

    from .const import DOMAIN

    return cv.config_entry_only_config_schema(DOMAIN)(config)


CONFIG_SCHEMA = _config_entry_only_schema


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Register research actions independently of loaded config entries."""
    from .services import async_register_protocol_actions

    async_register_protocol_actions(hass)
    return True


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
    await coordinator.async_load_smart_staging()
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    _enable_new_canonical_sensor_defaults(hass, list(coordinator.devices), DOMAIN)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    coordinator.async_start_stream_diagnostics()
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator: Any = entry.runtime_data
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await coordinator.async_shutdown()
    return unloaded
