"""Pure safety rules for charger Start and Stop actions."""

from __future__ import annotations

START_ACTION = "start"
STOP_ACTION = "stop"
START_ACTION_CONFIRM_SECONDS = 30
STOP_ACTION_CONFIRM_SECONDS = 15

_STARTABLE_STATUSES = frozenset({"plugged_in", "paused", "charge_complete", "standby"})
_STOPPABLE_STATUSES = frozenset({"charging", "paused"})
_START_CONFIRMED_STATUSES = frozenset({"charging", "paused"})
_STOP_CONFIRMED_STATUSES = frozenset({"plugged_in", "charge_complete", "standby"})


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


def charge_action_confirm_seconds(action: str) -> int:
    """Return the independent device-readback window for one charge action."""
    if action == START_ACTION:
        return START_ACTION_CONFIRM_SECONDS
    if action == STOP_ACTION:
        return STOP_ACTION_CONFIRM_SECONDS
    raise ValueError(f"Unknown charging action: {action}")
