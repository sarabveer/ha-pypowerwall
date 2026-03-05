# ha-pypowerwall

Home Assistant custom integration for [pypowerwall](https://github.com/jasonacox/pypowerwall) proxy.

## How it works

```
HA → HTTP GET → pypowerwall proxy (:8675) → Powerwall gateway
```

No Python pypowerwall library required in HA — pure `aiohttp`.

## Installation

1. Copy `custom_components/pypowerwall/` into your HA `custom_components/` directory.
2. Restart Home Assistant.
3. Go to **Settings → Devices & Services → Add Integration** and search for **PyPowerwall**.
4. Enter your pypowerwall proxy host and port (default: `8675`).

## Entities

### Sensors (7)
| Entity | Unit | Description |
|--------|------|-------------|
| Solar Power | W | Instantaneous solar generation |
| Battery Power | W | Battery charge/discharge (positive = discharging) |
| Grid Power | W | Grid import/export (positive = importing) |
| Home Power | W | Home load consumption |
| Battery Level | % | State of charge |
| Grid Voltage | V | Grid voltage |
| Grid Frequency | Hz | Grid frequency |

### Binary Sensors (1)
| Entity | Description |
|--------|-------------|
| Grid Connected | True when grid status is `SystemGridConnected` |

## Requirements

- Running pypowerwall proxy (e.g. `python -m pypowerwall -port 8675`)
- Home Assistant 2024.1+
