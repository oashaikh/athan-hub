"""Whether the server is playing the athan right now."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import AthanHubConfigEntry
from .entity import AthanHubEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AthanHubConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([PlayingSensor(entry.runtime_data)])


class PlayingSensor(AthanHubEntity, BinarySensorEntity):
    """On while /api/playback/status reports active playback (polled, so up to 60 s late)."""

    _attr_device_class = BinarySensorDeviceClass.SOUND

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "playing", "Athan playing")

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.playback.get("active"))

    @property
    def extra_state_attributes(self) -> dict:
        playback = self.coordinator.data.playback
        return {k: v for k, v in playback.items() if k in ("prayer", "remaining_seconds")}
