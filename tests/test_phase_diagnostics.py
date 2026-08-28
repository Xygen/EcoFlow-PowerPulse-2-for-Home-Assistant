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
