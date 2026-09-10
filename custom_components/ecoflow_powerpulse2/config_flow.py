"""Config flow for EcoFlow PowerPulse 2."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import PowerPulse2ApiClient
from .auth_classification import PowerPulse2AuthError, PowerPulse2ConnectionError
from .const import CONF_EMAIL, CONF_PASSWORD, DOMAIN

_LOGGER = logging.getLogger(__name__)

_CREDENTIAL_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


def _credential_schema(email: str = "") -> vol.Schema:
    """Return the credential form, prefilled with a known email address.

    The password is never prefilled: the stored one is what stopped working.
    """
    if not email:
        return _CREDENTIAL_SCHEMA
    return vol.Schema(
        {
            vol.Required(CONF_EMAIL, default=email): str,
            vol.Required(CONF_PASSWORD): str,
        }
    )


class PowerPulse2ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Validate EcoFlow app credentials and PowerPulse discovery."""

    VERSION = 1

    async def _async_check_credentials(
        self, email: str, password: str, *, require_devices: bool
    ) -> tuple[str, dict[str, dict[str, str]]]:
        """Sign in and report a translated error key, empty when accepted.

        The two failure kinds are kept apart deliberately: only a credential
        EcoFlow actually refused should send the user back to their password.
        """
        client = PowerPulse2ApiClient(
            async_get_clientsession(self.hass), email, password
        )
        try:
            await client.async_login()
            devices = await client.async_discover()
        except PowerPulse2AuthError:
            return "invalid_auth", {}
        except PowerPulse2ConnectionError:
            return "cannot_connect", {}
        except Exception:  # noqa: BLE001 - surfaced as an unknown-error form
            _LOGGER.exception("Unexpected error while validating EcoFlow credentials")
            return "unknown", {}
        if require_devices and not devices:
            return "no_devices", {}
        return "", devices

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Add a new EcoFlow account."""
        errors: dict[str, str] = {}
        email = ""
        if user_input is not None:
            email = user_input[CONF_EMAIL].strip()
            password = user_input[CONF_PASSWORD]
            error, _devices = await self._async_check_credentials(
                email, password, require_devices=True
            )
            if error:
                errors["base"] = error
            else:
                await self.async_set_unique_id(email.lower())
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="EcoFlow PowerPulse 2",
                    data={CONF_EMAIL: email, CONF_PASSWORD: password},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_credential_schema(email),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Start re-authentication for an entry whose credentials were refused."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect working credentials without replacing the config entry.

        Updating the existing entry is what preserves entity IDs, recorded
        history, user entity activations and the local Smart drafts, all of
        which a delete-and-re-add would discard.
        """
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        email = entry.data.get(CONF_EMAIL, "")

        if user_input is not None:
            email = user_input[CONF_EMAIL].strip()
            password = user_input[CONF_PASSWORD]
            # A new sign-in must not silently move the entry to a different
            # account: that account's serials would orphan every entity.
            await self.async_set_unique_id(email.lower())
            self._abort_if_unique_id_mismatch(reason="wrong_account")
            error, _devices = await self._async_check_credentials(
                email, password, require_devices=False
            )
            if error:
                errors["base"] = error
            else:
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={CONF_EMAIL: email, CONF_PASSWORD: password},
                    reason="reauth_successful",
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=_credential_schema(email),
            errors=errors,
            description_placeholders={"email": entry.data.get(CONF_EMAIL, "")},
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Update stored credentials before they are refused."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        email = entry.data.get(CONF_EMAIL, "")

        if user_input is not None:
            email = user_input[CONF_EMAIL].strip()
            password = user_input[CONF_PASSWORD]
            await self.async_set_unique_id(email.lower())
            self._abort_if_unique_id_mismatch(reason="wrong_account")
            error, _devices = await self._async_check_credentials(
                email, password, require_devices=False
            )
            if error:
                errors["base"] = error
            else:
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={CONF_EMAIL: email, CONF_PASSWORD: password},
                    reason="reconfigure_successful",
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_credential_schema(email),
            errors=errors,
        )
