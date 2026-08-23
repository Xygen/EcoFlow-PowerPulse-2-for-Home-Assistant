from __future__ import annotations

import json
from struct import pack

from custom_components.ecoflow_powerpulse2.ecoflow.proto_encoding import (
    encode_field_bytes,
    encode_field_varint,
)
from custom_components.ecoflow_powerpulse2.parser import parse_powerpulse2_payload


def _fixed32_tag(field: int, value: float) -> bytes:
    # All CP307 float fields exercised here fit in a two-byte protobuf tag.
    tag = (field << 3) | 5
    first = (tag & 0x7F) | 0x80
    second = tag >> 7
    return bytes((first, second)) + pack("<f", value)


def _heartbeat(*, state: int = 3, power: float = 3929.0) -> bytes:
    return b"".join(
        (
            encode_field_varint(1, state),
            encode_field_varint(9, 94708),
            encode_field_varint(17, 16),
            encode_field_varint(18, 16),
            _fixed32_tag(28, power),
            _fixed32_tag(29, 231.4),
            _fixed32_tag(30, 17.0),
            encode_field_varint(41, 720),
            encode_field_varint(42, 449),
            encode_field_varint(102, 0),
        )
    )


def test_cp307_heartbeat_inside_cloud_envelope() -> None:
    header = b"".join(
        (
            encode_field_bytes(1, _heartbeat()),
            encode_field_varint(8, 2),
            encode_field_varint(9, 33),
        )
    )
    result = parse_powerpulse2_payload(encode_field_bytes(1, header))

    assert result["charging_status"] == "charging"
    assert result["charging_power_w"] == 3929.0
    assert result["phase_voltage_v"] == 231.4
    assert result["phase_current_a"] == 17.0
    assert result["session_duration_s"] == 720
    assert result["session_energy_raw"] == 449


def test_cp307_xor_encoded_app_mqtt_envelope() -> None:
    """Regression test for the envelope observed on a live C376 charger."""
    heartbeat = _heartbeat(state=1, power=0.0)
    sequence = 5_499_149
    key = sequence & 0xFF
    encrypted = bytes(byte ^ key for byte in heartbeat)
    header = b"".join(
        (
            encode_field_bytes(1, encrypted),
            encode_field_varint(2, 2),
            encode_field_varint(3, 32),
            encode_field_varint(4, 1),
            encode_field_varint(6, 1),
            encode_field_varint(7, 3),
            encode_field_varint(8, 2),
            encode_field_varint(9, 33),
            encode_field_varint(10, len(heartbeat)),
            encode_field_varint(11, 1),
            encode_field_varint(14, sequence),
            encode_field_varint(15, 23_297),
            encode_field_varint(16, 3),
            encode_field_varint(17, 1),
        )
    )

    result = parse_powerpulse2_payload(encode_field_bytes(1, header))

    assert result["charging_status"] == "unplugged"
    assert result["charging_power_w"] == 0.0
    assert result["charge_current_set_raw"] == 16
    assert result["current_limit_raw"] == 16


def test_cp307_parameter_report_is_not_parsed_as_heartbeat() -> None:
    """cmd 2/34 reuses heartbeat field numbers for different parameters."""
    parameter_report = b"".join(
        (
            encode_field_varint(1, 15),
            encode_field_varint(9, 1_364_918),
            encode_field_varint(17, 15),
            encode_field_varint(18, 15),
        )
    )
    sequence = 5_508_714
    key = sequence & 0xFF
    encrypted = bytes(byte ^ key for byte in parameter_report)
    header = b"".join(
        (
            encode_field_bytes(1, encrypted),
            encode_field_varint(8, 2),
            encode_field_varint(9, 34),
            encode_field_varint(11, 1),
            encode_field_varint(14, sequence),
        )
    )

    assert parse_powerpulse2_payload(encode_field_bytes(1, header)) == {}


def test_cp307_packed_phase_values() -> None:
    heartbeat = b"".join(
        (
            encode_field_varint(1, 1),
            encode_field_bytes(29, pack("<fff", 232.3, 232.0, 231.3)),
            encode_field_bytes(30, pack("<fff", 0.1, 0.2, 0.3)),
        )
    )

    result = parse_powerpulse2_payload(heartbeat)

    assert result["phase_voltage_v"] == 232.3
    assert result["phase_current_a"] == 0.3


def test_nested_json_aliases() -> None:
    result = parse_powerpulse2_payload(
        {"data": {"params": {"chargePower": 7341, "systemState": 4}}}
    )
    assert result == {"charging_power_w": 7341, "charging_status": "paused"}


def test_nested_powerpulse_provider_report() -> None:
    report = {
        "devInfo": {"devSn": "C376TEST"},
        "pileChargingParamReport": {
            "chargingPwr": 0,
            "chargingStatus": 1,
            "paramSet": {
                "workMode": 4,
                "currentOuputMax": 160,
                "userCurrentSet": 60,
                "solarCurrentMin": 60,
                "switchBits": 9,
                "phaseSpecified": 0,
                "smartMode": {
                    "timeToUseCar": 1_787_528_301,
                    "chargeTarget": 30_000,
                },
            },
        },
        "vehicleInfo": {"currentVehicleComsumption": 175},
    }
    payload = {
        "data": {
            "quota": {
                "main_device_workMode": 99,
                "device_EDEV_PARAM_REPORT": {"C376TEST": json.dumps(report)},
            }
        }
    }

    result = parse_powerpulse2_payload(payload)

    assert result["charging_status"] == "unplugged"
    assert result["charging_power_w"] == 0
    assert result["work_mode"] == "smart"
    assert result["ready_by_timestamp"] == 1_787_528_301
    assert result["smart_charge_target_wh"] == 30_000
    assert result["output_current_max_raw"] == 160
    assert result["user_current_set_raw"] == 60
    assert result["solar_current_min_raw"] == 60
    assert result["switch_bits_raw"] == 9
    assert result["phase_specified_raw"] == 0
    assert result["vehicle_consumption_raw"] == 175


def test_powerpulse_provider_report_distance_target() -> None:
    result = parse_powerpulse2_payload(
        {
            "pileChargingParamReport": {
                "paramSet": {
                    "workMode": 4,
                    "smartMode": {
                        "timeToUseCar": 1_787_528_301,
                        "chargeTarget": 0,
                    },
                }
            }
        }
    )

    assert result == {
        "ready_by_timestamp": 1_787_528_301,
        "smart_charge_target_wh": 0,
        "work_mode": "smart",
    }


def test_unrelated_protobuf_is_not_a_heartbeat() -> None:
    assert parse_powerpulse2_payload(encode_field_varint(1, 999)) == {}
