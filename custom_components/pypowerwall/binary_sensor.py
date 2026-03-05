from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory
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
    async_add_entities([
        PyPowerwallGridConnected(coordinator, entry.entry_id),
        PyPowerwallGridFault(coordinator, entry.entry_id),
        PyPowerwallProxyDegraded(coordinator, entry.entry_id),
    ])


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


class PyPowerwallGridFault(PyPowerwallEntity, BinarySensorEntity):
    """Binary sensor: True when grid faults are present."""

    _attr_translation_key = "grid_fault"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator: PyPowerwallCoordinator, entry_id: str) -> None:
        super().__init__(coordinator, entry_id)
        self._attr_unique_id = f"{entry_id}_grid_fault"

    @property
    def is_on(self) -> bool | None:
        try:
            faults = self.coordinator.data["system_status"].get("grid_faults", [])
            return len(faults) > 0
        except (KeyError, TypeError):
            return None

    @property
    def extra_state_attributes(self) -> dict:
        try:
            return {"faults": self.coordinator.data["system_status"].get("grid_faults", [])}
        except (KeyError, TypeError):
            return {}


class PyPowerwallProxyDegraded(PyPowerwallEntity, BinarySensorEntity):
    """Binary sensor: True when pypowerwall proxy reports degraded connectivity."""

    _attr_translation_key = "proxy_degraded"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: PyPowerwallCoordinator, entry_id: str) -> None:
        super().__init__(coordinator, entry_id)
        self._attr_unique_id = f"{entry_id}_proxy_degraded"

    @property
    def is_on(self) -> bool | None:
        try:
            conn = self.coordinator.data["health"].get("connection_health", {})
            return bool(conn.get("is_degraded", False))
        except (KeyError, TypeError):
            return None

    @property
    def extra_state_attributes(self) -> dict:
        try:
            conn = self.coordinator.data["health"].get("connection_health", {})
            return {
                "consecutive_failures": conn.get("consecutive_failures"),
                "total_failures": conn.get("total_failures"),
                "total_successes": conn.get("total_successes"),
            }
        except (KeyError, TypeError):
            return {}
