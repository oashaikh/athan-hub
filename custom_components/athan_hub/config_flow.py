"""Config and options flows for Athan Hub."""

from __future__ import annotations

from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_URL
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_ATHAN_URL, DEFAULT_URL, DOMAIN
from .coordinator import fetch_json


class AthanHubConfigFlow(ConfigFlow, domain=DOMAIN):
    """Ask for the server URL and check /api/health."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            url = user_input[CONF_URL].strip().rstrip("/")
            await self.async_set_unique_id(url.lower())
            self._abort_if_unique_id_configured()
            try:
                health = await fetch_json(async_get_clientsession(self.hass), url, "/api/health")
            except (aiohttp.ClientError, TimeoutError, ValueError):
                errors["base"] = "cannot_connect"
            else:
                if isinstance(health, dict) and health.get("status") == "ok":
                    return self.async_create_entry(title="Athan Hub", data={CONF_URL: url})
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {vol.Required(CONF_URL, default=(user_input or {}).get(CONF_URL, DEFAULT_URL)): str}
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return AthanHubOptionsFlow()


class AthanHubOptionsFlow(OptionsFlow):
    """Athan audio URL used by athan_hub.play_athan."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data={CONF_ATHAN_URL: user_input.get(CONF_ATHAN_URL, "").strip()})
        current = self.config_entry.options.get(CONF_ATHAN_URL, "")
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {vol.Optional(CONF_ATHAN_URL, description={"suggested_value": current}): str}
            ),
        )
