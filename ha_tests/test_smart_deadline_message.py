"""Check the Smart deadline refusal against Home Assistant's real translations.

The portable tests assert which translation key is raised and that the key is
declared. Neither can answer the question the user actually cares about: does
a message come out. A translated `HomeAssistantError` carries no text of its
own, so if the key were wrong or the block were not loaded, the refusal would
reach the user empty and the portable suite would stay green.
"""

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import translation

from custom_components.ecoflow_powerpulse2.const import DOMAIN
from custom_components.ecoflow_powerpulse2.smart_staging import (
    SmartDeadlineError,
    validate_smart_activation,
)

NOW = 1_800_000_000
BUNDLE = {
    "ready_by_timestamp": NOW - 86_400,
    "smart_target_type": "energy",
    "smart_charge_target_wh": 30_000,
}


def _refusal() -> SmartDeadlineError:
    try:
        validate_smart_activation(BUNDLE, now=NOW)
    except SmartDeadlineError as exc:
        return exc
    raise AssertionError("an expired deadline must be refused")


async def test_the_expired_refusal_reaches_the_user_as_a_real_message(hass):
    await translation.async_load_integrations(hass, {DOMAIN})
    refusal = _refusal()

    error = HomeAssistantError(
        translation_domain=DOMAIN,
        translation_key=refusal.translation_key,
        translation_placeholders=refusal.translation_placeholders,
    )

    message = str(error)
    assert "{ready_by}" not in message, "the placeholder was never substituted"
    assert refusal.translation_key not in message, "the raw key reached the user"
    assert "2027-01-14 08:00 UTC" in message, "the refused time is not named"
    assert "has already passed" in message


async def test_every_declared_exception_message_resolves(hass):
    """A declared key with a broken message body would fail only in the UI."""
    await translation.async_load_integrations(hass, {DOMAIN})
    translations = translation.async_get_cached_translations(hass, "en", "exceptions")

    expected = {
        f"component.{DOMAIN}.exceptions.{key}.message"
        for key in ("smart_ready_by_expired", "smart_ready_by_too_far_ahead")
    }
    assert expected <= set(translations)
