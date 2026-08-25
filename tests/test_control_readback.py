from custom_components.ecoflow_powerpulse2.control_readback import (
    fresh_direct_value_available,
    fresh_polled_value_matches,
    matching_readback_source,
    provider_readback_attempt_details,
)


def test_phase_control_requires_recent_direct_value() -> None:
    values = {"phase_mode": "auto"}
    assert fresh_direct_value_available(
        current_values=values,
        direct_reported_at=100,
        now=109,
        max_age=10,
        key="phase_mode",
        allowed_values={"auto", "one_phase", "three_phase"},
    )
    assert not fresh_direct_value_available(
        current_values=values,
        direct_reported_at=100,
        now=111,
        max_age=10,
        key="phase_mode",
        allowed_values={"auto", "one_phase", "three_phase"},
    )
    assert not fresh_direct_value_available(
        current_values={"phase_specified_raw": 1},
        direct_reported_at=108,
        now=109,
        max_age=10,
        key="phase_mode",
        allowed_values={"auto", "one_phase", "three_phase"},
    )


def test_direct_readback_requires_fresh_matching_current_value() -> None:
    assert matching_readback_source(
        current_values={"switch_bits_raw": 19},
        direct_reported_at=11,
        polled_values={},
        polled_at=0,
        issued_at=10,
        expected_key="switch_bits_raw",
        expected_value=19,
    ) == "direct"
    assert matching_readback_source(
        current_values={"switch_bits_raw": 19},
        direct_reported_at=9,
        polled_values={},
        polled_at=0,
        issued_at=10,
        expected_key="switch_bits_raw",
        expected_value=19,
    ) is None


def test_provider_readback_requires_key_in_fresh_raw_snapshot() -> None:
    assert matching_readback_source(
        current_values={"battery_discharge_disabled": True},
        direct_reported_at=0,
        polled_values={"battery_discharge_disabled": True},
        polled_at=12,
        issued_at=10,
        expected_key="battery_discharge_disabled",
        expected_value=True,
    ) == "provider"
    assert matching_readback_source(
        current_values={"battery_discharge_disabled": True},
        direct_reported_at=0,
        polled_values={},
        polled_at=12,
        issued_at=10,
        expected_key="battery_discharge_disabled",
        expected_value=True,
    ) is None


def test_provider_attempt_details_distinguish_lag_from_missing_key() -> None:
    assert provider_readback_attempt_details(
        polled_values={"work_mode": "solar"},
        polled_at=12,
        issued_at=10,
        expected_key="work_mode",
        expected_value="fast",
    ) == {
        "snapshot_after_command": True,
        "expected_key_present": True,
        "matched": False,
    }
    assert provider_readback_attempt_details(
        polled_values={"phase_specified_raw": 1},
        polled_at=12,
        issued_at=10,
        expected_key="phase_mode",
        expected_value="one_phase",
    ) == {
        "snapshot_after_command": True,
        "expected_key_present": False,
        "matched": False,
    }


def test_noop_requires_recent_raw_provider_value() -> None:
    assert fresh_polled_value_matches(
        polled_values={"plug_and_play": True},
        polled_at=100,
        now=130,
        max_age=60,
        expected_key="plug_and_play",
        expected_value=True,
    )
    assert not fresh_polled_value_matches(
        polled_values={"plug_and_play": True},
        polled_at=100,
        now=161,
        max_age=60,
        expected_key="plug_and_play",
        expected_value=True,
    )
