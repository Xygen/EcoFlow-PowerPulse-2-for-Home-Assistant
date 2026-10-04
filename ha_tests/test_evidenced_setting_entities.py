"""Exercise real HA entities against production availability and setter dispatch."""

import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.components.number import NumberEntityDescription
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ecoflow_powerpulse2.const import DOMAIN
from custom_components.ecoflow_powerpulse2.coordinator import PowerPulse2Coordinator
from custom_components.ecoflow_powerpulse2.number import PowerPulse2CurrentNumber
from custom_components.ecoflow_powerpulse2.select import PowerPulse2PhaseSelect

SERIAL = "C376-test"


@pytest.fixture
async def coordinator(hass):
    entry = MockConfigEntry(domain=DOMAIN, data={"email": "test@example.invalid", "password": "test"})
    with patch("custom_components.ecoflow_powerpulse2.coordinator.PowerPulse2ApiClient"):
        c = PowerPulse2Coordinator(hass, entry)
    c.devices = {SERIAL: {}}
    c.observer_devices = {"parent": {}}
    c.mqtt_clients = {
        SERIAL: SimpleNamespace(is_connected=lambda: True),
        "parent": SimpleNamespace(is_connected=lambda: True),
    }
    c._accessory_descriptors[SERIAL] = b"opaque-accessory"
    c.data = {SERIAL: {
        "work_mode": "solar", "continuous_charging": False,
        "solar_current_min_raw": 60, "user_current_set_raw": 100,
        "phase_specified_raw": 0, "phase_mode": "auto", "direct_charging_status": "plugged_in",
    }}
    c._last_heartbeat_at[SERIAL] = time.monotonic()
    c._record_setting_observations(SERIAL, "direct_fast_settings_241_44", c.data[SERIAL])
    c._phase_readbacks.record(SERIAL, "direct_241_44", c.data[SERIAL])
    c.last_update_success = True
    return c


@pytest.mark.parametrize("mode", ["solar", "fast", "custom", "smart"])
@pytest.mark.parametrize("entity_key,method,value", [
    ("solar_minimum_current_control", "async_set_solar_minimum_current", 6),
    ("custom_current_control", "async_set_custom_current", 10),
])
async def test_idle_current_entity_uses_independent_storage(coordinator, mode, entity_key, method, value):
    coordinator.data[SERIAL]["work_mode"] = mode
    entity = PowerPulse2CurrentNumber(coordinator, SERIAL, NumberEntityDescription(key=entity_key))
    assert entity.available
    assert entity.native_value == value
    with patch.object(coordinator, method, new_callable=AsyncMock) as setter:
        await entity.async_set_native_value(7)
        setter.assert_awaited_once_with(SERIAL, 7)
    coordinator.data[SERIAL]["direct_charging_status"] = "charging"
    assert not entity.available


async def test_current_entity_requires_fresh_stored_field(coordinator):
    entity = PowerPulse2CurrentNumber(
        coordinator, SERIAL, NumberEntityDescription(key="solar_minimum_current_control")
    )
    assert entity.available
    coordinator._setting_observations = type(coordinator._setting_observations)({})
    assert not entity.available


async def test_phase_entity_allows_charging_but_requires_fresh_state(coordinator):
    coordinator.data[SERIAL]["direct_charging_status"] = "charging"
    entity = PowerPulse2PhaseSelect(coordinator, SERIAL)
    assert entity.available
    assert entity.current_option == "auto"
    with patch.object(coordinator, "async_set_phase_mode", new_callable=AsyncMock) as setter:
        await entity.async_select_option("three_phase")
        setter.assert_awaited_once_with(SERIAL, "three_phase")
    coordinator._last_heartbeat_at[SERIAL] = time.monotonic() - 91
    assert not entity.available
