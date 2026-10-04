"""Real HA global action registration, validation and translated descriptions."""

import pytest
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import translation
from homeassistant.setup import async_setup_component

from custom_components.ecoflow_powerpulse2 import CONFIG_SCHEMA, async_setup
from custom_components.ecoflow_powerpulse2.const import DOMAIN
from custom_components.ecoflow_powerpulse2.services import ACTIONS


async def test_research_actions_register_without_loaded_entries(hass):
    assert await async_setup(hass, {})
    assert not hass.config_entries.async_entries(DOMAIN)
    for action in ACTIONS:
        assert hass.services.has_service(DOMAIN, action)


async def test_ha_component_setup_registers_actions_without_entries(hass):
    assert await async_setup_component(hass, DOMAIN, {})
    for action in ACTIONS:
        assert hass.services.has_service(DOMAIN, action)


def test_config_schema_keeps_yaml_setup_unsupported(hass, caplog):
    config = {DOMAIN: {}}
    assert CONFIG_SCHEMA(config) is config
    assert "does not support YAML setup" in caplog.text


@pytest.mark.parametrize("confirmation", [None, False])
async def test_missing_or_false_confirmation_is_a_real_ha_validation_error(hass, confirmation):
    await async_setup(hass, {})
    data = {"device_id": "unknown-device", "current": 7, "expected_work_mode": "solar"}
    if confirmation is not None:
        data["confirm_protocol_test"] = confirmation
    with pytest.raises(ServiceValidationError, match="confirm_protocol_test=true"):
        await hass.services.async_call(DOMAIN, ACTIONS[0], data, blocking=True)


async def test_unknown_device_is_a_real_ha_validation_error(hass):
    await async_setup(hass, {})
    with pytest.raises(ServiceValidationError, match="Unknown PowerPulse"):
        await hass.services.async_call(
            DOMAIN, ACTIONS[2],
            {"device_id": "unknown-device", "phase": "three_phase", "confirm_protocol_test": True},
            blocking=True,
        )


@pytest.mark.parametrize("language", ["en", "de"])
async def test_research_action_and_field_translations_load_in_ha(hass, language):
    messages = await translation.async_get_translations(hass, language, "services", {DOMAIN})
    for action in ACTIONS:
        base = f"component.{DOMAIN}.services.{action}"
        assert messages[f"{base}.name"]
        assert messages[f"{base}.description"]
        assert messages[f"{base}.fields.device_id.name"]
        assert messages[f"{base}.fields.confirm_protocol_test.description"]
