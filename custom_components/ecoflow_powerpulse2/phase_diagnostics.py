"""Privacy-safe source tracking for phase-setting readback."""

from __future__ import annotations

import math
import time
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

_KNOWN_PHASE_MODES = frozenset({"auto", "one_phase", "three_phase", "unknown"})
_CONTROL_PHASE_MODES = frozenset({"auto", "one_phase", "three_phase"})
_RAW_PHASE_MODES = {0: "auto", 1: "one_phase", 2: "three_phase"}


@dataclass(frozen=True)
class PhaseEvidence:
    """One source-qualified control-grade phase observation."""

    source: str
    mode: str
    observed_monotonic: float


class PhaseReadbackTracker:
    """Retain the latest phase evidence from each independent read path."""

    def __init__(self) -> None:
        self._records: dict[str, dict[str, dict[str, Any]]] = {}
        self._snapshot_monotonic: dict[tuple[str, str], float] = {}
        self._raw_monotonic: dict[tuple[str, str], float] = {}
        self._mode_monotonic: dict[tuple[str, str], float] = {}

    def record(
        self,
        serial: str,
        source: str,
        values: Mapping[str, Any],
        *,
        timestamp: str | None = None,
        observed_monotonic: float | None = None,
    ) -> None:
        """Record one source snapshot without retaining device identifiers."""
        observed_at = timestamp or datetime.now(UTC).isoformat()
        monotonic_at = (
            observed_monotonic
            if observed_monotonic is not None
            else time.monotonic()
        )
        source_key = (serial, source)
        self._snapshot_monotonic[source_key] = monotonic_at
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
            self._raw_monotonic[source_key] = monotonic_at
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
            self._mode_monotonic[source_key] = monotonic_at
            if mode_valid:
                record["mode_value"] = phase_mode
            else:
                record.pop("mode_value", None)

        sources[source] = record

    def source_evidence(self, serial: str, source: str) -> PhaseEvidence | None:
        """Return exact evidence only when the latest source snapshot carried it."""
        record = self._records.get(serial, {}).get(source)
        if record is None:
            return None
        source_key = (serial, source)
        snapshot_monotonic = self._snapshot_monotonic.get(source_key)
        if snapshot_monotonic is None:
            return None

        if source in {"direct_241_44", "provider_parent_accessory"}:
            raw_value = record.get("raw_value")
            if (
                record.get("raw_present_in_last_snapshot") is not True
                or self._raw_monotonic.get(source_key) != snapshot_monotonic
                or not isinstance(raw_value, int)
                or isinstance(raw_value, bool)
                or raw_value not in _RAW_PHASE_MODES
            ):
                return None
            return PhaseEvidence(
                source=source,
                mode=_RAW_PHASE_MODES[raw_value],
                observed_monotonic=snapshot_monotonic,
            )

        if source == "direct_2_34":
            mode = record.get("mode_value")
            if (
                record.get("mode_present_in_last_snapshot") is not True
                or self._mode_monotonic.get(source_key) != snapshot_monotonic
                or mode not in _CONTROL_PHASE_MODES
            ):
                return None
            return PhaseEvidence(source, mode, snapshot_monotonic)
        return None

    def control_evidence(
        self,
        serial: str,
        *,
        now: float,
        direct_max_age: float,
        provider_max_age: float,
    ) -> PhaseEvidence | None:
        """Prefer fresh 241/44, then a qualified parent-accessory fallback."""
        direct = self.source_evidence(serial, "direct_241_44")
        if direct is not None and now - direct.observed_monotonic <= direct_max_age:
            return direct

        provider = self.source_evidence(serial, "provider_parent_accessory")
        if (
            provider is None
            or now - provider.observed_monotonic > provider_max_age
        ):
            return None
        if (
            direct is not None
            and direct.observed_monotonic > provider.observed_monotonic
            and direct.mode != provider.mode
        ):
            return None
        return provider

    def confirmation_source(
        self,
        serial: str,
        *,
        issued_at: float,
        expected_mode: str,
        prewrite_provider: PhaseEvidence | None,
        prewrite_max_age: float,
    ) -> str | None:
        """Confirm a post-write direct value or a real provider transition."""
        direct = self.source_evidence(serial, "direct_241_44")
        if direct is not None and direct.observed_monotonic > issued_at:
            return "direct" if direct.mode == expected_mode else None

        provider = self.source_evidence(serial, "provider_parent_accessory")
        if (
            prewrite_provider is not None
            and prewrite_provider.mode != expected_mode
            and 0
            <= issued_at - prewrite_provider.observed_monotonic
            <= prewrite_max_age
            and provider is not None
            and provider.observed_monotonic > issued_at
            and provider.observed_monotonic > prewrite_provider.observed_monotonic
            and provider.mode == expected_mode
        ):
            return "provider"
        return None

    def snapshot(self) -> list[dict[str, Any]]:
        """Return stable diagnostics with serials reduced to product prefixes."""
        return [
            {
                "device_prefix": serial[:4],
                "sources": {source: dict(values) for source, values in sorted(sources.items())},
            }
            for serial, sources in sorted(self._records.items())
        ]
