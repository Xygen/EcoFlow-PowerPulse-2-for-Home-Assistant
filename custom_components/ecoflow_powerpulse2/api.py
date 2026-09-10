"""EcoFlow app API used for PowerPulse 2 discovery and snapshots."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

from .auth_classification import (
    AuthOutcome,
    PowerPulse2AuthError,
    PowerPulse2ConnectionError,
    aggregate_outcomes,
    classify_data_response,
    describe_response,
)
from .discovery import classify_device_records
from .ecoflow.const import IOT_API_BASE
from .ecoflow.enhanced_auth import enhanced_login, get_enhanced_credentials
from .parser import parse_powerpulse2_accessory_payloads, parse_powerpulse2_payload

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
        self._mqtt_observers: dict[str, dict[str, str]] = {}

    @property
    def user_id(self) -> str:
        return self._user_id

    @property
    def mqtt_observers(self) -> dict[str, dict[str, str]]:
        """Return PowerOcean sources found alongside the charger."""
        return dict(self._mqtt_observers)

    async def async_login(self) -> None:
        """Sign in, letting a rejected credential stay distinguishable.

        Raises ``PowerPulse2AuthError`` or ``PowerPulse2ConnectionError`` so
        the coordinator can start a re-authentication flow instead of
        retrying a credential EcoFlow has already refused.
        """
        result = await enhanced_login(self._session, self._email, self._password)
        self._token = result["token"]
        self._user_id = result["user_id"]
        self._base_url = result.get("base_url", IOT_API_BASE)

    async def async_get_mqtt_credentials(self) -> dict[str, Any]:
        result = await get_enhanced_credentials(
            self._session, self._token, base_url=self._base_url
        )
        if not result:
            raise PowerPulse2ConnectionError("EcoFlow MQTT credentials unavailable")
        return result

    async def async_discover(self) -> dict[str, dict[str, str]]:
        """Return bound/shared CP307 PowerPulse devices keyed by serial."""
        try:
            async with self._session.get(
                f"{self._base_url}{_DEVICE_LIST_PATH}",
                headers=self._headers(),
                timeout=aiohttp.ClientTimeout(total=15),
            ) as response:
                status = response.status
                try:
                    body = await response.json(content_type=None)
                except (aiohttp.ClientError, ValueError):
                    body = None
        except (aiohttp.ClientError, TimeoutError) as exc:
            raise PowerPulse2ConnectionError(str(exc)) from exc

        outcome = classify_data_response(status, body)
        if outcome is AuthOutcome.AUTH_FAILURE:
            raise PowerPulse2AuthError(describe_response(status, body))
        if outcome is not AuthOutcome.SUCCESS:
            raise PowerPulse2ConnectionError(describe_response(status, body))

        found, self._mqtt_observers = classify_device_records(body.get("data", {}))
        return found

    async def async_read(self, device: dict[str, str]) -> dict[str, Any]:
        """Read a best-effort provider snapshot without making device changes."""
        body = await self._async_read_detail(device)
        return parse_powerpulse2_payload(body) if body is not None else {}

    async def async_read_accessories(
        self, device: dict[str, str]
    ) -> dict[str, dict[str, Any]]:
        """Read PowerPulse reports embedded in a parent PowerOcean detail."""
        body = await self._async_read_detail(device)
        return parse_powerpulse2_accessory_payloads(body) if body is not None else {}

    async def _async_read_detail(
        self, device: dict[str, str]
    ) -> dict[str, Any] | None:
        """Fetch one provider detail response without retaining raw data.

        This is the bounded best-effort fallback, so an endpoint that fails
        still yields ``None`` and leaves the direct path untouched. The one
        exception is a token every endpoint refuses: that is not a transient
        read failure but an expired session, and silently returning ``None``
        for it is what used to disable this path permanently and invisibly.
        """
        headers = self._headers(device.get("product_type", ""))
        outcomes: list[AuthOutcome] = []
        for base_url in dict.fromkeys((self._base_url, IOT_API_BASE, "https://api-a.ecoflow.com")):
            try:
                async with self._session.get(
                    f"{base_url}{_DEVICE_DETAIL_PATH}",
                    params={"sn": device["serial"]},
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as response:
                    status = response.status
                    try:
                        body = await response.json(content_type=None)
                    except (aiohttp.ClientError, ValueError):
                        body = None
            except (aiohttp.ClientError, TimeoutError) as exc:
                outcomes.append(AuthOutcome.CONNECTION_FAILURE)
                _LOGGER.debug("PowerPulse detail request failed via %s: %s", base_url, exc)
                continue

            outcome = classify_data_response(status, body)
            outcomes.append(outcome)
            if outcome is AuthOutcome.SUCCESS:
                return body
            _LOGGER.debug(
                "PowerPulse detail request rejected via %s: %s",
                base_url,
                describe_response(status, body, detailed=True),
            )

        if aggregate_outcomes(outcomes) is AuthOutcome.AUTH_FAILURE:
            raise PowerPulse2AuthError("provider detail rejected the stored session")
        return None

    def _headers(self, product_type: str = "") -> dict[str, str]:
        headers = {"Authorization": f"Bearer {self._token}"}
        if product_type:
            headers["product-type"] = product_type
        return headers
