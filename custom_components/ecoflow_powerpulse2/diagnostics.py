"""Privacy-safe diagnostics for EcoFlow PowerPulse 2."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_EMAIL, CONF_PASSWORD
from .coordinator import PowerPulse2Coordinator
from .diagnostic_support import (
    app_writes_watched,
    sanitize_diagnostics_export,
    stream_health,
)

TO_REDACT = {CONF_EMAIL, CONF_PASSWORD}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    coordinator: PowerPulse2Coordinator = entry.runtime_data
    passive_refresh = coordinator.passive_settings_refresh
    direct_policy = passive_refresh["direct_stream"]
    heartbeat_policy = passive_refresh["heartbeat_stream"]

    def source(serial: str, role: str) -> dict[str, Any]:
        client = coordinator.mqtt_clients.get(serial)
        connected = bool(client and client.is_connected())
        subscriptions = client.subscription_results if client else {}
        result: dict[str, Any] = {
            "device_prefix": serial[:4],
            "source_role": role,
            "connected": connected,
            "subscriptions": subscriptions,
            "app_writes_watched": app_writes_watched(
                connected, subscriptions
            ),
        }
        if role == "powerpulse":
            direct = coordinator.direct_stream_diagnostics(serial)
            heartbeat = coordinator.heartbeat_stream_diagnostics(serial)
            result["direct_settings_stream"] = stream_health(
                connected=connected,
                last_report=direct["last_direct_report"],
                fresh_seconds=direct_policy["fresh_seconds"],
            )
            result["heartbeat_stream"] = stream_health(
                connected=connected,
                last_report=heartbeat["last_heartbeat_report"],
                fresh_seconds=heartbeat_policy["fresh_seconds"],
            )
        return result

    mqtt_sources = [
        *(source(serial, "powerpulse") for serial in coordinator.devices),
        *(
            source(serial, "powerocean_observer")
            for serial in coordinator.observer_devices
        ),
    ]
    export = {
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
        "mqtt_capture_schema": 12,
        "mqtt_capture": {
            "schema": 12,
            "policy": coordinator.mqtt_capture_policy,
            "limits": coordinator.mqtt_capture_limits,
            "statistics": coordinator.mqtt_capture_statistics,
            "sources": mqtt_sources,
            "samples": {
                "recent": list(coordinator.mqtt_frames),
                "per_type": coordinator.mqtt_frame_buckets,
                "commands": list(coordinator.mqtt_command_frames),
                "requests": list(coordinator.mqtt_request_frames),
                "correlations": coordinator.mqtt_command_correlations,
            },
            "unmapped_fields": coordinator.mqtt_unmapped_fields,
        },
        "passive_settings_refresh": passive_refresh,
        "phase_readback_sources": coordinator.phase_readback_sources,
        "mqtt_frames": list(coordinator.mqtt_frames),
        "mqtt_command_frames": list(coordinator.mqtt_command_frames),
        "mqtt_request_frames": list(coordinator.mqtt_request_frames),
        "mqtt_command_correlations": coordinator.mqtt_command_correlations,
        "mqtt_frame_buckets": coordinator.mqtt_frame_buckets,
    }
    identifiers = {
        *coordinator.devices,
        *coordinator.observer_devices,
        *(
            client.user_id
            for client in coordinator.mqtt_clients.values()
            if client.user_id
        ),
        str(entry.data.get(CONF_EMAIL, "")),
    }
    return sanitize_diagnostics_export(export, identifiers=identifiers)
