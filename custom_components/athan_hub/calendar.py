"""Prayer times calendar covering today and the next few days."""

from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import PRAYERS
from .coordinator import AthanHubConfigEntry, AthanHubCoordinator, Prayer
from .entity import AthanHubEntity

# ponytail: fixed event length; a prayer has no natural end time in the timetable.
EVENT_LENGTH = timedelta(minutes=15)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AthanHubConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([PrayerCalendar(entry.runtime_data)])


def to_event(prayer: Prayer) -> CalendarEvent:
    return CalendarEvent(
        start=prayer.at,
        end=prayer.at + EVENT_LENGTH,
        summary=PRAYERS[prayer.key],
        description="Athan excluded" if prayer.excluded else None,
        uid=f"{prayer.key}-{prayer.at.date().isoformat()}",
    )


class PrayerCalendar(AthanHubEntity, CalendarEntity):
    """Mirrors Mawaqit's "Prayer Times" calendar."""

    def __init__(self, coordinator: AthanHubCoordinator) -> None:
        super().__init__(coordinator, "calendar", "Prayer times")

    @property
    def event(self) -> CalendarEvent | None:
        now = dt_util.now()
        for prayer in self.coordinator.data.prayers:
            if prayer.at + EVENT_LENGTH > now:
                return to_event(prayer)
        return None

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        return [
            to_event(p)
            for p in self.coordinator.data.prayers
            if p.at < end_date and p.at + EVENT_LENGTH > start_date
        ]
