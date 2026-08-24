from custom_components.ecoflow_powerpulse2.ecoflow.energy_stream import (
    build_powerpulse_phase_payload,
    build_powerpulse_settings_payload,
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
    for settings in ({}, {8: 1}, {1: -1}):
        try:
            build_powerpulse_settings_payload(b"opaque", settings, seq=1)
        except ValueError:
            pass
        else:
            raise AssertionError(f"unsafe settings accepted: {settings}")
