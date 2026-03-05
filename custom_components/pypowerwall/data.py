from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import aiohttp

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

    from .coordinator import PyPowerwallCoordinator


@dataclass
class PyPowerwallData:
    """Runtime data stored on the config entry."""

    session: aiohttp.ClientSession
    coordinator: PyPowerwallCoordinator


type PyPowerwallConfigEntry = ConfigEntry[PyPowerwallData]
