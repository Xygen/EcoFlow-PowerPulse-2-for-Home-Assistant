"""Race-safe helpers for combining cloud polling and MQTT telemetry."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Collection, Mapping
from typing import Any


async def merge_snapshot_after_read(
    read_snapshot: Callable[[], Awaitable[Mapping[str, Any]]],
    latest_values: Callable[[], Mapping[str, Any] | None],
    prefer_latest_keys: Callable[[], Collection[str]] | None = None,
) -> dict[str, Any]:
    """Merge a poll into the latest MQTT state after the poll completes.

    MQTT callbacks can update coordinator data while the HTTP request is in
    flight. Reading the current values only after that await prevents a slow or
    empty provider response from replacing freshly received telemetry. Callers
    may additionally name selected, independently freshness-gated MQTT keys
    that must win over a cached provider value.
    """
    polled_values = await read_snapshot()
    latest = dict(latest_values() or {})
    merged = dict(latest)
    merged.update(polled_values)
    for key in prefer_latest_keys() if prefer_latest_keys else ():
        if key in latest:
            merged[key] = latest[key]
    return merged
