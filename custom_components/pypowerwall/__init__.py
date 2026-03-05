from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .coordinator import PyPowerwallCoordinator
from .data import PyPowerwallConfigEntry, PyPowerwallData

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: PyPowerwallConfigEntry) -> bool:
    session = async_get_clientsession(hass)
    coordinator = PyPowerwallCoordinator(
        hass,
        session,
        host=entry.data[CONF_HOST],
        port=entry.data[CONF_PORT],
    )
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = PyPowerwallData(coordinator=coordinator)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: PyPowerwallConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
