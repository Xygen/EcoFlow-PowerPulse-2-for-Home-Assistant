"""Three bounded hardware experiments, separate from production validation."""

from __future__ import annotations

import asyncio
import time
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from .charge_control import direct_charging_status
from .control_safety import idle_control_allowed

DIRECT_SOURCE = "direct_fast_settings_241_44"
READBACK_SECONDS = 15
PHASE_OBSERVATION_SECONDS = 15
PHASE_VALUES = {"auto": 0, "one_phase": 1, "three_phase": 2}


class ProtocolResearchMixin:
    """Use the coordinator's existing transport, lock and source trackers."""

    @property
    def protocol_research_transactions(self) -> list[dict[str, Any]]:
        """Return a detached bounded history containing no device identifiers."""
        return deepcopy(list(self._protocol_research_transactions))

    async def async_protocol_test_solar_minimum_field_only(
        self, serial: str, current: float, expected_work_mode: str, *,
        confirm_protocol_test: bool = False,
        expected_continuous_charging: bool | None = None,
    ) -> dict[str, Any]:
        return await self._async_protocol_test(
            serial, "solar_minimum_field_only", current, expected_work_mode,
            confirm_protocol_test, expected_continuous_charging,
        )

    async def async_protocol_test_custom_current_field_only(
        self, serial: str, current: float, expected_work_mode: str, *,
        confirm_protocol_test: bool = False,
    ) -> dict[str, Any]:
        return await self._async_protocol_test(
            serial, "custom_current_field_only", current, expected_work_mode,
            confirm_protocol_test,
        )

    async def async_protocol_test_phase_while_charging(
        self, serial: str, phase: str, *, confirm_protocol_test: bool = False,
    ) -> dict[str, Any]:
        return await self._async_protocol_test(
            serial, "phase_while_charging", phase, None, confirm_protocol_test,
        )

    def _research_direct(self, serial: str, key: str, *, after: float = -1) -> Any:
        observations = self._setting_observations.fresh_observations(
            serial=serial, key=key, now=time.monotonic(),
        )
        return next((o.value for o in observations
                     if o.source == DIRECT_SOURCE and o.observed_monotonic > after), None)

    def _research_physical(self, serial: str) -> dict[str, Any]:
        if not self.heartbeat_stream_active(serial):
            return {}
        values = (self.data or {}).get(serial, {})
        return {key: values[key] for key in (
            "direct_active_phase", "direct_active_phase_raw", "direct_phase_current_a",
        ) if key in values}

    async def _async_protocol_test(
        self, serial: str, action: str, target: Any, expected_mode: str | None,
        confirmed: bool, expected_continuous: bool | None = None,
    ) -> dict[str, Any]:
        record: dict[str, Any] = {
            "action": action, "started_at": datetime.now(UTC).isoformat(),
            "device_prefix": serial[:4], "published_fields": {},
            "set_reply_received": False, "readback_source": None,
            "before": {}, "after": {}, "invariants": {}, "result": "validation_failed",
        }
        try:
            if confirmed is not True:
                raise ServiceValidationError("Protocol test requires confirm_protocol_test=true")
            phase_test = action == "phase_while_charging"
            if phase_test:
                if target not in PHASE_VALUES:
                    raise ServiceValidationError("Phase must be auto, one_phase or three_phase")
                field, key, value = 5, "phase_mode", target
                raw = PHASE_VALUES[target]
                keys = ("phase_mode",)
            else:
                if type(target) not in (int, float):
                    raise ServiceValidationError("Current must be a whole number from 6 to 16 A")
                raw = self._validated_whole_amp_setting(target)
                if expected_mode not in ("solar", "fast"):
                    raise ServiceValidationError("Expected work mode must be solar or fast")
                if expected_continuous is not None and type(expected_continuous) is not bool:
                    raise ServiceValidationError("Expected Continuous charging must be boolean")
                field, key = ((4, "solar_current_min_raw") if action == "solar_minimum_field_only"
                              else (6, "user_current_set_raw"))
                value = raw
                keys = (key, "work_mode", "switch_bits_raw", "continuous_charging")
            record.update(expected_key=key, expected_value=value, requested_fields={str(field): raw})
            queued = self._control_lock.locked()
            async with self._control_lock:
                record["result"] = "state_changed_before_dispatch" if queued else "validation_failed"
                if not self.settings_control_available(serial):
                    raise ServiceValidationError(
                        "Protocol test requires a loaded device, accessory descriptor and exactly one "
                        "qualified connected PowerOcean routing source"
                    )
                if not self.direct_stream_available(serial) or not self.heartbeat_stream_active(serial):
                    raise ServiceValidationError("Protocol test requires a fresh direct PowerPulse heartbeat")
                status = direct_charging_status((self.data or {}).get(serial, {}))
                if phase_test:
                    if status != "charging":
                        raise ServiceValidationError("Phase charging test requires an actively charging PowerPulse 2")
                    # Same strict direct phase age as normal control; no charging gate here.
                    phase = self._phase_readbacks.control_evidence(
                        serial, now=time.monotonic(),
                        direct_max_age=self._protocol_direct_phase_fresh_seconds,
                        provider_max_age=self._protocol_provider_phase_fresh_seconds,
                    )
                    direct = self._phase_readbacks.source_evidence(serial, "direct_241_44")
                    if (phase is None or direct is None or time.monotonic() - direct.observed_monotonic
                            > self._protocol_direct_phase_fresh_seconds
                            or phase.mode != direct.mode):
                        raise ServiceValidationError("No fresh qualified direct phase-setting evidence is available")
                elif not idle_control_allowed(status):
                    raise ServiceValidationError("Protocol test requires an idle PowerPulse 2")
                before = {item: self._research_direct(serial, item) for item in keys}
                if any(item is None for item in before.values()):
                    raise ServiceValidationError("No fresh direct PowerPulse settings report is available")
                if not phase_test:
                    if before["work_mode"] != expected_mode:
                        raise ServiceValidationError(
                            f"Expected {expected_mode} mode but fresh device readback reports {before['work_mode']}"
                        )
                    if self._control_setting_value(serial, "work_mode") != expected_mode:
                        raise ServiceValidationError("Expected work mode conflicts with fresh settings evidence")
                    if expected_continuous is not None and (
                        before["continuous_charging"] != expected_continuous
                        or self._control_setting_value(serial, "continuous_charging") != expected_continuous
                    ):
                        raise ServiceValidationError("Expected Continuous charging state differs from fresh readback")
                if before[key] == value:
                    raise ServiceValidationError(
                        "Target value already equals current value; no protocol write was sent"
                    )
                before["charging_status"] = status
                if phase_test:
                    before["phase_specified_raw"] = PHASE_VALUES[direct.mode]
                    before.update(self._research_physical(serial))
                elif field == 4:
                    before["output_current_max_raw"] = self._research_direct(serial, "output_current_max_raw")
                record["before"] = before
                await self._async_execute_settings_transaction_locked(
                    serial, {field: raw}, expected_key=key, expected_value=value, research=record,
                )
                record["result"] = "confirmed"
        except asyncio.CancelledError:
            record["result"] = "cancelled"
            raise
        except HomeAssistantError:
            raise
        except Exception as exc:
            # Do not export arbitrary exception text: it may contain identifiers or credentials.
            raise HomeAssistantError("Protocol research transaction failed; see bounded diagnostics") from exc
        finally:
            record["finished_at"] = datetime.now(UTC).isoformat()
            self._protocol_research_transactions.append(deepcopy(record))
        return deepcopy(record)

    async def _async_confirm_protocol_research(
        self, serial: str, issued_at: float, record: dict[str, Any],
    ) -> None:
        """Require actual post-write fields, never merged state or provider echoes."""
        record["result"] = "direct_readback_timeout"
        key, expected = record["expected_key"], record["expected_value"]
        phase_test = record["action"] == "phase_while_charging"
        invariant_keys = (() if phase_test else ("work_mode", "switch_bits_raw", "continuous_charging"))
        required = (key, *invariant_keys)
        deadline = time.monotonic() + READBACK_SECONDS
        while True:
            after = {item: self._research_direct(serial, item, after=issued_at) for item in required}
            record["after"] = after
            target_matches = after[key] == expected
            if phase_test:
                phase = self._phase_readbacks.source_evidence(serial, "direct_241_44")
                target_matches = (target_matches and phase is not None
                                  and phase.observed_monotonic > issued_at and phase.mode == expected)
            if target_matches and all(after[item] is not None for item in required):
                break
            if time.monotonic() >= deadline:
                if after[key] is not None and after[key] != expected:
                    record["result"] = "device_rejected"
                raise HomeAssistantError(
                    "The requested value was delivered but not confirmed with required companion evidence "
                    "by a newer direct PowerPulse settings report"
                )
            await asyncio.sleep(0.2)
        record["readback_source"] = DIRECT_SOURCE
        record["after"]["charging_status"] = (
            direct_charging_status((self.data or {}).get(serial, {}))
            if self.heartbeat_stream_active(serial) else None
        )
        invariants = {f"{item}_unchanged": after[item] == record["before"][item] for item in invariant_keys}
        record["invariants"] = invariants
        enforced = invariant_keys if record["action"] == "solar_minimum_field_only" else ("work_mode",)
        if not phase_test and any(not invariants[f"{item}_unchanged"] for item in enforced):
            record["result"] = "unexpected_companion_change"
            raise HomeAssistantError("The target value changed but companion settings changed unexpectedly")
        if phase_test:
            record["after"]["phase_specified_raw"] = PHASE_VALUES[expected]
            await self._async_observe_research_phase(serial, record)

    async def _async_observe_research_phase(self, serial: str, record: dict[str, Any]) -> None:
        """Observe existing push telemetry without publishing or requesting refreshes."""
        deadline = time.monotonic() + PHASE_OBSERVATION_SECONDS
        start = time.monotonic()
        baseline = record["before"].get("direct_active_phase_raw")
        observed = False
        changed = False
        session_ended = False
        while time.monotonic() < deadline:
            values = self._research_physical(serial)
            status = (direct_charging_status((self.data or {}).get(serial, {}))
                      if self.heartbeat_stream_active(serial) else None)
            if status is not None and status != "charging":
                session_ended = True
            record["after"]["charging_status"] = status
            if self._last_heartbeat_at.get(serial, 0) > start and "direct_active_phase_raw" in values:
                record["after"].update(values)
                if status == "charging":
                    observed = True
                    changed |= baseline is not None and values["direct_active_phase_raw"] != baseline
            await asyncio.sleep(0.2)
        record["physical_phase_observation"] = {
            "window_seconds": PHASE_OBSERVATION_SECONDS,
            "session_ended": session_ended,
            "result": ("changed" if changed else "unchanged" if observed and baseline is not None
                       else "insufficient_fresh_telemetry"),
        }
