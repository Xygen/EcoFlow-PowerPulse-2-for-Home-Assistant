"""Validated, serial-scoped staging for Smart charging configuration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

STAGED_SMART_KEYS = frozenset(
    {
        "ready_by_timestamp",
        "smart_target_type",
        "smart_charge_target_wh",
        "smart_target_distance_km",
    }
)


class SmartStagingError(ValueError):
    """A staged Smart value is invalid."""


def _validated_value(key: str, value: Any) -> int | str:
    """Validate one user-owned staged value without coercing its type."""
    if key == "ready_by_timestamp":
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise SmartStagingError("Smart ready-by time must be a valid timestamp")
        return value
    if key == "smart_target_type":
        if value not in ("energy", "distance"):
            raise SmartStagingError("Smart target type must be energy or distance")
        return value
    if key == "smart_charge_target_wh":
        if (
            not isinstance(value, int)
            or isinstance(value, bool)
            or not 1_000 <= value <= 100_000
            or value % 1_000
        ):
            raise SmartStagingError(
                "Smart energy target must be 1 to 100 whole kWh"
            )
        return value
    if key == "smart_target_distance_km":
        if (
            not isinstance(value, int)
            or isinstance(value, bool)
            or not 10 <= value <= 600
        ):
            raise SmartStagingError(
                "Smart distance target must be 10 to 600 whole km"
            )
        return value
    raise SmartStagingError(f"Unsupported staged Smart setting: {key}")


class SmartStaging:
    """Hold validated Smart configuration drafts independently per serial."""

    def __init__(self) -> None:
        self._devices: dict[str, dict[str, int | str]] = {}

    def load(self, stored: Any) -> None:
        """Load valid fields while isolating malformed devices and values."""
        self._devices = {}
        if not isinstance(stored, Mapping):
            return
        devices = stored.get("devices")
        if not isinstance(devices, Mapping):
            return
        for serial, values in devices.items():
            if not isinstance(serial, str) or not serial or not isinstance(values, Mapping):
                continue
            validated: dict[str, int | str] = {}
            for key in STAGED_SMART_KEYS:
                if key not in values:
                    continue
                try:
                    validated[key] = _validated_value(key, values[key])
                except SmartStagingError:
                    continue
            if validated:
                self._devices[serial] = validated

    def update(self, serial: str, changes: Mapping[str, Any]) -> bool:
        """Apply validated semantic changes and report whether state changed."""
        if not isinstance(serial, str) or not serial:
            raise SmartStagingError("Smart staging requires a device serial")
        validated = {
            key: _validated_value(key, value) for key, value in changes.items()
        }
        current = dict(self._devices.get(serial, {}))
        updated = dict(current)
        updated.update(validated)
        if updated == current:
            return False
        self._devices[serial] = updated
        return True

    def values(self, serial: str) -> dict[str, int | str]:
        """Return a copy of one serial's staged draft."""
        return dict(self._devices.get(serial, {}))

    def value(self, serial: str, key: str) -> int | str | None:
        """Return one staged value without falling back to device state."""
        return self._devices.get(serial, {}).get(key)

    def export(self) -> dict[str, dict[str, dict[str, int | str]]]:
        """Return the versioned Store payload body without sensitive context."""
        return {
            "devices": {
                serial: dict(values) for serial, values in self._devices.items()
            }
        }


def validate_smart_bundle(values: Mapping[str, Any]) -> None:
    """Require the selected target's complete user-owned activation bundle."""
    ready_by = values.get("ready_by_timestamp")
    if not isinstance(ready_by, int) or isinstance(ready_by, bool) or ready_by <= 0:
        raise SmartStagingError("Smart mode requires a ready-by time")

    target_type = values.get("smart_target_type")
    if target_type not in ("energy", "distance"):
        raise SmartStagingError("Smart mode requires a target type")

    if target_type == "energy":
        try:
            _validated_value("smart_charge_target_wh", values.get("smart_charge_target_wh"))
        except SmartStagingError as exc:
            raise SmartStagingError("Smart mode requires an energy target") from exc
    else:
        try:
            _validated_value(
                "smart_target_distance_km", values.get("smart_target_distance_km")
            )
        except SmartStagingError as exc:
            raise SmartStagingError("Smart mode requires a distance target") from exc
