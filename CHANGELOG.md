# Changelog

This file records delivered changes and the state of each historical build.
Current outstanding work is maintained only in
[the project backlog](docs/backlog.md).

## Unreleased

- Centralize all active work in `docs/backlog.md`, replace parallel roadmap and
  TODO lists with links, and define where completed changes and protocol
  evidence are recorded.
- Reconcile the documentation with the dev22 implementation: Smart field `31`,
  phase field `7`, and Custom-current field `8` are resolved; older dev-stage
  statements remain explicitly historical evidence.

## 0.1.0-dev24

- Add a disabled-by-default diagnostic button that renews only the existing
  direct C376 MQTT data subscriptions. It never publishes a device command and
  waits up to ten seconds for a new `241/44` report.
- Add a disabled-by-default connectivity binary sensor for direct-stream
  freshness plus a bounded identifier-free trace of reactivation attempts,
  local subscription results, outcome, and confirmation latency.
- Classify official-app GET topics separately from telemetry and retain them in
  a dedicated bounded diagnostic view. JSON operation metadata and generic
  Protobuf routing fields are summarized without raw payloads or request IDs.
- Document the parallel `ecoflow_energy` Enhanced cloud connection to the
  PowerOcean and the local Modbus integration so later app-open tests can
  separate their effects.
- Extend the local test suite to 60 passing tests.
- Installed validation confirms HACS commit `875b532`, manifest version
  `0.1.0-dev24`, and both new diagnostic entities. They were enabled in the
  entity registry; the direct-stream sensor reported connected after a
  targeted integration reload. The reactivation button was deliberately not
  pressed while the direct stream was fresh, and no device setting was changed.

## 0.1.0-dev23

- Extend strict provider confirmation from roughly 9 seconds to bounded checks
  through roughly 20 seconds after an acknowledged SET. The idle test showed
  valid mode/flag snapshots arriving about 12–15 seconds after publication.
- Retain the requirement for a fresh raw provider key/value match; neither the
  SET reply nor merged cached state can confirm a write.
- Add a bounded identifier-free diagnostic trace for every provider attempt,
  including delay, expected-key presence, post-command freshness, and match
  result.
- Split general settings-transport availability from phase availability. Other
  controls keep their provider fallback after idle, while phase selection is
  unavailable without a fresh direct `241/44` phase mapping because provider
  `phaseSpecified` remains raw and cannot confirm `phase_mode` safely.
- Add helper coverage for fresh direct phase availability and provider lag vs
  missing-key diagnostics; extend the local suite to 55 passing tests.
- Installed validation confirms manifest version `0.1.0-dev23`, the new empty
  provider-attempt trace after restart, and fresh direct phase readback of
  `one_phase`. This proves an earlier acknowledged phase SET was applied even
  though dev22 could not confirm it while the direct path slept.

## 0.1.0-dev22

- Fix false write failures after an idle period: after the acknowledged SET,
  first retain direct MQTT readback, then actively request a fresh provider
  snapshot and accept it only when its raw response contains the expected key
  and value.
- Avoid unnecessary SET commands when a provider value no older than two poll
  intervals already confirms the requested state.
- Do not schedule the separate delayed passive-app refresh for an integration-
  owned SET reply; its synchronous provider verification replaces that read.
- Add privacy-safe diagnostics for direct/provider/no-op confirmation counts.
- Initial installed validation confirms two successful direct-readback writes
  and that integration-owned replies no longer schedule a delayed refresh;
  provider-fallback validation remains pending after a new idle period.
- Document the live incident in which two acknowledged `4.1=19` commands were
  reported as failures before the delayed provider refresh confirmed value 19.
- Extend the local suite to 53 passing tests.

## 0.1.0-dev21

- Add disabled-by-default controls for the screen, LED indicator, and their
  four brightness levels (25/50/75/100%).
- Preserve all four display values in the observed nested `241/102 -> 4.21`
  block and continue requiring acknowledgement plus fresh device readback.
- Make each brightness control unavailable while its corresponding display is
  switched off.
- Live-validate both switches and both brightness controls from Home Assistant:
  off/on, 25 -> 50 -> 25%, matching readback, and correct disabled-state
  availability. Restore screen and LED to on at 25%.
- Extend the local suite to 50 passing tests.

## 0.1.0-dev20

- Capture complete forward and reverse app sequences for Fast, Solar, Custom,
  and Smart modes, including Custom 6/7/16 A and Smart 30/40 kWh plus 200/300 km.
- Add disabled-by-default controls for operating mode, Custom current,
  Plug-and-Play, Smart ready-by date/time, Smart target type, energy target,
  and distance target.
- Preserve complete mode-specific payloads and unrelated settings flags, cache
  the last device-reported Smart block, serialize writes, and continue requiring
  same-sequence acknowledgement plus direct `241/44` readback.
- Remove the experimental name suffix from the controls already validated live;
  controls remain disabled by default until charging-state interlocks can be
  tested with a connected vehicle.
- Extend the local suite to 48 passing tests.
- Keep both Smart target-value controls writable while Smart mode is active so
  the inactive target can be initialised atomically with its target type after
  a restart. Enable the separate type-only selector only when both stored target
  values are known, avoiding a guessed fallback.
- Live-validate the installed dev20 controls for all four operating modes,
  Custom current 6/7 A, Plug-and-Play off/on/off, Smart energy 30/40 kWh,
  Smart distance 200/300 km, target-type switching, and ready-by republish.
  Restore the charger to Solar mode, Plug-and-Play off, Custom 6 A, and stored
  Smart distance 200 km after the reversible test sequence.

## 0.1.0-dev19

- Live-validate the dev18 phase control for Auto, one phase, and three phases
  through same-sequence replies, direct readback, and EcoFlow-app display.
