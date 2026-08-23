"""Race-safe helpers for combining cloud polling and MQTT telemetry."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from typing import Any


async def merge_snapshot_after_read(
    read_snapshot: Callable[[], Awaitable[Mapping[str, Any]]],
    latest_values: Callable[[], Mapping[str, Any] | None],
) -> dict[str, Any]:
    """Merge a poll into the latest MQTT state after the poll completes.

    MQTT callbacks can update coordinator data while the HTTP request is in
    flight. Reading the current values only after that await prevents a slow or
    empty provider response from replacing freshly received telemetry.
    """
    polled_values = await read_snapshot()
    merged = dict(latest_values() or {})
    merged.update(polled_values)
    return merged
