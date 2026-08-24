from __future__ import annotations

from struct import pack

from custom_components.ecoflow_powerpulse2.ecoflow.proto_encoding import (
    encode_field_bytes,
    encode_field_varint,
)
from custom_components.ecoflow_powerpulse2.frame_capture import (
    DiagnosticFrameCapture,
    channel_carries_telemetry,
    classify_mqtt_topic,
    inspect_envelope_headers,
    inspect_powerpulse_accessory_reports,
)


def _frame(channel: str, cmd_func: int, cmd_id: int, timestamp: str) -> dict:
    return {
        "timestamp": timestamp,
        "channel": channel,
        "protocol_headers": [{"cmd_func": cmd_func, "cmd_id": cmd_id}],
        "redacted_hex": "00",
    }


def test_command_channels_are_not_telemetry() -> None:
    assert classify_mqtt_topic("/app/u/sn/thing/property/set") == "observed_set"
    assert classify_mqtt_topic("/open/account/sn/set") == "observed_set"
    assert classify_mqtt_topic("/app/device/property/sn/set") == "observed_set"
    assert classify_mqtt_topic("/app/u/sn/thing/property/set_reply") == "set_reply"
    assert classify_mqtt_topic("/app/u/sn/thing/property/get_reply") == "get_reply"
    assert not channel_carries_telemetry("observed_set")
    assert not channel_carries_telemetry("set_reply")
    assert channel_carries_telemetry("property")
    assert channel_carries_telemetry("get_reply")


def test_envelope_metadata_exposes_command_tuple() -> None:
    pdata = encode_field_varint(1, 3)
    header = b"".join(
        (
            encode_field_bytes(1, pdata),
            encode_field_varint(2, 2),
            encode_field_varint(3, 32),
            encode_field_varint(8, 2),
            encode_field_varint(9, 33),
            encode_field_varint(10, len(pdata)),
            encode_field_varint(11, 1),
            encode_field_varint(14, 12345),
        )
    )

    assert inspect_envelope_headers(encode_field_bytes(1, header)) == [
        {
            "cmd_src": 2,
            "cmd_dst": 32,
            "cmd_func": 2,
            "cmd_id": 33,
            "declared_payload_size": len(pdata),
            "enc_type": 1,
            "sequence": 12345,
            "actual_payload_size": len(pdata),
        }
    ]


def test_powerocean_accessory_report_is_numeric_and_privacy_safe() -> None:
    report = b"".join(
        (
            encode_field_bytes(1, b"C376-serial-secret"),
            encode_field_varint(5, 0),
            encode_field_varint(6, 1),
            bytes(((8 << 3) | 5,)) + pack("<f", 0.0),
            bytes(((9 << 3) | 5,)) + pack("<f", 1815.0),
            encode_field_varint(10, 2),
            encode_field_varint(18, 9),
            encode_field_bytes(14, b"vehicle-secret"),
        )
    )
    header = b"".join(
        (
            encode_field_bytes(1, report),
            encode_field_varint(8, 209),
            encode_field_varint(9, 8),
        )
    )

    result = inspect_powerpulse_accessory_reports(encode_field_bytes(1, header))

    assert result == [
        {
            "target_prefix": "C376",
            "numeric_fields": {
                "5": 0,
                "6": 1,
                "8": 0.0,
                "9": 1815.0,
                "10": 2,
                "18": 9,
            },
            "byte_field_sizes": {"1": 18, "14": 14},
            "work_mode_raw": 2,
            "switch_bits_raw": 9,
            "cmd_id": 8,
        }
    ]
    assert "serial-secret" not in repr(result)
    assert "vehicle-secret" not in repr(result)


def test_command_bucket_survives_frequent_telemetry() -> None:
    capture = DiagnosticFrameCapture(max_recent=3, max_commands=3, max_samples_per_bucket=2)
    capture.record(_frame("observed_set", 2, 81, "command"))
    for index in range(10):
        capture.record(_frame("property", 2, 33, f"telemetry-{index}"))

    assert [frame["timestamp"] for frame in capture.recent] == [
        "telemetry-7",
        "telemetry-8",
        "telemetry-9",
    ]
    assert [frame["timestamp"] for frame in capture.commands] == ["command"]

    buckets = capture.bucket_snapshot()
    assert buckets["observed_set:2/81"]["count"] == 1
    assert buckets["observed_set:2/81"]["samples"][0]["timestamp"] == "command"
    assert buckets["property:2/33"]["count"] == 10
    assert [sample["timestamp"] for sample in buckets["property:2/33"]["samples"]] == [
        "telemetry-8",
        "telemetry-9",
    ]
