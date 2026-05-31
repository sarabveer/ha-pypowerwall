from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import PERCENTAGE, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import PyPowerwallCoordinator
from .data import PyPowerwallConfigEntry
from .entity import PyPowerwallEntity, clamp_percent, raw_percent_to_app_percent


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PyPowerwallConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data.coordinator
    if coordinator.has_control_secret:
        async_add_entities([
            PyPowerwallBackupReserve(coordinator, entry.entry_id),
            PyPowerwallMaxBackupDuration(coordinator, entry.entry_id),
        ])


class PyPowerwallBackupReserve(PyPowerwallEntity, NumberEntity):
    """Backup reserve percentage control."""

    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_mode = NumberMode.SLIDER
    _attr_icon = "mdi:battery-lock"
    _attr_translation_key = "backup_reserve"

    def __init__(self, coordinator: PyPowerwallCoordinator, entry_id: str) -> None:
        super().__init__(coordinator, entry_id)
        self._attr_unique_id = f"{entry_id}_backup_reserve"

    @property
    def native_value(self) -> float | None:
        d = self.coordinator.data
        # /api/operation reports raw physical reserve. HA should match the Tesla app.
        op = d.get("operation")
        if op and isinstance(op, dict):
            val = op.get("backup_reserve_percent")
            if val is not None:
                return raw_percent_to_app_percent(float(val))

        # /control/reserve and /json come from pypowerwall.get_reserve(), which
        # already returns Tesla app scale by default.
        reserve = d.get("control_reserve")
        if reserve and isinstance(reserve, dict):
            val = reserve.get("reserve")
            if val is not None:
                return clamp_percent(float(val))
        val = d.get("json", {}).get("reserve")
        if val is not None:
            return clamp_percent(float(val))
        return None

    async def async_set_native_value(self, value: float) -> None:
        app_percent = int(round(clamp_percent(value)))
        success = await self.coordinator.send_command(
            "/control/reserve", app_percent
        )
        if not success:
            raise HomeAssistantError(
                f"Failed to set backup reserve to {app_percent}%"
            )
        await self.coordinator.async_request_refresh()


class PyPowerwallMaxBackupDuration(PyPowerwallEntity, NumberEntity):
    """Max backup duration control."""

    _attr_native_min_value = 1
    _attr_native_max_value = 480
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_mode = NumberMode.SLIDER
    _attr_icon = "mdi:timer-outline"
    _attr_translation_key = "max_backup_duration"

    def __init__(self, coordinator: PyPowerwallCoordinator, entry_id: str) -> None:
        super().__init__(coordinator, entry_id)
        self._attr_unique_id = f"{entry_id}_max_backup_duration"

    @property
    def native_value(self) -> float | None:
        return self.coordinator.max_backup_duration / 60

    async def async_set_native_value(self, value: float) -> None:
        self.coordinator.max_backup_duration = int(value) * 60
        self.async_write_ha_state()
