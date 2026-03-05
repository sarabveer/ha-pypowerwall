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

    async def _async_update_data(self) -> dict[str, Any]:
        # Requests are sequential — pypowerwall proxy is single-threaded
        # and force_close=True avoids reusing stale connections
        connector = aiohttp.TCPConnector(force_close=True)
        try:
            async with aiohttp.ClientSession(connector=connector) as session:
                aggregates = await self._get(session, "/api/meters/aggregates")
                soe = await self._get(session, "/api/system_status/soe")
                grid_status = await self._get(session, "/api/grid_status")
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error communicating with pypowerwall proxy: {err}") from err

        return {
            "aggregates": aggregates,
            "soe": soe,
            "grid_status": grid_status,
        }

    async def _get(self, session: aiohttp.ClientSession, path: str) -> Any:
        async with session.get(
            f"{self._base_url}{path}",
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            resp.raise_for_status()
            return await resp.json(content_type=None)
