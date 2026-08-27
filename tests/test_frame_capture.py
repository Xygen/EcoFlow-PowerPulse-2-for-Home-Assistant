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
    inspect_get_request,
    inspect_observer_command_payloads,
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
    assert classify_mqtt_topic("/app/u/sn/thing/property/get") == "observed_get"
    assert classify_mqtt_topic("/open/account/sn/get") == "observed_get"
    assert not channel_carries_telemetry("observed_set")
    assert not channel_carries_telemetry("set_reply")
    assert not channel_carries_telemetry("observed_get")
    assert channel_carries_telemetry("property")
    assert channel_carries_telemetry("get_reply")


def test_json_get_request_summary_omits_ids_and_parameter_values() -> None:
    payload = (
        b'{"from":"Android","id":"secret-request-id","moduleType":0,'
        b'"operateType":"latestQuotas","params":{"secret":"hidden"},'
        b'"version":"1.0"}'
    )

    result = inspect_get_request(payload)

    assert result == {
        "classification": "json",
        "operate_type": "latestQuotas",
        "source": "Android",
        "module_type": 0,
        "version": "1.0",
        "parameter_keys": ["secret"],
    }
    assert "request-id" not in repr(result)
    assert "hidden" not in repr(result)


def test_protobuf_get_all_summary_retains_only_routing_metadata() -> None:
    header = b"".join(
        (
            encode_field_varint(2, 32),
            encode_field_varint(3, 32),
            encode_field_varint(14, 12345),
            encode_field_bytes(23, b"app"),
            encode_field_bytes(24, b"secret"),
        )
    )

    assert inspect_get_request(encode_field_bytes(1, header)) == {
        "classification": "protobuf",
        "cmd_src": 32,
        "cmd_dst": 32,
        "sequence": 12345,
        "source": "app",
    }


