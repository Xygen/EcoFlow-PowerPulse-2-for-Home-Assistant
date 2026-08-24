# Changelog

## Unreleased

- Release requirement: create and bundle a dedicated PowerPulse 2 integration
  icon no later than the first non-development release.
- Protocol hypothesis for a future release: `session_energy_raw` may be watt-hours.
  A live value of `1815` corresponded to `1.82 kWh` in the EcoFlow app. Keep the
  raw entity unchanged until additional sessions confirm the unit and rounding.

## 0.1.0-dev13

- Correct the EcoFlow envelope mapping: field 6 is `enc_type`; field 11 is
  `need_ack`. dev12 incorrectly XOR-decoded acknowledgement-requesting
  plaintext `241/102` bodies and classified them as opaque.
- Apply the correction consistently to direct CP307 telemetry, PowerOcean
  accessory diagnostics, observer-command inspection, and exported envelope
  metadata.
- Preserve `need_ack` separately in diagnostics and inspect the bounded nested
  `241/102` protobuf structure without retaining raw byte or text contents.
- Increase the diagnostic capture schema to 6 without adding any MQTT publish
  route; the integration remains hard `listen_only`.
- Extend the suite to 31 passing tests, including regressions proving that
  `need_ack=1` alone never triggers XOR while `enc_type=1` still does.

## 0.1.0-dev12

- Add privacy-safe structural inspection for the live-confirmed PowerOcean
  `241/102` request/reply route. Only decoded bodies up to 64 bytes are accepted.
- Traverse at most three nested protobuf levels and 32 total fields. Small
  varints are visible for controlled comparison; larger numbers and all byte or
  text contents remain omitted.
- Add runtime-keyed fingerprints to individual byte fields so a paired capture
  can locate changed fields without storing identifiers or raw payload bytes.
- Keep the existing 16-byte `96/97` limit and formally treat that tuple as
  independent background traffic rather than the Solar-current command.
- Increase the diagnostic capture schema to 5 without adding any publish path;
  MQTT remains hard `listen_only`.
- Extend the parser/capture suite to 30 passing tests, including the `241/102`
  size bound, nested privacy rules, and cleartext/hex leak checks.
- Confirm in a live `6 A -> 7 A -> 6 A` test that both `241/102` requests
  received same-sequence replies and the provider returned `60 -> 70 -> 60`.
  dev12 classified the 31-byte requests and 23-byte replies as non-protobuf and
  exposed only differing runtime fingerprints; dev13 corrects that result as a
  header-decoding bug rather than a proprietary payload format.

## 0.1.0-dev11

- Add privacy-safe structural inspection for the live-observed PowerOcean
  `96/97` SET candidate. Only the exact tuple and payloads up to 16 decoded
  bytes are considered; opaque bytes and larger numeric values remain omitted.
- Group passive SET requests, retries, and replies by source and sequence in a
  bounded diagnostic view.
- Add a runtime-keyed HMAC fingerprint for small opaque bodies. It supports
  equality comparisons during one HA runtime without exporting the key, raw
  bytes, or an offline brute-forceable hash of the two-byte payload.
- Confirm in a paired live 6 A to 7 A to 6 A test that provider
  `solarCurrentMin` uses tenths of an ampere (`60`, `70`, `60`). Both saves
  correlated with PowerOcean `241/102` SET requests and same-sequence replies;
  their payloads remain omitted and are not treated as write templates.
- Increase the diagnostic capture schema to 4 without adding any publish path;
  MQTT remains hard `listen_only`.
- Extend the parser/capture suite to 28 passing tests, including privacy,
  XOR-decoding, tuple allow-listing, and request/reply correlation checks.

## 0.1.0-dev10

- Add a read-only `Kontinuierlich laden` binary sensor for Solar mode.
- Decode the live-confirmed `switchBits` mask `0x10`: enabled reported `16`
  and disabled reported `0` while the separately stored 6 A minimum remained
  unchanged.
- Keep the setting passive; this release does not add a write command.

## 0.1.0-dev9

- Read the provider detail from the linked PowerOcean instead of relying only
  on the PowerPulse's mostly empty device-detail endpoint.
- Match embedded `pileChargingParamReport` objects back to the exact PowerPulse
  serial before merging their read-only mode, Smart and raw setting values.
- Retain only matched field names in diagnostics; raw provider responses and
  identifiers are not stored.
- Preserve the MQTT-vs-HTTP race protection by combining parent data before the
  coordinator's final merge with the latest live charger state.

## 0.1.0-dev8

- Discover linked PowerOcean systems as passive MQTT sources without creating
  PowerOcean devices or entities in Home Assistant.
- Capture privacy-safe numeric fields from PowerOcean's PowerPulse accessory
  report (`cmd_func 209`). Raw parent payloads, serials, and vehicle identifiers
  are omitted from diagnostics.
- Expose raw diagnostic values for the accessory report's operating mode and
  switch bitmask so Solar/Fast/Custom/Smart and continuous-charging changes can
  be compared against the official EcoFlow app before entity mappings are made.
- Keep all MQTT clients hard listen-only; this release adds subscriptions only
  and does not transmit stream activation, queries, or device commands.

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
