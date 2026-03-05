from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

    from .coordinator import PyPowerwallCoordinator


@dataclass
class PyPowerwallData:
    """Runtime data stored on the config entry."""

    coordinator: PyPowerwallCoordinator


type PyPowerwallConfigEntry = ConfigEntry[PyPowerwallData]
