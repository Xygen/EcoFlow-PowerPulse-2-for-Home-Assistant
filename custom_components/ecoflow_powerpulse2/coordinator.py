"""Read-only PowerPulse 2 cloud coordinator."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import PowerPulse2ApiClient
from .const import CONF_EMAIL, CONF_PASSWORD, DOMAIN, UPDATE_INTERVAL_SECONDS
from .data_merge import merge_snapshot_after_read
from .ecoflow.cloud_mqtt import EcoFlowMQTTClient
from .frame_capture import (
    COMMAND_CHANNELS,
    DiagnosticFrameCapture,
    channel_carries_telemetry,
    classify_mqtt_topic,
    inspect_envelope_headers,
    inspect_observer_command_payloads,
    inspect_powerpulse_accessory_reports,
)
from .parser import parse_powerpulse2_payload

_LOGGER = logging.getLogger(__name__)
_MAX_FRAME_BYTES = 2048


class PowerPulse2Coordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Discover devices, poll snapshots, and merge listen-only MQTT pushes."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL_SECONDS),
        )
        self.api = PowerPulse2ApiClient(
            async_get_clientsession(hass),
            entry.data[CONF_EMAIL],
            entry.data[CONF_PASSWORD],
        )
        self.devices: dict[str, dict[str, str]] = {}
        self.observer_devices: dict[str, dict[str, str]] = {}
        self.observer_snapshot_keys: dict[str, list[str]] = {}
        self.mqtt_clients: dict[str, EcoFlowMQTTClient] = {}
        self._frame_capture = DiagnosticFrameCapture()
        self._initialized = False

    @property
    def mqtt_frames(self) -> list[dict[str, Any]]:
        """Return the bounded all-frame diagnostic view."""
        return self._frame_capture.recent

    @property
    def mqtt_command_frames(self) -> list[dict[str, Any]]:
        """Return official-app SET and SET-reply diagnostic frames."""
        return self._frame_capture.commands

    @property
    def mqtt_frame_buckets(self) -> dict[str, dict[str, Any]]:
        """Return frames grouped by channel and protocol command tuple."""
        return self._frame_capture.bucket_snapshot()

    @property
    def mqtt_command_correlations(self) -> list[dict[str, Any]]:
        """Return passive command requests and replies grouped by sequence."""
        return self._frame_capture.command_correlations

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        try:
            if not self._initialized:
                await self.api.async_login()
                self.devices = await self.api.async_discover()
                self.observer_devices = self.api.mqtt_observers
                if not self.devices:
                    raise UpdateFailed("No EcoFlow PowerPulse device found")
                try:
                    await self._async_setup_mqtt()
                except Exception as exc:
                    # HTTP snapshots can still provide useful read-only data;
                    # the coordinator watchdog retries MQTT independently.
                    _LOGGER.warning("PowerPulse MQTT diagnostics unavailable: %s", exc)
                self._initialized = True
            else:
                await self._async_maintain_mqtt()

            provider_updates = await self._async_read_parent_accessories()
            result: dict[str, dict[str, Any]] = {}
            for serial, device in self.devices.items():
                result[serial] = await merge_snapshot_after_read(
                    lambda device=device, provider=provider_updates.get(serial, {}): (
                        self._async_read_combined_snapshot(device, provider)
                    ),
                    lambda serial=serial: (self.data or {}).get(serial),
                )
            return result
        except UpdateFailed:
            raise
        except Exception as exc:
            raise UpdateFailed(f"EcoFlow PowerPulse 2 update failed: {exc}") from exc

    async def _async_read_parent_accessories(self) -> dict[str, dict[str, Any]]:
        """Read embedded wallbox snapshots once per discovered PowerOcean."""
        updates: dict[str, dict[str, Any]] = {}
        snapshot_keys: dict[str, list[str]] = {}
        for source_serial, device in self.observer_devices.items():
            reports = await self.api.async_read_accessories(device)
            matched_keys: set[str] = set()
            for target_serial, values in reports.items():
                if target_serial not in self.devices:
                    continue
                updates.setdefault(target_serial, {}).update(values)
                matched_keys.update(values)
            snapshot_keys[source_serial] = sorted(matched_keys)
        self.observer_snapshot_keys = snapshot_keys
        return updates

    async def _async_read_combined_snapshot(
        self,
        device: dict[str, str],
        provider: dict[str, Any],
    ) -> dict[str, Any]:
        """Combine direct and already-fetched parent data before race-safe merge."""
        snapshot = await self.api.async_read(device)
        snapshot.update(provider)
        return snapshot

    async def _async_setup_mqtt(self) -> None:
        """Connect hard listen-only WSS clients for chargers and parent sources."""
        credentials = await self.api.async_get_mqtt_credentials()
        account = credentials.get("certificateAccount") or credentials.get("userName", "")
        password = credentials.get("certificatePassword") or credentials.get("password", "")
        if not account or not password:
            raise ConnectionError("Incomplete MQTT credentials")

        for serial in self._mqtt_sources:
            if serial in self.mqtt_clients:
                continue
            client = EcoFlowMQTTClient(
                certificate_account=account,
                certificate_password=password,
                device_sn=serial,
                message_handler=lambda topic, payload, sn=serial: self._schedule_mqtt_frame(sn, topic, payload),
                user_id=self.api.user_id,
                wss_mode=True,
                enhanced_mode=True,
                subscribe_data=True,
                listen_only=True,
            )
            created = await self.hass.async_add_executor_job(client.create_client)
            if not created:
                continue
            self.mqtt_clients[serial] = client
            connected = await self.hass.async_add_executor_job(client.connect)
            if not connected:
                _LOGGER.debug("PowerPulse MQTT listen-only connection failed for %s…", serial[:4])
                continue
            await self.hass.async_add_executor_job(client.start_loop)

    async def _async_maintain_mqtt(self) -> None:
        """Retry missing or disconnected listen-only MQTT clients."""
        if any(serial not in self.mqtt_clients for serial in self._mqtt_sources):
            try:
                await self._async_setup_mqtt()
            except Exception as exc:
                _LOGGER.debug("PowerPulse MQTT setup retry failed: %s", exc)

        for serial, client in list(self.mqtt_clients.items()):
            if client.is_connected():
                continue
            attempted = await self.hass.async_add_executor_job(client.try_reconnect)
            if attempted:
                _LOGGER.debug("PowerPulse MQTT reconnect started for %s…", serial[:4])

    def _schedule_mqtt_frame(self, serial: str, topic: str, payload: bytes) -> None:
        loop = self.hass.loop
        if loop.is_closed():
            return
        try:
            loop.call_soon_threadsafe(self._record_mqtt_frame, serial, topic, payload)
        except RuntimeError:
            return

    def _record_mqtt_frame(self, serial: str, topic: str, payload: bytes) -> None:
        channel = classify_mqtt_topic(topic)
        client = self.mqtt_clients.get(serial)
        parsed = (
            parse_powerpulse2_payload(payload)
            if serial in self.devices and channel_carries_telemetry(channel)
            else {}
        )
        if parsed:
            updated = dict(self.data or {})
            values = dict(updated.get(serial, {}))
            values.update(parsed)
            updated[serial] = values
            self.async_set_updated_data(updated)

        is_observer = serial in self.observer_devices
        accessory_reports = (
            inspect_powerpulse_accessory_reports(payload) if is_observer else []
        )
        command_payloads = (
            inspect_observer_command_payloads(payload)
            if is_observer and channel in COMMAND_CHANNELS
            else []
        )
        frame = {
            "timestamp": datetime.now(UTC).isoformat(),
            "device_prefix": serial[:4],
            "source_role": "powerocean_observer" if is_observer else "powerpulse",
            "channel": channel,
            "topic_pattern": (
                client.diagnostic_topic(topic) if client is not None else "unknown"
            ),
            "size": len(payload),
            "parsed_keys": sorted(parsed),
            "protocol_headers": inspect_envelope_headers(payload),
            "powerpulse_accessory_reports": accessory_reports,
            "observer_command_payloads": command_payloads,
            "truncated": len(payload) > _MAX_FRAME_BYTES,
            # A PowerOcean frame can bundle accessory, battery and vehicle
            # identifiers unknown to this integration. Keep only the safe
            # numeric summary above rather than exporting the parent payload.
            "redacted_hex": (
                "" if is_observer else self._redact(payload[:_MAX_FRAME_BYTES]).hex()
            ),
            "payload_omitted": is_observer,
        }
        self._frame_capture.record(frame)

    @property
    def _mqtt_sources(self) -> dict[str, dict[str, str]]:
        """Return all device serials whose topics are observed passively."""
        return {**self.devices, **self.observer_devices}

    def _redact(self, payload: bytes) -> bytes:
        redacted = payload
        for secret in (*self._mqtt_sources, self.api.user_id):
            encoded = secret.encode("ascii", errors="ignore")
            if encoded:
                redacted = redacted.replace(encoded, b"X" * len(encoded))
        return redacted

    async def async_shutdown(self) -> None:
        for client in self.mqtt_clients.values():
            await self.hass.async_add_executor_job(client.disconnect)
        self.mqtt_clients.clear()
