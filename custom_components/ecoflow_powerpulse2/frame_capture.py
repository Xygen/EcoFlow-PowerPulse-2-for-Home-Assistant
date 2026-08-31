"""Bounded, privacy-conscious MQTT frame capture helpers."""

from __future__ import annotations

import hmac
import json
import math
from collections import OrderedDict
from hashlib import sha256
from secrets import token_bytes
from struct import unpack
from typing import Any

from .ecoflow.proto_encoding import iter_protobuf_fields

COMMAND_CHANNELS = frozenset({"observed_set", "set_reply"})
REQUEST_CHANNELS = frozenset({"observed_get"})
NON_TELEMETRY_CHANNELS = COMMAND_CHANNELS | REQUEST_CHANNELS
_SAFE_OBSERVER_COMMAND_LIMITS = {
    (96, 97): 16,
    (241, 100): 64,
    (241, 102): 64,
}
_MAX_SAFE_SMALL_VARINT = 255
_MAX_SAFE_COMMAND_NESTING_DEPTH = 3
_MAX_SAFE_COMMAND_FIELDS = 32


def classify_mqtt_topic(topic: str) -> str:
    """Return a stable diagnostic channel without retaining the full topic."""
    if topic.endswith("/quota"):
        return "quota"
    if topic.endswith("/get_reply"):
        return "get_reply"
    if topic.endswith("/set_reply"):
        return "set_reply"
    if topic.endswith("/thing/property/set"):
        return "observed_set"
    if topic.endswith("/set"):
        return "observed_set"
    if topic.endswith("/thing/property/get") or topic.endswith("/get"):
        return "observed_get"
    if "/app/device/property/" in topic:
        return "property"
    return "other"


def channel_carries_telemetry(channel: str) -> bool:
    """Return whether a channel may safely update entity state."""
    return channel not in NON_TELEMETRY_CHANNELS


def inspect_get_request(payload: bytes) -> dict[str, Any]:
    """Summarize an app GET without retaining identifiers or raw content."""
    try:
        decoded = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        decoded = None
    if isinstance(decoded, dict):
        summary: dict[str, Any] = {"classification": "json"}
        operate_type = decoded.get("operateType")
        if isinstance(operate_type, str) and operate_type.isascii() and len(operate_type) <= 64:
            summary["operate_type"] = operate_type
        source = decoded.get("from")
        if source in {"Android", "iOS", "Web"}:
            summary["source"] = source
        module_type = decoded.get("moduleType")
        if isinstance(module_type, int) and 0 <= module_type <= 255:
            summary["module_type"] = module_type
        version = decoded.get("version")
        if isinstance(version, str) and version.isascii() and len(version) <= 16:
            summary["version"] = version
        params = decoded.get("params")
        if isinstance(params, dict):
            summary["parameter_keys"] = sorted(
                key
                for key in params
                if isinstance(key, str) and key.isascii() and len(key) <= 32
            )[:16]
        return summary

    try:
        for field, wire, header_bytes in iter_protobuf_fields(payload):
            if field != 1 or wire != 2 or not isinstance(header_bytes, bytes):
                continue
            summary = {"classification": "protobuf"}
            recognized = False
            for inner_field, inner_wire, value in iter_protobuf_fields(header_bytes):
                if inner_wire == 0 and isinstance(value, int):
                    if inner_field == 2:
                        summary["cmd_src"] = value
                        recognized = True
                    elif inner_field == 3:
                        summary["cmd_dst"] = value
                        recognized = True
                    elif inner_field == 14:
                        summary["sequence"] = value
                        recognized = True
                elif inner_field == 23 and inner_wire == 2 and value == b"app":
                    summary["source"] = "app"
                    recognized = True
            if recognized:
                return summary
    except ValueError:
        pass
    return {"classification": "opaque", "size": len(payload)}


