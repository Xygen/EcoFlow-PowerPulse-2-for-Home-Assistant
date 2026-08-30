import pytest

from custom_components.ecoflow_powerpulse2.phase_diagnostics import PhaseReadbackTracker


def test_phase_readback_sources_remain_separate_and_redacted() -> None:
    tracker = PhaseReadbackTracker()
    tracker.record(
        "C376SECRET",
        "direct_241_44",
        {"phase_specified_raw": 2, "phase_mode": "three_phase"},
        timestamp="2026-08-28T09:39:30+00:00",
    )
    tracker.record(
        "C376SECRET",
        "provider_parent_accessory",
        {"phase_specified_raw": 7},
        timestamp="2026-08-28T09:39:45+00:00",
    )

    assert tracker.snapshot() == [
        {
            "device_prefix": "C376",
            "sources": {
                "direct_241_44": {
                    "last_snapshot_at": "2026-08-28T09:39:30+00:00",
                    "raw_present_in_last_snapshot": True,
                    "mode_present_in_last_snapshot": True,
                    "raw_value_valid": True,
                    "last_raw_at": "2026-08-28T09:39:30+00:00",
                    "raw_value": 2,
                    "mode_value_valid": True,
                    "last_mode_at": "2026-08-28T09:39:30+00:00",
                    "mode_value": "three_phase",
                },
                "provider_parent_accessory": {
                    "last_snapshot_at": "2026-08-28T09:39:45+00:00",
                    "raw_present_in_last_snapshot": True,
                    "mode_present_in_last_snapshot": False,
                    "raw_value_valid": True,
                    "last_raw_at": "2026-08-28T09:39:45+00:00",
                    "raw_value": 7,
                },
            },
        }
    ]


def test_missing_provider_value_preserves_last_observation_but_marks_snapshot() -> None:
    tracker = PhaseReadbackTracker()
    tracker.record(
        "C376DEVICE",
        "provider_device_detail",
        {"phase_specified_raw": 0},
        timestamp="2026-08-28T09:40:00+00:00",
    )
    tracker.record(
        "C376DEVICE",
        "provider_device_detail",
        {},
        timestamp="2026-08-28T09:41:00+00:00",
    )

    source = tracker.snapshot()[0]["sources"]["provider_device_detail"]
    assert source["last_snapshot_at"] == "2026-08-28T09:41:00+00:00"
    assert source["raw_present_in_last_snapshot"] is False
    assert source["raw_value"] == 0
    assert source["last_raw_at"] == "2026-08-28T09:40:00+00:00"


def test_fresh_direct_phase_is_authoritative_over_lagging_provider() -> None:
    tracker = PhaseReadbackTracker()
    tracker.record(
        "C376DEVICE",
        "provider_parent_accessory",
        {"phase_specified_raw": 1},
        observed_monotonic=100,
    )
    tracker.record(
        "C376DEVICE",
        "direct_241_44",
        {"phase_specified_raw": 2},
        observed_monotonic=105,
    )

    evidence = tracker.control_evidence(
        "C376DEVICE", now=106, direct_max_age=10, provider_max_age=60
    )
    assert evidence is not None
    assert (evidence.source, evidence.mode) == ("direct_241_44", "three_phase")


def test_parent_accessory_is_fallback_when_direct_is_not_fresh() -> None:
    tracker = PhaseReadbackTracker()
    tracker.record(
        "C376DEVICE",
        "direct_241_44",
        {"phase_specified_raw": 1},
        observed_monotonic=100,
    )
    tracker.record(
        "C376DEVICE",
        "provider_parent_accessory",
        {"phase_specified_raw": 2},
        observed_monotonic=120,
    )

    evidence = tracker.control_evidence(
        "C376DEVICE", now=121, direct_max_age=10, provider_max_age=60
    )
    assert evidence is not None
    assert (evidence.source, evidence.mode) == (
        "provider_parent_accessory",
        "three_phase",
    )


def test_newer_conflicting_stale_direct_blocks_older_provider_fallback() -> None:
    tracker = PhaseReadbackTracker()
    tracker.record(
        "C376DEVICE",
        "provider_parent_accessory",
        {"phase_specified_raw": 0},
        observed_monotonic=100,
    )
    tracker.record(
        "C376DEVICE",
        "direct_241_44",
        {"phase_specified_raw": 1},
        observed_monotonic=105,
    )

    assert tracker.control_evidence(
        "C376DEVICE", now=116, direct_max_age=10, provider_max_age=60
    ) is None


@pytest.mark.parametrize("raw_value", [True, 1.0, 1.5, float("nan"), float("inf"), -1, 3])
def test_provider_control_evidence_requires_exact_raw_value(raw_value: object) -> None:
    tracker = PhaseReadbackTracker()
    tracker.record(
        "C376DEVICE",
        "provider_parent_accessory",
        {"phase_specified_raw": raw_value},
        observed_monotonic=100,
    )

    assert tracker.control_evidence(
        "C376DEVICE", now=101, direct_max_age=10, provider_max_age=60
    ) is None


