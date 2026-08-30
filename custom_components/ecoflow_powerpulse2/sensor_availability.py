"""Availability helpers for read-only telemetry sensors."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def telemetry_sensor_available(
    *,
    coordinator_available: bool,
    device_present: bool,
    source_available: bool,
) -> bool:
    """Return whether the sensor can currently attempt to expose a value.

    Field presence is deliberately not part of availability. A healthy source
    can omit an individual field, in which case Home Assistant should expose
    ``unknown`` instead of implying that the device is unavailable.
    """
    return coordinator_available and device_present and source_available


def telemetry_sensor_value(values: Mapping[str, Any], source_key: str) -> Any:
    """Return a field value or ``None`` for Home Assistant's unknown state."""
    return values.get(source_key)