def inspect_envelope_headers(payload: bytes) -> list[dict[str, int]]:
    """Extract non-secret routing metadata from EcoFlow protobuf headers."""
    headers: list[dict[str, int]] = []
    field_names = {
        2: "cmd_src",
        3: "cmd_dst",
        6: "enc_type",
        8: "cmd_func",
        9: "cmd_id",
        10: "declared_payload_size",
        11: "need_ack",
        14: "sequence",
    }
    try:
        outer_fields = iter_protobuf_fields(payload)
        for field, wire, value in outer_fields:
            if field != 1 or wire != 2 or not isinstance(value, bytes):
                continue
            header: dict[str, int] = {}
            actual_payload_size: int | None = None
            for inner_field, inner_wire, inner_value in iter_protobuf_fields(value):
                if inner_field == 1 and inner_wire == 2 and isinstance(inner_value, bytes):
                    actual_payload_size = len(inner_value)
                elif inner_wire == 0 and isinstance(inner_value, int):
                    name = field_names.get(inner_field)
                    if name is not None:
                        header[name] = inner_value
            if "cmd_func" in header or "cmd_id" in header:
                if actual_payload_size is not None:
                    header["actual_payload_size"] = actual_payload_size
                headers.append(header)
    except ValueError:
        return []
    return headers


def inspect_observer_command_payloads(
    payload: bytes, *, fingerprint_key: bytes | None = None
) -> list[dict[str, Any]]:
    """Summarize narrowly allow-listed live-observed PowerOcean commands.

    Parent payloads can contain identifiers belonging to the charger, battery,
    or vehicle. This helper therefore accepts only exact command tuples with a
    per-tuple decoded-size limit. Small protobuf varints are retained; opaque
    fields expose their size only, and larger numbers are omitted. The 241/102
    candidate additionally receives bounded nested-structure summaries and
    runtime-only fingerprints for byte fields so paired captures can identify
    which field changed without retaining its contents.
    """
    summaries: list[dict[str, Any]] = []
    try:
        for field, wire, header_bytes in iter_protobuf_fields(payload):
            if field != 1 or wire != 2 or not isinstance(header_bytes, bytes):
                continue
            header_fields = list(iter_protobuf_fields(header_bytes))
            varints = {
                inner_field: inner_value
                for inner_field, inner_wire, inner_value in header_fields
                if inner_wire == 0 and isinstance(inner_value, int)
            }
            command_pair = (varints.get(8), varints.get(9))
            payload_limit = _SAFE_OBSERVER_COMMAND_LIMITS.get(command_pair)
            if payload_limit is None:
                continue

            for inner_field, inner_wire, pdata in header_fields:
                if inner_field != 1 or inner_wire != 2 or not isinstance(pdata, bytes):
                    continue
                summary: dict[str, Any] = {
                    "cmd_func": command_pair[0],
                    "cmd_id": command_pair[1],
                    "decoded_size": len(pdata),
                }
                sequence = varints.get(14)
                if isinstance(sequence, int):
                    summary["sequence"] = sequence

                if varints.get(6) == 1:
                    if not isinstance(sequence, int):
                        summary["classification"] = "missing_xor_sequence"
                        summaries.append(summary)
                        continue
                    key = sequence & 0xFF
                    pdata = bytes(byte ^ key for byte in pdata)
                    summary["xor_decoded"] = True
                else:
                    summary["xor_decoded"] = False

                if len(pdata) > payload_limit:
                    summary["classification"] = "omitted_size_limit"
                else:
                    if fingerprint_key:
                        # The key is random for each integration runtime and is
                        # never exported. This permits equality checks without
                        # exposing a brute-forceable hash of a two-byte body.
                        summary["runtime_fingerprint"] = hmac.new(
                            fingerprint_key, pdata, sha256
                        ).hexdigest()[:16]
                    summary.update(
                        _summarize_safe_command_fields(
                            pdata,
                            fingerprint_key=fingerprint_key,
                            recursive=command_pair in {(241, 100), (241, 102)},
                        )
                    )
                summaries.append(summary)
    except ValueError:
        return []
    return summaries


