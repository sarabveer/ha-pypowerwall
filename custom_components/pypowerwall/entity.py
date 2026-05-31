from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PyPowerwallCoordinator


def clamp_percent(value: float) -> float:
    """Clamp a percentage value to Home Assistant's valid percentage range."""
    return max(0.0, min(100.0, value))


def raw_percent_to_app_percent(value: float) -> float:
    """Convert pypowerwall raw physical percent to Tesla app percent."""
    return clamp_percent((value - 5) / 0.95)


def build_alerts_by_source(coordinator_data: dict[str, Any]) -> dict[str, set[str]]:
    """Return current alerts grouped by source.

    Prefer per-device vitals alerts when available. Fall back to pypowerwall's
    normalized alerts helper, which also covers grid-status and solar fallback
    alerts on systems that don't expose vitals.
    """
    alerts_by_source: dict[str, set[str]] = {}
    for key, val in (coordinator_data.get("vitals") or {}).items():
        if isinstance(val, dict) and val.get("alerts"):
            alerts_by_source[key] = {str(alert) for alert in val["alerts"]}

    if alerts_by_source:
        return alerts_by_source

    alerts = coordinator_data.get("alerts")
    if isinstance(alerts, dict):
        alerts = alerts.get("alerts")
    if isinstance(alerts, list) and alerts:
        alerts_by_source["pypowerwall"] = {str(alert) for alert in alerts}

    return alerts_by_source


class PyPowerwallEntity(CoordinatorEntity[PyPowerwallCoordinator]):
    """Base entity for PyPowerwall integration."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: PyPowerwallCoordinator, entry_id: str) -> None:
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name="PyPowerwall",
            manufacturer="Tesla",
            model="Powerwall",
        )


def parse_vitals_key(key: str) -> tuple[str, str]:
    """Return (part_number, serial) from a vitals key like TEPOD--1707000-21-K--TG12...

    For TESYNC devices (key contains TESYNC----), returns ("", "tesync").
    """
    if key.startswith("TESYNC"):
        return "", "tesync"
    parts = key.split("--")
    serial = parts[-1] if len(parts) >= 3 else key
    part_number = parts[1] if len(parts) >= 2 else ""
    return part_number, serial


def build_block_by_serial(coordinator_data: dict[str, Any]) -> dict[str, dict]:
    """Build serial -> battery block lookup from system_status."""
    battery_blocks = (
        coordinator_data.get("system_status", {}).get("battery_blocks") or []
    )
    block_by_serial: dict[str, dict] = {}
    for block in battery_blocks:
        s = block.get("PackageSerialNumber")
        if s:
            block_by_serial[s] = block
    return block_by_serial


def build_device_labels(
    block_by_serial: dict[str, dict],
    vitals: dict[str, Any] | None = None,
) -> dict[str, str]:
    """Determine Primary/Follower/Expansion label for each serial.

    Uses the STSTSM gateway serial from vitals to definitively identify the
    Primary Powerwall.  The STSTSM device has ``STSTSM-Location: "Gateway"``
    and its serial matches the leader Powerwall's PVAC/TEPOD/TEPINV serial.

    For serials found in vitals but NOT in block_by_serial (e.g. PVAC/TEPINV
    devices), the label is inherited from the matching block serial or defaults
    to "Primary" when the serial matches the gateway.
    """
    labels: dict[str, str] = {}
    vitals = vitals or {}

    # 1. Find gateway serial from STSTSM key in vitals
    gateway_serial: str | None = None
    for vkey in vitals:
        if vkey.startswith("STSTSM"):
            _, gateway_serial = parse_vitals_key(vkey)
            break

    # 2. Label battery blocks
    non_expansion: list[str] = []
    for serial, block in block_by_serial.items():
        block_type = block.get("Type", "")
        if "Expansion" in block_type:
            labels[serial] = "Expansion"
        else:
            non_expansion.append(serial)

    if gateway_serial:
        # Definitive: gateway serial is Primary, rest are Followers
        for serial in non_expansion:
            labels[serial] = "Primary" if serial == gateway_serial else "Follower"
    elif len(non_expansion) == 1:
        labels[non_expansion[0]] = "Primary"
    elif len(non_expansion) > 1:
        # Fallback: first non-expansion is Primary
        labels[non_expansion[0]] = "Primary"
        for serial in non_expansion[1:]:
            labels[serial] = "Follower"

    # 3. Label vitals-only serials (PVAC, TEPINV without a battery_block)
    for vkey in vitals:
        if vkey.startswith(("PVAC", "TEPINV", "TEPOD")):
            _, serial = parse_vitals_key(vkey)
            if serial not in labels:
                if serial == gateway_serial:
                    labels[serial] = "Primary"
                else:
                    labels[serial] = labels.get(serial, "Follower")

    return labels


def parse_pod_data(pod_data: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    """Parse flat /pod response into per-powerwall dicts.

    The /pod endpoint returns a flat dict with PW1_, PW2_ prefixed keys.
    Returns {serial: {key_without_prefix: value, ...}} for each group.
    """
    if not pod_data:
        return {}

    result: dict[str, dict[str, Any]] = {}
    prefixes: set[str] = set()
    for key in pod_data:
        if key.startswith("PW") and "_" in key:
            prefix = key[: key.index("_") + 1]
            prefixes.add(prefix)

    for prefix in sorted(prefixes):
        pw_data: dict[str, Any] = {}
        for key, value in pod_data.items():
            if key.startswith(prefix):
                pw_data[key[len(prefix) :]] = value
        serial = pw_data.get("PackageSerialNumber", "")
        if serial:
            result[serial] = pw_data

    return result
