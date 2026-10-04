"""Globally registered, explicitly confirmed protocol-research actions."""

from __future__ import annotations

from functools import partial
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN

ACTIONS = (
    "protocol_test_solar_minimum_field_only",
    "protocol_test_custom_current_field_only",
    "protocol_test_phase_while_charging",
    "protocol_test_continuous_field_only",
)


def _strict_bool(value: Any) -> bool:
    if type(value) is not bool:
        raise vol.Invalid("Expected a boolean")
    return value


def _current(value: Any) -> int:
    if type(value) not in (int, float) or not 6 <= value <= 16 or not float(value).is_integer():
        raise vol.Invalid("Current must be a whole number from 6 to 16 A")
    return int(value)


def _resolve_device(hass: HomeAssistant, device_id: str) -> tuple[Any, str]:
    device = dr.async_get(hass).async_get(device_id)
    if device is None:
        raise ServiceValidationError("Unknown PowerPulse device")
    serials = {serial for domain, serial in device.identifiers if domain == DOMAIN}
    if len(serials) != 1:
        raise ServiceValidationError("Device must identify exactly one PowerPulse 2")
    serial = next(iter(serials))
    entries = [entry for entry in hass.config_entries.async_entries(DOMAIN)
               if entry.entry_id in device.config_entries]
    if len(entries) != 1:
        raise ServiceValidationError("PowerPulse config-entry mapping is missing or ambiguous")
    entry = entries[0]
    coordinator = getattr(entry, "runtime_data", None)
    if entry.state is not ConfigEntryState.LOADED or coordinator is None:
        raise ServiceValidationError("PowerPulse config entry is not loaded")
    if serial not in coordinator.devices:
        raise ServiceValidationError("Device is not a PowerPulse device in the loaded coordinator")
    # Also refuse duplicate loaded ownership, including stale registry associations.
    owners = [item for item in hass.config_entries.async_entries(DOMAIN)
              if item.state is ConfigEntryState.LOADED and getattr(item, "runtime_data", None) is not None
              and serial in item.runtime_data.devices]
    if len(owners) != 1:
        raise ServiceValidationError("PowerPulse coordinator mapping is ambiguous")
    return coordinator, serial


async def _async_handle(hass: HomeAssistant, action: str, call: ServiceCall) -> dict[str, Any]:
    if call.data.get("confirm_protocol_test") is not True:
        raise ServiceValidationError("Protocol test requires confirm_protocol_test=true")
    coordinator, serial = _resolve_device(hass, call.data["device_id"])
    parameters = {key: value for key, value in call.data.items() if key != "device_id"}
    return await getattr(coordinator, f"async_{action}")(serial, **parameters)


@callback
def async_register_protocol_actions(hass: HomeAssistant) -> None:
    """Keep actions available even when no config entry is loaded."""
    for action in ACTIONS:
        fields = {
            vol.Required("device_id"): str,
            vol.Optional("confirm_protocol_test"): _strict_bool,
        }
        if action == ACTIONS[2]:
            fields[vol.Required("phase")] = vol.In(("auto", "one_phase", "three_phase"))
        elif action == ACTIONS[3]:
            fields[vol.Required("enabled")] = _strict_bool
        else:
            fields[vol.Required("current")] = _current
            fields[vol.Required("expected_work_mode")] = vol.In(("solar", "fast"))
            if action == ACTIONS[0]:
                fields[vol.Optional("expected_continuous_charging")] = _strict_bool
        hass.services.async_register(
            DOMAIN, action, partial(_async_handle, hass, action),
            schema=vol.Schema(fields), supports_response=SupportsResponse.OPTIONAL,
        )
