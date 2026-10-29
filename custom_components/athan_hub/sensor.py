"""Prayer time sensors, named like the Mawaqit integration's."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import PRAYERS
from .coordinator import AthanHubConfigEntry, AthanHubCoordinator
from .entity import AthanHubEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AthanHubConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        [
            *(PrayerSensor(coordinator, key) for key in PRAYERS),
            NextPrayerSensor(coordinator),
            NextPrayerTimeSensor(coordinator),
        ]
    )


class PrayerSensor(AthanHubEntity, SensorEntity):
    """Today's time for one prayer."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: AthanHubCoordinator, key: str) -> None:
        super().__init__(coordinator, key, PRAYERS[key])
        self._key = key

    @property
    def native_value(self) -> datetime | None:
        prayer = self.coordinator.data.today.get(self._key)
        return prayer.at if prayer else None

    @property
    def extra_state_attributes(self) -> dict[str, bool]:
        prayer = self.coordinator.data.today.get(self._key)
        return {"excluded": bool(prayer and prayer.excluded)}


class NextPrayerSensor(AthanHubEntity, SensorEntity):
    """Name of the next prayer that will sound the athan."""

    _attr_icon = "mdi:mosque"

    def __init__(self, coordinator: AthanHubCoordinator) -> None:
        super().__init__(coordinator, "next_prayer", "Next prayer")

    @property
    def native_value(self) -> str | None:
        key = self.coordinator.data.next_prayer
        return PRAYERS.get(key, key) if key else None


class NextPrayerTimeSensor(AthanHubEntity, SensorEntity):
    """Time of the next prayer."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: AthanHubCoordinator) -> None:
        super().__init__(coordinator, "next_prayer_time", "Next prayer time")

    @property
    def native_value(self) -> datetime | None:
        return self.coordinator.data.next_time
