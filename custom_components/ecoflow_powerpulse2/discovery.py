"""Dependency-free normalization of EcoFlow account device records."""

from __future__ import annotations

from typing import Any

from .device_types import POWEROCEAN_PREFIXES, POWERPULSE_PREFIXES


def iter_device_records(value: Any):
    """Walk EcoFlow's regional bound/share response variants."""
    if isinstance(value, dict):
        if "sn" in value:
            yield value
        for key, nested in value.items():
            if (
                isinstance(key, str)
                and key.upper().startswith((*POWERPULSE_PREFIXES, *POWEROCEAN_PREFIXES))
                and isinstance(nested, dict)
            ):
                yield {"sn": key, **nested}
            yield from iter_device_records(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from iter_device_records(nested)


def classify_device_records(
    data: Any,
) -> tuple[dict[str, dict[str, str]], dict[str, dict[str, str]]]:
    """Split account devices into chargers and passive PowerOcean sources."""
    chargers: dict[str, dict[str, str]] = {}
    observers: dict[str, dict[str, str]] = {}
    for item in iter_device_records(data):
        serial = str(item.get("sn") or "").upper()
        if not serial:
            continue
        device = {
            "serial": serial,
            "name": str(
                item.get("deviceName")
                or item.get("productName")
                or (
                    "EcoFlow PowerPulse 2"
                    if serial.startswith(POWERPULSE_PREFIXES)
                    else "EcoFlow PowerOcean"
                )
            ),
            "product_type": str(
                item.get("productType") or item.get("product_type") or ""
            ),
        }
        if serial.startswith(POWERPULSE_PREFIXES):
            chargers[serial] = device
        elif serial.startswith(POWEROCEAN_PREFIXES):
            observers[serial] = device
    return chargers, observers
