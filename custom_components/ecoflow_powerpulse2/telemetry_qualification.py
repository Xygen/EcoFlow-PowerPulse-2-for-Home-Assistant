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
    values: Mapping[str, Any],
    *,
    direct_heartbeat_fresh: bool,
    powerocean_power_fresh: bool,
) -> object:
    """Return fast PowerOcean power only when Direct confirms physical charging.

    PowerOcean relay reports can claim a non-zero charging power while a fresh
    Direct heartbeat proves the wallbox is idle. A stale or absent Direct state
    must not turn an unqualified PowerOcean report into automation-safe data.

    The two ages are tracked separately and neither substitutes for the other.
    Direct says whether the wallbox is charging at all; the PowerOcean age says
    whether the number itself still describes now. A charger that is genuinely
    charging while the relay has gone quiet leaves the reading unknown rather
    than freezing the last watts, because a frozen value is indistinguishable
    from a live one to an automation.

    Idle is decided by Direct alone, and deliberately so: a fresh Direct idle
    state proves there is nothing to measure, so no PowerOcean report of any age
    is needed to report zero.
    """
    direct_status = values.get("direct_charging_status")
    if not direct_heartbeat_fresh:
        return None
    if direct_status == "charging":
        if not powerocean_power_fresh:
            return None
        return values.get("powerocean_charging_power_w")
    if direct_status in _DIRECT_IDLE_STATUSES:
        return 0.0
    return None
