"""Generic protobuf request builders for EcoFlow cloud MQTT."""

from __future__ import annotations

import time

from .proto_encoding import encode_field_bytes, encode_field_varint


def _sequence(seq: int) -> int:
    return seq or (int(time.time() * 1000) & 0x7FFFFFFF)


def _short_sequence(seq: int) -> int:
    """Match the one-byte rolling sequences observed on app settings SETs."""
    return seq if seq else (int(time.time() * 1000) & 0xFF)


def build_energy_stream_activate_payload(seq: int = 0) -> bytes:
    """Build the verified PowerOcean EnergyStreamSwitch keepalive frame."""
    pdata = encode_field_varint(1, 1)
    return _build_envelope(
        pdata,
        destination=96,
        cmd_func=96,
        cmd_id=97,
        seq=_sequence(seq),
    )


def build_device_get_all_payload(seq: int = 0) -> bytes:
    """Build the generic app get-all request used after reconnects."""
    header = bytearray()
    header.extend(encode_field_varint(2, 32))
    header.extend(encode_field_varint(3, 32))
    header.extend(encode_field_varint(14, _sequence(seq)))
    header.extend(encode_field_bytes(23, b"app"))
    return encode_field_bytes(1, bytes(header))


def build_powerpulse_phase_payload(
    accessory_descriptor: bytes, phase: int, seq: int = 0
) -> tuple[bytes, int]:
    """Build the observed PowerOcean-routed PowerPulse phase SET command."""
    if phase not in (0, 1, 2):
        raise ValueError("phase must be 0 (auto), 1 (one phase), or 2 (three phase)")
    return build_powerpulse_settings_payload(
        accessory_descriptor, {5: phase}, seq=seq
    )


def build_powerpulse_settings_payload(
    accessory_descriptor: bytes, settings: dict[int, int], seq: int = 0
) -> tuple[bytes, int]:
    """Build the observed PowerOcean-routed PowerPulse settings SET command."""
    if not settings or any(field not in range(1, 8) for field in settings):
        raise ValueError("settings must contain observed fields 1 through 7")
    if any(not isinstance(value, int) or value < 0 for value in settings.values()):
        raise ValueError("settings values must be non-negative integers")
    sequence = _short_sequence(seq)
    settings_payload = b"".join(
        encode_field_varint(field, value) for field, value in sorted(settings.items())
    )
    pdata = b"".join(
        (
            encode_field_bytes(1, accessory_descriptor),
            encode_field_bytes(4, settings_payload),
        )
    )
    return (
        _build_envelope(
            pdata,
            destination=96,
            cmd_func=241,
            cmd_id=102,
            seq=sequence,
        ),
        sequence,
    )


def _build_envelope(
    pdata: bytes,
    *,
    destination: int,
    cmd_func: int,
    cmd_id: int,
    seq: int,
    device_sn: str = "",
) -> bytes:
    """Build the app-compatible Send_Header_Msg envelope."""
    header = bytearray()
    header.extend(encode_field_bytes(1, pdata))
    header.extend(encode_field_varint(2, 32))
    header.extend(encode_field_varint(3, destination))
    header.extend(encode_field_varint(4, 1))
    header.extend(encode_field_varint(5, 1))
    header.extend(encode_field_varint(7, 3))
    header.extend(encode_field_varint(8, cmd_func))
    header.extend(encode_field_varint(9, cmd_id))
    header.extend(encode_field_varint(10, len(pdata)))
    header.extend(encode_field_varint(11, 1))
    header.extend(encode_field_varint(14, seq))
    header.extend(encode_field_varint(16, 3))
    header.extend(encode_field_varint(17, 1))
    header.extend(encode_field_bytes(23, b"ios"))
    if device_sn:
        header.extend(encode_field_bytes(25, device_sn.encode("ascii")))
    return encode_field_bytes(1, bytes(header))
