from __future__ import annotations

import json
from struct import pack

from custom_components.ecoflow_powerpulse2.ecoflow.proto_encoding import (
    encode_field_bytes,
    encode_field_varint,
)
from custom_components.ecoflow_powerpulse2.parser import (
    extract_powerpulse_accessory_descriptor,
    parse_powerpulse2_accessory_payloads,
    parse_powerpulse2_payload,
)


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
            encode_field_varint(17, 60),
            encode_field_varint(18, 160),
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
    assert result["direct_charging_status"] == "charging"
    assert result["direct_charging_power_w"] == 3929.0
    assert result["direct_phase_voltage_v"] == 231.4
    assert result["direct_phase_current_a"] == 17.0
    assert result["direct_session_duration_s"] == 720
    assert result["direct_session_energy_raw"] == 449
    assert result["direct_total_energy_raw"] == 94708


def test_need_ack_does_not_trigger_xor_decoding() -> None:
    """Header field 11 is need_ack; only field 6 marks XOR encoding."""
    heartbeat = _heartbeat(state=1, power=0.0)
    header = b"".join(
        (
            encode_field_bytes(1, heartbeat),
            encode_field_varint(8, 2),
            encode_field_varint(9, 33),
            encode_field_varint(11, 1),
            encode_field_varint(14, 1234),
        )
    )

    result = parse_powerpulse2_payload(encode_field_bytes(1, header))

    assert result["charging_status"] == "unplugged"
    assert result["charging_power_w"] == 0.0


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
    assert result["charge_current_set_raw"] == 60
    assert result["current_limit_raw"] == 160


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
            encode_field_varint(6, 1),
            encode_field_varint(14, sequence),
        )
    )

    assert parse_powerpulse2_payload(encode_field_bytes(1, header)) == {}


def test_cp307_xor_encoded_settings_report() -> None:
    """Decode the live-confirmed C376 2/34 setting fields."""
    parameter_report = b"".join(
        (
            encode_field_varint(1, 9),
            encode_field_varint(2, 1),
            encode_field_varint(9, 160),
            encode_field_varint(11, 3),
            encode_field_varint(13, 1),
            encode_field_varint(14, 25),
            encode_field_varint(15, 1),
            encode_field_varint(16, 25),
            encode_field_varint(22, 0),
        )
    )
    sequence = 5_605_587
    key = sequence & 0xFF
    encrypted = bytes(byte ^ key for byte in parameter_report)
    header = b"".join(
        (
            encode_field_bytes(1, encrypted),
            encode_field_varint(8, 2),
            encode_field_varint(9, 34),
            encode_field_varint(6, 1),
            encode_field_varint(14, sequence),
        )
    )

    assert parse_powerpulse2_payload(encode_field_bytes(1, header)) == {
        "battery_discharge_disabled": False,
        "current_limit_raw": 160,
        "indicator_brightness_pct": 25,
        "indicator_enabled": True,
        "phase_mode": "auto",
        "plug_and_play": True,
        "screen_brightness_pct": 25,
        "screen_enabled": True,
    }


def _direct_param_set_envelope(
    *,
    cmd_id: int = 44,
    switch_bits: int = 16,
    work_mode: int = 2,
    solar_current_min: int = 70,
    display_settings: bytes | None = None,
    smart_settings: bytes = b"unknown",
) -> bytes:
    param_fields = [
        encode_field_varint(1, switch_bits),
        encode_field_varint(2, work_mode),
        encode_field_varint(4, 160),
        encode_field_bytes(5, b"unknown-smart"),
        encode_field_varint(6, solar_current_min),
        encode_field_varint(7, 0),
        encode_field_varint(8, 60),
    ]
    if display_settings is not None:
        param_fields.append(encode_field_bytes(21, display_settings))
    param_fields.append(encode_field_bytes(31, smart_settings))
    param_set = b"".join(param_fields)
    report = b"".join(
        (
            encode_field_bytes(
                1,
                encode_field_varint(1, 215)
                + encode_field_bytes(2, b"0123456789abcdef")
                + encode_field_varint(3, 1),
            ),
            encode_field_bytes(4, encode_field_bytes(8, param_set)),
        )
    )
    plaintext = encode_field_bytes(1, report)
    sequence = 5_636_034
    key = sequence & 0xFF
    encrypted = bytes(byte ^ key for byte in plaintext)
    header = b"".join(
        (
            encode_field_bytes(1, encrypted),
            encode_field_varint(6, 1),
            encode_field_varint(8, 241),
            encode_field_varint(9, cmd_id),
            encode_field_varint(14, sequence),
        )
    )
    return encode_field_bytes(1, header)


