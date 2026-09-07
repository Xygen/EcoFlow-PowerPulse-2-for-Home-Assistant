"""Source-qualified values safe for automation-facing telemetry."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

_DIRECT_IDLE_STATUSES = frozenset(
    {
        "unplugged",
        "plugged_in",
        "paused",
        "charge_complete",
        "standby",
        "updating",
    }
)


def qualified_powerocean_charging_power(
    values: Mapping[str, Any], *, direct_heartbeat_fresh: bool
) -> object:
    """Return fast PowerOcean power only when Direct confirms physical charging.

    PowerOcean relay reports can claim a non-zero charging power while a fresh
    Direct heartbeat proves the wallbox is idle. A stale or absent Direct state
    must not turn an unqualified PowerOcean report into automation-safe data.
    """
    direct_status = values.get("direct_charging_status")
    if not direct_heartbeat_fresh:
        return None
    if direct_status == "charging":
        return values.get("powerocean_charging_power_w")
    if direct_status in _DIRECT_IDLE_STATUSES:
        return 0.0
    return None
