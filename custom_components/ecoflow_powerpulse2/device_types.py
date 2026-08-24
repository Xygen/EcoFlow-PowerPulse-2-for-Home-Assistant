"""Serial-prefix device families used by discovery."""

from __future__ import annotations

# CP307 protocol devices observed by the EcoFlow BLE community. C37x covers
# the European 7/11/22 kW PowerPulse 2 family; the C10x variants use the same
# heartbeat and are retained so discovery remains useful across regions.
POWERPULSE_PREFIXES = (
    "C101",
    "C102",
    "C103",
    "C371",
    "C372",
    "C373",
    "C374",
    "C375",
    "C376",
)

# PowerPulse accessories linked to a PowerOcean report part of their state on
# the parent system's MQTT stream. These prefixes are intentionally used only
# for passive observation; no Home Assistant device or controls are created for
# the PowerOcean by this integration.
POWEROCEAN_PREFIXES = (
    "HJ31",
    "HJ32",
    "HJ35",
    "HJ37",
    "J327",
    "J32B",
    "J32D",
    "J32E",
    "R371",
    "R372",
    "R374",
    "HJ3C",
)
