# Changelog

## Unreleased

- Protocol hypothesis for a future release: `session_energy_raw` may be watt-hours.
  A live value of `1815` corresponded to `1.82 kWh` in the EcoFlow app. Keep the
  raw entity unchanged until additional sessions confirm the unit and rounding.
- Present session duration dynamically in a human-readable form instead of raw
  seconds (for example `42 s`, `12 min`, `1 h 08 min`, or `2 d 03 h`). Preserve
  the numeric seconds value internally for calculations and automations.

## 0.1.0-dev3

- Passively subscribe to C376 app-auth and device-facing SET candidate topics.
- Capture all observed SET traffic without allowing it to update entities.
- Add identifier-free MQTT subscription result codes to diagnostics.
- Keep the hard `listen_only` publish guard unchanged and covered by tests.

## 0.1.0-dev2

- Package manual-install ZIP files below `custom_components/`.
- Preserve diagnostic MQTT samples per channel and protocol command tuple.
- Keep official-app `set` and `set_reply` frames separate from telemetry.
- Prevent command and reply payloads from updating Home Assistant entities.
- Add CP307 envelope routing metadata to diagnostics.
- Retry interrupted listen-only MQTT connections from the coordinator.
- Mask account, user, and device identifiers in MQTT topic log messages.

## 0.1.0-dev1

- Decode XOR-protected CP307 heartbeat payloads from live C376 MQTT frames.
- Decode packed three-phase voltage and current values.
