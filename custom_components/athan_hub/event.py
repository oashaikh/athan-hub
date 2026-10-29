"""Event entity that fires at each prayer time.

The coordinator polls every minute, but the event is driven by a timer set for
the exact prayer time, so it fires on the minute rather than up to 60 s late.
If Home Assistant is not running at that moment, the event is skipped.
"""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.event import EventEntity
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_track_point_in_time
from homeassistant.util import dt as dt_util

from .const import PRAYERS
from .coordinator import AthanHubConfigEntry, AthanHubCoordinator, Prayer
from .entity import AthanHubEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AthanHubConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([PrayerEvent(entry.runtime_data)])


class PrayerEvent(AthanHubEntity, EventEntity):
    """event.athan_hub_prayer; event_type is the prayer key, e.g. "maghrib"."""

    _attr_event_types = list(PRAYERS)
    _attr_icon = "mdi:mosque"

    def __init__(self, coordinator: AthanHubCoordinator) -> None:
        super().__init__(coordinator, "prayer", "Prayer")
        self._target: Prayer | None = None
        self._unsub: CALLBACK_TYPE | None = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._schedule()
        self.async_on_remove(self._cancel)

    @callback
    def _handle_coordinator_update(self) -> None:
        self._schedule()
        super()._handle_coordinator_update()

    def _cancel(self) -> None:
        if self._unsub:
            self._unsub()
            self._unsub = None

    @callback
    def _schedule(self) -> None:
        now = dt_util.now()
        upcoming = next((p for p in self.coordinator.data.prayers if p.at > now), None)
        if upcoming == self._target and self._unsub:
            return
        self._cancel()
        self._target = upcoming
        if upcoming:
            self._unsub = async_track_point_in_time(self.hass, self._fire, upcoming.at)

    @callback
    def _fire(self, _now: datetime) -> None:
        prayer = self._target
        self._unsub = None
        self._target = None
        if prayer:
            self._trigger_event(
                prayer.key,
                {"name": PRAYERS[prayer.key], "time": prayer.at.isoformat(), "excluded": prayer.excluded},
            )
            self.async_write_ha_state()
        self._schedule()
