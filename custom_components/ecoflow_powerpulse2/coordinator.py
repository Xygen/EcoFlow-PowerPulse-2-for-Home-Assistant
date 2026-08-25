"""PowerPulse 2 cloud coordinator with evidence-gated user controls."""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from datetime import UTC, datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import PowerPulse2ApiClient
from .const import (
    CONF_EMAIL,
    CONF_PASSWORD,
    DOMAIN,
    SETTINGS_REFRESH_DELAY_SECONDS,
    UPDATE_INTERVAL_SECONDS,
)
from .control_readback import (
    fresh_direct_value_available,
    fresh_polled_value_matches,
    matching_readback_source,
    provider_readback_attempt_details,
)
from .data_merge import merge_snapshot_after_read
from .ecoflow.cloud_mqtt import EcoFlowMQTTClient
from .ecoflow.energy_stream import (
    build_powerpulse_settings_payload,
    build_powerpulse_smart_settings,
)
from .frame_capture import (
    COMMAND_CHANNELS,
    DiagnosticFrameCapture,
    channel_carries_telemetry,
    classify_mqtt_topic,
    inspect_envelope_headers,
    inspect_get_request,
    inspect_powerpulse_accessory_reports,
)
from .parser import extract_powerpulse_accessory_descriptor, parse_powerpulse2_payload
from .passive_refresh import ConfirmedSettingsReplyGate, DelayedRefreshCoalescer

