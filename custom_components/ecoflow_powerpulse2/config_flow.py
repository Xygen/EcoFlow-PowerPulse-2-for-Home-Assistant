"""Config flow for EcoFlow PowerPulse 2."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import PowerPulse2ApiClient
from .const import CONF_EMAIL, CONF_PASSWORD, DOMAIN


class PowerPulse2ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Validate EcoFlow app credentials and PowerPulse discovery."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            client = PowerPulse2ApiClient(
                async_get_clientsession(self.hass),
                user_input[CONF_EMAIL],
                user_input[CONF_PASSWORD],
            )
            try:
                await client.async_login()
                devices = await client.async_discover()
            except Exception:
                errors["base"] = "cannot_connect"
            else:
                if not devices:
                    errors["base"] = "no_devices"
                else:
                    email = user_input[CONF_EMAIL].strip()
                    await self.async_set_unique_id(email.lower())
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title="EcoFlow PowerPulse 2",
                        data={CONF_EMAIL: email, CONF_PASSWORD: user_input[CONF_PASSWORD]},
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_EMAIL): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )
