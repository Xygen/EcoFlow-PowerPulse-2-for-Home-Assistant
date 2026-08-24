# PowerPulse 2 protocol observations

These observations come from privacy-redacted cloud MQTT diagnostics captured
from a live C376 charger. They document evidence only; they are not permission
to transmit inferred commands.

## Scope boundary

EcoFlow's first-generation **PowerPulse** wallbox (named without a version
number) and **PowerPulse 2** can theoretically be used without a PowerOcean
inverter. These observations intentionally cover only **PowerPulse 2 paired
with a PowerOcean inverter/system**. They do not establish protocol mappings or
integration support for the first-generation PowerPulse or for a standalone
PowerPulse 2 installation. References to the linked PowerOcean below describe
the selected installation scope, not a universal wallbox requirement.

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
- `paramSet.solarCurrentMin`: Solar minimum/continuous current in tenths of an
  ampere; later paired as `60` = 6 A and `70` = 7 A
- `paramSet.userCurrentSet`, `phaseSpecified`, and
  `vehicleInfo.currentVehicleComsumption`: retained raw pending further paired
  tests

The linked PowerOcean MQTT stream also emits a PowerPulse accessory report
under `cmd_func=209` (observed with `cmd_id=8` during an earlier charging
session). Earlier notes assigned body field 10 to operating mode and field 18
to the settings bitmask by comparing it with provider data. That attribution
was not isolated by a controlled `209/8` comparison and is therefore withdrawn
pending direct evidence. The no-car settings capture below contained no
`209/8` report at all, so it neither confirms nor disproves either field
meaning.

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

- Retain `96/97` only as background diagnostic evidence until a specific
  function is demonstrated; the controlled current test below does not assign
  that function to it.
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

This periodic baseline made unrelated PowerOcean housekeeping traffic more
likely. The controlled comparison below did not associate `96/97` with the
current change; it exposed a different acknowledged tuple instead.

## 2026-08-24: Controlled Solar current 6 A to 7 A to 6 A

Conditions:

- Solar Mode remained selected.
- Continuous charging remained enabled throughout (`switchBits=16`).
- Only its permitted-without-solar current was changed and saved, first from
  6 A to 7 A and then back to 6 A.

Observed provider values:

- initial 6 A: `solarCurrentMin=60`
- saved 7 A: `solarCurrentMin=70`
- restored 6 A: `solarCurrentMin=60`

This confirms tenths-of-an-ampere scaling for `solarCurrentMin` across a paired
change in both directions.

Observed PowerOcean command metadata:

- 6 A to 7 A: `cmd_func=241`, `cmd_id=102`, 31-byte request, same-sequence
  23-byte SET reply after approximately 64 ms
- 7 A to 6 A: the same `241/102` tuple and sizes, with the SET reply after
  approximately 119 ms
- `96/97` continued independently as periodic and retried traffic without a
  matching reply

Conclusion:

- `241/102` is strongly correlated with saving the Solar minimum current in
  this PowerOcean-linked PowerPulse 2 installation.
- The metadata and provider result establish a route candidate, not a command
  payload. The privacy guard still omits both bodies.
- Before any write implementation, a later diagnostic must compare the request
  and reply structures safely, isolate the field that changed between 6 A and
  7 A, confirm target attribution, and interpret the acknowledgement.
- `96/97` is no longer considered the Solar current-setting candidate.

Implementation note for `0.1.0-dev12`:

- Passive body inspection now admits the exact `241/102` tuple with a 64-byte
  decoded-body limit; the observed request and reply sizes are 31 and 23 bytes.
- The diagnostic records only protobuf field numbers, wire types, byte-field
  sizes, small varints up to 255, and runtime-keyed fingerprints. It never
  exports byte/text contents or the random fingerprint key.
- Nested messages are traversed no deeper than three levels and the entire
  structure is capped at 32 fields. Larger numeric values remain omitted.
- `96/97` retains its stricter 16-byte limit. No other tuple is inspected.
- Diagnostic capture schema 5 adds no MQTT publish route and remains hard
  `listen_only`.

Controlled dev12 result (`6 A -> 7 A -> 6 A`):

- 6 A to 7 A used sequence 88. The 31-byte request received a same-sequence
  23-byte reply after approximately 139 ms; the provider then changed
  `solarCurrentMin` from `60` to `70`.
- 7 A to 6 A used sequence 96. The same request/reply sizes were observed and
  the reply followed after approximately 83 ms; the provider later returned
  from `70` to `60`.
- Solar Mode, Continuous charging, and `switchBits=16` remained unchanged.
- Both request bodies and both reply bodies were classified
  `opaque_non_protobuf` by dev12. That classification is now known to be a
  decoder artefact: the observer treated header field 11 (`need_ack`) as
  `enc_type`; the EcoFlow header uses field 6 for `enc_type`. Because the SET
  requests set `need_ack=1`, dev12 XOR-mutated plaintext protobuf bodies.

Corrected conclusion after the upstream diagnostic comparison:

- The acknowledged route and bidirectional provider effect are reproducible.
- The request body is nested protobuf, not proprietary binary. Its settings
  object is top-level field 4. The field assignments from the controlled
  no-car test are recorded below.
