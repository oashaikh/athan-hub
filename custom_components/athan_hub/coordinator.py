"""Poll the Athan Hub server."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
import logging
from typing import Any

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_URL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import DAYS_AHEAD, DOMAIN, PRAYERS

_LOGGER = logging.getLogger(__name__)

type AthanHubConfigEntry = ConfigEntry[AthanHubCoordinator]


@dataclass
class Prayer:
    """One prayer on one day."""

    key: str
    at: datetime
    excluded: bool


@dataclass
class AthanHubData:
    """Parsed server state."""

    today: dict[str, Prayer | None]
    prayers: list[Prayer] = field(default_factory=list)  # all days, sorted
    next_prayer: str | None = None
    next_time: datetime | None = None
    playback: dict[str, Any] = field(default_factory=dict)


async def fetch_json(session: aiohttp.ClientSession, url: str, path: str, **params: str) -> Any:
    """GET a JSON document from the server."""
    async with session.get(
        f"{url}{path}", params=params, timeout=aiohttp.ClientTimeout(total=10)
    ) as resp:
        resp.raise_for_status()
        return await resp.json()


def parse_day(day: dict[str, Any], tz) -> dict[str, Prayer | None]:
    """Turn a /api/timetable/day payload into aware datetimes."""
    on = date.fromisoformat(day["date"])
    result: dict[str, Prayer | None] = {}
    for key in PRAYERS:
        info = (day.get("prayers") or {}).get(key) or {}
        value = info.get("effective")
        if not value:
            result[key] = None  # no timetable row, or disabled by override
            continue
        hour, minute = (int(part) for part in value.split(":"))
        result[key] = Prayer(key, datetime.combine(on, time(hour, minute), tz), bool(info.get("excluded")))
    return result


class AthanHubCoordinator(DataUpdateCoordinator[AthanHubData]):
    """Fetch today's timetable, the next few days and the next prayer."""

    config_entry: AthanHubConfigEntry

    def __init__(self, hass: HomeAssistant, entry: AthanHubConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=60),
        )
        self.url: str = entry.data[CONF_URL]
        self.session = async_get_clientsession(hass)

    async def _get(self, path: str, **params: str) -> Any:
        return await fetch_json(self.session, self.url, path, **params)

    async def _async_update_data(self) -> AthanHubData:
        try:
            config = await self._get("/api/public/config")
            # Server times are local to the server's zone, which may differ from HA's.
            tz = await dt_util.async_get_time_zone(
                config.get("timezone") or self.hass.config.time_zone
            ) or dt_util.get_default_time_zone()
            today = dt_util.now(tz).date()
            dates = [(today + timedelta(days=i)).isoformat() for i in range(DAYS_AHEAD)]
            nxt, playback, *days = await asyncio.gather(
                self._get("/api/timetable/next"),
                self._get("/api/playback/status"),
                *(self._get("/api/timetable/day", date=d) for d in dates),
            )
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise UpdateFailed(f"Cannot reach Athan Hub at {self.url}: {err}") from err

        parsed = [parse_day(day, tz) for day in days]
        data = AthanHubData(
            today=parsed[0],
            prayers=sorted((p for day in parsed for p in day.values() if p), key=lambda p: p.at),
            playback=playback or {},
        )
        if nxt := (nxt or {}).get("next"):
            data.next_prayer = nxt.get("prayer")
            data.next_time = dt_util.parse_datetime(nxt.get("at") or "")
        return data