def test_missing_latest_provider_field_and_device_detail_are_not_fallbacks() -> None:
    tracker = PhaseReadbackTracker()
    tracker.record(
        "C376DEVICE",
        "provider_parent_accessory",
        {"phase_specified_raw": 0},
        observed_monotonic=100,
    )
    tracker.record(
        "C376DEVICE",
        "provider_parent_accessory",
        {},
        observed_monotonic=101,
    )
    tracker.record(
        "C376DEVICE",
        "provider_device_detail",
        {"phase_specified_raw": 2},
        observed_monotonic=102,
    )

    assert tracker.control_evidence(
        "C376DEVICE", now=103, direct_max_age=10, provider_max_age=60
    ) is None


def test_cp307_settings_phase_remains_separate_non_control_evidence() -> None:
    tracker = PhaseReadbackTracker()
    tracker.record(
        "C376DEVICE",
        "direct_2_34",
        {"phase_mode": "auto"},
        observed_monotonic=100,
    )

    evidence = tracker.source_evidence("C376DEVICE", "direct_2_34")
    assert evidence is not None and evidence.mode == "auto"
    assert tracker.control_evidence(
        "C376DEVICE", now=101, direct_max_age=10, provider_max_age=60
    ) is None


def test_provider_confirmation_requires_a_transition_from_different_prewrite_value() -> None:
    tracker = PhaseReadbackTracker()
    tracker.record(
        "C376DEVICE",
        "provider_parent_accessory",
        {"phase_specified_raw": 1},
        observed_monotonic=100,
    )
    prewrite = tracker.source_evidence("C376DEVICE", "provider_parent_accessory")
    tracker.record(
        "C376DEVICE",
        "provider_parent_accessory",
        {"phase_specified_raw": 2},
        observed_monotonic=120,
    )

    assert tracker.confirmation_source(
        "C376DEVICE",
        issued_at=110,
        expected_mode="three_phase",
        prewrite_provider=prewrite,
        prewrite_max_age=60,
    ) == "provider"


def test_provider_already_at_target_cannot_confirm_without_direct_readback() -> None:
    tracker = PhaseReadbackTracker()
    tracker.record(
        "C376DEVICE",
        "provider_parent_accessory",
        {"phase_specified_raw": 2},
        observed_monotonic=100,
    )
    prewrite = tracker.source_evidence("C376DEVICE", "provider_parent_accessory")
    tracker.record(
        "C376DEVICE",
        "provider_parent_accessory",
        {"phase_specified_raw": 2},
        observed_monotonic=120,
    )

    assert tracker.confirmation_source(
        "C376DEVICE",
        issued_at=110,
        expected_mode="three_phase",
        prewrite_provider=prewrite,
        prewrite_max_age=60,
    ) is None


def test_postwrite_direct_mismatch_blocks_provider_confirmation() -> None:
    tracker = PhaseReadbackTracker()
    tracker.record(
        "C376DEVICE",
        "provider_parent_accessory",
        {"phase_specified_raw": 1},
        observed_monotonic=100,
    )
    prewrite = tracker.source_evidence("C376DEVICE", "provider_parent_accessory")
    tracker.record(
        "C376DEVICE",
        "provider_parent_accessory",
        {"phase_specified_raw": 2},
        observed_monotonic=120,
    )
    tracker.record(
        "C376DEVICE",
        "direct_241_44",
        {"phase_specified_raw": 0},
        observed_monotonic=121,
    )

    assert tracker.confirmation_source(
        "C376DEVICE",
        issued_at=110,
        expected_mode="three_phase",
        prewrite_provider=prewrite,
        prewrite_max_age=60,
    ) is None


def test_postwrite_direct_target_confirms_without_provider_transition() -> None:
    tracker = PhaseReadbackTracker()
    tracker.record(
        "C376DEVICE",
        "direct_241_44",
        {"phase_specified_raw": 2},
        observed_monotonic=120,
    )

    assert tracker.confirmation_source(
        "C376DEVICE",
        issued_at=110,
        expected_mode="three_phase",
        prewrite_provider=None,
        prewrite_max_age=60,
    ) == "direct"


def test_stale_prewrite_provider_value_cannot_confirm_transition() -> None:
    tracker = PhaseReadbackTracker()
    tracker.record(
        "C376DEVICE",
        "provider_parent_accessory",
        {"phase_specified_raw": 1},
        observed_monotonic=10,
    )
    prewrite = tracker.source_evidence("C376DEVICE", "provider_parent_accessory")
    tracker.record(
        "C376DEVICE",
        "provider_parent_accessory",
        {"phase_specified_raw": 2},
        observed_monotonic=120,
    )

    assert tracker.confirmation_source(
        "C376DEVICE",
        issued_at=110,
        expected_mode="three_phase",
        prewrite_provider=prewrite,
        prewrite_max_age=60,
    ) is None
