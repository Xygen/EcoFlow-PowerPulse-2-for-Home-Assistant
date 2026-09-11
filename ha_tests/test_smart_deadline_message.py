"""Check the Smart deadline refusal against Home Assistant's real translations.

The portable tests assert which translation key is raised and that the key is
declared in `strings.json`. Neither can answer the question the user cares
about: does a message come out. A translated `HomeAssistantError` carries no
text of its own, so a key that Home Assistant cannot resolve reaches the user
as the bare key with every portable test still green.

What this proves is that Home Assistant loads this integration's `exceptions`
block and renders the message with the deadline substituted. What it does not
prove is the last step in the runtime, where the service layer catches the
error and renders it: that needs the integration set up, and the cost of
standing the whole device stack up here buys less than it costs.

The first draft of this file asserted on `str(error)` instead. It failed, and
the failure was informative: with the integration merely loaded and never set
up, `str()` returns the raw key. That is a fact about an un-set-up `hass` in a
test, not about the runtime, but it is exactly why the assertions below are on
the rendered translation rather than on the exception object.
"""

from homeassistant.helpers import translation

from custom_components.ecoflow_powerpulse2.const import DOMAIN
from custom_components.ecoflow_powerpulse2.smart_staging import (
    SmartDeadlineError,
    validate_smart_activation,
)

NOW = 1_800_000_000  # 2027-01-15 08:00 UTC
EXPIRED = NOW - 86_400  # 2027-01-14 08:00 UTC
BUNDLE = {
    "ready_by_timestamp": EXPIRED,
    "smart_target_type": "energy",
    "smart_charge_target_wh": 30_000,
}


def _refusal() -> SmartDeadlineError:
    try:
        validate_smart_activation(BUNDLE, now=NOW)
    except SmartDeadlineError as exc:
        return exc
    raise AssertionError("an expired deadline must be refused")


async def test_home_assistant_can_resolve_both_deadline_messages(hass):
    messages = await translation.async_get_translations(
        hass, "en", "exceptions", {DOMAIN}
    )

    expected = {
        f"component.{DOMAIN}.exceptions.{key}.message"
        for key in ("smart_ready_by_expired", "smart_ready_by_too_far_ahead")
    }
    assert expected <= set(messages)


async def test_the_expired_message_renders_with_the_refused_time(hass):
    messages = await translation.async_get_translations(
        hass, "en", "exceptions", {DOMAIN}
    )
    refusal = _refusal()

    template = messages[
        f"component.{DOMAIN}.exceptions.{refusal.translation_key}.message"
    ]
    rendered = template.format(**refusal.translation_placeholders)

    assert "2027-01-14 08:00 UTC" in rendered, "the refused time is not named"
    assert "{" not in rendered, "a placeholder was left unsubstituted"
    assert "has already passed" in rendered


async def test_the_german_message_carries_the_same_placeholder(hass):
    """A placeholder the code does not supply would render as a literal brace."""
    messages = await translation.async_get_translations(
        hass, "de", "exceptions", {DOMAIN}
    )
    refusal = _refusal()

    template = messages[
        f"component.{DOMAIN}.exceptions.{refusal.translation_key}.message"
    ]
    rendered = template.format(**refusal.translation_placeholders)

    assert "2027-01-14 08:00 UTC" in rendered
    assert "{" not in rendered
