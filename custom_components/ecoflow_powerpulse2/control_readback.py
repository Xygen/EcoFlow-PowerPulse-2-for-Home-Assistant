"""Field- and source-qualified evidence for generic settings transactions."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .ecoflow.proto_encoding import iter_protobuf_fields
from .setting_observation import SettingObservation


def matching_readback_source(
    *, observations: Sequence[SettingObservation], issued_at: float, expected_value: Any,
) -> str | None:
    """Confirm only an actual post-command field, with no newer contradiction.

    A fresh conflicting Direct value blocks a provider fallback even if it was
    observed before the command. A new Direct value can supersede older evidence.
    Callers supply only fresh observations for the exact device and field.
    """
    direct = [o for o in observations if o.source.startswith("direct_")]
    candidates = sorted(
        (o for o in observations if o.observed_monotonic > issued_at),
        key=lambda o: (o.source.startswith("direct_"), o.observed_monotonic),
        reverse=True,
    )
    for candidate in candidates:
        if candidate.value != expected_value:
            continue
        if any(o.value != expected_value and o.observed_monotonic >= candidate.observed_monotonic
               for o in observations):
            continue
        if candidate.source.startswith("direct_"):
            return "direct"
        if any(o.value != expected_value for o in direct):
            continue
        return "provider"
    return None


def provider_bundle_matches(
    *, evidence: Mapping[str, Sequence[SettingObservation]], expected: Mapping[str, Any],
) -> bool:
    """A no-op requires the entire SET in one provider snapshot without conflict."""
    if not expected:
        return False
    common_snapshots: set[tuple[str, float]] | None = None
    for key, value in expected.items():
        observations = evidence.get(key, ())
        if any(o.value != value for o in observations):
            return False
        snapshots = {
            (o.source, o.observed_monotonic) for o in observations
            if o.source.startswith("provider_") and o.value == value
        }
        common_snapshots = snapshots if common_snapshots is None else common_snapshots & snapshots
        if not common_snapshots:
            return False
    return bool(common_snapshots)


def settings_bundle_values(settings: Mapping[int, int | bytes]) -> dict[str, Any]:
    """Map the already-built SET bundle to all fields a no-op must establish."""
    values: dict[str, Any] = {}
    scalar_keys = {1: "switch_bits_raw", 3: "output_current_max_raw",
                   4: "solar_current_min_raw", 6: "user_current_set_raw"}
    for field, value in settings.items():
        if field in scalar_keys:
            values[scalar_keys[field]] = value
        elif field == 2:
            values["work_mode"] = {1: "fast", 2: "solar", 3: "custom", 4: "smart"}[value]
        elif field == 21 and isinstance(value, bytes) and len(value) == 6:
            values.update(indicator_enabled=bool(value[0]), screen_enabled=bool(value[1]),
                          indicator_brightness_pct=value[2], screen_brightness_pct=value[3])
        elif field == 7 and isinstance(value, bytes):
            smart = {key: val for key, wire, val in iter_protobuf_fields(value) if wire == 0}
            values.update(ready_by_timestamp=smart[1],
                          smart_target_type="energy" if smart[2] == 1 else "distance")
            if smart[2] == 1:
                values["smart_charge_target_wh"] = smart[3]
            else:
                values["smart_target_distance_km"] = smart[4]
                values["smart_calculated_energy_wh"] = smart[3]
        else:
            return {}  # Unqualified bundle: send and require a reply/readback.
    return values
