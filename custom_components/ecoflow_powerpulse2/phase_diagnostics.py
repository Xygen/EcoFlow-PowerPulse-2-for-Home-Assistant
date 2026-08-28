"""Privacy-safe source tracking for phase-setting readback."""

from __future__ import annotations

import math
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

_KNOWN_PHASE_MODES = frozenset({"auto", "one_phase", "three_phase", "unknown"})


class PhaseReadbackTracker:
    """Retain the latest phase evidence from each independent read path."""

    def __init__(self) -> None:
        self._records: dict[str, dict[str, dict[str, Any]]] = {}

    def record(
        self,
        serial: str,
        source: str,
        values: Mapping[str, Any],
        *,
        timestamp: str | None = None,
    ) -> None:
        """Record one source snapshot without retaining device identifiers."""
        observed_at = timestamp or datetime.now(UTC).isoformat()
        sources = self._records.setdefault(serial, {})
        record = dict(sources.get(source, {}))
        record.update(
            {
                "last_snapshot_at": observed_at,
                "raw_present_in_last_snapshot": "phase_specified_raw" in values,
                "mode_present_in_last_snapshot": "phase_mode" in values,
            }
        )

        if "phase_specified_raw" in values:
            raw_value = values.get("phase_specified_raw")
            raw_valid = (
                isinstance(raw_value, (int, float)) and not isinstance(raw_value, bool) and math.isfinite(raw_value)
            )
            record["raw_value_valid"] = raw_valid
            record["last_raw_at"] = observed_at
            if raw_valid:
                record["raw_value"] = raw_value
            else:
                record.pop("raw_value", None)

        if "phase_mode" in values:
            phase_mode = values.get("phase_mode")
            mode_valid = (
                isinstance(phase_mode, str) and phase_mode in _KNOWN_PHASE_MODES
            )
            record["mode_value_valid"] = mode_valid
            record["last_mode_at"] = observed_at
            if mode_valid:
                record["mode_value"] = phase_mode
            else:
                record.pop("mode_value", None)

        sources[source] = record

    def snapshot(self) -> list[dict[str, Any]]:
        """Return stable diagnostics with serials reduced to product prefixes."""
        return [
            {
                "device_prefix": serial[:4],
                "sources": {source: dict(values) for source, values in sorted(sources.items())},
            }
            for serial, sources in sorted(self._records.items())
        ]
