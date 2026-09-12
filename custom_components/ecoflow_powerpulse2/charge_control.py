"""Pure safety rules for charger Start and Stop actions."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

START_ACTION = "start"
STOP_ACTION = "stop"
START_ACTION_CONFIRM_SECONDS = 30
START_ACTION_PROGRESS_CONFIRM_SECONDS = 50
STOP_ACTION_CONFIRM_SECONDS = 15

_STARTABLE_STATUSES = frozenset({"plugged_in", "paused", "charge_complete", "standby"})
_STOPPABLE_STATUSES = frozenset({"charging", "paused"})
_START_CONFIRMED_STATUSES = frozenset({"charging", "paused"})
_STOP_CONFIRMED_STATUSES = frozenset({"plugged_in", "charge_complete", "standby"})


def direct_charging_status(values: Mapping[str, Any]) -> object:
    """Return only the state paired with the Direct CP307 heartbeat source."""
    return values.get("direct_charging_status")


def charge_action_allowed(action: str, charging_status: object) -> bool:
    """Return whether an action is valid for the latest known charger state."""
    if action == START_ACTION:
        return charging_status in _STARTABLE_STATUSES
    if action == STOP_ACTION:
        return charging_status in _STOPPABLE_STATUSES
    return False


def charge_action_confirmed(action: str, charging_status: object) -> bool:
    """Return whether fresh heartbeat readback confirms an action outcome."""
    if action == START_ACTION:
        return charging_status in _START_CONFIRMED_STATUSES
    if action == STOP_ACTION:
        return charging_status in _STOP_CONFIRMED_STATUSES
    return False


def fresh_direct_charge_action_confirmed(
    action: str,
    values: Mapping[str, Any],
    *,
    heartbeat_reported_at: float,
    issued_at: float,
) -> bool:
    """Return whether one newer Direct heartbeat confirms the requested action."""
    return heartbeat_reported_at > issued_at and charge_action_confirmed(
        action, direct_charging_status(values)
    )


def fresh_direct_start_progress_observed(
    action: str,
    values: Mapping[str, Any],
    *,
    heartbeat_reported_at: float,
    issued_at: float,
    pre_direct_state: object,
) -> bool:
    """Return whether a newer Direct transition proves Start progress."""
    return (
        action == START_ACTION
        and heartbeat_reported_at > issued_at
        and pre_direct_state != "plugged_in"
        and direct_charging_status(values) == "plugged_in"
    )


def charge_action_confirm_seconds(action: str) -> int:
    """Return the independent device-readback window for one charge action."""
    if action == START_ACTION:
        return START_ACTION_CONFIRM_SECONDS
    if action == STOP_ACTION:
        return STOP_ACTION_CONFIRM_SECONDS
    raise ValueError(f"Unknown charging action: {action}")


def charge_action_progress_confirm_seconds(action: str) -> int:
    """Return the absolute deadline after qualified Start progress."""
    if action == START_ACTION:
        return START_ACTION_PROGRESS_CONFIRM_SECONDS
    return charge_action_confirm_seconds(action)
