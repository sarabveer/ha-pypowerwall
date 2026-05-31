from __future__ import annotations

from homeassistant.components.event import EventEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .data import PyPowerwallConfigEntry
from .entity import PyPowerwallEntity

EVENT_ALERT_FIRED = "alert_fired"
EVENT_ALERT_CLEARED = "alert_cleared"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PyPowerwallConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data.coordinator
    async_add_entities([PyPowerwallAlertEvent(coordinator, entry.entry_id)])


class PyPowerwallAlertEvent(PyPowerwallEntity, EventEntity):
    """Fires events when Powerwall alerts are raised or cleared."""

    _attr_translation_key = "powerwall_alert"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_event_types = [EVENT_ALERT_FIRED, EVENT_ALERT_CLEARED]

    def __init__(self, coordinator, entry_id: str) -> None:
        super().__init__(coordinator, entry_id)
        self._attr_unique_id = f"{entry_id}_powerwall_alert"
        self._previous_alerts: dict[str, set[str]] | None = None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Diff current vs previous alerts and fire events for changes."""
        vitals = self.coordinator.data.get("vitals") or {}

        current_alerts: dict[str, set[str]] = {}
        for key, val in vitals.items():
            if isinstance(val, dict) and val.get("alerts"):
                current_alerts[key] = set(val["alerts"])

        if self._previous_alerts is not None:
            all_keys = set(self._previous_alerts) | set(current_alerts)
            for key in sorted(all_keys):
                prev = self._previous_alerts.get(key, set())
                curr = current_alerts.get(key, set())
                device_type = key.split("--")[0]

                for alert in sorted(curr - prev):
                    self._trigger_event(
                        EVENT_ALERT_FIRED,
                        {"alert": alert, "device": key, "device_type": device_type},
                    )

                for alert in sorted(prev - curr):
                    self._trigger_event(
                        EVENT_ALERT_CLEARED,
                        {"alert": alert, "device": key, "device_type": device_type},
                    )

        self._previous_alerts = current_alerts
        super()._handle_coordinator_update()
