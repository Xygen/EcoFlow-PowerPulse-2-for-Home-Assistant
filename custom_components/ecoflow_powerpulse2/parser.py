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

_WORK_MODE_MAP = {
    1: "fast",
    2: "solar",
    3: "custom",
    4: "smart",
}

_PHASE_MODE_MAP = {
    1: "one_phase",
    2: "three_phase",
    3: "auto",
}

# Live paired Solar-mode tests confirmed that provider switchBits changes
# between 0 (disabled) and 16 (enabled) while the stored 6 A minimum remains
# unchanged. Other bits may describe unrelated settings, so isolate bit 4.
_CONTINUOUS_CHARGING_MASK = 0x10

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


def parse_powerpulse2_accessory_payloads(
    payload: bytes | dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Return PowerPulse provider reports keyed by their embedded serial."""
    if isinstance(payload, bytes):
        try:
            value = json.loads(payload)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}
    else:
        value = payload
    if not isinstance(value, dict):
        return {}

    reports: dict[str, dict[str, Any]] = {}
    for item in _iter_dicts(value):
        if not isinstance(item.get("pileChargingParamReport"), dict):
            continue
        dev_info = item.get("devInfo")
        serial = ""
        if isinstance(dev_info, dict):
            serial = str(dev_info.get("devSn") or "").upper()
        if not serial:
            serial = str(item.get("devSn") or "").upper()
        if not serial:
            continue

        result: dict[str, Any] = {}
        _parse_powerpulse_json(item, result)
        _finish(result)
        if result:
            reports.setdefault(serial, {}).update(result)
    return reports


def _parse_json(value: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for item in _iter_dicts(value):
        for source, target in _JSON_FIELD_MAP.items():
            raw = item.get(source)
            if isinstance(raw, (int, float)) and math.isfinite(float(raw)):
                result[target] = raw
    _parse_powerpulse_json(value, result)
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
    elif isinstance(value, str) and value.lstrip().startswith("{"):
        try:
            nested = json.loads(value)
        except json.JSONDecodeError:
            return
        yield from _iter_dicts(nested)


def _parse_powerpulse_json(value: dict[str, Any], result: dict[str, Any]) -> None:
    """Extract fields only from a PowerPulse parameter report.

    A PowerOcean provider response can contain several products with fields
    named ``workMode``. Restricting these aliases to
    ``pileChargingParamReport`` prevents an inverter mode from becoming the
    charger mode.
    """
    for item in _iter_dicts(value):
        report = item.get("pileChargingParamReport")
        if not isinstance(report, dict):
            continue

        params = report.get("paramSet")
        if not isinstance(params, dict):
            params = {}
        smart = params.get("smartMode")
        if not isinstance(smart, dict):
            smart = {}

        _copy_finite(report, "chargingPwr", "charging_power_w", result)
        _copy_finite(report, "chargingStatus", "system_state_raw", result)
        _copy_finite(params, "workMode", "work_mode_raw", result)
        _copy_finite(smart, "timeToUseCar", "ready_by_timestamp", result)
        _copy_finite(smart, "chargeTarget", "smart_charge_target_wh", result)

        for source, target in (
            ("currentOuputMax", "output_current_max_raw"),
            ("userCurrentSet", "user_current_set_raw"),
            ("solarCurrentMin", "solar_current_min_raw"),
            ("switchBits", "switch_bits_raw"),
            ("phaseSpecified", "phase_specified_raw"),
        ):
            _copy_from_first((params, report), source, target, result)

        # Live paired tests confirmed that the provider's misspelled
        # currentOuputMax field and CP307 setting-report field 9 describe the
        # same maximum output-current setting.
        if "output_current_max_raw" in result:
            result["current_limit_raw"] = result["output_current_max_raw"]

        vehicle = item.get("vehicleInfo")
        if isinstance(vehicle, dict):
            _copy_finite(
                vehicle,
                "currentVehicleComsumption",
                "vehicle_consumption_raw",
                result,
            )


def _copy_from_first(
    sources: tuple[dict[str, Any], ...],
    source: str,
    target: str,
    result: dict[str, Any],
) -> None:
    for item in sources:
        if _copy_finite(item, source, target, result):
            return


def _copy_finite(
    item: dict[str, Any],
    source: str,
    target: str,
    result: dict[str, Any],
) -> bool:
    raw = item.get(source)
    if not isinstance(raw, (int, float)) or not math.isfinite(float(raw)):
        return False
    result[target] = raw
    return True


def _parse_proto(payload: bytes) -> dict[str, Any]:
    result: dict[str, Any] = {}
    candidates: list[tuple[str, bytes]] = []
    envelope_seen = False
    try:
        for field, wire, value in iter_protobuf_fields(payload):
            if field != 1 or wire != 2 or not isinstance(value, bytes):
                continue
            # Standard EcoFlow MQTT envelope: repeated Header at field 1,
            # with CP307 pdata at field 1 of that header. App MQTT frames use
            # enc_type=1 (field 6): pdata is XORed with the low byte of the
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
                    if inner_field == 6 and inner_wire == 0 and isinstance(inner_value, int)
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

            # CP307 status and parameter messages reuse field numbers for
            # different meanings, so retain the command-specific schema with
            # every decoded payload.
            parser_kind = {
                (2, 33): "heartbeat",
                (2, 34): "settings",
            }.get((cmd_func, cmd_id))
            if parser_kind is None:
                continue
            for inner_field, inner_wire, inner_value in header_fields:
                if inner_field != 1 or inner_wire != 2 or not isinstance(inner_value, bytes):
                    continue
                if enc_type == 1 and isinstance(sequence, int):
                    key = sequence & 0xFF
                    candidates.append(
                        (parser_kind, bytes(byte ^ key for byte in inner_value))
                    )
                else:
                    candidates.append((parser_kind, inner_value))
    except ValueError:
        return {}

    # Captured BLE payloads are bare HeartBeat messages. Supporting that shape
    # also makes diagnostics fixtures usable, but plausibility checks below
    # prevent arbitrary envelopes from becoming entities.
    if not envelope_seen:
        candidates.append(("heartbeat", payload))
    for parser_kind, candidate in candidates:
        parsed = (
            _parse_cp307_heartbeat(candidate)
            if parser_kind == "heartbeat"
            else _parse_cp307_settings(candidate)
        )
        if parsed:
            result.update(parsed)
    return result


def _parse_cp307_settings(payload: bytes) -> dict[str, Any]:
    """Parse live-confirmed fields from the CP307 2/34 settings report."""
    try:
        fields = {
            field: value
            for field, wire, value in iter_protobuf_fields(payload)
            if wire == 0 and isinstance(value, int)
        }
    except ValueError:
        return {}

    # Every paired C376 settings capture used schema marker 9 in field 1.
    # Requiring it prevents unrelated 2/34 payload variants from becoming
    # charger settings.
    if fields.get(1) != 9:
        return {}

    result: dict[str, Any] = {}
    for field, key in (
        (2, "plug_and_play"),
        (13, "indicator_enabled"),
        (15, "screen_enabled"),
        (22, "battery_discharge_disabled"),
    ):
        if fields.get(field) in (0, 1):
            result[key] = bool(fields[field])

    current_limit = fields.get(9)
    if isinstance(current_limit, int) and 0 <= current_limit <= 1_000:
        result["current_limit_raw"] = current_limit

    phase_mode = fields.get(11)
    if isinstance(phase_mode, int):
        result["phase_mode"] = _PHASE_MODE_MAP.get(phase_mode, "unknown")

    for field, key in (
        (14, "indicator_brightness_pct"),
        (16, "screen_brightness_pct"),
    ):
        brightness = fields.get(field)
        if isinstance(brightness, int) and 0 <= brightness <= 100:
            result[key] = brightness

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
    work_mode = result.pop("work_mode_raw", None)
    if isinstance(work_mode, (int, float)):
        result["work_mode"] = _WORK_MODE_MAP.get(int(work_mode), "unknown")
    switch_bits = result.get("switch_bits_raw")
    if (
        isinstance(switch_bits, (int, float))
        and math.isfinite(float(switch_bits))
        and float(switch_bits).is_integer()
    ):
        result["continuous_charging"] = bool(
            int(switch_bits) & _CONTINUOUS_CHARGING_MASK
        )