- The correction does not make the frame a reusable write template. Target
  attribution, complete value coverage, acknowledgement semantics and safety
  constraints still need review before any control is considered.

Implementation note for `0.1.0-dev13`:

- The local envelope parser and diagnostic capture now read `enc_type` from
  header field 6 and retain field 11 separately as `need_ack`.
- XOR is applied only when field 6 explicitly equals `1`; an
  acknowledgement-requesting plaintext SET is no longer mutated.
- The fix applies to direct CP307 `2/33` and `2/34` parsing, PowerOcean
  accessory inspection, and the allow-listed `241/102` observer.
- Diagnostic capture schema 6 retains only the bounded field tree, small
  varints, byte-field sizes and runtime-keyed fingerprints. Raw PowerOcean
  payloads remain omitted and MQTT remains hard `listen_only`.
- Regression tests cover both directions: `enc_type=1` still XOR-decodes, while
  `need_ack=1` without field 6 leaves a plaintext protobuf unchanged.

A live dev13 `6 A -> 7 A -> 6 A` check should now expose the safe settings path
inside top-level field 4 and confirm whether path `4.4` follows `60 -> 70 -> 60`
in the same acknowledged request/reply sequence.

## 2026-08-24: No-car PowerOcean settings capture for issue #247

The official app changed 13 settings while the upstream integration recorded
the linked PowerOcean. No car was connected. Changes were approximately one
minute apart, shorter than the requested roughly two-minute interval. The
diagnostic was downloaded immediately after the final change.

Capture facts:

- `app_writes_watched=true`
- 13 `241/102` SET frames and 13 `241/102` SET replies were seen
- time-slot sampling retained seven request/reply pairs
- no `209/8` frame was present anywhere in the capture

Recorded test timeline (Europe/Berlin):

| Note time | App change | Retained request evidence |
| --- | --- | --- |
| 15:45 | maximum current 16 A to 11 A | 15:45:38, `4.3=110`, reply after 117 ms |
| 15:47 | maximum current 11 A to 16 A | body not retained |
| 15:49 | Solar to Smart | 15:49:04, `4.1=16`, `4.2=4`, Smart block in `4.7`, reply after 120 ms |
| 15:50 | Smart to Fast | body not retained |
| 15:51 | Fast to Custom | 15:51:09, `4.2=3`, `4.6=60`, reply after 98 ms |
| 15:52 | Custom to Solar | body not retained |
| 15:53 | Plug-and-Play off to on | 15:53:03, `4.1=18`, reply after 217 ms |
| 15:54 | Plug-and-Play on to off | body not retained |
| 15:55 | Continuous charging on to off | 15:55:10, `4.1=0`, `4.2=2`, `4.4=60`, reply after 118 ms |
| 15:56 | Continuous charging off to on | body not retained |
| 15:57 | phase auto to one phase | body not retained |
| 15:58 | phase one to three phase | 15:58:09, `4.5=2`, reply after 57 ms |
| 15:59 | phase three to auto | 15:59:08, `4.5=0`, reply after 203 ms |

Consequently there is no controlled diff for fields 5, 10 or 18 of `209/8`:
the report is absent rather than those fields being unchanged. Field 31 must
not be folded into that schema: the upstream maintainer reports that fields 30
and above are not present in his accessory message and instead belong to a
neighbouring message. This capture provides no isolated before/after evidence
for that neighbouring field 31 either. It does establish that the no-car
settings sequence did not cause an observable `209/8` report in this
installation.

The retained `241/102` requests are plaintext nested protobuf. Top-level field
1 identifies the accessory; top-level field 4 contains the settings object:

| `241/102` path | Observed meaning | Retained evidence |
| --- | --- | --- |
| `4.1` | settings bitmask | `16` with Continuous charging on and Plug-and-Play off; `18` after Plug-and-Play was enabled; `0` after both were disabled |
| `4.2` | work mode | `4` Smart; `3` Custom; `2` Solar |
| `4.3` | maximum output current, 0.1 A | `110` for 11 A |
| `4.4` | Solar continuous/minimum current, 0.1 A | `60` for 6 A |
| `4.5` | phase selection | `2` three phase; `0` auto |
| `4.6` | Custom-mode current, 0.1 A | `60` for 6 A |
| `4.7` | Smart-mode settings | nested values included a ready-by Unix timestamp, selector `1`, target `30000`, and final value `0` |

The sampler did not retain the reverse/current values at 16 A, Fast, the
return to Solar, Plug-and-Play off, Continuous charging on, or one-phase. Their
SET/reply frames are included in the seen counts but their bodies cannot be
reconstructed from this diagnostic. These missing bodies must not be inferred.
`241/102` is reported only as an additional observation on the existing
PowerOcean MQTT connection; it is an app-write path, not a startup/readback
source and not a substitute for the requested `209/8` telemetry evidence.

## 2026-08-24: Session-energy scaling hypothesis

A non-zero charging session reported CP307 heartbeat field 42 as `1815` while
the EcoFlow app displayed `1.82 kWh`. This strongly suggests that field 42 is
session energy in Wh, but the integration keeps it raw until additional
sessions confirm the unit and app-rounding behaviour.
