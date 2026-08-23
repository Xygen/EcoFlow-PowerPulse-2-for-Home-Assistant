"""Bounded, privacy-conscious MQTT frame capture helpers."""

from __future__ import annotations

from collections import OrderedDict
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