_LOGGER = logging.getLogger(__name__)
_MAX_FRAME_BYTES = 2048
_DIRECT_SETTINGS_FRESH_SECONDS = 10
_CONTROL_DIRECT_WAIT_SECONDS = 2
_CONTROL_PROVIDER_RETRY_DELAYS = (0, 3, 5, 5, 5)
_CONTROL_NOOP_FRESH_SECONDS = UPDATE_INTERVAL_SECONDS * 2
_CONTROL_DIAGNOSTIC_ATTEMPTS = 32
_DIRECT_STREAM_CONFIRM_SECONDS = 10
_DIRECT_STREAM_DIAGNOSTIC_ATTEMPTS = 16
_DIRECT_SETTINGS_KEYS = frozenset(
    {
        "continuous_charging",
        "battery_discharge_disabled",
        "current_limit_raw",
        "output_current_max_raw",
        "phase_specified_raw",
        "phase_mode",
        "plug_and_play",
        "solar_current_min_raw",
        "switch_bits_raw",
        "user_current_set_raw",
        "smart_calculated_energy_wh",
        "smart_charge_target_wh",
        "smart_target_distance_km",
        "smart_target_type",
        "ready_by_timestamp",
        "work_mode",
    }
)


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
        self._settings_reply_gate = ConfirmedSettingsReplyGate()
        self._settings_refresh = DelayedRefreshCoalescer(
            self._async_refresh_after_settings_reply,
            delay_seconds=SETTINGS_REFRESH_DELAY_SECONDS,
        )
        self._settings_reply_count = 0
        self._settings_refresh_count = 0
        self._last_settings_reply_at: str | None = None
        self._last_settings_refresh_at: str | None = None
        self._last_direct_settings_at: dict[str, float] = {}
        self._last_direct_settings_utc: dict[str, str] = {}
        self._last_polled_settings_at: dict[str, float] = {}
        self._last_polled_settings: dict[str, dict[str, Any]] = {}
        self._control_readback_counts = {"direct": 0, "provider": 0, "noop": 0}
        self._last_control_readback_source: str | None = None
        self._last_control_readback_at: str | None = None
        self._control_provider_attempts: deque[dict[str, Any]] = deque(
            maxlen=_CONTROL_DIAGNOSTIC_ATTEMPTS
        )
        self._direct_stream_attempts: deque[dict[str, Any]] = deque(
            maxlen=_DIRECT_STREAM_DIAGNOSTIC_ATTEMPTS
        )
        self._accessory_descriptors: dict[str, bytes] = {}
        self._reply_waiters: dict[tuple[str, int], asyncio.Future[None]] = {}
        self._control_lock = asyncio.Lock()
        self._direct_stream_lock = asyncio.Lock()
        self._last_smart_settings: dict[str, dict[str, Any]] = {}
        self._shutting_down = False
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
    def mqtt_request_frames(self) -> list[dict[str, Any]]:
        """Return official-app GET request diagnostic frames."""
        return self._frame_capture.requests

    @property
    def mqtt_frame_buckets(self) -> dict[str, dict[str, Any]]:
        """Return frames grouped by channel and protocol command tuple."""
        return self._frame_capture.bucket_snapshot()

    @property
    def mqtt_command_correlations(self) -> list[dict[str, Any]]:
        """Return passive command requests and replies grouped by sequence."""
        return self._frame_capture.command_correlations

    @property
    def passive_settings_refresh(self) -> dict[str, Any]:
        """Return identifier-free diagnostics for app-triggered provider reads."""
        return {
            "delay_seconds": SETTINGS_REFRESH_DELAY_SECONDS,
            "confirmed_reply_count": self._settings_reply_count,
            "completed_refresh_count": self._settings_refresh_count,
            "active": self._settings_refresh.active,
            "pending": self._settings_refresh.pending,
            "last_confirmed_reply_at": self._last_settings_reply_at,
            "last_completed_refresh_at": self._last_settings_refresh_at,
            "control_readback_counts": dict(self._control_readback_counts),
            "last_control_readback_source": self._last_control_readback_source,
            "last_control_readback_at": self._last_control_readback_at,
            "recent_provider_attempts": list(self._control_provider_attempts),
            "direct_stream": {
                "fresh_seconds": _DIRECT_SETTINGS_FRESH_SECONDS,
                "confirmation_timeout_seconds": _DIRECT_STREAM_CONFIRM_SECONDS,
                "last_reports": [
                    {
                        "device_prefix": serial[:4],
                        "timestamp": timestamp,
                    }
                    for serial, timestamp in self._last_direct_settings_utc.items()
                ],
                "recent_reactivation_attempts": list(self._direct_stream_attempts),
            },
        }

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
                        self._async_read_combined_snapshot(serial, device, provider)
                    ),
                    lambda serial=serial: (self.data or {}).get(serial),
                    lambda serial=serial: self._preferred_live_settings(serial),
                )
                self._remember_smart_settings(serial, result[serial])
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
        serial: str,
        device: dict[str, str],
        provider: dict[str, Any],
    ) -> dict[str, Any]:
        """Combine direct and already-fetched parent data before race-safe merge."""
        snapshot = await self.api.async_read(device)
        snapshot.update(provider)
        self._last_polled_settings[serial] = dict(snapshot)
        self._last_polled_settings_at[serial] = time.monotonic()
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
        protocol_headers = inspect_envelope_headers(payload)
        if serial in self.devices:
            descriptor = extract_powerpulse_accessory_descriptor(payload)
            if descriptor is not None:
                self._accessory_descriptors[serial] = descriptor
        parsed = (
            parse_powerpulse2_payload(payload)
            if serial in self.devices and channel_carries_telemetry(channel)
            else {}
        )
        if parsed and any(
            header.get("cmd_func") == 241 and header.get("cmd_id") == 44
            for header in protocol_headers
        ):
            self._last_direct_settings_at[serial] = time.monotonic()
            self._last_direct_settings_utc[serial] = datetime.now(UTC).isoformat()
        if parsed:
            self._remember_smart_settings(serial, parsed)
            updated = dict(self.data or {})
            values = dict(updated.get(serial, {}))
            if parsed.get("work_mode") != "smart":
                for key in (
                    "ready_by_timestamp",
                    "smart_calculated_energy_wh",
                    "smart_charge_target_wh",
                    "smart_target_distance_km",
                    "smart_target_type",
                ):
                    values.pop(key, None)
            elif parsed.get("smart_target_type") == "energy":
                values.pop("smart_target_distance_km", None)
                values.pop("smart_calculated_energy_wh", None)
            elif parsed.get("smart_target_type") == "distance":
                values.pop("smart_charge_target_wh", None)
            values.update(parsed)
            updated[serial] = values
            self.async_set_updated_data(updated)

        is_observer = serial in self.observer_devices
        accessory_reports = (
            inspect_powerpulse_accessory_reports(payload) if is_observer else []
        )
        command_payloads = (
            self._frame_capture.inspect_observer_command_payloads(payload)
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
            "protocol_headers": protocol_headers,
            "powerpulse_accessory_reports": accessory_reports,
            "observer_command_payloads": command_payloads,
            "get_request": (
                inspect_get_request(payload) if channel == "observed_get" else {}
            ),
            "truncated": len(payload) > _MAX_FRAME_BYTES,
            # A PowerOcean frame can bundle accessory, battery and vehicle
            # identifiers unknown to this integration. Keep only the safe
            # numeric summary above rather than exporting the parent payload.
            "redacted_hex": (
                ""
                if is_observer or channel == "observed_get"
                else self._redact(payload[:_MAX_FRAME_BYTES]).hex()
            ),
            "payload_omitted": is_observer or channel == "observed_get",
        }
        self._frame_capture.record(frame)
        own_settings_reply = False
        if channel == "set_reply":
            for header in protocol_headers:
                if (header.get("cmd_func"), header.get("cmd_id")) != (241, 102):
                    continue
                sequence = header.get("sequence")
                if isinstance(sequence, int):
                    waiter = self._reply_waiters.pop((serial, sequence), None)
                    if waiter is not None and not waiter.done():
                        own_settings_reply = True
                        waiter.set_result(None)
        if not self._shutting_down and self._settings_reply_gate.observe(frame):
            self._settings_reply_count += 1
            self._last_settings_reply_at = frame["timestamp"]
            if not own_settings_reply:
                self._settings_refresh.request()

    def _preferred_live_settings(self, serial: str) -> frozenset[str]:
        """Prefer a recent direct device report over a cached provider poll."""
        reported_at = self._last_direct_settings_at.get(serial)
        if reported_at is None:
            return frozenset()
        if time.monotonic() - reported_at > _DIRECT_SETTINGS_FRESH_SECONDS:
            return frozenset()
        return _DIRECT_SETTINGS_KEYS

    async def _async_refresh_after_settings_reply(self) -> None:
        """Refresh provider state after a confirmed official-app settings reply."""
        try:
            await self.async_request_refresh()
        except Exception as exc:
            _LOGGER.debug("Provider refresh after settings reply failed: %s", exc)
            return
        self._settings_refresh_count += 1
        self._last_settings_refresh_at = datetime.now(UTC).isoformat()

    def settings_control_available(self, serial: str) -> bool:
        """Return whether the captured settings transport can be used."""
        if serial not in self._accessory_descriptors or len(self.observer_devices) != 1:
            return False
        observer_serial = next(iter(self.observer_devices))
        client = self.mqtt_clients.get(observer_serial)
        return client is not None and client.is_connected()

    def direct_stream_active(self, serial: str) -> bool:
        """Return whether the direct settings stream reported recently."""
        reported_at = self._last_direct_settings_at.get(serial)
        return bool(
            reported_at is not None
            and time.monotonic() - reported_at <= _DIRECT_SETTINGS_FRESH_SECONDS
        )

    def direct_stream_available(self, serial: str) -> bool:
        """Return whether a direct MQTT client can renew its subscriptions."""
        client = self.mqtt_clients.get(serial)
        return serial in self.devices and client is not None and client.is_connected()

    def direct_stream_diagnostics(self, serial: str) -> dict[str, Any]:
        """Return safe per-device stream state for diagnostic entities."""
        latest = next(
            (
                dict(attempt)
                for attempt in reversed(self._direct_stream_attempts)
                if attempt.get("device_prefix") == serial[:4]
            ),
            None,
        )
        return {
            "last_direct_report": self._last_direct_settings_utc.get(serial),
            "last_reactivation": latest,
        }

    async def async_reactivate_direct_stream(self, serial: str) -> None:
        """Renew C376 data subscriptions and observe whether reports resume."""
        if serial not in self.devices:
            raise HomeAssistantError("Unknown PowerPulse device")
        client = self.mqtt_clients.get(serial)
        if client is None or not client.is_connected():
            raise HomeAssistantError("Direct PowerPulse MQTT is not connected")

        async with self._direct_stream_lock:
            requested_at = time.monotonic()
            attempt: dict[str, Any] = {
                "timestamp": datetime.now(UTC).isoformat(),
                "device_prefix": serial[:4],
                "direct_was_fresh": self.direct_stream_active(serial),
            }
            if attempt["direct_was_fresh"]:
                attempt["status"] = "already_active"
                self._direct_stream_attempts.append(attempt)
                self.async_update_listeners()
                return

            results = await self.hass.async_add_executor_job(
                client.resubscribe_data_topics
            )
            attempt["subscription_results"] = results
            if not results or any(result != 0 for result in results.values()):
                attempt["status"] = "subscription_failed"
                self._direct_stream_attempts.append(attempt)
                self.async_update_listeners()
                raise HomeAssistantError("Direct MQTT subscription renewal failed")

            deadline = requested_at + _DIRECT_STREAM_CONFIRM_SECONDS
            while time.monotonic() < deadline:
                reported_at = self._last_direct_settings_at.get(serial, 0)
                if reported_at > requested_at:
                    attempt["status"] = "confirmed"
                    attempt["seconds_to_direct_report"] = round(
                        reported_at - requested_at, 3
                    )
                    break
                await asyncio.sleep(0.25)
            else:
                attempt["status"] = "no_direct_report"

            self._direct_stream_attempts.append(attempt)
            self.async_update_listeners()

    def phase_control_available(self, serial: str) -> bool:
        """Return whether phase control also has a confirmable direct readback."""
        return self.settings_control_available(serial) and fresh_direct_value_available(
            current_values=(self.data or {}).get(serial, {}),
            direct_reported_at=self._last_direct_settings_at.get(serial, 0),
            now=time.monotonic(),
            max_age=_DIRECT_SETTINGS_FRESH_SECONDS,
            key="phase_mode",
            allowed_values={"auto", "one_phase", "three_phase"},
        )

    async def async_set_phase_mode(self, serial: str, option: str) -> None:
        """Send a user-requested phase SET and require reply plus device readback."""
        phase_values = {"auto": 0, "one_phase": 1, "three_phase": 2}
        if option not in phase_values:
            raise HomeAssistantError(f"Unsupported phase option: {option}")
        if not self.phase_control_available(serial):
            raise HomeAssistantError(
                "Phase control is unavailable until fresh direct phase readback "
                "and exactly one connected PowerOcean source are available"
            )

        await self._async_write_settings(
            serial,
            {5: phase_values[option]},
            expected_key="phase_mode",
            expected_value=option,
        )

    async def async_set_battery_discharge_disabled(
        self, serial: str, enabled: bool
    ) -> None:
        """Set battery-discharge blocking while preserving every other flag."""
        flags = self._required_int_setting(serial, "switch_bits_raw")
        flags = flags | 0x01 if enabled else flags & ~0x01
        await self._async_write_settings(
            serial,
            {1: flags},
            expected_key="battery_discharge_disabled",
            expected_value=enabled,
        )

    async def async_set_plug_and_play(self, serial: str, enabled: bool) -> None:
        """Set Plug-and-Play while preserving every other settings flag."""
        flags = self._required_int_setting(serial, "switch_bits_raw")
        flags = flags | 0x02 if enabled else flags & ~0x02
        await self._async_write_settings(
            serial,
            {1: flags},
            expected_key="plug_and_play",
            expected_value=enabled,
        )

    async def async_set_work_mode(self, serial: str, mode: str) -> None:
        """Select a live-confirmed charging mode with its required companion data."""
        if mode == "fast":
            settings: dict[int, int | bytes] = {2: 1}
        elif mode == "solar":
            settings = {
                1: self._required_int_setting(serial, "switch_bits_raw"),
                2: 2,
                4: self._required_int_setting(serial, "solar_current_min_raw"),
            }
        elif mode == "custom":
            settings = {
                2: 3,
                6: self._required_int_setting(serial, "user_current_set_raw"),
            }
        elif mode == "smart":
            settings = {
                1: self._required_int_setting(serial, "switch_bits_raw"),
                2: 4,
                7: self._smart_settings_payload(serial),
            }
        else:
            raise HomeAssistantError(f"Unsupported charging mode: {mode}")
        await self._async_write_settings(
            serial, settings, expected_key="work_mode", expected_value=mode
        )

    async def async_set_custom_current(self, serial: str, amps: float) -> None:
        """Set the whole-ampere current used in Custom mode."""
        if (self.data or {}).get(serial, {}).get("work_mode") != "custom":
            raise HomeAssistantError("Custom current requires Custom mode")
        raw = self._validated_whole_amp_setting(amps)
        await self._async_write_settings(
            serial,
            {2: 3, 6: raw},
            expected_key="user_current_set_raw",
            expected_value=raw,
        )

    async def async_set_smart_ready_by(self, serial: str, timestamp: int) -> None:
        """Set Smart ready-by time while preserving the selected target."""
        await self._async_write_smart_setting(
            serial, {"ready_by_timestamp": timestamp}, "ready_by_timestamp", timestamp
        )

    async def async_set_smart_target_type(self, serial: str, target_type: str) -> None:
        """Switch between energy and distance Smart targets."""
        if target_type not in ("energy", "distance"):
            raise HomeAssistantError(f"Unsupported Smart target type: {target_type}")
        await self._async_write_smart_setting(
            serial, {"smart_target_type": target_type}, "smart_target_type", target_type
        )

    async def async_set_smart_energy_target(self, serial: str, kwh: float) -> None:
        """Set a whole-kWh Smart energy target."""
        if not 1 <= kwh <= 100 or not float(kwh).is_integer():
            raise HomeAssistantError("Smart energy target must be 1 to 100 whole kWh")
        raw = int(kwh) * 1000
        await self._async_write_smart_setting(
            serial,
            {"smart_target_type": "energy", "smart_charge_target_wh": raw},
            "smart_charge_target_wh",
            raw,
        )

    async def async_set_smart_distance_target(self, serial: str, km: float) -> None:
        """Set a whole-kilometre Smart distance target."""
        if not 10 <= km <= 600 or not float(km).is_integer():
            raise HomeAssistantError("Smart distance target must be 10 to 600 whole km")
        await self._async_write_smart_setting(
            serial,
            {"smart_target_type": "distance", "smart_target_distance_km": int(km)},
            "smart_target_distance_km",
            int(km),
        )

    async def _async_write_smart_setting(
        self,
        serial: str,
        overrides: dict[str, Any],
        expected_key: str,
        expected_value: Any,
    ) -> None:
        if (self.data or {}).get(serial, {}).get("work_mode") != "smart":
            raise HomeAssistantError("Smart settings require Smart mode")
        cached = dict(self._last_smart_settings.get(serial, {}))
        cached.update(overrides)
        await self._async_write_settings(
            serial,
            {
                1: self._required_int_setting(serial, "switch_bits_raw"),
                2: 4,
                7: self._smart_settings_payload(serial, cached),
            },
            expected_key=expected_key,
            expected_value=expected_value,
        )

    def _remember_smart_settings(self, serial: str, values: dict[str, Any]) -> None:
        keys = (
            "ready_by_timestamp",
            "smart_target_type",
            "smart_charge_target_wh",
            "smart_target_distance_km",
            "smart_calculated_energy_wh",
            "vehicle_consumption_raw",
        )
        remembered = self._last_smart_settings.setdefault(serial, {})
        remembered.update({key: values[key] for key in keys if key in values})

    def remembered_smart_setting(self, serial: str, key: str) -> Any:
        """Return a last device-reported Smart value for mode-transition controls."""
        return self._last_smart_settings.get(serial, {}).get(key)

    def smart_target_type_control_available(self, serial: str) -> bool:
        """Require a reusable value for both target types before switching alone."""
        smart = self._last_smart_settings.get(serial, {})
        return all(
            isinstance(smart.get(key), int) and smart[key] > 0
            for key in ("smart_charge_target_wh", "smart_target_distance_km")
        )

    def _smart_settings_payload(
        self, serial: str, values: dict[str, Any] | None = None
    ) -> bytes:
        smart = dict(self._last_smart_settings.get(serial, {}))
        previous_distance = smart.get("smart_target_distance_km")
        if values:
            smart.update(values)
        ready_by = smart.get("ready_by_timestamp")
        target_type = smart.get("smart_target_type")
        target = (
            smart.get("smart_charge_target_wh")
            if target_type == "energy"
            else smart.get("smart_target_distance_km")
        )
        if (
            not isinstance(ready_by, int)
            or target_type not in ("energy", "distance")
            or not isinstance(target, int)
        ):
            raise HomeAssistantError("Stored Smart settings are unavailable")
        calculated = smart.get("smart_calculated_energy_wh")
        if target_type == "distance":
            consumption = smart.get("vehicle_consumption_raw")
            if isinstance(consumption, int) and consumption > 0:
                calculated = target * consumption
            else:
                if (
                    isinstance(calculated, int)
                    and calculated > 0
                    and isinstance(previous_distance, int)
                    and previous_distance > 0
                ):
                    calculated = round(target * calculated / previous_distance)
                else:
                    raise HomeAssistantError(
                        "Vehicle consumption for the Smart distance target is unavailable"
                    )
        return build_powerpulse_smart_settings(
            ready_by_timestamp=ready_by,
            target_type=target_type,
            target_value=target,
            calculated_energy_wh=calculated or 0,
        )

    async def async_set_continuous_charging(self, serial: str, enabled: bool) -> None:
        """Set Solar continuous charging while preserving unrelated flags."""
        values = (self.data or {}).get(serial, {})
        if values.get("work_mode") != "solar":
            raise HomeAssistantError("Continuous charging can only be changed in Solar mode")
        flags = self._required_int_setting(serial, "switch_bits_raw")
        solar_current = self._required_int_setting(serial, "solar_current_min_raw")
        flags = flags | 0x10 if enabled else flags & ~0x10
        await self._async_write_settings(
            serial,
            {1: flags, 2: 2, 4: solar_current},
            expected_key="continuous_charging",
            expected_value=enabled,
        )

    async def async_set_maximum_output_current(self, serial: str, amps: float) -> None:
        """Set the independently configured maximum output current."""
        raw = self._validated_whole_amp_setting(amps)
        await self._async_write_settings(
            serial,
            {3: raw},
            expected_key="output_current_max_raw",
            expected_value=raw,
        )

    async def async_set_solar_minimum_current(self, serial: str, amps: float) -> None:
        """Set the no-sun current used by Solar continuous charging."""
        values = (self.data or {}).get(serial, {})
        if values.get("work_mode") != "solar" or not values.get("continuous_charging"):
            raise HomeAssistantError(
                "Solar minimum current requires Solar mode and Continuous charging"
            )
        raw = self._validated_whole_amp_setting(amps)
        flags = self._required_int_setting(serial, "switch_bits_raw")
        await self._async_write_settings(
            serial,
            {1: flags, 2: 2, 4: raw},
            expected_key="solar_current_min_raw",
            expected_value=raw,
        )

    async def async_set_screen_enabled(self, serial: str, enabled: bool) -> None:
        """Switch the wallbox screen while preserving all display settings."""
        await self._async_write_display_settings(
            serial, screen_enabled=enabled,
            expected_key="screen_enabled", expected_value=enabled,
        )

    async def async_set_indicator_enabled(self, serial: str, enabled: bool) -> None:
        """Switch the wallbox LED indicator while preserving display settings."""
        await self._async_write_display_settings(
            serial, indicator_enabled=enabled,
            expected_key="indicator_enabled", expected_value=enabled,
        )

    async def async_set_screen_brightness(self, serial: str, percent: float) -> None:
        """Set the screen to one of the four observed brightness levels."""
        await self._async_write_display_settings(
            serial, screen_brightness_pct=self._validated_brightness(percent),
            expected_key="screen_brightness_pct", expected_value=int(percent),
        )

    async def async_set_indicator_brightness(self, serial: str, percent: float) -> None:
        """Set the LED indicator to one of the four observed brightness levels."""
        await self._async_write_display_settings(
            serial, indicator_brightness_pct=self._validated_brightness(percent),
            expected_key="indicator_brightness_pct", expected_value=int(percent),
        )

    async def _async_write_display_settings(
        self, serial: str, *, expected_key: str, expected_value: Any, **overrides: Any
    ) -> None:
        values = dict((self.data or {}).get(serial, {}))
        values.update(overrides)
        required = (
            "indicator_enabled", "screen_enabled",
            "indicator_brightness_pct", "screen_brightness_pct",
        )
        if any(key not in values for key in required):
            raise HomeAssistantError("Complete display settings readback is unavailable")
        raw = bytes((
            int(values["indicator_enabled"]),
            int(values["screen_enabled"]),
            int(values["indicator_brightness_pct"]),
            int(values["screen_brightness_pct"]),
            0,
            0,
        ))
        await self._async_write_settings(
            serial, {21: raw}, expected_key=expected_key, expected_value=expected_value
        )

    @staticmethod
    def _validated_brightness(percent: float) -> int:
        if percent not in (25, 50, 75, 100):
            raise HomeAssistantError("Brightness must be 25, 50, 75, or 100 percent")
        return int(percent)

    def _required_int_setting(self, serial: str, key: str) -> int:
        value = (self.data or {}).get(serial, {}).get(key)
        if not isinstance(value, int):
            raise HomeAssistantError(f"Required device readback is unavailable: {key}")
        return value

    @staticmethod
    def _validated_whole_amp_setting(amps: float) -> int:
        if not 6 <= amps <= 16 or not float(amps).is_integer():
            raise HomeAssistantError("Current must be a whole number from 6 to 16 A")
        return int(amps) * 10

    async def _async_write_settings(
        self,
        serial: str,
        settings: dict[int, int | bytes],
        *,
        expected_key: str,
        expected_value: Any,
    ) -> None:
        """Publish one settings command and require reply plus confirmed readback."""
        async with self._control_lock:
            await self._async_write_settings_locked(
                serial,
                settings,
                expected_key=expected_key,
                expected_value=expected_value,
            )

    async def _async_write_settings_locked(
        self,
        serial: str,
        settings: dict[int, int | bytes],
        *,
        expected_key: str,
        expected_value: Any,
    ) -> None:
        if not self.settings_control_available(serial):
            raise HomeAssistantError(
                "Control is unavailable until a direct device settings report "
                "and exactly one connected PowerOcean source are available"
            )
        now = time.monotonic()
        if fresh_polled_value_matches(
            polled_values=self._last_polled_settings.get(serial, {}),
            polled_at=self._last_polled_settings_at.get(serial, 0),
            now=now,
            max_age=_CONTROL_NOOP_FRESH_SECONDS,
            expected_key=expected_key,
            expected_value=expected_value,
        ):
            self._record_control_readback("noop")
            return
        observer_serial = next(iter(self.observer_devices))
        client = self.mqtt_clients[observer_serial]
        payload, sequence = build_powerpulse_settings_payload(
            self._accessory_descriptors[serial], settings
        )
        waiter = self.hass.loop.create_future()
        self._reply_waiters[(observer_serial, sequence)] = waiter
        issued_at = time.monotonic()
        published = await self.hass.async_add_executor_job(
            client.send_explicit_control, payload
        )
        if not published:
            self._reply_waiters.pop((observer_serial, sequence), None)
            raise HomeAssistantError("EcoFlow rejected the MQTT publish request")
        try:
            await asyncio.wait_for(waiter, timeout=5)
        except TimeoutError as exc:
            self._reply_waiters.pop((observer_serial, sequence), None)
            raise HomeAssistantError("No EcoFlow SET reply was received") from exc

        source = await self._async_wait_for_control_readback(
            serial,
            issued_at=issued_at,
            expected_key=expected_key,
            expected_value=expected_value,
            timeout=_CONTROL_DIRECT_WAIT_SECONDS,
        )
        if source is not None:
            self._record_control_readback(source)
            return

        for attempt, delay in enumerate(_CONTROL_PROVIDER_RETRY_DELAYS, start=1):
            if delay:
                await asyncio.sleep(delay)
            refresh_succeeded = True
            try:
                await self.async_request_refresh()
            except Exception as exc:
                refresh_succeeded = False
                _LOGGER.debug("Provider readback after settings write failed: %s", exc)
            self._record_provider_readback_attempt(
                serial,
                issued_at=issued_at,
                expected_key=expected_key,
                expected_value=expected_value,
                attempt=attempt,
                delay=delay,
                refresh_succeeded=refresh_succeeded,
            )
            source = self._control_readback_source(
                serial, issued_at, expected_key, expected_value
            )
            if source is not None:
                self._record_control_readback(source)
                return
        raise HomeAssistantError(
            "EcoFlow acknowledged the command, but neither direct nor provider "
            "readback confirmed it"
        )

    async def _async_wait_for_control_readback(
        self,
        serial: str,
        *,
        issued_at: float,
        expected_key: str,
        expected_value: Any,
        timeout: float,
    ) -> str | None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            source = self._control_readback_source(
                serial, issued_at, expected_key, expected_value
            )
            if source is not None:
                return source
            await asyncio.sleep(0.2)
        return self._control_readback_source(
            serial, issued_at, expected_key, expected_value
        )

    def _control_readback_source(
        self,
        serial: str,
        issued_at: float,
        expected_key: str,
        expected_value: Any,
    ) -> str | None:
        return matching_readback_source(
            current_values=(self.data or {}).get(serial, {}),
            direct_reported_at=self._last_direct_settings_at.get(serial, 0),
            polled_values=self._last_polled_settings.get(serial, {}),
            polled_at=self._last_polled_settings_at.get(serial, 0),
            issued_at=issued_at,
            expected_key=expected_key,
            expected_value=expected_value,
        )

    def _record_control_readback(self, source: str) -> None:
        self._control_readback_counts[source] += 1
        self._last_control_readback_source = source
        self._last_control_readback_at = datetime.now(UTC).isoformat()

    def _record_provider_readback_attempt(
        self,
        serial: str,
        *,
        issued_at: float,
        expected_key: str,
        expected_value: Any,
        attempt: int,
        delay: int,
        refresh_succeeded: bool,
    ) -> None:
        """Retain a bounded, identifier-free provider qualification trace."""
        details = provider_readback_attempt_details(
            polled_values=self._last_polled_settings.get(serial, {}),
            polled_at=self._last_polled_settings_at.get(serial, 0),
            issued_at=issued_at,
            expected_key=expected_key,
            expected_value=expected_value,
        )
        self._control_provider_attempts.append(
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "attempt": attempt,
                "delay_seconds": delay,
                "expected_key": expected_key,
                "refresh_succeeded": refresh_succeeded,
                **details,
            }
        )

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
        self._shutting_down = True
        await self._settings_refresh.async_close()
        for waiter in self._reply_waiters.values():
            if not waiter.done():
                waiter.cancel()
        self._reply_waiters.clear()
        for client in self.mqtt_clients.values():
            await self.hass.async_add_executor_job(client.disconnect)
        self.mqtt_clients.clear()