def _summarize_safe_command_fields(
    payload: bytes,
    *,
    fingerprint_key: bytes | None = None,
    recursive: bool = False,
) -> dict[str, Any]:
    """Describe protobuf structure without retaining opaque command bytes."""
    try:
        parsed = list(iter_protobuf_fields(payload))
    except ValueError:
        return {"classification": "opaque_non_protobuf", "fields": []}

    fields, structure_truncated = _summarize_command_field_list(
        parsed,
        fingerprint_key=fingerprint_key,
        recursive=recursive,
        depth=0,
        remaining_fields=[_MAX_SAFE_COMMAND_FIELDS],
    )
    contains_opaque = any(_field_contains_opaque(item) for item in fields)
    contains_omitted_number = any(_field_contains_omitted_number(item) for item in fields)
    if not fields:
        classification = "empty"
    elif contains_opaque or contains_omitted_number:
        classification = "structured_opaque"
    else:
        classification = "small_numeric_only"
    result: dict[str, Any] = {"classification": classification, "fields": fields}
    if structure_truncated:
        result["structure_truncated"] = True
    return result


def _summarize_command_field_list(
    parsed: list[tuple[int, int, int | bytes]],
    *,
    fingerprint_key: bytes | None,
    recursive: bool,
    depth: int,
    remaining_fields: list[int],
) -> tuple[list[dict[str, Any]], bool]:
    """Return a bounded field tree plus whether the shared budget was reached."""
    fields: list[dict[str, Any]] = []
    truncated = False
    for field, wire, value in parsed:
        if remaining_fields[0] <= 0:
            truncated = True
            break
        remaining_fields[0] -= 1

        item: dict[str, Any] = {"field": field, "wire_type": wire}
        if wire == 0 and isinstance(value, int):
            if value <= _MAX_SAFE_SMALL_VARINT:
                item["small_value"] = value
            else:
                item["value_omitted"] = True
        elif isinstance(value, bytes):
            item["size"] = len(value)
            # Top-level command field 4 is the already identified settings
            # object. Very small non-protobuf display blocks contain numeric
            # switches/brightness bytes, not descriptors or identifiers. Keep
            # this narrow diagnostic view so controlled app diffs can identify
            # their write layout without exporting any other opaque field.
            if depth == 0 and field == 4 and len(value) <= 16:
                item["small_settings_bytes"] = list(value)
            if recursive and fingerprint_key:
                item["runtime_fingerprint"] = hmac.new(
                    fingerprint_key, value, sha256
                ).hexdigest()[:16]
            if recursive and depth < _MAX_SAFE_COMMAND_NESTING_DEPTH:
                nested = _parse_nested_command_message(value)
                if nested is not None:
                    nested_fields, nested_truncated = _summarize_command_field_list(
                        nested,
                        fingerprint_key=fingerprint_key,
                        recursive=True,
                        depth=depth + 1,
                        remaining_fields=remaining_fields,
                    )
                    item["nested_fields"] = nested_fields
                    truncated = truncated or nested_truncated
        fields.append(item)
    return fields, truncated


def _parse_nested_command_message(
    payload: bytes,
) -> list[tuple[int, int, int | bytes]] | None:
    """Recognize a complete nested protobuf message conservatively."""
    if not payload or len(payload) > 64:
        return None
    try:
        parsed = list(iter_protobuf_fields(payload))
    except ValueError:
        return None
    if not parsed or not any(wire == 0 for _, wire, _ in parsed):
        return None
    if any(field > 1024 for field, _, _ in parsed):
        return None
    return parsed


def _field_contains_opaque(item: dict[str, Any]) -> bool:
    """Return whether a summarized field contains hidden byte content."""
    if "size" in item:
        return True
    nested = item.get("nested_fields")
    return isinstance(nested, list) and any(
        isinstance(child, dict) and _field_contains_opaque(child) for child in nested
    )


def _field_contains_omitted_number(item: dict[str, Any]) -> bool:
    """Return whether a summarized field tree contains a hidden large number."""
    if item.get("value_omitted") is True:
        return True
    nested = item.get("nested_fields")
    return isinstance(nested, list) and any(
        isinstance(child, dict) and _field_contains_omitted_number(child)
        for child in nested
    )


