from __future__ import annotations

import asyncio
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_CONTROL_SECRET,
    CONF_SCAN_INTERVAL,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=65535)
        ),
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
            vol.Coerce(int), vol.Range(min=5, max=300)
        ),
        vol.Optional(CONF_CONTROL_SECRET): str,
    }
)


async def _test_connection(hass: HomeAssistant, host: str, port: int) -> bool:
    url = f"http://{host}:{port}/api/system_status/soe"
    try:
        session = async_get_clientsession(hass)
        async with session.get(
            url,
            headers={"Connection": "close"},
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            if resp.status != 200:
                return False
            data = await resp.json(content_type=None)
            return isinstance(data, dict)
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
        return False


class PyPowerwallConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow for PyPowerwall."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            port = user_input[CONF_PORT]

            if await _test_connection(self.hass, host, port):
                await self.async_set_unique_id(f"{host}:{port}")
                self._abort_if_unique_id_configured()
                options = {
                    CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL],
                    CONF_CONTROL_SECRET: user_input.get(CONF_CONTROL_SECRET, ""),
                }
                return self.async_create_entry(
                    title=f"PyPowerwall ({host}:{port})",
                    data={CONF_HOST: host, CONF_PORT: port},
                    options=options,
                )
            errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return PyPowerwallOptionsFlow(config_entry)


class PyPowerwallOptionsFlow(OptionsFlow):
    """Options flow to change scan interval."""

    def __init__(self, config_entry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current_interval = self._config_entry.options.get(
            CONF_SCAN_INTERVAL,
            self._config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )
        current_secret = self._config_entry.options.get(
            CONF_CONTROL_SECRET,
            self._config_entry.data.get(CONF_CONTROL_SECRET, ""),
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_SCAN_INTERVAL, default=current_interval): vol.All(
                        vol.Coerce(int), vol.Range(min=5, max=300),
                    ),
                    vol.Optional(CONF_CONTROL_SECRET, default=current_secret): str,
                }
            ),
        )
