"""Privacy-safe diagnostics for EcoFlow PowerPulse 2."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_EMAIL, CONF_PASSWORD
from .coordinator import PowerPulse2Coordinator

TO_REDACT = {CONF_EMAIL, CONF_PASSWORD}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    coordinator: PowerPulse2Coordinator = entry.runtime_data
    return {
        "config_entry": async_redact_data(dict(entry.data), TO_REDACT),
        "devices": [
            {
                "serial_prefix": serial[:4],
                "product_type": device.get("product_type", ""),
                "data_keys": sorted(coordinator.data.get(serial, {})),
                "mqtt_connected": bool(
                    coordinator.mqtt_clients.get(serial)
                    and coordinator.mqtt_clients[serial].is_connected()
                ),
                "mqtt_reconnect_attempts": (
                    coordinator.mqtt_clients[serial].reconnect_attempts
                    if serial in coordinator.mqtt_clients
                    else 0
                ),
                "mqtt_subscriptions": (
                    coordinator.mqtt_clients[serial].subscription_results
                    if serial in coordinator.mqtt_clients
                    else {}
                ),
            }
            for serial, device in coordinator.devices.items()
        ],
        "powerocean_observers": [
            {
                "serial_prefix": serial[:4],
                "product_type": device.get("product_type", ""),
                "matched_accessory_data_keys": coordinator.observer_snapshot_keys.get(
                    serial, []
                ),
                "mqtt_connected": bool(
                    coordinator.mqtt_clients.get(serial)
                    and coordinator.mqtt_clients[serial].is_connected()
                ),
                "mqtt_reconnect_attempts": (
                    coordinator.mqtt_clients[serial].reconnect_attempts
                    if serial in coordinator.mqtt_clients
                    else 0
                ),
                "mqtt_subscriptions": (
                    coordinator.mqtt_clients[serial].subscription_results
                    if serial in coordinator.mqtt_clients
                    else {}
                ),
            }
            for serial, device in coordinator.observer_devices.items()
        ],
        "mqtt_mode": "listen_only",
        "mqtt_capture_schema": 11,
        "passive_settings_refresh": coordinator.passive_settings_refresh,
        "phase_readback_sources": coordinator.phase_readback_sources,
        "mqtt_frames": list(coordinator.mqtt_frames),
        "mqtt_command_frames": list(coordinator.mqtt_command_frames),
        "mqtt_request_frames": list(coordinator.mqtt_request_frames),
        "mqtt_command_correlations": coordinator.mqtt_command_correlations,
        "mqtt_frame_buckets": coordinator.mqtt_frame_buckets,
    }