def inspect_powerpulse_accessory_reports(payload: bytes) -> list[dict[str, Any]]:
    """Return privacy-safe numeric fields from PowerOcean cmd_func 209.

    String and byte fields can contain serial or vehicle identifiers. They are
    represented only by their byte length; the PowerPulse serial contributes
    its four-character product prefix solely for matching diagnostics.
    """
    reports: list[dict[str, Any]] = []
    try:
        for field, wire, header_bytes in iter_protobuf_fields(payload):
            if field != 1 or wire != 2 or not isinstance(header_bytes, bytes):
                continue
            header_fields = list(iter_protobuf_fields(header_bytes))
            varints = {
                inner_field: inner_value
                for inner_field, inner_wire, inner_value in header_fields
                if inner_wire == 0 and isinstance(inner_value, int)
            }
            if varints.get(8) != 209:
                continue
            pdata_values = [
                inner_value
                for inner_field, inner_wire, inner_value in header_fields
                if inner_field == 1
                and inner_wire == 2
                and isinstance(inner_value, bytes)
            ]
            for pdata in pdata_values:
                if varints.get(6) == 1 and isinstance(varints.get(14), int):
                    key = varints[14] & 0xFF
                    pdata = bytes(byte ^ key for byte in pdata)
                report = _summarize_accessory_report(pdata)
                if report:
                    report["cmd_id"] = varints.get(9)
                    reports.append(report)
    except ValueError:
        return []
    return reports


_POWER_OCEAN_CHARGING_STATUS = {
    0: "none",
    1: "available",
    2: "preparing",
    3: "charging",
    4: "suspended_charger",
    5: "suspended_vehicle",
    6: "finishing",
    9: "faulted",
}


def parse_powerocean_charging_reports(payload: bytes) -> list[dict[str, Any]]:
    """Decode confirmed session telemetry from PowerOcean 241/3 or 209/8.

    Unlike the privacy-safe diagnostic summary, this internal parser retains
    the target serial just long enough for the coordinator to route the report
    to the correct charger. Vehicle identifiers and unconfirmed fields are
    deliberately not returned.
    """
    reports: list[dict[str, Any]] = []
    try:
        for field, wire, header_bytes in iter_protobuf_fields(payload):
            if field != 1 or wire != 2 or not isinstance(header_bytes, bytes):
                continue
            header_fields = list(iter_protobuf_fields(header_bytes))
            varints = {
                inner_field: inner_value
                for inner_field, inner_wire, inner_value in header_fields
                if inner_wire == 0 and isinstance(inner_value, int)
            }
            command = (varints.get(8), varints.get(9))
            if command not in ((209, 8), (241, 3)):
                continue
            for inner_field, inner_wire, inner_value in header_fields:
                if (
                    inner_field != 1
                    or inner_wire != 2
                    or not isinstance(inner_value, bytes)
                ):
                    continue
                report_payload = inner_value
                if varints.get(6) == 1 and isinstance(varints.get(14), int):
                    key = varints[14] & 0xFF
                    report_payload = bytes(byte ^ key for byte in report_payload)
                report = (
                    _parse_powerocean_charging_report(report_payload)
                    if command == (209, 8)
                    else _parse_powerocean_relay_charging_report(report_payload)
                )
                if report:
                    reports.append(report)
    except ValueError:
        return []
    return reports


def _parse_powerocean_charging_report(payload: bytes) -> dict[str, Any]:
    """Decode the confirmed, entity-safe subset of EVChargingParamReport."""
    result: dict[str, Any] = {}
    try:
        for field, wire, value in iter_protobuf_fields(payload):
            if field == 1 and wire == 2 and isinstance(value, bytes):
                try:
                    target_serial = value.decode("ascii")
                except UnicodeDecodeError:
                    continue
                if target_serial:
                    result["target_serial"] = target_serial.upper()
            elif field == 6 and wire == 0 and isinstance(value, int):
                status = _POWER_OCEAN_CHARGING_STATUS.get(value)
                if status is not None:
                    result["powerocean_charging_status"] = status
            elif field in (11,) and wire == 0 and isinstance(value, int):
                result["powerocean_session_duration_s"] = value
            elif field in (8, 9) and wire == 5 and isinstance(value, bytes):
                number = unpack("<f", value)[0]
                if not math.isfinite(number):
                    continue
                if field == 8:
                    result["powerocean_charging_power_w"] = round(number, 1)
                else:
                    result["powerocean_session_energy_wh"] = round(number, 1)
    except ValueError:
        return {}

    if "target_serial" not in result:
        return {}
    return result


