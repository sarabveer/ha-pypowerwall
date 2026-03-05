from __future__ import annotations

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant

from .coordinator import PyPowerwallCoordinator
from .data import PyPowerwallConfigEntry, PyPowerwallData

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: PyPowerwallConfigEntry) -> bool:
    session = aiohttp.ClientSession()
    coordinator = PyPowerwallCoordinator(
        hass,
        session,
        host=entry.data[CONF_HOST],
        port=entry.data[CONF_PORT],
    )
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = PyPowerwallData(session=session, coordinator=coordinator)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: PyPowerwallConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.session.close()
    return unload_ok
