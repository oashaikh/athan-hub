"""Fixtures for Athan Hub integration tests."""

from datetime import date, timedelta

import pytest

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.athan_hub.const import DOMAIN

URL = "http://athan.test"
TODAY = date(2026, 10, 29)  # Europe/London is on GMT, so local == UTC


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


def day_payload(on: date) -> dict:
    def p(effective, excluded=False):
        return {"base": effective, "override": None, "enabled": effective is not None,
                "effective": effective, "source": "csv", "excluded": excluded}

    return {
        "date": on.isoformat(),
        "prayers": {
            "fajr": p("5:09"),
            "shurooq": p("6:55"),
            "dhuhr": p("11:50"),
            "asr": p("14:20", excluded=True),
            "maghrib": p("16:45"),
            "isha": p(None),  # disabled by an override
        },
    }


@pytest.fixture
def server(aioclient_mock):
    """Fake Athan Hub server answering the read-only endpoints."""
    aioclient_mock.get(f"{URL}/api/health", json={"status": "ok", "time": "x"})
    aioclient_mock.get(f"{URL}/api/public/config", json={"timezone": "Europe/London"})
    aioclient_mock.get(
        f"{URL}/api/timetable/next",
        json={"next": {"date": "2026-10-29", "prayer": "maghrib", "time": "16:45",
                       "at": "2026-10-29T16:45:00+00:00", "countdown": 3933}},
    )
    aioclient_mock.get(f"{URL}/api/playback/status", json={"active": False, "remaining_seconds": 0})
    for i in range(7):
        on = TODAY + timedelta(days=i)
        aioclient_mock.get(f"{URL}/api/timetable/day?date={on.isoformat()}", json=day_payload(on))
    return aioclient_mock


@pytest.fixture
async def entry(hass, server, freezer):
    freezer.move_to("2026-10-29T12:00:00+00:00")
    await hass.config.async_set_time_zone("Europe/London")
    entry = MockConfigEntry(domain=DOMAIN, data={"url": URL}, unique_id=URL)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry
