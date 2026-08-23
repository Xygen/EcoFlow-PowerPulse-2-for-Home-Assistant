"""EcoFlow app API used for PowerPulse 2 discovery and snapshots."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

from .const import POWERPULSE_PREFIXES
from .ecoflow.const import IOT_API_BASE
from .ecoflow.enhanced_auth import enhanced_login, get_enhanced_credentials
from .parser import parse_powerpulse2_payload

_LOGGER = logging.getLogger(__name__)
_DEVICE_LIST_PATH = "/iot-service/user/device"
_DEVICE_DETAIL_PATH = "/provider-service/user/device/detail"


class PowerPulse2ApiClient:
    """Small async client for app login, discovery, and read-only snapshots."""

    def __init__(self, session: aiohttp.ClientSession, email: str, password: str) -> None:
        self._session = session
        self._email = email
        self._password = password
        self._token = ""
        self._user_id = ""
        self._base_url = IOT_API_BASE

    @property
    def user_id(self) -> str:
        return self._user_id

    async def async_login(self) -> None:
        result = await enhanced_login(self._session, self._email, self._password)
        if result is None:
            raise ConnectionError("EcoFlow login failed")
        self._token = result["token"]
        self._user_id = result["user_id"]
        self._base_url = result.get("base_url", IOT_API_BASE)

    async def async_get_mqtt_credentials(self) -> dict[str, Any]:
        result = await get_enhanced_credentials(self._session, self._token, base_url=self._base_url)
        if not result:
            raise ConnectionError("EcoFlow MQTT credentials unavailable")
        return result

    async def async_discover(self) -> dict[str, dict[str, str]]:
        """Return bound/shared CP307 PowerPulse devices keyed by serial."""
        async with self._session.get(
            f"{self._base_url}{_DEVICE_LIST_PATH}",
            headers=self._headers(),
            timeout=aiohttp.ClientTimeout(total=15),
        ) as response:
            response.raise_for_status()
            data = (await response.json()).get("data", {})

        found: dict[str, dict[str, str]] = {}
        for item in _iter_device_records(data):
            serial = str(item.get("sn") or "").upper()
            if not serial.startswith(POWERPULSE_PREFIXES):
                continue
            found[serial] = {
                "serial": serial,
                "name": str(item.get("deviceName") or item.get("productName") or "EcoFlow PowerPulse 2"),
                "product_type": str(item.get("productType") or item.get("product_type") or ""),
            }
        return found

    async def async_read(self, device: dict[str, str]) -> dict[str, Any]:
        """Read a best-effort provider snapshot without making device changes."""
        headers = self._headers(device.get("product_type", ""))
        for base_url in dict.fromkeys((self._base_url, IOT_API_BASE, "https://api-a.ecoflow.com")):
            try:
                async with self._session.get(
                    f"{base_url}{_DEVICE_DETAIL_PATH}",
                    params={"sn": device["serial"]},
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as response:
                    response.raise_for_status()
                    body = await response.json()
                if str(body.get("code", "0")) == "0":
                    return parse_powerpulse2_payload(body)
            except (aiohttp.ClientError, TimeoutError, ValueError) as exc:
                _LOGGER.debug("PowerPulse detail request failed via %s: %s", base_url, exc)
        return {}

    def _headers(self, product_type: str = "") -> dict[str, str]:
        headers = {"Authorization": f"Bearer {self._token}"}
        if product_type:
            headers["product-type"] = product_type
        return headers


def _iter_device_records(value: Any):
    """Walk EcoFlow's regional bound/share response variants."""
    if isinstance(value, dict):
        if "sn" in value:
            yield value
        for key, nested in value.items():
            if (
                isinstance(key, str)
                and key.upper().startswith(POWERPULSE_PREFIXES)
                and isinstance(nested, dict)
            ):
                yield {"sn": key, **nested}
            yield from _iter_device_records(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _iter_device_records(nested)
