"""Real coordinator and HA runtime, with only the EcoFlow boundary replaced."""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ecoflow_powerpulse2.auth_classification import (
    PowerPulse2AuthError,
    PowerPulse2ConnectionError,
)
from custom_components.ecoflow_powerpulse2.const import DOMAIN
from custom_components.ecoflow_powerpulse2.coordinator import PowerPulse2Coordinator
from custom_components.ecoflow_powerpulse2.ecoflow.cloud_mqtt import EcoFlowMQTTClient


@pytest.fixture
async def coordinator(hass):
    entry = MockConfigEntry(domain=DOMAIN, unique_id="test@example.invalid",
                            data={"email": "test@example.invalid", "password": "test"})
    entry.add_to_hass(hass)
    result = PowerPulse2Coordinator(hass, entry)
    result.api = Mock(async_login=AsyncMock(), async_get_mqtt_credentials=AsyncMock())
    entry.runtime_data = result
    yield result
    await result.async_shutdown()


async def test_successful_login_then_certificate_refusal_is_not_wrong_password(coordinator):
    coordinator.api.async_get_mqtt_credentials.side_effect = PowerPulse2AuthError("session refused")
    with patch.object(coordinator.config_entry, "async_start_reauth") as reauth:
        await coordinator._async_refresh_mqtt_credentials("test")
    coordinator.api.async_login.assert_awaited_once()
    assert coordinator.api.async_get_mqtt_credentials.await_count == 2
    reauth.assert_not_called()


async def test_refused_stored_password_starts_real_ha_reauth(coordinator, hass):
    coordinator.api.async_get_mqtt_credentials.side_effect = PowerPulse2AuthError("expired")
    coordinator.api.async_login.side_effect = PowerPulse2AuthError("refused sign-in")
    await coordinator._async_refresh_mqtt_credentials("test")
    await hass.async_block_till_done()
    flows = hass.config_entries.flow.async_progress()
    assert any(flow["context"].get("entry_id") == coordinator.config_entry.entry_id
               and flow["context"]["source"] == "reauth" for flow in flows)


async def test_network_failure_does_not_start_reauth(coordinator):
    coordinator.api.async_get_mqtt_credentials.side_effect = PowerPulse2ConnectionError("offline")
    with patch.object(coordinator.config_entry, "async_start_reauth") as reauth:
        await coordinator._async_refresh_mqtt_credentials("test")
    reauth.assert_not_called()
    coordinator.api.async_login.assert_not_awaited()


async def test_expired_session_recovers_once_without_prompt(coordinator):
    credentials = {"certificateAccount": "test-account", "certificatePassword": "test-password"}
    coordinator.api.async_get_mqtt_credentials.side_effect = [PowerPulse2AuthError("expired"), credentials]
    with patch.object(coordinator, "_async_apply_mqtt_credentials", new=AsyncMock()) as apply:
        with patch.object(coordinator.config_entry, "async_start_reauth") as reauth:
            await coordinator._async_refresh_mqtt_credentials("test")
            await coordinator._async_refresh_mqtt_credentials("duplicate")
    apply.assert_awaited_once_with(credentials)
    coordinator.api.async_login.assert_awaited_once()
    reauth.assert_not_called()


async def test_same_account_new_certificate_password_reconnects(coordinator):
    client = EcoFlowMQTTClient(certificate_account="test-account", certificate_password="old",
                              device_sn="test-device", user_id="test-user",
                              message_handler=lambda *args: None, listen_only=True)
    client.force_reconnect = Mock(return_value=True)
    coordinator.mqtt_clients["test-device"] = client
    credentials = {"certificateAccount": "test-account", "certificatePassword": "new"}
    await coordinator._async_apply_mqtt_credentials(credentials)
    client.force_reconnect.assert_called_once()
    await coordinator._async_apply_mqtt_credentials(credentials)
    client.force_reconnect.assert_called_once()


async def test_refresh_still_coalesces_when_first_request_outlives_cooldown(coordinator):
    entered, release = asyncio.Event(), asyncio.Event()
    async def fetch():
        entered.set()
        await release.wait()
        return None
    with patch.object(coordinator, "_async_fetch_credentials_with_retry", side_effect=fetch) as fetch_mock:
        first = asyncio.create_task(coordinator._async_refresh_mqtt_credentials("first"))
        await asyncio.wait_for(entered.wait(), timeout=3)
        coordinator._last_credential_refresh -= 600
        second = asyncio.create_task(coordinator._async_refresh_mqtt_credentials("second"))
        await asyncio.sleep(0)
        release.set()
        await asyncio.gather(first, second)
    assert fetch_mock.await_count == 1
