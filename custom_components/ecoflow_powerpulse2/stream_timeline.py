"""Bounded runtime evidence; never stores payloads, topics or full identifiers."""

from collections import deque
from copy import deepcopy
from datetime import UTC, datetime


class StreamTimeline:
    """Record transitions plus five-minute samples, without disk writes."""

    def __init__(self, limit: int = 2048) -> None:
        self.started_at = datetime.now(UTC).isoformat()
        self._events: deque[dict] = deque(maxlen=limit)
        self._sources: dict[str, str] = {}
        self._samples: dict[str, tuple[tuple, float]] = {}
        self._dropped = 0

    def record(
        self, serial: str, *, now: float, role: str, event: str,
        reason: str, connected: bool, settings_age: float | None,
        heartbeat_age: float | None, cooldown_remaining: float,
        settings_fresh: bool, heartbeat_fresh: bool,
        reason_code: int | None = None,
    ) -> None:
        """Called only on the HA loop with fixed event/reason vocabularies."""
        signature = (reason, connected, settings_fresh, heartbeat_fresh)
        if event == "recovery_check":
            previous = self._samples.get(serial)
            if previous and previous[0] == signature and now - previous[1] < 300:
                return
            self._samples[serial] = (signature, now)
        source = self._sources.setdefault(serial, f"source_{len(self._sources) + 1}")
        if len(self._events) == self._events.maxlen:
            self._dropped += 1
        self._events.append({
            "timestamp": datetime.now(UTC).isoformat(),
            "source": source, "role": role, "event": event, "reason": reason,
            "connected": connected, "reason_code": reason_code,
            "settings_age_s": round(settings_age, 3) if settings_age is not None else None,
            "heartbeat_age_s": round(heartbeat_age, 3) if heartbeat_age is not None else None,
            "settings_fresh": settings_fresh, "heartbeat_fresh": heartbeat_fresh,
            "cooldown_remaining_s": round(cooldown_remaining, 3),
        })

    def snapshot(self) -> dict:
        """Expose retention boundaries and detached records for diagnostics."""
        return {
            "started_at": self.started_at, "retention": "current_runtime_only",
            "timestamp_basis": "HA event-loop observation (UTC)",
            "limit": self._events.maxlen, "dropped_events": self._dropped,
            "sample_interval_s": 300,
            "events": deepcopy(list(self._events)),
        }