def _parse_powerocean_relay_charging_report(payload: bytes) -> dict[str, Any]:
    """Decode the PowerPulse 2 session nested in PowerOcean relay 241/3."""
    result: dict[str, Any] = {}
    try:
        for field, wire, value in iter_protobuf_fields(payload):
            if wire != 2 or not isinstance(value, bytes):
                continue
            if field == 1:
                for nested_field, nested_wire, nested_value in iter_protobuf_fields(
                    value
                ):
                    if (
                        nested_field == 2
                        and nested_wire == 2
                        and isinstance(nested_value, bytes)
                    ):
                        try:
                            target_serial = nested_value.decode("ascii")
                        except UnicodeDecodeError:
                            continue
                        if target_serial:
                            result["target_serial"] = target_serial.upper()
            elif field == 4:
                _parse_powerocean_relay_pile_report(value, result)
    except ValueError:
        return {}

    if "target_serial" not in result:
        return {}
    return result


def _parse_powerocean_relay_pile_report(
    payload: bytes, result: dict[str, Any]
) -> None:
    """Decode the entity-safe EDevPileChargingParamReport subset."""
    for field, wire, value in iter_protobuf_fields(payload):
        if wire == 0 and isinstance(value, int):
            if field == 4:
                status = _POWER_OCEAN_CHARGING_STATUS.get(value)
                if status is not None:
                    result["powerocean_charging_status"] = status
            elif field == 6:
                result["powerocean_charging_power_w"] = value
        elif field == 8 and wire == 2 and isinstance(value, bytes):
            for nested_field, nested_wire, nested_value in iter_protobuf_fields(
                value
            ):
                if nested_wire != 0 or not isinstance(nested_value, int):
                    continue
                if nested_field == 5:
                    result["powerocean_session_energy_wh"] = nested_value
                elif nested_field == 6:
                    result["powerocean_session_duration_s"] = nested_value


def _summarize_accessory_report(payload: bytes) -> dict[str, Any]:
    """Summarize an EVChargingParamReport without retaining identifiers."""
    numeric_fields: dict[str, int | float] = {}
    byte_field_sizes: dict[str, int] = {}
    target_prefix = ""
    try:
        for field, wire, value in iter_protobuf_fields(payload):
            key = str(field)
            if wire == 0 and isinstance(value, int):
                numeric_fields[key] = value
            elif wire == 5 and isinstance(value, bytes):
                if field in (8, 9):
                    numeric_fields[key] = round(unpack("<f", value)[0], 4)
                elif field in (15, 16):
                    numeric_fields[key] = unpack("<I", value)[0]
                else:
                    byte_field_sizes[key] = len(value)
            elif wire in (1, 2) and isinstance(value, bytes):
                byte_field_sizes[key] = len(value)
                if field == 1:
                    try:
                        target_prefix = value.decode("ascii")[:4]
                    except UnicodeDecodeError:
                        target_prefix = ""
    except ValueError:
        return {}

    result: dict[str, Any] = {
        "target_prefix": target_prefix,
        "numeric_fields": numeric_fields,
        "byte_field_sizes": byte_field_sizes,
    }
    if "10" in numeric_fields:
        result["work_mode_raw"] = numeric_fields["10"]
    if "18" in numeric_fields:
        result["switch_bits_raw"] = numeric_fields["18"]
    return result


