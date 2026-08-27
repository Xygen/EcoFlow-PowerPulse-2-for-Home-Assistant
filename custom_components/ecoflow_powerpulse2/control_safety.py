"""Pure helpers for evidence-backed charging-time control interlocks."""

from __future__ import annotations

CHARGING_LOCKED_SETTING_KEYS = frozenset(
    {
        "continuous_charging",
        "output_current_max_raw",
        "phase_mode",
        "solar_current_min_raw",
        "work_mode",
    }
)

_KNOWN_NON_CHARGING_STATUSES = frozenset(
    {
        "unplugged",
        "plugged_in",
        "paused",
        "charge_complete",
        "standby",
    }
)


def control_allowed_for_status(setting_key: str, charging_status: object) -> bool:
    """Return whether a setting may be written for the observed charger state."""
    if setting_key not in CHARGING_LOCKED_SETTING_KEYS:
        return True
    return charging_status in _KNOWN_NON_CHARGING_STATUSES
