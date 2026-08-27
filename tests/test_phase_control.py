from custom_components.ecoflow_powerpulse2.ecoflow.energy_stream import (
    build_powerpulse_charge_action_payload,
    build_powerpulse_phase_payload,
    build_powerpulse_settings_payload,
    build_powerpulse_smart_settings,
)
from custom_components.ecoflow_powerpulse2.ecoflow.proto_encoding import (
    iter_protobuf_fields,
)


def _bytes_field(payload: bytes, number: int) -> bytes:
    matches = [
        value
        for field, wire, value in iter_protobuf_fields(payload)
        if field == number and wire == 2 and isinstance(value, bytes)
    ]
    assert len(matches) == 1
    return matches[0]


def test_phase_control_matches_observed_241_102_shape() -> None:
    descriptor = b"opaque-accessory"
    payload, sequence = build_powerpulse_phase_payload(descriptor, 2, seq=1234)
    header = _bytes_field(payload, 1)
    header_fields = list(iter_protobuf_fields(header))
    varints = {
        field: value
        for field, wire, value in header_fields
        if wire == 0 and isinstance(value, int)
    }
    pdata = _bytes_field(header, 1)
    settings = _bytes_field(pdata, 4)

    assert sequence == 1234
    assert varints[2] == 32
    assert varints[3] == 96
    assert varints[8] == 241
    assert varints[9] == 102
    assert varints[11] == 1
    assert _bytes_field(pdata, 1) == descriptor
    assert list(iter_protobuf_fields(settings)) == [(5, 0, 2)]


def test_charge_actions_match_observed_241_100_shape() -> None:
    descriptor = b"opaque-accessory"
    for action, selector in (("stop", 1), ("start", 2)):
        payload, sequence = build_powerpulse_charge_action_payload(
            descriptor, action, seq=243
        )
        header = _bytes_field(payload, 1)
        header_fields = list(iter_protobuf_fields(header))
        varints = {
            field: value
            for field, wire, value in header_fields
            if wire == 0 and isinstance(value, int)
        }
        pdata = _bytes_field(header, 1)

        assert sequence == 243
        assert varints[3] == 96
        assert varints[8] == 241
        assert varints[9] == 100
        assert varints[11] == 1
        assert list(iter_protobuf_fields(pdata)) == [
            (1, 2, descriptor),
            (2, 0, selector),
        ]


def test_charge_action_rejects_unknown_action_or_missing_descriptor() -> None:
    for descriptor, action in ((b"opaque", "pause"), (b"", "start")):
        try:
            build_powerpulse_charge_action_payload(descriptor, action, seq=1)
        except ValueError:
            pass
        else:
            raise AssertionError("unsafe charging action accepted")


def test_settings_control_preserves_multi_field_app_shape() -> None:
    payload, _ = build_powerpulse_settings_payload(
        b"opaque-accessory", {1: 17, 2: 2, 4: 70}, seq=12
    )
    header = _bytes_field(payload, 1)
    pdata = _bytes_field(header, 1)
    settings = _bytes_field(pdata, 4)

    assert list(iter_protobuf_fields(settings)) == [
        (1, 0, 17),
        (2, 0, 2),
        (4, 0, 70),
    ]


def test_settings_control_rejects_unobserved_fields_and_ranges() -> None:
    for settings in ({}, {8: 1}, {22: 1}, {1: -1}, {7: b""}):
        try:
            build_powerpulse_settings_payload(b"opaque", settings, seq=1)
        except ValueError:
            pass
        else:
            raise AssertionError(f"unsafe settings accepted: {settings}")


def test_display_settings_match_observed_nested_shape() -> None:
    payload, _ = build_powerpulse_settings_payload(
        b"opaque-accessory", {21: bytes((1, 1, 25, 100, 0, 0))}, seq=171
    )
    header = _bytes_field(payload, 1)
    pdata = _bytes_field(header, 1)
    settings = _bytes_field(pdata, 4)

    assert list(iter_protobuf_fields(settings)) == [
        (21, 2, bytes((1, 1, 25, 100, 0, 0)))
    ]


def test_smart_energy_settings_match_observed_nested_shape() -> None:
    smart = build_powerpulse_smart_settings(
        ready_by_timestamp=1_787_625_600,
        target_type="energy",
        target_value=40_000,
    )
    payload, _ = build_powerpulse_settings_payload(
        b"opaque-accessory", {1: 0, 2: 4, 7: smart}, seq=65
    )
    header = _bytes_field(payload, 1)
    pdata = _bytes_field(header, 1)
    settings = _bytes_field(pdata, 4)
    nested = _bytes_field(settings, 7)

    assert list(iter_protobuf_fields(nested)) == [
        (1, 0, 1_787_625_600),
        (2, 0, 1),
        (3, 0, 40_000),
        (4, 0, 0),
    ]


def test_smart_distance_settings_include_calculated_energy() -> None:
    smart = build_powerpulse_smart_settings(
        ready_by_timestamp=1_787_625_600,
        target_type="distance",
        target_value=200,
        calculated_energy_wh=30_000,
    )

    assert list(iter_protobuf_fields(smart)) == [
        (1, 0, 1_787_625_600),
        (2, 0, 2),
        (3, 0, 30_000),
        (4, 0, 200),
    ]
