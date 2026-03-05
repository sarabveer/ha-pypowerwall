from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class PyPowerwallCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator that polls the pypowerwall proxy."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        port: int,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=SCAN_INTERVAL),
        )
        self._base_url = f"http://{host}:{port}"
        _LOGGER.debug("PyPowerwallCoordinator initialised, base_url=%s", self._base_url)

    async def _async_update_data(self) -> dict[str, Any]:
        _LOGGER.debug("Starting data refresh from %s", self._base_url)
        connector = aiohttp.TCPConnector(force_close=True)
        try:
            async with aiohttp.ClientSession(connector=connector) as session:
                aggregates = await self._get(session, "/api/meters/aggregates")
                _LOGGER.debug("aggregates OK: %s", aggregates)
                soe = await self._get(session, "/api/system_status/soe")
                _LOGGER.debug("soe OK: %s", soe)
                grid_status = await self._get(session, "/api/grid_status")
                _LOGGER.debug("grid_status OK: %s", grid_status)
        except UpdateFailed:
            raise
        except Exception as err:
            _LOGGER.exception("Unexpected error fetching pypowerwall data")
            raise UpdateFailed(f"Unexpected error: {err}") from err

        return {
            "aggregates": aggregates,
            "soe": soe,
            "grid_status": grid_status,
        }

    async def _get(self, session: aiohttp.ClientSession, path: str) -> Any:
        url = f"{self._base_url}{path}"
        _LOGGER.debug("GET %s", url)
        try:
            async with session.get(
                url,
                headers={"Connection": "close"},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                _LOGGER.debug("Response %s: status=%s", url, resp.status)
                resp.raise_for_status()
                data = await resp.json(content_type=None)
                return data
        except aiohttp.ClientError as err:
            _LOGGER.error("ClientError on GET %s: %s (%s)", url, err, type(err).__name__)
            raise UpdateFailed(f"Error communicating with pypowerwall proxy: {err}") from err
