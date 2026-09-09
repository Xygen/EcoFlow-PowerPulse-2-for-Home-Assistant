"""Tests for automation-safe PowerOcean telemetry qualification."""

import pytest

from custom_components.ecoflow_powerpulse2.telemetry_qualification import (
    qualified_powerocean_charging_power,
)


def test_qualified_power_keeps_fast_power_during_direct_charging() -> None:
    assert (
        qualified_powerocean_charging_power(
            {
                "direct_charging_status": "charging",
                "powerocean_charging_power_w": 1352,
            },
            direct_heartbeat_fresh=True,
        )
        == 1352
    )


@pytest.mark.parametrize(
    "direct_status",
    ("unplugged", "plugged_in", "paused", "charge_complete", "standby", "updating"),
)
def test_qualified_power_rejects_false_power_while_direct_is_idle(
    direct_status: str,
) -> None:
    assert (
        qualified_powerocean_charging_power(
            {
                "direct_charging_status": direct_status,
                "powerocean_charging_power_w": 4380,
            },
            direct_heartbeat_fresh=True,
        )
        == 0.0
    )


def test_qualified_power_requires_a_fresh_direct_heartbeat() -> None:
    assert (
        qualified_powerocean_charging_power(
            {
                "direct_charging_status": "charging",
                "powerocean_charging_power_w": 1352,
            },
            direct_heartbeat_fresh=False,
        )
        is None
    )


def test_qualified_power_is_unknown_for_an_unmapped_direct_status() -> None:
    assert (
        qualified_powerocean_charging_power(
            {
                "direct_charging_status": "unknown",
                "powerocean_charging_power_w": 4380,
            },
            direct_heartbeat_fresh=True,
        )
        is None
    )
