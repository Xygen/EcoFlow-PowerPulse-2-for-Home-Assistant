"""Bounded, privacy-conscious MQTT frame capture helpers."""

from __future__ import annotations

import hmac
from collections import OrderedDict
from hashlib import sha256
from secrets import token_bytes
from struct import unpack
from typing import Any

from .ecoflow.proto_encoding import iter_protobuf_fields

COMMAND_CHANNELS = frozenset({"observed_set", "set_reply"})
_SAFE_OBSERVER_COMMAND_LIMITS = {
    (96, 97): 16,
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
    if "/app/device/property/" in topic:
        return "property"
    return "other"


def channel_carries_telemetry(channel: str) -> bool:
    """Return whether a channel may safely update entity state."""
    return channel not in COMMAND_CHANNELS


def inspect_envelope_headers(payload: bytes) -> list[dict[str, int]]:
    """Extract non-secret routing metadata from EcoFlow protobuf headers."""
    headers: list[dict[str, int]] = []
    field_names = {
        2: "cmd_src",
        3: "cmd_dst",
        8: "cmd_func",
        9: "cmd_id",
        10: "declared_payload_size",
        11: "enc_type",
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

                if varints.get(11) == 1:
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
                            recursive=command_pair == (241, 102),
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
                if varints.get(11) == 1 and isinstance(varints.get(14), int):
                    key = varints[14] & 0xFF
                    pdata = bytes(byte ^ key for byte in pdata)
                report = _summarize_accessory_report(pdata)
                if report:
                    report["cmd_id"] = varints.get(9)
                    reports.append(report)
    except ValueError:
        return []
    return reports


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
        max_buckets: int = 48,
        max_samples_per_bucket: int = 8,
        max_correlations: int = 48,
        fingerprint_key: bytes | None = None,
    ) -> None:
        self._max_recent = max_recent
        self._max_commands = max_commands
        self._max_buckets = max_buckets
        self._max_samples_per_bucket = max_samples_per_bucket
        self._max_correlations = max_correlations
        self._fingerprint_key = fingerprint_key or token_bytes(32)
        self._recent: list[dict[str, Any]] = []
        self._commands: list[dict[str, Any]] = []
        self._buckets: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._correlations: OrderedDict[str, dict[str, Any]] = OrderedDict()

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
        self._append_bounded(self._recent, stored, self._max_recent)

        channel = str(stored.get("channel", "other"))
        if channel in COMMAND_CHANNELS:
            self._append_bounded(self._commands, stored, self._max_commands)
            self._record_command_correlations(stored)

        bucket_key = _bucket_key(stored)
        bucket = self._buckets.get(bucket_key)
        if bucket is None:
            if len(self._buckets) >= self._max_buckets:
                self._buckets.popitem(last=False)
            bucket = {
                "channel": channel,
                "command_pairs": _command_pairs(stored),
                "count": 0,
                "first_timestamp": stored.get("timestamp"),
                "last_timestamp": stored.get("timestamp"),
                "samples": [],
            }
            self._buckets[bucket_key] = bucket
        else:
            self._buckets.move_to_end(bucket_key)

        bucket["count"] += 1
        bucket["last_timestamp"] = stored.get("timestamp")
        self._append_bounded(
            bucket["samples"],
            stored,
            self._max_samples_per_bucket,
        )

    @property
    def recent(self) -> list[dict[str, Any]]:
        """Return the bounded chronological all-frame view."""
        return [dict(frame) for frame in self._recent]

    @property
    def commands(self) -> list[dict[str, Any]]:
        """Return the bounded official-app command/reply view."""
        return [dict(frame) for frame in self._commands]

    def bucket_snapshot(self) -> dict[str, dict[str, Any]]:
        """Return per-channel and per-command samples for diagnostics."""
        return {
            key: {
                **{name: value for name, value in bucket.items() if name != "samples"},
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