def test_direct_c376_param_set_report() -> None:
    """Decode the exact high-frequency C376 241/44 report shape."""
    assert parse_powerpulse2_payload(_direct_param_set_envelope()) == {
        "battery_discharge_disabled": False,
        "continuous_charging": True,
        "current_limit_raw": 160,
        "output_current_max_raw": 160,
        "phase_specified_raw": 0,
        "phase_mode": "auto",
        "plug_and_play": False,
        "solar_current_min_raw": 70,
        "switch_bits_raw": 16,
        "user_current_set_raw": 60,
        "work_mode": "solar",
    }


def test_direct_display_settings_block() -> None:
    result = parse_powerpulse2_payload(
        _direct_param_set_envelope(
            display_settings=bytes((1, 0, 100, 25, 2, 0))
        )
    )

    assert result["indicator_enabled"] is True
    assert result["screen_enabled"] is False
    assert result["indicator_brightness_pct"] == 100
    assert result["screen_brightness_pct"] == 25


def test_direct_display_settings_rejects_malformed_block() -> None:
    result = parse_powerpulse2_payload(
        _direct_param_set_envelope(
            display_settings=bytes((1, 0, 99, 25, 2, 0))
        )
    )

    assert "indicator_enabled" not in result
    assert "screen_enabled" not in result
    assert "indicator_brightness_pct" not in result
    assert "screen_brightness_pct" not in result


def test_direct_param_set_exposes_validated_descriptor_only_to_control_helper() -> None:
    assert extract_powerpulse_accessory_descriptor(_direct_param_set_envelope()) == (
        encode_field_varint(1, 215) + encode_field_bytes(2, b"0123456789abcdef")
    )


def test_direct_smart_distance_fields() -> None:
    smart = b"".join(
        (
            encode_field_varint(1, 1_787_637_600),
            encode_field_varint(2, 2),
            encode_field_varint(3, 45_000),
            encode_field_varint(4, 300),
            encode_field_varint(5, 0),
        )
    )
    result = parse_powerpulse2_payload(
        _direct_param_set_envelope(work_mode=4, smart_settings=smart)
    )

    assert result["smart_target_type"] == "distance"
    assert result["smart_target_distance_km"] == 300
    assert result["smart_calculated_energy_wh"] == 45_000
    assert result["ready_by_timestamp"] == 1_787_637_600


def test_direct_param_set_decodes_plug_and_play_bit() -> None:
    result = parse_powerpulse2_payload(
        _direct_param_set_envelope(switch_bits=18)
    )

    assert result["continuous_charging"] is True
    assert result["plug_and_play"] is True
    assert result["switch_bits_raw"] == 18


def test_direct_param_set_requires_exact_command() -> None:
    assert parse_powerpulse2_payload(_direct_param_set_envelope(cmd_id=45)) == {}


def test_direct_param_set_rejects_unknown_mode_and_current_range() -> None:
    assert parse_powerpulse2_payload(
        _direct_param_set_envelope(work_mode=9)
    ) == {}
    assert parse_powerpulse2_payload(
        _direct_param_set_envelope(solar_current_min=20)
    ) == {}


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
    assert result["current_limit_raw"] == 160
    assert result["user_current_set_raw"] == 60
    assert result["solar_current_min_raw"] == 60
    assert result["switch_bits_raw"] == 9
    assert result["continuous_charging"] is False
    assert result["plug_and_play"] is False
    assert result["phase_specified_raw"] == 0
    assert result["vehicle_consumption_raw"] == 175


def test_parent_provider_reports_are_keyed_by_embedded_wallbox_serial() -> None:
    report = {
        "devInfo": {"devSn": "c376test"},
        "pileChargingParamReport": {
            "chargingPwr": 0,
            "chargingStatus": 1,
            "paramSet": {
                "workMode": 2,
                "solarCurrentMin": 60,
                "switchBits": 9,
            },
        },
    }
    payload = {
        "data": {
            "quota": {
                "device_EDEV_PARAM_REPORT": {"C376TEST": json.dumps(report)}
            }
        }
    }

    assert parse_powerpulse2_accessory_payloads(payload) == {
            "C376TEST": {
                "battery_discharge_disabled": True,
            "charging_power_w": 0,
            "charging_status": "unplugged",
            "continuous_charging": False,
            "plug_and_play": False,
            "solar_current_min_raw": 60,
            "switch_bits_raw": 9,
            "work_mode": "solar",
        }
    }


def test_continuous_charging_switch_bit() -> None:
    """Live Solar-mode tests isolated bit 4 without changing the stored current."""
    enabled = parse_powerpulse2_payload(
        {
            "pileChargingParamReport": {
                "paramSet": {"solarCurrentMin": 60, "switchBits": 16}
            }
        }
    )
    disabled = parse_powerpulse2_payload(
        {
            "pileChargingParamReport": {
                "paramSet": {"solarCurrentMin": 60, "switchBits": 0}
            }
        }
    )

    assert enabled["continuous_charging"] is True
    assert disabled["continuous_charging"] is False
    assert enabled["solar_current_min_raw"] == disabled["solar_current_min_raw"] == 60


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
