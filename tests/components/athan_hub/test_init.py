"""Tests for the Athan Hub integration."""

from datetime import datetime, timedelta
from unittest.mock import patch

import aiohttp
import pytest

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import ServiceValidationError
from homeassistant.util import dt as dt_util

from pytest_homeassistant_custom_component.common import async_fire_time_changed, async_mock_service

from custom_components.athan_hub.const import DOMAIN

from .conftest import URL


async def test_config_flow_success(hass: HomeAssistant, server) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    assert result["type"] is FlowResultType.FORM
    with patch("custom_components.athan_hub.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"url": f" {URL}/ "})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {"url": URL}
    assert result["result"].unique_id == URL


async def test_config_flow_cannot_connect(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.get(f"{URL}/api/health", exc=aiohttp.ClientError())
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"url": URL})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_config_flow_duplicate(hass: HomeAssistant, entry) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"url": URL})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_setup_fails_when_server_down(hass: HomeAssistant, aioclient_mock) -> None:
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    aioclient_mock.get(f"{URL}/api/public/config", exc=aiohttp.ClientError())
    entry = MockConfigEntry(domain=DOMAIN, data={"url": URL})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_sensors(hass: HomeAssistant, entry) -> None:
    def state(name):
        return hass.states.get(f"sensor.athan_hub_{name}")

    assert state("fajr").state == "2026-10-29T05:09:00+00:00"
    assert state("shuruq").state == "2026-10-29T06:55:00+00:00"
    assert state("dhuhr").state == "2026-10-29T11:50:00+00:00"
    assert state("asr").attributes["excluded"] is True
    assert state("maghrib").attributes["excluded"] is False
    assert state("isha").state == "unknown"
    assert state("next_prayer").state == "Maghrib"
    assert state("next_prayer_time").state == "2026-10-29T16:45:00+00:00"
    assert hass.states.get("binary_sensor.athan_hub_athan_playing").state == "off"


async def test_calendar(hass: HomeAssistant, entry) -> None:
    calendar = hass.states.get("calendar.athan_hub_prayer_times")
    assert calendar.attributes["message"] == "Dhuhr"  # 11:50 event still running at 12:00
    assert calendar.state == "on"
    response = await hass.services.async_call(
        "calendar",
        "get_events",
        {"entity_id": "calendar.athan_hub_prayer_times",
         "start_date_time": "2026-10-29T00:00:00+00:00", "end_date_time": "2026-10-31T00:00:00+00:00"},
        blocking=True,
        return_response=True,
    )
    events = response["calendar.athan_hub_prayer_times"]["events"]
    assert len(events) == 10  # five timed prayers a day, Isha disabled
    assert events[0]["summary"] == "Fajr"
    assert events[0]["start"] == "2026-10-29T05:09:00+00:00"
    assert events[3]["description"] == "Athan excluded"


async def test_event_fires_at_prayer_time(hass: HomeAssistant, entry, freezer) -> None:
    assert hass.states.get("event.athan_hub_prayer").state == "unknown"
    target = datetime(2026, 10, 29, 14, 20, tzinfo=dt_util.UTC)
    freezer.move_to(target)
    async_fire_time_changed(hass, target)
    await hass.async_block_till_done()
    state = hass.states.get("event.athan_hub_prayer")
    assert state.attributes["event_type"] == "asr"
    assert state.attributes["excluded"] is True

    target += timedelta(hours=2, minutes=25)
    freezer.move_to(target)
    async_fire_time_changed(hass, target)
    await hass.async_block_till_done()
    assert hass.states.get("event.athan_hub_prayer").attributes["event_type"] == "maghrib"


async def test_play_athan(hass: HomeAssistant, entry) -> None:
    calls = async_mock_service(hass, "media_player", "play_media")

    with pytest.raises(ServiceValidationError, match="No athan audio URL"):
        await hass.services.async_call(
            DOMAIN, "play_athan", {"media_player": "media_player.kitchen"}, blocking=True
        )

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"athan_url": " https://example.org/athan.mp3 "}
    )
    assert entry.options == {"athan_url": "https://example.org/athan.mp3"}

    await hass.services.async_call(
        DOMAIN, "play_athan", {"media_player": "media_player.kitchen", "announce": True}, blocking=True
    )
    await hass.services.async_call(
        DOMAIN, "play_athan",
        {"media_player": ["media_player.a", "media_player.b"], "media_content_id": "media-source://x"},
        blocking=True,
    )
    assert calls[0].data == {
        "entity_id": ["media_player.kitchen"],
        "media_content_id": "https://example.org/athan.mp3",
        "media_content_type": "music",
        "announce": True,
    }
    assert calls[1].data["entity_id"] == ["media_player.a", "media_player.b"]
    assert calls[1].data["media_content_id"] == "media-source://x"
    assert "announce" not in calls[1].data


async def test_unload(hass: HomeAssistant, entry) -> None:
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state is ConfigEntryState.NOT_LOADED