def test_envelope_metadata_exposes_command_tuple() -> None:
    pdata = encode_field_varint(1, 3)
    header = b"".join(
        (
            encode_field_bytes(1, pdata),
            encode_field_varint(2, 2),
            encode_field_varint(3, 32),
            encode_field_varint(6, 1),
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
            "need_ack": 1,
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


def test_small_observer_command_is_xor_decoded_without_raw_bytes() -> None:
    pdata = encode_field_varint(1, 7)
    sequence = 185
    key = sequence & 0xFF
    encrypted = bytes(byte ^ key for byte in pdata)
    header = b"".join(
        (
            encode_field_bytes(1, encrypted),
            encode_field_varint(8, 96),
            encode_field_varint(9, 97),
            encode_field_varint(6, 1),
            encode_field_varint(11, 1),
            encode_field_varint(14, sequence),
        )
    )

    result = inspect_observer_command_payloads(
        encode_field_bytes(1, header), fingerprint_key=b"test-runtime-key"
    )
    fingerprint = result[0].pop("runtime_fingerprint")

    assert len(fingerprint) == 16
    assert result == [
        {
            "cmd_func": 96,
            "cmd_id": 97,
            "decoded_size": 2,
            "sequence": sequence,
            "xor_decoded": True,
            "classification": "small_numeric_only",
            "fields": [{"field": 1, "wire_type": 0, "small_value": 7}],
        }
    ]


def test_observer_command_omits_opaque_content_and_other_tuples() -> None:
    secret = b"vehicle-secret"
    safe_header = b"".join(
        (
            encode_field_bytes(1, encode_field_bytes(2, secret)),
            encode_field_varint(8, 96),
            encode_field_varint(9, 97),
        )
    )
    unrelated_header = b"".join(
        (
            encode_field_bytes(1, encode_field_varint(1, 7)),
            encode_field_varint(8, 2),
            encode_field_varint(9, 81),
        )
    )

    result = inspect_observer_command_payloads(
        encode_field_bytes(1, safe_header) + encode_field_bytes(1, unrelated_header),
        fingerprint_key=b"test-runtime-key",
    )
    fingerprint = result[0].pop("runtime_fingerprint")

    assert len(fingerprint) == 16
    assert result == [
        {
            "cmd_func": 96,
            "cmd_id": 97,
            "decoded_size": len(secret) + 2,
            "xor_decoded": False,
            "classification": "structured_opaque",
            "fields": [{"field": 2, "wire_type": 2, "size": len(secret)}],
        }
    ]
    assert "vehicle-secret" not in repr(result)


def test_241_102_need_ack_plaintext_exposes_bounded_settings_structure() -> None:
    secret = b"vehicle-secret"
    settings = b"".join(
        (
            encode_field_varint(1, 16),
            encode_field_varint(2, 2),
            encode_field_varint(3, 160),
            encode_field_varint(4, 60),
            encode_field_varint(5, 0),
            encode_field_varint(6, 60),
        )
    )
    pdata = encode_field_bytes(1, secret) + encode_field_bytes(4, settings)
    header = b"".join(
        (
            encode_field_bytes(1, pdata),
            encode_field_varint(8, 241),
            encode_field_varint(9, 102),
            # need_ack must not be mistaken for enc_type.
            encode_field_varint(11, 1),
            encode_field_varint(14, 1234),
        )
    )

    result = inspect_observer_command_payloads(
        encode_field_bytes(1, header), fingerprint_key=b"test-runtime-key"
    )
    whole_fingerprint = result[0].pop("runtime_fingerprint")
    secret_fingerprint = result[0]["fields"][0].pop("runtime_fingerprint")
    settings_fingerprint = result[0]["fields"][1].pop("runtime_fingerprint")

    assert len(whole_fingerprint) == 16
    assert len(secret_fingerprint) == 16
    assert len(settings_fingerprint) == 16
    assert len(pdata) == 31
    assert result == [
        {
            "cmd_func": 241,
            "cmd_id": 102,
            "decoded_size": len(pdata),
            "sequence": 1234,
            "xor_decoded": False,
            "classification": "structured_opaque",
            "fields": [
                {"field": 1, "wire_type": 2, "size": len(secret)},
                {
                    "field": 4,
                    "wire_type": 2,
                    "size": len(settings),
                    "small_settings_bytes": list(settings),
                    "nested_fields": [
                        {"field": 1, "wire_type": 0, "small_value": 16},
                        {"field": 2, "wire_type": 0, "small_value": 2},
                        {"field": 3, "wire_type": 0, "small_value": 160},
                        {"field": 4, "wire_type": 0, "small_value": 60},
                        {"field": 5, "wire_type": 0, "small_value": 0},
                        {"field": 6, "wire_type": 0, "small_value": 60},
                    ],
                },
            ],
        }
    ]
    assert "vehicle-secret" not in repr(result)
    assert secret.hex() not in repr(result)


def test_241_100_exposes_only_small_start_stop_value() -> None:
    secret = b"vehicle-secret"
    pdata = encode_field_bytes(1, secret) + encode_field_varint(4, 1)
    header = b"".join(
        (
            encode_field_bytes(1, pdata),
            encode_field_varint(8, 241),
            encode_field_varint(9, 100),
            encode_field_varint(11, 1),
            encode_field_varint(14, 118),
        )
    )

    result = inspect_observer_command_payloads(
        encode_field_bytes(1, header), fingerprint_key=b"test-runtime-key"
    )
    result[0].pop("runtime_fingerprint")
    result[0]["fields"][0].pop("runtime_fingerprint")

    assert result == [
        {
            "cmd_func": 241,
            "cmd_id": 100,
            "decoded_size": len(pdata),
            "sequence": 118,
            "xor_decoded": False,
            "classification": "structured_opaque",
            "fields": [
                {"field": 1, "wire_type": 2, "size": len(secret)},
                {"field": 4, "wire_type": 0, "small_value": 1},
            ],
        }
    ]
    assert "vehicle-secret" not in repr(result)
    assert secret.hex() not in repr(result)


def test_241_102_exposes_only_tiny_top_level_settings_bytes() -> None:
    secret = b"vehicle-secret"
    display_settings = bytes((66, 7, 1, 1, 25, 25, 2, 0, 0))
    pdata = encode_field_bytes(1, secret) + encode_field_bytes(4, display_settings)
    header = b"".join(
        (
            encode_field_bytes(1, pdata),
            encode_field_varint(8, 241),
            encode_field_varint(9, 102),
            encode_field_varint(14, 9),
        )
    )

    result = inspect_observer_command_payloads(
        encode_field_bytes(1, header), fingerprint_key=b"test-runtime-key"
    )
    fields = result[0]["fields"]

    assert fields[0]["size"] == len(secret)
    assert "small_settings_bytes" not in fields[0]
    assert fields[1]["small_settings_bytes"] == list(display_settings)
    assert "vehicle-secret" not in repr(result)


def test_241_102_command_omits_body_over_pair_specific_limit() -> None:
    pdata = b"X" * 65
    header = b"".join(
        (
            encode_field_bytes(1, pdata),
            encode_field_varint(8, 241),
            encode_field_varint(9, 102),
        )
    )

    result = inspect_observer_command_payloads(
        encode_field_bytes(1, header), fingerprint_key=b"test-runtime-key"
    )

    assert result == [
        {
            "cmd_func": 241,
            "cmd_id": 102,
            "decoded_size": 65,
            "xor_decoded": False,
            "classification": "omitted_size_limit",
        }
    ]
    assert "58" * 65 not in repr(result)


def test_opaque_runtime_fingerprint_supports_equality_only() -> None:
    def envelope(pdata: bytes, sequence: int) -> bytes:
        key = sequence & 0xFF
        encrypted = bytes(byte ^ key for byte in pdata)
        header = b"".join(
            (
                encode_field_bytes(1, encrypted),
                encode_field_varint(8, 96),
                encode_field_varint(9, 97),
                encode_field_varint(6, 1),
                encode_field_varint(14, sequence),
            )
        )
        return encode_field_bytes(1, header)

    capture = DiagnosticFrameCapture(fingerprint_key=b"runtime-secret")
    first = capture.inspect_observer_command_payloads(envelope(b"\xff\x00", 1))[0]
    repeated = capture.inspect_observer_command_payloads(envelope(b"\xff\x00", 2))[0]
    changed = capture.inspect_observer_command_payloads(envelope(b"\xff\x01", 3))[0]

    assert first["classification"] == "opaque_non_protobuf"
    assert first["runtime_fingerprint"] == repeated["runtime_fingerprint"]
    assert first["runtime_fingerprint"] != changed["runtime_fingerprint"]
    assert "ff00" not in repr(first)


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


def test_get_request_view_survives_frequent_telemetry() -> None:
    capture = DiagnosticFrameCapture(max_recent=3, max_requests=2)
    capture.record(_frame("observed_get", 0, 0, "get-1"))
    capture.record(_frame("observed_get", 0, 0, "get-2"))
    for index in range(10):
        capture.record(_frame("property", 2, 33, f"telemetry-{index}"))

    assert [frame["timestamp"] for frame in capture.requests] == ["get-1", "get-2"]
    assert capture.bucket_snapshot()["observed_get:0/0"]["count"] == 2


def test_command_correlation_counts_retries_and_reply_by_sequence() -> None:
    capture = DiagnosticFrameCapture(max_correlations=2)
    request = _frame("observed_set", 96, 97, "request")
    request.update(
        {
            "device_prefix": "HJ31",
            "source_role": "powerocean_observer",
            "protocol_headers": [
                {"cmd_func": 96, "cmd_id": 97, "sequence": 185}
            ],
        }
    )
    reply = _frame("set_reply", 96, 97, "reply")
    reply.update(
        {
            "device_prefix": "HJ31",
            "source_role": "powerocean_observer",
            "protocol_headers": [
                {"cmd_func": 96, "cmd_id": 97, "sequence": 185}
            ],
        }
    )

    capture.record(request)
    capture.record(request)
    capture.record(reply)

    assert capture.command_correlations == [
        {
            "device_prefix": "HJ31",
            "source_role": "powerocean_observer",
            "sequence": 185,
            "first_timestamp": "request",
            "last_timestamp": "reply",
            "request_count": 2,
            "reply_count": 1,
            "request_pairs": ["96/97"],
            "reply_pairs": ["96/97"],
            "status": "matched",
        }
    ]
