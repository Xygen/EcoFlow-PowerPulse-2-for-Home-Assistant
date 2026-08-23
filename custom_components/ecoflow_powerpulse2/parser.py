"""Read-only PowerPulse 2 HTTP and MQTT telemetry parser."""

from __future__ import annotations

import json
import math
from struct import unpack
from typing import Any

from .ecoflow.proto_encoding import iter_protobuf_fields

_STATE_MAP = {
    1: "unplugged",
    2: "plugged_in",
    3: "charging",
    4: "paused",
    6: "charge_complete",
    7: "standby",
    8: "updating",
}

_JSON_FIELD_MAP = {
    "chargePower": "charging_power_w",
    "chargingPower": "charging_power_w",
    "evchargingPower": "charging_power_w",
    "evPwr": "charging_power_w",
    "outputPower": "charging_power_w",
    "systemState": "system_state_raw",
    "system_state": "system_state_raw",
    "chargeTime": "session_duration_s",
    "charge_time": "session_duration_s",
    "energyValue": "total_energy_raw",
    "energy_value": "total_energy_raw",
    "chargeEnergy": "session_energy_raw",
    "charge_energy": "session_energy_raw",
    "chargeCurrentSet": "charge_current_set_raw",
    "charge_current_set": "charge_current_set_raw",
    "currentLimit": "current_limit_raw",
    "current_limit": "current_limit_raw",
    "suspendReason": "suspend_reason_raw",
    "suspend_reason": "suspend_reason_raw",
}


def parse_powerpulse2_payload(payload: bytes | dict[str, Any]) -> dict[str, Any]:
    """Parse known JSON shapes or a CP307 heartbeat in an EcoFlow envelope."""
    if isinstance(payload, dict):
        return _parse_json(payload)
    try:
        value = json.loads(payload)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return _parse_proto(payload)
    return _parse_json(value) if isinstance(value, dict) else {}


def _parse_json(value: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for item in _iter_dicts(value):
        for source, target in _JSON_FIELD_MAP.items():
            raw = item.get(source)
            if isinstance(raw, (int, float)) and math.isfinite(float(raw)):
                result[target] = raw
    _finish(result)
    return result


def _iter_dicts(value: Any):
    if isinstance(value, dict):
        yield value
        for nested in value.values():
            yield from _iter_dicts(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _iter_dicts(nested)


def _parse_proto(payload: bytes) -> dict[str, Any]:
    result: dict[str, Any] = {}
    candidates: list[bytes] = []
    envelope_seen = False
    try:
        for field, wire, value in iter_protobuf_fields(payload):
            if field != 1 or wire != 2 or not isinstance(value, bytes):
                continue
            # Standard EcoFlow MQTT envelope: repeated Header at field 1,
            # with CP307 pdata at field 1 of that header. App MQTT frames use
            # enc_type=1 (field 11): pdata is XORed with the low byte of the
            # sequence number (field 14). Keep the wire payload as a fallback
            # only when the header does not mark it as encrypted.
            header_fields = list(iter_protobuf_fields(value))
            cmd_func = next(
                (
                    inner_value
                    for inner_field, inner_wire, inner_value in header_fields
                    if inner_field == 8 and inner_wire == 0 and isinstance(inner_value, int)
                ),
                None,
            )
            cmd_id = next(
                (
                    inner_value
                    for inner_field, inner_wire, inner_value in header_fields
                    if inner_field == 9 and inner_wire == 0 and isinstance(inner_value, int)
                ),
                None,
            )
            enc_type = next(
                (
                    inner_value
                    for inner_field, inner_wire, inner_value in header_fields
                    if inner_field == 11 and inner_wire == 0 and isinstance(inner_value, int)
                ),
                None,
            )
            sequence = next(
                (
                    inner_value
                    for inner_field, inner_wire, inner_value in header_fields
                    if inner_field == 14 and inner_wire == 0 and isinstance(inner_value, int)
                ),
                None,
            )
            pdata_values = [
                inner_value
                for inner_field, inner_wire, inner_value in header_fields
                if inner_field == 1 and inner_wire == 2 and isinstance(inner_value, bytes)
            ]
            if pdata_values:
                envelope_seen = True

            # CP307 status, parameter, charging-record, and acknowledgement
            # messages reuse field numbers for different meanings. Only
            # command 2/33 uses the heartbeat schema below. Treating the 2/34
            # parameter report as a heartbeat can create false states/currents.
            if (cmd_func, cmd_id) != (2, 33):
                continue
            for inner_field, inner_wire, inner_value in header_fields:
                if inner_field != 1 or inner_wire != 2 or not isinstance(inner_value, bytes):
                    continue
                if enc_type == 1 and isinstance(sequence, int):
                    key = sequence & 0xFF
                    candidates.append(bytes(byte ^ key for byte in inner_value))
                else:
                    candidates.append(inner_value)
    except ValueError:
        return {}

    # Captured BLE payloads are bare HeartBeat messages. Supporting that shape
    # also makes diagnostics fixtures usable, but plausibility checks below
    # prevent arbitrary envelopes from becoming entities.
    if not envelope_seen:
        candidates.append(payload)
    for candidate in candidates:
        parsed = _parse_cp307_heartbeat(candidate)
        if parsed:
            result.update(parsed)
    return result


def _parse_cp307_heartbeat(payload: bytes) -> dict[str, Any]:
    result: dict[str, Any] = {}
    phase_voltages: list[float] = []
    phase_currents: list[float] = []
    try:
        fields = list(iter_protobuf_fields(payload))
    except ValueError:
        return {}

    for field, wire, value in fields:
        if wire == 0 and isinstance(value, int):
            target = {
                1: "system_state_raw",
                9: "total_energy_raw",
                17: "charge_current_set_raw",
                18: "current_limit_raw",
                41: "session_duration_s",
                42: "session_energy_raw",
                102: "suspend_reason_raw",
            }.get(field)
            if target:
                result[target] = value
        elif wire == 5 and isinstance(value, bytes):
            number = unpack("<f", value)[0]
            if not math.isfinite(number):
                continue
            if field == 28:
                result["charging_power_w"] = round(number, 1)
            elif field == 29:
                phase_voltages.append(number)
            elif field == 30:
                phase_currents.append(number)
        elif wire == 2 and isinstance(value, bytes) and field in (29, 30):
            # Protobuf 3 encodes repeated float values as one packed
            # length-delimited field. CP307 heartbeats use this form for the
            # three phase voltages and currents.
            if len(value) % 4:
                continue
            target = phase_voltages if field == 29 else phase_currents
            for offset in range(0, len(value), 4):
                number = unpack("<f", value[offset : offset + 4])[0]
                if math.isfinite(number):
                    target.append(number)

    # A heartbeat always contains a state. Requiring it prevents nested data
    # from unrelated EcoFlow products from being mistaken for CP307 status.
    state = result.get("system_state_raw")
    if not isinstance(state, int) or state > 255:
        return {}
    if phase_voltages:
        result["phase_voltage_v"] = round(max(phase_voltages), 1)
    if phase_currents:
        result["phase_current_a"] = round(max(phase_currents), 2)
    _finish(result)
    return result


def _finish(result: dict[str, Any]) -> None:
    state = result.pop("system_state_raw", None)
    if isinstance(state, (int, float)):
        result["charging_status"] = _STATE_MAP.get(int(state), "unknown")
