from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfElectricPotential,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .coordinator import PyPowerwallCoordinator
from .data import PyPowerwallConfigEntry
from .entity import PyPowerwallEntity


@dataclass(frozen=True, kw_only=True)
class PyPowerwallSensorDescription(SensorEntityDescription):
    """Describe a PyPowerwall sensor."""

    value_fn: Any


def _vitals_frequency(d: dict) -> float | None:
    """Extract AC frequency from the first PVAC device in vitals."""
    for key, val in (d.get("vitals") or {}).items():
        if key.startswith("PVAC"):
            return val.get("PVAC_Fout")
    return None


SENSOR_DESCRIPTIONS: tuple[PyPowerwallSensorDescription, ...] = (
    # --- Power ---
    PyPowerwallSensorDescription(
        key="solar_power",
        translation_key="solar_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:solar-power",
        value_fn=lambda d: d["json"].get("solar"),
    ),
    PyPowerwallSensorDescription(
        key="battery_power",
        translation_key="battery_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:battery-charging",
        value_fn=lambda d: d["json"].get("battery"),
    ),
    PyPowerwallSensorDescription(
        key="grid_power",
        translation_key="grid_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:transmission-tower",
        value_fn=lambda d: d["json"].get("grid"),
    ),
    PyPowerwallSensorDescription(
        key="home_power",
        translation_key="home_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:home-lightning-bolt",
        value_fn=lambda d: d["json"].get("home"),
    ),
    # --- Battery ---
    PyPowerwallSensorDescription(
        key="battery_level",
        translation_key="battery_level",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: round(d["json"]["soe"], 1) if d["json"].get("soe") is not None else None,
    ),
    PyPowerwallSensorDescription(
        key="battery_reserve",
        translation_key="battery_reserve",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:battery-lock",
        value_fn=lambda d: d["json"].get("reserve"),
    ),
    PyPowerwallSensorDescription(
        key="time_remaining",
        translation_key="time_remaining",
        native_unit_of_measurement=UnitOfTime.HOURS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:timer-outline",
        value_fn=lambda d: round(d["json"]["time_remaining_hours"], 2) if d["json"].get("time_remaining_hours") is not None else None,
    ),
    # --- Grid ---
    PyPowerwallSensorDescription(
        key="grid_voltage",
        translation_key="grid_voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d["aggregates"].get("site", {}).get("instant_average_voltage"),
    ),
    PyPowerwallSensorDescription(
        key="grid_frequency",
        translation_key="grid_frequency",
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_vitals_frequency,
    ),
    # --- Diagnostic ---
    PyPowerwallSensorDescription(
        key="operation_mode",
        translation_key="operation_mode",
        icon="mdi:cog",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: (d.get("operation") or {}).get("real_mode"),
    ),
    PyPowerwallSensorDescription(
        key="pypowerwall_version",
        translation_key="pypowerwall_version",
        icon="mdi:information-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: (d.get("health") or {}).get("pypowerwall"),
    ),
    PyPowerwallSensorDescription(
        key="firmware_version",
        translation_key="firmware_version",
        icon="mdi:chip",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: (d.get("version_info") or {}).get("version"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PyPowerwallConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        PyPowerwallSensor(coordinator, entry.entry_id, description)
        for description in SENSOR_DESCRIPTIONS
    )


class PyPowerwallSensor(PyPowerwallEntity, SensorEntity):
    """A PyPowerwall sensor."""

    entity_description: PyPowerwallSensorDescription

    def __init__(
        self,
        coordinator: PyPowerwallCoordinator,
        entry_id: str,
        description: PyPowerwallSensorDescription,
    ) -> None:
        super().__init__(coordinator, entry_id)
        self.entity_description = description
        self._attr_unique_id = f"{entry_id}_{description.key}"

    @property
    def native_value(self) -> StateType:
        try:
            return self.entity_description.value_fn(self.coordinator.data)
        except (KeyError, TypeError):
            return None
