"""Source-aware current observations for device settings."""

from __future__ import annotations

from collections.abc import Collection, Mapping
from dataclasses import dataclass
from typing import Any, Literal

SettingSource = Literal[
    "direct_heartbeat_2_33",
    "direct_settings_2_34",
    "direct_fast_settings_241_44",
    "provider_parent_accessory",
    "provider_device_detail",
]

_SOURCE_PRIORITY: dict[SettingSource, int] = {
    "direct_fast_settings_241_44": 50,
    "direct_settings_2_34": 40,
    "direct_heartbeat_2_33": 30,
    "provider_parent_accessory": 20,
    "provider_device_detail": 10,
}


def setting_source_from_headers(
    headers: Collection[Mapping[str, Any]],
) -> SettingSource | None:
    """Identify the exact settings report family carried by one frame."""
    pairs = {(header.get("cmd_func"), header.get("cmd_id")) for header in headers}
    if (241, 44) in pairs:
        return "direct_fast_settings_241_44"
    if (2, 34) in pairs:
        return "direct_settings_2_34"
    if (2, 33) in pairs:
        return "direct_heartbeat_2_33"
    return None


@dataclass(frozen=True)
class SettingObservation:
    """One actual field observation from one qualified source."""

    value: Any
    source: SettingSource
    observed_at: str
    observed_monotonic: float


class SettingObservationTracker:
    """Select fresh current values without exposing changing age attributes."""

    def __init__(self, fresh_seconds: Mapping[SettingSource, float]) -> None:
        self._fresh_seconds = dict(fresh_seconds)
        self._observations: dict[
            tuple[str, str, SettingSource], SettingObservation
        ] = {}

    def record_snapshot(
        self,
        *,
        serial: str,
        source: SettingSource,
        values: Mapping[str, Any],
        keys: Collection[str],
        observed_at: str,
        observed_monotonic: float,
    ) -> None:
        """Record only fields truly present in one source report."""
        for key in keys:
            if key not in values:
                continue
            self._observations[(serial, key, source)] = SettingObservation(
                value=values[key],
                source=source,
                observed_at=observed_at,
                observed_monotonic=observed_monotonic,
            )

    def current_value(self, *, serial: str, key: str, now: float) -> Any:
        """Return the highest-priority fresh observation, otherwise unknown."""
        candidates = [
            observation
            for (item_serial, item_key, source), observation in self._observations.items()
            if item_serial == serial
            and item_key == key
            and now - observation.observed_monotonic
            <= self._fresh_seconds[source]
        ]
        if not candidates:
            return None
        selected = max(
            candidates,
            key=lambda item: (_SOURCE_PRIORITY[item.source], item.observed_monotonic),
        )
        return selected.value
