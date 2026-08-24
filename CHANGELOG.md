# Changelog

## Unreleased

- Release requirement: create and bundle a dedicated PowerPulse 2 integration
  icon no later than the first non-development release.
- Protocol hypothesis for a future release: `session_energy_raw` may be watt-hours.
  A live value of `1815` corresponded to `1.82 kWh` in the EcoFlow app. Keep the
  raw entity unchanged until additional sessions confirm the unit and rounding.

## 0.1.0-dev7

- Decode the XOR-protected CP307 `2/34` settings report after paired live tests.
- Add read-only entities for Plug-and-Play, phase selection (`1-phasig`,
  `3-phasig`, `Auto`), battery-discharge blocking, screen and LED state, and
  their four brightness levels.
- Present the confirmed maximum-output-current value in amperes. Raw values
  `150` and `160` matched `15 A` and `16 A` in the EcoFlow app.
- Keep OCPP and every write/control path deferred; MQTT remains hard
  listen-only.

## 0.1.0-dev6

- Preserve MQTT telemetry received while an HTTP snapshot request is in flight.
  A slow or empty provider response can no longer replace fresh charger values
  with an empty data set and make every entity unavailable.

## 0.1.0-dev5

- Add a read-only, translated operating-mode sensor for the live-confirmed
  values Fast charging, Solar mode, Custom, and Smart mode.
- Read Smart ready-by time and energy target from the provider snapshot. A
  `30 kWh` target was confirmed as raw `30000`; distance mode reports `0` in
  this energy field and keeps its kilometre target elsewhere.
- Add disabled-by-default raw provider fields for current, setting flags,
  phase selection, and vehicle consumption to support the next paired tests.
- Present session duration dynamically in a human-readable form instead of raw
  seconds (for example `42 s`, `12 min`, `1 h 08 min`, or `2 d 03 h`). Preserve
  the numeric seconds value internally for calculations and automations.
- Keep every MQTT client hard listen-only; the mode and target tests exposed no
  validated SET request or acknowledgement.
- Pin the lightweight test dependencies to avoid incompatible pytest resolver
  choices on Windows.

## 0.1.0-dev4

- Route CP307 protobuf envelopes by command type so the `2/34` parameter
  report can no longer overwrite heartbeat telemetry with unrelated fields.
- Ignore encrypted wire payloads after their decoded form has been selected.
- Add three passive wildcard subscriptions and privacy-safe topic patterns to
  help discover PowerPulse-specific command routes without enabling writes.
- Record that Solar Mode's continuous-charging current is distinct from the
  charger's separate maximum-current setting.

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
