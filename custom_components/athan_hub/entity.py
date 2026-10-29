"""Base entity for Athan Hub."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AthanHubCoordinator


class AthanHubEntity(CoordinatorEntity[AthanHubCoordinator]):
    """Groups every entity under one device per server."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: AthanHubCoordinator, key: str, name: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_name = name
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Athan Hub",
            manufacturer="Athan Hub",
            configuration_url=coordinator.url,
        )
