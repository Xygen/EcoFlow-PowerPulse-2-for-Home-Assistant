# PowerPulse 2 protocol observations

These observations come from privacy-redacted cloud MQTT diagnostics captured
from a live C376 charger. They document evidence only; they are not permission
to transmit inferred commands.

## 2026-08-23: Solar-mode start and stop

Conditions:

- The charger was in Solar Mode with no available solar surplus.
- Starting in the EcoFlow app created a paused session with zero charging power.
- Stopping in the EcoFlow app ended that session without delivering energy.

Observed results:

- No frame arrived on the subscribed official-app `set` or `set_reply` topics.
- Start correlated with a CP307 heartbeat `(cmd_func=2, cmd_id=33)` changing to
  `system_state=4` (`paused`).
- Start also correlated with `cmd_func=2, cmd_id=133` (`CHARGED_RECORD`). Its
  start and end timestamps were initially identical and its meter values were
  unchanged.
- Stop correlated with a heartbeat changing to `system_state=6`
  (`charge_complete`) and further `CHARGED_RECORD` reports.
- The completed heartbeat reported `session_duration_s=278`,
  `session_energy_raw=0`, and identical start/end meter energy values.
- The completed charging record's end timestamp was 278 seconds after its
  start timestamp, independently confirming the heartbeat duration.

Conclusion:

- The telemetry state and duration fields are confirmed for a paused,
  zero-energy Solar Mode session.
- `cmd_id=133` is a charging-record report, not evidence of the control write.
- The actual app Start/Stop request remains unobserved. It may use another MQTT
  topic or another transport. Do not implement `CHARGE_CTRL` writes until the
  request envelope and acknowledgement are captured.

## 2026-08-23: Solar continuous-charging option

- Solar Mode exposes an optional "Continuous charging" setting. Its 6-16 A
  value is the current allowed even without solar production; it is not the
  charger's separately configured maximum current.
- Enabling the option at 6 A and saving produced a CP307 `cmd_func=2`,
  `cmd_id=34` parameter report. Disabling and saving produced the same command
  type in the opposite state.
- dev3 incorrectly treated that `2/34` message as a `2/33` heartbeat, briefly
  exposing `15`, `15`, and `unknown` as current/status values. The next real
  heartbeat restored `60`, `160`, and `unplugged`.
- No frame appeared on the eight exact SET/SET-reply topics subscribed by
  dev3. The setting may use another MQTT route or a non-MQTT API.
- dev4 routes envelopes by command type and adds passive discovery filters.
  Subsequent paired captures established the settings mappings recorded in the
  2026-08-24 section below.

## 2026-08-23: Operating modes and Smart targets

The official app was used to save one setting at a time while both the
provider snapshot and privacy-redacted MQTT diagnostics were observed. No car
was connected. The charger was restored to Solar Mode at the end.

Confirmed provider values:

- `workMode=1`: Fast charging
- `workMode=2`: Solar Mode
- `workMode=3`: Custom
- `workMode=4`: Smart Mode
- Smart energy target `30 kWh`: `chargeTarget=30000`
- Smart ready-by `01:38 (+1)`: `timeToUseCar=1787528301`, a Unix timestamp for
  `2026-08-23T23:38:21Z` / `2026-08-24 01:38:21` Europe/Berlin
- Smart distance target `200 km`: `chargeTarget=0`; the kilometre target is
  stored in another provider field that the reference integration does not
  currently expose as an entity
- Returning to Solar Mode reset `timeToUseCar` to `0`

Further current-setting observations:

- Custom Mode was saved at both 6 A and 11 A. The heartbeat-derived
  `charge_current_set_raw` remained `60`, while `current_limit_raw` remained
  `160`. Therefore the former cannot yet be labelled as the Custom slider.
- Solar continuous charging at 6 A and Custom charging at 6/11 A each produced
  a `2/34` parameter report. After XOR decoding, all captured `2/34` parameter
  bodies were byte-for-byte identical, including the reports produced while
  restoring the original settings.
- No official-app SET or SET-reply frame was observed on the exact or wildcard
  subscriptions during any mode, target, or current change. These writes may
  use the provider HTTP API or a route unavailable to the integration's MQTT
  credentials.

Conclusion:

- The provider values above are safe to expose read-only.
- Do not infer mode/current write payloads from the identical `2/34` report.
  Mode switching, Smart targets, continuous charging, and current controls
  remain blocked until a real request and acknowledgement are captured.

## 2026-08-24: Confirmed CP307 settings-report fields

The official app was used to change one charger setting at a time. The
resulting XOR-decoded CP307 `(cmd_func=2, cmd_id=34)` reports were compared in
pairs. Every accepted C376 settings body used schema marker `field 1 = 9`.

Confirmed fields:

| CP307 field | Function | Confirmed values |
| --- | --- | --- |
| 2 | Plug-and-Play enabled | `0` / `1` |
| 9 | maximum output current | tenths of an ampere; `150` = 15 A and `160` = 16 A |
| 11 | phase selection | `1` one phase, `2` three phases, `3` auto |
| 13 | indicator/LED enabled | `0` / `1` |
| 14 | indicator/LED brightness | percentage |
| 15 | screen enabled | `0` / `1` |
| 16 | screen brightness | percentage |
| 22 | battery discharge disabled | `0` / `1` |

