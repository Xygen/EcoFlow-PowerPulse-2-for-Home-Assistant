"""Bounded, privacy-conscious MQTT frame capture helpers."""

from __future__ import annotations

from collections import OrderedDict
from struct import unpack
from typing import Any

from .ecoflow.proto_encoding import iter_protobuf_fields

COMMAND_CHANNELS = frozenset({"observed_set", "set_reply"})


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
    ) -> None:
        self._max_recent = max_recent
        self._max_commands = max_commands
        self._max_buckets = max_buckets
        self._max_samples_per_bucket = max_samples_per_bucket
        self._recent: list[dict[str, Any]] = []
        self._commands: list[dict[str, Any]] = []
        self._buckets: OrderedDict[str, dict[str, Any]] = OrderedDict()

    def record(self, frame: dict[str, Any]) -> None:
        """Record one already-redacted frame in all applicable views."""
        stored = dict(frame)
        self._append_bounded(self._recent, stored, self._max_recent)

        channel = str(stored.get("channel", "other"))
        if channel in COMMAND_CHANNELS:
            self._append_bounded(self._commands, stored, self._max_commands)

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
