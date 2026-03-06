from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import PyPowerwallCoordinator
from .data import PyPowerwallConfigEntry
from .entity import PyPowerwallEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PyPowerwallConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data.coordinator
    if coordinator.has_control_secret:
        async_add_entities([PyPowerwallGridCharging(coordinator, entry.entry_id)])


class PyPowerwallGridCharging(PyPowerwallEntity, SwitchEntity):
    """Grid charging control switch."""

    _attr_translation_key = "grid_charging"
    _attr_icon = "mdi:transmission-tower-import"

    def __init__(self, coordinator: PyPowerwallCoordinator, entry_id: str) -> None:
        super().__init__(coordinator, entry_id)
        self._attr_unique_id = f"{entry_id}_grid_charging"

    @property
    def is_on(self) -> bool | None:
        data = self.coordinator.data.get("control_grid_charging")
        if data and isinstance(data, dict):
            val = data.get("grid_charging")
            if val is not None:
                return bool(val)
        return None

    async def async_turn_on(self, **kwargs) -> None:
        success = await self.coordinator.send_command(
            "/control/grid_charging", "true"
        )
        if not success:
            raise HomeAssistantError("Failed to enable grid charging")
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        success = await self.coordinator.send_command(
            "/control/grid_charging", "false"
        )
        if not success:
            raise HomeAssistantError("Failed to disable grid charging")
        await self.coordinator.async_request_refresh()
