from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PyPowerwallCoordinator


class PyPowerwallEntity(CoordinatorEntity[PyPowerwallCoordinator]):
    """Base entity for PyPowerwall integration."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: PyPowerwallCoordinator, entry_id: str) -> None:
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name="PyPowerwall",
            manufacturer="Tesla",
            model="Powerwall",
        )