- Confirm battery-discharge blocking as bit `0x01` through an official-app
  `16 -> 17 -> 16` comparison.
- Add disabled-by-default experimental controls for battery-discharge blocking,
  Solar Continuous charging, maximum output current, and Solar minimum current.
- Preserve unrelated flag bits, enforce whole-ampere 6-16 A ranges and known
  Solar conditions, serialize writes, and require reply plus direct readback.
- Derive battery-discharge state from the fast direct bitfield and extend the
  local suite to 46 passing tests.

## 0.1.0-dev18

- Complete the fast phase mapping (`0` Auto, `1` one phase, `2` three phase)
  and expose it through the existing enum sensor.
- Confirm Custom current field `8` at 6 A and 11 A and add a normal Ampere
  sensor while retaining the raw diagnostic entity.
- Decode Smart field `31` into ready-by time, target type, energy target,
  distance target, and calculated energy in distance mode. Controlled 200 km
  and 300 km tests produced 30,000 Wh and 45,000 Wh.
- Add the first disabled-by-default experimental control: a phase `select`
  routed through the linked PowerOcean using captured `241/102 -> 4.5`.
  Require a device-derived accessory descriptor, exactly one PowerOcean,
  same-sequence acknowledgement, and matching direct device readback.
- Keep all automatic MQTT traffic listen-only and leave Start/Stop and every
  other setting write unimplemented. Extend the suite to 44 passing tests.

## 0.1.0-dev17

- Confirm through a controlled Plug-and-Play off-on-off test that bit `0x02` in
  the direct `241/44` settings bitmask is Plug-and-Play. The fast bitfield
  changed `16 -> 18 -> 16` while Solar mode, Continuous charging, and the 6 A
  Solar minimum remained unchanged.
- Derive the existing Plug-and-Play binary sensor from that bit and prefer the
  direct device value over cached provider state while `241/44` remains fresh.
- Keep MQTT hard `listen_only` and extend the local suite to 40 passing tests.

## 0.1.0-dev16

- Decode the direct, XOR-encrypted C376 `241/44` parameter report observed
  roughly once per second. Its fixed protobuf path `1.4.8` now supplies the
  live-confirmed settings bitmask, operating mode, maximum output current,
  Solar minimum current, raw phase selection, and Custom current.
- Require the exact `241/44` command, complete six-field shape, bounded payload
  sizes, valid mode, and plausible current/range values before accepting the
  report. Unknown length-delimited fields remain ignored and are documented for
  later controlled investigation rather than exposed by guesswork.
- Prefer only these confirmed direct settings over an HTTP snapshot while the
  device report is no more than ten seconds old. If MQTT becomes stale, the
  existing provider polling and 20-second confirmed-reply refresh resume as the
  authoritative fallback.
- Keep MQTT hard `listen_only`, retain diagnostic schema 7, and extend the
  local suite to 39 passing tests.

## 0.1.0-dev15

- Record from the live dev14 test that the same-sequence `241/102` replies
  arrived after approximately 56 ms and 207 ms, but provider reads around two
  seconds later still returned the preceding Solar minimum current.
- Replace the ineffective two-second read with one coalesced provider refresh
  after 20 seconds. The normal 30-second poll remains available and may update
  the entity earlier depending on its existing schedule.
- Keep the provider snapshot authoritative. The integration does not
  optimistically copy values from the observed app request because the reply
  does not echo the settings object or prove value-level application.
- Retain diagnostic schema 7, the hard MQTT `listen_only` guard, and all 35
  passing tests from dev14.

## 0.1.0-dev14

- Rename the German screen switch from `Anzeigebildschirm` to `Bildschirm` and
  the English equivalent from `Display screen` to `Screen`, grouping each with
  its brightness entity without changing the existing unique ID.
- Display the existing maximum-output-current entity with zero decimal places
  by default.
- Add a normal `Solar minimum charging current` Ampere sensor backed by
  `solarCurrentMin / 10`, while retaining the disabled-by-default raw diagnostic
  entity separately.
- After an official-app `241/102` request and same-source/same-sequence reply
  have both been observed, schedule one delayed provider read. Rapid changes
  are coalesced and a change received during an active HTTP read permits only
  one further delayed read.
- Keep the regular 30-second provider poll as fallback and every MQTT publish
  route blocked by the existing hard `listen_only` guard.
- Increase the diagnostic capture schema to 7 and expose only identifier-free
  refresh counters/timestamps so the live entity-update delay can be measured.
- Extend the local suite to 35 passing tests, including unmatched, duplicate,
  wrong-source and unrelated-command reply cases plus refresh coalescing.

## 0.1.0-dev13

- Correct the EcoFlow envelope mapping: field 6 is `enc_type`; field 11 is
  `need_ack`. dev12 incorrectly XOR-decoded acknowledgement-requesting
  plaintext `241/102` bodies and classified them as opaque.
- Apply the correction consistently to direct CP307 telemetry, PowerOcean
  accessory diagnostics, observer-command inspection, and exported envelope
  metadata.
- Preserve `need_ack` separately in diagnostics and inspect the bounded nested
  `241/102` protobuf structure without retaining raw byte or text contents.
- Confirm the corrected decoder live with a controlled `6 A -> 7 A -> 6 A`
  Solar-minimum-current test. The acknowledged requests exposed
  `4.4=70 -> 60`, while `4.1=16` and `4.2=2` remained stable; independent
  provider readback later reported `70 -> 60`.
- Record that the same-sequence replies arrived after approximately 144 ms and
  226 ms but echoed only the accessory descriptor, not the settings object.
  The provider-backed Home Assistant entity followed approximately 31 s and
  36 s after the corresponding SET requests.
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
