"""Bounded privacy-safe diagnostics for Start and Stop readback."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any

_KNOWN_STATES = frozenset(
    {
        "none",
        "available",
        "preparing",
        "charging",
        "suspended_vehicle",
        "suspended_charger",
        "finishing",
        "faulted",
        "unknown",
        "unplugged",
        "plugged_in",
        "paused",
        "charge_complete",
        "standby",
    }
)


def _safe_state(value: object) -> str | None:
    return value if isinstance(value, str) and value in _KNOWN_STATES else None


def _elapsed(started_at: float, observed_at: float) -> float:
    return round(max(0.0, observed_at - started_at), 3)


@dataclass
class _ActiveAttempt:
    issued_monotonic: float
    record: dict[str, Any]


class ChargeActionDiagnostics:
    """Retain bounded source-qualified timing records without identifiers."""

    def __init__(self, max_attempts: int) -> None:
        if max_attempts <= 0:
            raise ValueError("max_attempts must be positive")
        self._max_attempts = max_attempts
        self._active: dict[str, _ActiveAttempt] = {}
        self._completed: deque[dict[str, Any]] = deque(maxlen=max_attempts)

    def begin(
        self,
        serial: str,
        *,
        action: str,
        issued_at: str,
        issued_monotonic: float,
        pre_direct_state: object,
        pre_direct_reported_at: float,
    ) -> None:
        """Begin one attempt after all local preconditions have passed."""
        self.finish(
            serial,
            outcome="superseded",
            completed_monotonic=issued_monotonic,
        )
        self._active[serial] = _ActiveAttempt(
            issued_monotonic=issued_monotonic,
            record={
                "device_prefix": serial[:4],
                "action": action,
                "issued_at": issued_at,
                "pre_direct_state": _safe_state(pre_direct_state),
                "pre_direct_age_seconds": (
                    _elapsed(pre_direct_reported_at, issued_monotonic)
                    if pre_direct_reported_at > 0
                    else None
                ),
                "publish_result": "pending",
                "set_reply_result": "not_received",
                "set_reply_latency_seconds": None,
                "first_post_command_direct_state": None,
                "first_post_command_direct_latency_seconds": None,
                "first_post_command_powerocean_state": None,
                "first_post_command_powerocean_latency_seconds": None,
                "confirmation_source": None,
                "progress_extension_granted": False,
            },
        )

    def record_publish(self, serial: str, result: str) -> None:
        """Record only the bounded publish outcome classification."""
        attempt = self._active.get(serial)
        if attempt is not None:
            attempt.record["publish_result"] = result

    def record_set_reply(
        self, serial: str, *, result: str, observed_monotonic: float
    ) -> None:
        """Record correlated SET-reply outcome and relative latency."""
        attempt = self._active.get(serial)
        if attempt is None:
            return
        attempt.record["set_reply_result"] = result
        attempt.record["set_reply_latency_seconds"] = _elapsed(
            attempt.issued_monotonic, observed_monotonic
        )

    def record_progress_extension(self, serial: str) -> None:
        """Record that qualified Direct progress extended this attempt once."""
        attempt = self._active.get(serial)
        if attempt is not None:
            attempt.record["progress_extension_granted"] = True

    def record_direct(
        self, serial: str, state: object, *, observed_monotonic: float
    ) -> None:
        """Record the first newer Direct state for the active attempt."""
        self._record_first_state(
            serial,
            source="direct",
            state=state,
            observed_monotonic=observed_monotonic,
        )

    def record_powerocean(
        self, serial: str, state: object, *, observed_monotonic: float
    ) -> None:
        """Record the first newer exact-serial PowerOcean state for diagnostics."""
        self._record_first_state(
            serial,
            source="powerocean",
            state=state,
            observed_monotonic=observed_monotonic,
        )

    def _record_first_state(
        self,
        serial: str,
        *,
        source: str,
        state: object,
        observed_monotonic: float,
    ) -> None:
        attempt = self._active.get(serial)
        safe_state = _safe_state(state)
        state_key = f"first_post_command_{source}_state"
        if (
            attempt is None
            or observed_monotonic <= attempt.issued_monotonic
            or safe_state is None
            or attempt.record[state_key] is not None
        ):
            return
        attempt.record[state_key] = safe_state
        attempt.record[f"first_post_command_{source}_latency_seconds"] = _elapsed(
            attempt.issued_monotonic, observed_monotonic
        )

    def finish(
        self,
        serial: str,
        *,
        outcome: str,
        completed_monotonic: float,
        confirmation_source: str | None = None,
    ) -> None:
        """Complete and retain one attempt if it is currently active."""
        attempt = self._active.pop(serial, None)
        if attempt is None:
            return
        attempt.record.update(
            {
                "confirmation_source": confirmation_source,
                "outcome": outcome,
                "elapsed_seconds": _elapsed(
                    attempt.issued_monotonic, completed_monotonic
                ),
            }
        )
        self._completed.append(attempt.record)

    def snapshot(self) -> dict[str, Any]:
        """Return detached active and completed records for diagnostics export."""
        return {
            "max_completed_attempts": self._max_attempts,
            "active_attempts": [
                dict(attempt.record) for attempt in self._active.values()
            ],
            "recent_attempts": [dict(record) for record in self._completed],
        }
