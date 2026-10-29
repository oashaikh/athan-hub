"""Athan Hub: a thin Home Assistant client for an Athan Hub server."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.components.media_player import (
    ATTR_MEDIA_ANNOUNCE,
    ATTR_MEDIA_CONTENT_ID,
    ATTR_MEDIA_CONTENT_TYPE,
    DOMAIN as MEDIA_PLAYER_DOMAIN,
    SERVICE_PLAY_MEDIA,
    MediaType,
)
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import ATTR_ENTITY_ID, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import CONF_ATHAN_URL, DOMAIN
from .coordinator import AthanHubConfigEntry, AthanHubCoordinator

PLATFORMS = [Platform.BINARY_SENSOR, Platform.CALENDAR, Platform.EVENT, Platform.SENSOR]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

SERVICE_PLAY_ATHAN = "play_athan"
ATTR_MEDIA_PLAYER = "media_player"
PLAY_ATHAN_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_MEDIA_PLAYER): cv.entity_ids,
        vol.Optional(ATTR_MEDIA_CONTENT_ID): cv.string,
        vol.Optional(ATTR_MEDIA_ANNOUNCE): cv.boolean,
    }
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the play_athan action once, independent of config entries."""

    async def play_athan(call: ServiceCall) -> None:
        url = call.data.get(ATTR_MEDIA_CONTENT_ID) or next(
            (
                entry.options.get(CONF_ATHAN_URL)
                for entry in hass.config_entries.async_entries(DOMAIN)
                if entry.state is ConfigEntryState.LOADED and entry.options.get(CONF_ATHAN_URL)
            ),
            None,
        )
        if not url:
            raise ServiceValidationError(
                "No athan audio URL. Set one in the Athan Hub integration options "
                "or pass media_content_id."
            )
        data = {
            ATTR_ENTITY_ID: call.data[ATTR_MEDIA_PLAYER],
            ATTR_MEDIA_CONTENT_ID: url,
            ATTR_MEDIA_CONTENT_TYPE: MediaType.MUSIC,
        }
        if ATTR_MEDIA_ANNOUNCE in call.data:
            data[ATTR_MEDIA_ANNOUNCE] = call.data[ATTR_MEDIA_ANNOUNCE]
        await hass.services.async_call(
            MEDIA_PLAYER_DOMAIN, SERVICE_PLAY_MEDIA, data, blocking=True, context=call.context
        )

    hass.services.async_register(DOMAIN, SERVICE_PLAY_ATHAN, play_athan, schema=PLAY_ATHAN_SCHEMA)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: AthanHubConfigEntry) -> bool:
    coordinator = AthanHubCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: AthanHubConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
