from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class PyPowerwallCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator that polls the pypowerwall proxy."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        port: int,
        session: aiohttp.ClientSession,
        scan_interval: int = DEFAULT_SCAN_INTERVAL,
        control_secret: str = "",
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self._base_url = f"http://{host}:{port}"
        self._session = session
        self._control_secret = control_secret
        self.max_backup_duration: int = 3600
        _LOGGER.debug(
            "PyPowerwallCoordinator initialised, base_url=%s, interval=%ss, control=%s",
            self._base_url,
            scan_interval,
            "enabled" if control_secret else "disabled",
        )

    async def _async_update_data(self) -> dict[str, Any]:
        _LOGGER.debug("Starting data refresh from %s", self._base_url)
        try:
            # Fire all requests concurrently
            (
                aggregates,
                vitals,
                health,
                data,
                soe,
                version_info,
                operation,
                system_status,
                sitemaster,
                pod,
                troubleshooting,
                stats,
            ) = await asyncio.gather(
                # Required endpoints
                self._get("/aggregates"),
                self._get("/vitals"),
                self._get("/health"),
                # Optional endpoints
                self._get_optional("/json"),
                self._get_optional("/api/system_status/soe"),
                self._get_optional("/version"),
                self._get_optional("/api/operation"),
                self._get_optional("/api/system_status"),
                self._get_optional("/api/sitemaster"),
                self._get_optional("/pod"),
                self._get_optional("/api/troubleshooting/problems"),
                self._get_optional("/stats"),
            )
            (
                control_reserve,
                control_mode,
                control_grid_charging,
                control_grid_export,
                control_max_backup,
            ) = await self._async_get_control_state()
        except UpdateFailed:
            raise
        except Exception as err:
            _LOGGER.exception("Unexpected error fetching pypowerwall data")
            raise UpdateFailed(f"Unexpected error: {err}") from err

        # Failsafe: if all core endpoints return None, proxy is down
        if all(v is None for v in [aggregates, vitals, health]):
            raise UpdateFailed("All core endpoints unreachable")

        return {
            "json": data or {},
            "aggregates": aggregates or {},
            "vitals": vitals or {},
            "health": health or {},
            "soe": soe or {},
            "version_info": version_info or {},
            "operation": operation,
            "system_status": system_status or {},
            "sitemaster": sitemaster or {},
            "pod": pod,
            "troubleshooting": troubleshooting,
            "stats": stats,
            "control_reserve": control_reserve,
            "control_mode": control_mode,
            "control_grid_charging": control_grid_charging,
            "control_grid_export": control_grid_export,
            "control_max_backup": control_max_backup,
        }

    async def _get(self, path: str) -> Any:
        url = f"{self._base_url}{path}"
        _LOGGER.debug("GET %s", url)
        try:
            async with self._session.get(
                url,
                headers={"Connection": "close"},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                _LOGGER.debug("Response %s: status=%s", url, resp.status)
                resp.raise_for_status()
                return await resp.json(content_type=None)
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as err:
            _LOGGER.error(
                "Error on GET %s: %s (%s)",
                url,
                err,
                type(err).__name__,
            )
            raise UpdateFailed(
                f"Error communicating with pypowerwall proxy: {err}"
            ) from err

    async def _get_optional(self, path: str) -> Any:
        """Fetch an endpoint, returning None on 404 or any client error."""
        url = f"{self._base_url}{path}"
        _LOGGER.debug("GET (optional) %s", url)
        try:
            async with self._session.get(
                url,
                headers={"Connection": "close"},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 404:
                    _LOGGER.debug("Optional endpoint %s returned 404", url)
                    return None
                resp.raise_for_status()
                data = await resp.json(content_type=None)
                if isinstance(data, dict) and (
                    "error" in data or "unauthorized" in data
                ):
                    _LOGGER.debug("Optional endpoint %s returned error: %s", url, data)
                    return None
                return data
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as err:
            _LOGGER.debug("Optional endpoint %s failed: %s", url, err)
            return None

    @property
    def has_control_secret(self) -> bool:
        """Return True if a control secret is configured."""
        return bool(self._control_secret)

    async def _async_get_control_state(self) -> tuple[Any, Any, Any, Any, Any]:
        """Fetch control state endpoints when control is configured."""
        if not self.has_control_secret:
            return None, None, None, None, None

        return tuple(
            await asyncio.gather(
                self._get_optional("/control/reserve"),
                self._get_optional("/control/mode"),
                self._get_optional("/control/grid_charging"),
                self._get_optional("/control/grid_export"),
                self._get_optional("/control/max_backup"),
            )
        )

    async def send_command(self, path: str, value: str | int | float) -> bool:
        """POST a control command to the proxy.

        Uses form data with value + token as expected by pypowerwall proxy:
          curl -X POST -d "value=VALUE&token=SECRET" http://host:port/control/...
        """
        if not self._control_secret:
            _LOGGER.error("Control secret not configured — cannot send command")
            return False
        url = f"{self._base_url}{path}"
        form_data = {"value": str(value), "token": self._control_secret}
        _LOGGER.debug("POST %s value=%s", url, value)
        try:
            async with self._session.post(
                url,
                data=form_data,
                headers={"Connection": "close"},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                _LOGGER.debug("POST %s: status=%s", url, resp.status)
                resp.raise_for_status()
                try:
                    response = await resp.json(content_type=None)
                except ValueError:
                    return True
                if isinstance(response, dict) and (
                    "error" in response or "unauthorized" in response
                ):
                    _LOGGER.error("POST %s returned error: %s", url, response)
                    return False
                return True
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            _LOGGER.error("POST %s failed: %s", url, err)
            return False
