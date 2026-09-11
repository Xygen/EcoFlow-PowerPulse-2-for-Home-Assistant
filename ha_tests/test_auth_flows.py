"""Exercise HA's real flow manager, config entries and entity registry."""

from copy import deepcopy
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import SOURCE_REAUTH, SOURCE_RECONFIGURE, SOURCE_USER
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ecoflow_powerpulse2.auth_classification import (
    PowerPulse2AuthError,
    PowerPulse2ConnectionError,
)
from custom_components.ecoflow_powerpulse2.const import DOMAIN

API = f"custom_components.{DOMAIN}.config_flow.PowerPulse2ApiClient"
EMAIL = "test@example.invalid"


@pytest.fixture
def api():
    with patch(API) as factory:
        factory.return_value.async_login = AsyncMock()
        factory.return_value.async_discover = AsyncMock(return_value={"test-device": {}})
        yield factory.return_value


@pytest.fixture
def entry(hass):
    result = MockConfigEntry(
        domain=DOMAIN, unique_id=EMAIL,
        data={"email": EMAIL, "password": "old-test-password"},
    )
    result.add_to_hass(hass)
    return result


@pytest.mark.parametrize("source", [SOURCE_USER, SOURCE_REAUTH, SOURCE_RECONFIGURE])
@pytest.mark.parametrize("failure,expected", [
    (PowerPulse2AuthError("test rejection"), "invalid_auth"),
    (PowerPulse2ConnectionError("test outage"), "cannot_connect"),
])
async def test_failure_stays_in_correct_form(hass, entry, api, source, failure, expected):
    api.async_login.side_effect = failure
    context = {"source": source}
    if source != SOURCE_USER:
        context["entry_id"] = entry.entry_id
    flow = await hass.config_entries.flow.async_init(DOMAIN, context=context, data=None)
    before = dict(entry.data)
    result = await hass.config_entries.flow.async_configure(
        flow["flow_id"], {"email": EMAIL, "password": "rejected-test-password"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": expected}
    assert entry.data == before
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1
    api.async_discover.assert_not_awaited()


@pytest.mark.parametrize("source", [SOURCE_REAUTH, SOURCE_RECONFIGURE])
async def test_wrong_account_never_contacts_ecoflow(hass, entry, api, source):
    flow = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": source, "entry_id": entry.entry_id}, data=None
    )
    result = await hass.config_entries.flow.async_configure(
        flow["flow_id"], {"email": "other@example.invalid", "password": "test"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "wrong_account"
    assert entry.unique_id == EMAIL
    api.async_login.assert_not_awaited()


@pytest.mark.parametrize("source,reason", [
    (SOURCE_REAUTH, "reauth_successful"),
    (SOURCE_RECONFIGURE, "reconfigure_successful"),
])
async def test_changed_credentials_update_existing_entry(hass, entry, api, hass_storage, source, reason):
    registry = er.async_get(hass)
    entity = registry.async_get_or_create(
        "sensor", DOMAIN, "test-device_power", config_entry=entry,
        disabled_by=er.RegistryEntryDisabler.USER,
    )
    key = f"{DOMAIN}.smart_staging.{entry.entry_id}"
    hass_storage[key] = {"version": 1, "minor_version": 1, "key": key,
                         "data": {"test-device": {"smart_target_distance_km": 200}}}
    stored = deepcopy(hass_storage[key])
    with patch.object(hass.config_entries, "async_reload", new=AsyncMock(return_value=True)) as reload:
        flow = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": source, "entry_id": entry.entry_id}, data=None
        )
        result = await hass.config_entries.flow.async_configure(
            flow["flow_id"], {"email": EMAIL, "password": "new-test-password"}
        )
        await hass.async_block_till_done()
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == reason
    assert entry.data["password"] == "new-test-password"
    assert entry.unique_id == EMAIL
    assert hass.config_entries.async_entries(DOMAIN) == [entry]
    assert registry.async_get(entity.entity_id).disabled_by is er.RegistryEntryDisabler.USER
    assert hass_storage[key] == stored
    reload.assert_awaited_once_with(entry.entry_id)
