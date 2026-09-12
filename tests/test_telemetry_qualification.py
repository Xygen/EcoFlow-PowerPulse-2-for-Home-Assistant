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
            powerocean_power_fresh=True,
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
            powerocean_power_fresh=True,
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
            powerocean_power_fresh=True,
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
            powerocean_power_fresh=True,
        )
        is None
    )


def test_a_stale_relay_value_is_unknown_rather_than_frozen() -> None:
    """A frozen number is indistinguishable from a live one to an automation."""
    assert (
        qualified_powerocean_charging_power(
            {
                "direct_charging_status": "charging",
                "powerocean_charging_power_w": 6665,
            },
            direct_heartbeat_fresh=True,
            powerocean_power_fresh=False,
        )
        is None
    )


def test_an_absent_relay_value_is_unknown_while_charging() -> None:
    assert (
        qualified_powerocean_charging_power(
            {"direct_charging_status": "charging"},
            direct_heartbeat_fresh=True,
            powerocean_power_fresh=True,
        )
        is None
    )


@pytest.mark.parametrize("power_fresh", (True, False))
def test_direct_idle_reports_zero_whatever_the_relay_age(power_fresh: bool) -> None:
    """Fresh Direct idle proves there is nothing to measure.

    Zero does not depend on the relay, so a stale relay must not turn a known
    idle charger into an unknown reading.
    """
    assert (
        qualified_powerocean_charging_power(
            {
                "direct_charging_status": "charge_complete",
                "powerocean_charging_power_w": 4380,
            },
            direct_heartbeat_fresh=True,
            powerocean_power_fresh=power_fresh,
        )
        == 0.0
    )


def test_both_ages_must_qualify_before_a_value_is_published() -> None:
    """Neither age substitutes for the other."""
    values = {
        "direct_charging_status": "charging",
        "powerocean_charging_power_w": 1352,
    }
    assert (
        qualified_powerocean_charging_power(
            values, direct_heartbeat_fresh=False, powerocean_power_fresh=True
        )
        is None
    )
    assert (
        qualified_powerocean_charging_power(
            values, direct_heartbeat_fresh=True, powerocean_power_fresh=False
        )
        is None
    )
    assert (
        qualified_powerocean_charging_power(
            values, direct_heartbeat_fresh=True, powerocean_power_fresh=True
        )
        == 1352
    )