The maximum-current mapping is independently corroborated by the provider's
misspelled `paramSet.currentOuputMax` field. Its values matched CP307 field 9
during the paired tests.

These are report mappings only. Mode changes and different current settings
can produce the same `2/34` body, so the message must not be repurposed as a
write-command template.

## 2026-08-24: Linked PowerOcean data paths

The direct C376 response from
`/provider-service/user/device/detail?sn=<C376 SN>` is mostly empty. The same
endpoint queried for the linked PowerOcean returns a richer PowerPulse report
nested below `pileChargingParamReport`.

Attribution requirements:

- Match each nested report to the charger through its embedded
  `devInfo.devSn`.
- Restrict charger aliases such as `workMode` to `pileChargingParamReport`.
  The parent response contains multiple products with similarly named fields.
- Do not retain the raw parent response in diagnostics because it can include
  charger, battery, and vehicle identifiers.

Confirmed or currently retained provider fields:

- `chargingPwr`: charging power in watts
- `chargingStatus`: charger state
- `paramSet.workMode`: `1` Fast, `2` Solar, `3` Custom, `4` Smart
- `paramSet.currentOuputMax`: maximum output current in tenths of an ampere
- `paramSet.smartMode.timeToUseCar`: Unix ready-by timestamp
- `paramSet.smartMode.chargeTarget`: energy target in Wh; `30000` matched
  30 kWh, while distance-target mode reported `0`
- `paramSet.userCurrentSet`, `solarCurrentMin`, `phaseSpecified`, and
  `vehicleInfo.currentVehicleComsumption`: retained raw pending further paired
  tests

The linked PowerOcean MQTT stream also emits a PowerPulse accessory report
under `cmd_func=209` (observed with `cmd_id=8`). In that protobuf body, field 10
tracks the operating-mode value and field 18 tracks the settings bitmask. This
route remains diagnostic-only; the matched provider-detail report contains
more named values and can be attributed to the complete embedded serial.

## 2026-08-24: Solar continuous-charging bit

Paired provider snapshots confirmed that `paramSet.switchBits & 0x10` is the
Solar-mode "Continuous charging" switch:

- enabled: `switchBits=16`
- disabled: `switchBits=0`

The separately stored `solarCurrentMin` remained `60` in both snapshots, so
the enable flag and its 6 A current setting are distinct fields. This mapping
is safe for a read-only boolean sensor; it does not reveal how to write either
setting.

The `0.1.0-dev10` binary sensor was subsequently installed through HACS and
verified in Home Assistant in both directions:

- disabled: entity `off`, `switchBits=0`, `solarCurrentMin=60`
- enabled again: entity `on`, `switchBits=16`, `solarCurrentMin=60`

The charger was left in Solar Mode with Continuous charging enabled at 6 A.

## 2026-08-24: Unassigned parent SET candidate `96/97`

Later diagnostics captured 24 frames from the linked PowerOcean observer on
the official-app property-SET topic. Every captured envelope contained
`cmd_func=96`, `cmd_id=97`, and a two-byte `pdata`; several sequence values were
repeated at short intervals. There was no corresponding SET-reply bucket.

This traffic started after the final Continuous-charging state had already
appeared in the provider snapshot. It therefore cannot be temporally assigned
to that change, and nothing in the retained metadata proves that it targets the
PowerPulse rather than another PowerOcean component. Raw parent payloads remain
omitted because they may bundle device and vehicle identifiers.

Conclusion:

- Treat `96/97` only as a route to investigate in a new, tightly timed paired
  test.
- Passive diagnostics may classify only the exact candidate with strict
  privacy limits and request/reply correlation.
- Do not use these frames as a command template unless the exact setting
  effect and a device acknowledgement are both reproduced.

Implementation note for `0.1.0-dev11`:

- Only `cmd_func=96`, `cmd_id=97` is eligible for parent-command inspection.
- XOR-decoded bodies longer than 16 bytes are omitted.
- Small protobuf varints are retained; opaque fields expose only their length,
  and larger numeric values are not retained.
- Requests, retries, and replies are grouped by source and sequence in a
  bounded diagnostic view.
- Small opaque bodies receive a runtime-keyed HMAC fingerprint. The secret key
  is never exported, making the fingerprint useful only for equality checks
  within one integration runtime rather than for recovering the two bytes.
- Diagnostic capture schema 4 adds no publish path and remains hard
  `listen_only`.

Initial dev11 baseline after restart:

- the XOR-decoded two-byte `96/97` body was not valid protobuf;
- no SET reply was present;
- `96/97` appeared without a user action in recurring pairs, approximately
  every 20 seconds.

This periodic baseline makes unrelated PowerOcean housekeeping traffic more
likely. The live 6 A to 7 A to 6 A comparison is still pending. Until that test
shows a time-aligned fingerprint or field change and acknowledgement, `96/97`
remains unassigned.

## 2026-08-24: Session-energy scaling hypothesis

A non-zero charging session reported CP307 heartbeat field 42 as `1815` while
the EcoFlow app displayed `1.82 kWh`. This strongly suggests that field 42 is
session energy in Wh, but the integration keeps it raw until additional
sessions confirm the unit and app-rounding behaviour.