class DiagnosticFrameCapture:
    """Keep bounded recent frames plus per-message-type samples."""

    def __init__(
        self,
        *,
        max_recent: int = 40,
        max_commands: int = 24,
        max_requests: int = 24,
        max_buckets: int = 48,
        max_samples_per_bucket: int = 16,
        reserved_command_buckets: int = 8,
        max_dropped_types: int = 16,
        max_correlations: int = 48,
        fingerprint_key: bytes | None = None,
    ) -> None:
        self._max_recent = max_recent
        self._max_commands = max_commands
        self._max_requests = max_requests
        self._max_buckets = max_buckets
        self._max_samples_per_bucket = max_samples_per_bucket
        self._reserved_command_buckets = min(reserved_command_buckets, max_buckets)
        self._max_dropped_types = max_dropped_types
        self._max_correlations = max_correlations
        self._fingerprint_key = fingerprint_key or token_bytes(32)
        self._recent: list[dict[str, Any]] = []
        self._commands: list[dict[str, Any]] = []
        self._requests: list[dict[str, Any]] = []
        self._buckets: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._correlations: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._frames_seen = 0
        self._frames_dropped_type_budget = 0
        self._dropped_per_type: OrderedDict[str, int] = OrderedDict()
        self._dropped_types_untracked = 0

    def inspect_observer_command_payloads(
        self, payload: bytes
    ) -> list[dict[str, Any]]:
        """Return runtime-linkable summaries without exporting the HMAC key."""
        return inspect_observer_command_payloads(
            payload, fingerprint_key=self._fingerprint_key
        )

    def record(self, frame: dict[str, Any]) -> None:
        """Record one already-redacted frame in all applicable views."""
        stored = dict(frame)
        self._frames_seen += 1
        self._append_bounded(self._recent, stored, self._max_recent)

        channel = str(stored.get("channel", "other"))
        if channel in COMMAND_CHANNELS:
            self._append_bounded(self._commands, stored, self._max_commands)
            self._record_command_correlations(stored)
        if channel in REQUEST_CHANNELS:
            self._append_bounded(self._requests, stored, self._max_requests)

        bucket_key = _bucket_key(stored)
        bucket = self._buckets.get(bucket_key)
        if bucket is None:
            if not self._make_bucket_space(channel):
                self._record_dropped_type(bucket_key)
                return
            bucket = {
                "channel": channel,
                "command_pairs": _command_pairs(stored),
                "count": 0,
                "first_timestamp": stored.get("timestamp"),
                "last_timestamp": stored.get("timestamp"),
                "samples": [],
                "sample_stride": 1,
            }
            self._buckets[bucket_key] = bucket
        else:
            self._buckets.move_to_end(bucket_key)

        bucket["count"] += 1
        bucket["last_timestamp"] = stored.get("timestamp")
        self._record_long_window_sample(bucket, stored)

    def _make_bucket_space(self, channel: str) -> bool:
        """Keep bucket capacity reserved for SET traffic."""
        if len(self._buckets) >= self._max_buckets:
            return False
        if channel in COMMAND_CHANNELS:
            return True
        command_count = sum(
            bucket["channel"] in COMMAND_CHANNELS
            for bucket in self._buckets.values()
        )
        non_command_limit = self._max_buckets - max(
            0, self._reserved_command_buckets - command_count
        )
        return len(self._buckets) < non_command_limit

    def _record_dropped_type(self, bucket_key: str) -> None:
        self._frames_dropped_type_budget += 1
        if bucket_key in self._dropped_per_type:
            self._dropped_per_type[bucket_key] += 1
        elif len(self._dropped_per_type) < self._max_dropped_types:
            self._dropped_per_type[bucket_key] = 1
        else:
            self._dropped_types_untracked += 1

    def _record_long_window_sample(
        self, bucket: dict[str, Any], frame: dict[str, Any]
    ) -> None:
        """Retain first/latest frames and bounded samples across the full window."""
        samples = bucket["samples"]
        limit = self._max_samples_per_bucket
        if limit <= 0:
            return
        if len(samples) < limit:
            samples.append(frame)
            return
        if limit == 1:
            samples[0] = frame
            return
        stride = bucket["sample_stride"]
        if (bucket["count"] - 1) % stride == 0:
            # Compact older interior samples before increasing the interval.
            interior = samples[1:-1:2]
            samples[:] = [samples[0], *interior, frame]
            bucket["sample_stride"] = stride * 2
        else:
            samples[-1] = frame

    @property
    def statistics(self) -> dict[str, Any]:
        """Return bounded, reconcilable capture statistics."""
        frames_kept = sum(
            len(bucket["samples"]) for bucket in self._buckets.values()
        )
        frames_dropped_sample_budget = (
            self._frames_seen
            - frames_kept
            - self._frames_dropped_type_budget
        )
        return {
            "frames_seen": self._frames_seen,
            "frames_kept": frames_kept,
            "frames_dropped_sample_budget": frames_dropped_sample_budget,
            "frames_dropped_type_budget": self._frames_dropped_type_budget,
            "dropped_per_type": dict(self._dropped_per_type),
            "dropped_types_untracked": self._dropped_types_untracked,
            "per_type": {
                key: {
                    "seen": bucket["count"],
                    "kept_samples": len(bucket["samples"]),
                    "dropped_samples": bucket["count"] - len(bucket["samples"]),
                }
                for key, bucket in self._buckets.items()
            },
        }

    @property
    def recent(self) -> list[dict[str, Any]]:
        """Return the bounded chronological all-frame view."""
        return [dict(frame) for frame in self._recent]

    @property
    def commands(self) -> list[dict[str, Any]]:
        """Return the bounded official-app command/reply view."""
        return [dict(frame) for frame in self._commands]

    @property
    def requests(self) -> list[dict[str, Any]]:
        """Return the bounded official-app GET request view."""
        return [dict(frame) for frame in self._requests]

    def bucket_snapshot(self) -> dict[str, dict[str, Any]]:
        """Return per-channel and per-command samples for diagnostics."""
        return {
            key: {
                **{
                    name: value
                    for name, value in bucket.items()
                    if name not in {"samples", "sample_stride"}
                },
                "samples": [dict(frame) for frame in bucket["samples"]],
            }
            for key, bucket in self._buckets.items()
        }

    @property
    def command_correlations(self) -> list[dict[str, Any]]:
        """Return bounded request/reply groups matched by source and sequence."""
        return [
            {
                **correlation,
                "status": (
                    "matched"
                    if correlation["request_count"] and correlation["reply_count"]
                    else "reply_only"
                    if correlation["reply_count"]
                    else "request_only"
                ),
            }
            for correlation in self._correlations.values()
        ]

    def _record_command_correlations(self, frame: dict[str, Any]) -> None:
        channel = str(frame.get("channel", "other"))
        count_key = "reply_count" if channel == "set_reply" else "request_count"
        pairs_key = "reply_pairs" if channel == "set_reply" else "request_pairs"
        headers = frame.get("protocol_headers")
        if not isinstance(headers, list):
            return

        for header in headers:
            if not isinstance(header, dict):
                continue
            sequence = header.get("sequence")
            if not isinstance(sequence, int):
                continue
            device_prefix = str(frame.get("device_prefix", ""))
            source_role = str(frame.get("source_role", "unknown"))
            key = f"{source_role}:{device_prefix}:{sequence}"
            correlation = self._correlations.get(key)
            if correlation is None:
                if len(self._correlations) >= self._max_correlations:
                    self._correlations.popitem(last=False)
                correlation = {
                    "device_prefix": device_prefix,
                    "source_role": source_role,
                    "sequence": sequence,
                    "first_timestamp": frame.get("timestamp"),
                    "last_timestamp": frame.get("timestamp"),
                    "request_count": 0,
                    "reply_count": 0,
                    "request_pairs": [],
                    "reply_pairs": [],
                }
                self._correlations[key] = correlation
            else:
                self._correlations.move_to_end(key)

            correlation[count_key] += 1
            correlation["last_timestamp"] = frame.get("timestamp")
            cmd_func = header.get("cmd_func")
            cmd_id = header.get("cmd_id")
            if isinstance(cmd_func, int) and isinstance(cmd_id, int):
                pair = f"{cmd_func}/{cmd_id}"
                if pair not in correlation[pairs_key]:
                    correlation[pairs_key].append(pair)

    @staticmethod
    def _append_bounded(items: list[Any], item: Any, maximum: int) -> None:
        items.append(item)
        del items[:-maximum]


def _command_pairs(frame: dict[str, Any]) -> list[str]:
    pairs: list[str] = []
    headers = frame.get("protocol_headers")
    if not isinstance(headers, list):
        return pairs
    for header in headers:
        if not isinstance(header, dict):
            continue
        cmd_func = header.get("cmd_func")
        cmd_id = header.get("cmd_id")
        if isinstance(cmd_func, int) and isinstance(cmd_id, int):
            pairs.append(f"{cmd_func}/{cmd_id}")
    return pairs


def _bucket_key(frame: dict[str, Any]) -> str:
    channel = str(frame.get("channel", "other"))
    pairs = _command_pairs(frame)
    return f"{channel}:{','.join(pairs)}" if pairs else channel
