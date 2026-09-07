"""Tests for automation-safe PowerOcean telemetry qualification."""

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


def test_qualified_power_rejects_false_power_while_direct_is_idle() -> None:
    assert (
        qualified_powerocean_charging_power(
            {
                "direct_charging_status": "charge_complete",
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


def test_qualified_power_is_zero_for_paused_direct_charging() -> None:
    assert (
        qualified_powerocean_charging_power(
            {
                "direct_charging_status": "paused",
                "powerocean_charging_power_w": 4380,
            },
            direct_heartbeat_fresh=True,
        )
        == 0.0
    )
