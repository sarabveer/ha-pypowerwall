from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import PyPowerwallCoordinator
from .data import PyPowerwallConfigEntry
from .entity import PyPowerwallEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PyPowerwallConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data.coordinator
    async_add_entities([PyPowerwallGridConnected(coordinator, entry.entry_id)])


class PyPowerwallGridConnected(PyPowerwallEntity, BinarySensorEntity):
    """Binary sensor: is the grid connected? grid_status=1 means connected."""

    _attr_translation_key = "grid_connected"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, coordinator: PyPowerwallCoordinator, entry_id: str) -> None:
        super().__init__(coordinator, entry_id)
        self._attr_unique_id = f"{entry_id}_grid_connected"

    @property
    def is_on(self) -> bool | None:
        try:
            return self.coordinator.data["json"].get("grid_status") == 1
        except (KeyError, TypeError):
            return None
