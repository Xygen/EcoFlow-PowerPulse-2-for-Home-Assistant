# PowerPulse 2 protocol observations

These observations come from privacy-redacted cloud MQTT diagnostics captured
from a live C376 charger. They document evidence only; they are not permission
to transmit inferred commands.

For a compact value-by-path matrix, see
[data_paths_overview.md](data_paths_overview.md).

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
- `paramSet.userCurrentSet`: Custom-mode current in tenths of an ampere; the
  direct field later confirmed `60` = 6 A and `110` = 11 A
- `phaseSpecified`: retained raw on this provider path; direct field `7` and
  settings-report field `11` provide the confirmed phase mappings
- `vehicleInfo.currentVehicleComsumption`: retained raw pending further paired
  tests

The dev14 presentation update later exposed `solarCurrentMin` as a normal
Ampere sensor (`raw / 10`) while retaining its raw diagnostic entity, and set
the maximum-output-current entity to zero decimal places by default.

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

A live dev13 `6 A -> 7 A -> 6 A` check completed the corrected structural
comparison:

- Saving 7 A produced sequence 68 at `16:57:16.655` Europe/Berlin. The
  31-byte `241/102` request decoded without XOR and contained `4.1=16`,
  `4.2=2`, and `4.4=70`. Its 23-byte same-sequence reply arrived approximately
  144 ms later.
- Restoring 6 A produced sequence 80 at `16:59:06.257`. The same request
  structure contained `4.1=16`, `4.2=2`, and `4.4=60`; the 23-byte reply
  arrived approximately 226 ms later.
- In both directions the request and reply carried the same top-level field-1
  accessory descriptor within the running HA instance. The replies contained
  that descriptor but no top-level field-4 settings object. They therefore
  confirm matching transport/target correlation, not explicit value readback.
- The independent provider snapshot changed the HA raw Solar-minimum-current
  entity to `70` at `16:57:48.103` and back to `60` at `16:59:42.151`, about
  31 and 36 seconds after the respective SET requests. Continuous charging
  remained enabled and `switchBits=16` throughout.

This confirms path `4.4` as the Solar continuous/minimum-current value in
tenths of an ampere for the tested 6 A and 7 A values. It also separates the
fast same-sequence acknowledgement from the slower provider-backed readback;
the current integration intentionally continues to expose only the latter as
entity state.

Implementation note for `0.1.0-dev14`:

- A provider refresh is now scheduled two seconds after the passive observer
  has seen both a `241/102` request and a same-source, same-sequence
  `241/102` reply.
- A reply without a retained request, a duplicate reply, the periodic `96/97`
  traffic, and direct PowerPulse frames cannot trigger this path.
- Requests received before the delayed read are coalesced. A new confirmed
  change arriving while the HTTP read itself is active can schedule only one
  additional delayed pass. The normal 30-second poll remains the fallback.
- The trigger performs only the existing provider HTTP read. MQTT remains hard
  `listen_only`; no command body is retained or published.
- Diagnostic schema 7 adds only the configured delay, aggregate counts,
  pending/active flags, and UTC timestamps for the last confirmed reply and
  completed refresh.

Live dev14 latency result:

- Saving 7 A used sequence 213. The reply followed after approximately 56 ms;
  the scheduled provider refresh completed about 2.06 seconds later but still
  returned 6 A. A later read confirmed 7 A.
- Restoring 6 A used sequence 222. The reply followed after approximately
  207 ms; the scheduled provider refresh completed about 2.09 seconds later
  but still returned 7 A. The normal/provider readback exposed 6 A about
  28.8 seconds after the SET.
- A further 7 A change used sequence 237. The reply followed after about
  204 ms, and 7 A was confirmed no later than about 25 seconds after the SET.

The fast reply therefore confirms request/reply correlation but is not followed
by an immediately fresh provider snapshot. dev15 replaces the ineffective
two-second read with one coalesced read after 20 seconds. The integration does
not apply the observed request optimistically: the reply carries only the
accessory descriptor, not the settings object or an explicit value readback.
The normal 30-second provider poll remains as fallback and may win earlier.

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

## 2026-08-24: Direct C376 `241/44` parameter report

The installed dev15 diagnostics revealed a substantially faster readback path
than the provider snapshot. The PowerPulse 2 itself publishes an encrypted
`cmd_func=241`, `cmd_id=44` property report on
`/app/device/property/<device>` roughly once per second. The observed frame had
`cmd_src=2`, `cmd_dst=32`, `enc_type=1`, a 100-byte encrypted `pdata`, and a
sequence whose low byte correctly XOR-decodes that body.

After decoding, the bounded protobuf path to the parameter object is `1.4.8`.
The six scalar values in one live frame matched the simultaneously visible HA
and provider state without using the official-app SET request as state:

| `241/44` parameter field | Live value | Matched read-only meaning |
| --- | ---: | --- |
| `1` | `16` | settings bitmask; Continuous charging on and Plug-and-Play off |
| `2` | `2` | Solar operating mode |
| `4` | `160` | maximum output current, 0.1 A |
| `6` | `70` | Solar minimum/continuous current, 0.1 A |
| `7` | `0` | raw phase selection |
| `8` | `60` | raw Custom/user current, 0.1 A |

This is device-originated readback, unlike the `241/102` app request, and can
therefore update those settings without waiting approximately 25-29 seconds
for the cached provider view. dev16 accepts only this exact command and nested
shape, requires all six fields with bounded plausible values, and ignores all
siblings. A recent report takes precedence over provider values for ten
seconds; after that, HTTP automatically becomes the fallback again. MQTT stays
hard `listen_only` and no get-all or other request is transmitted.

The installed dev16 build was then validated live by restoring the Solar
minimum current from 7 A to 6 A while Continuous charging remained enabled:

- the official-app `241/102` SET carrying `4.4=60` was observed at
  `18:22:22.169` Europe/Berlin;
- its same-sequence reply arrived approximately 152 ms later;
- the HA raw and converted entities changed to `60` and `6.0 A` at
  `18:22:23.935`, approximately 1.77 seconds after the SET request and 1.61
  seconds after its reply;
- the coalesced provider fallback completed only about 20.26 seconds after the
  SET, so it was not responsible for the entity update.

This confirms that device-originated `241/44` readback, rather than an
optimistic application of the observed request, now provides the fast HA state
for this setting. The measured delay is consistent with the report's roughly
one-second cadence plus coordinator processing.

A subsequent controlled Plug-and-Play off-on-off comparison isolated another
bit in the same direct field while Solar mode, Continuous charging, and the
6 A Solar minimum remained unchanged:

- enabling Plug-and-Play sent `241/102` path `4.1=18`; the same-sequence reply
  arrived after approximately 306 ms, and direct `241/44` field `1` changed
  from `16` to `18` approximately 1.47 seconds after the SET;
- disabling Plug-and-Play sent `4.1=16`; its reply arrived after approximately
  101 ms, and direct field `1` returned from `18` to `16` approximately 1.69
  seconds after the SET;
- the existing Plug-and-Play entity changed in both directions, while
  Continuous charging remained on, the mode remained Solar, and the Solar
  minimum remained 6 A.

The bidirectional controlled difference confirms `switchBits & 0x02` as
Plug-and-Play. dev17 derives the existing binary sensor from this bit and adds
it to the recent-direct-value preference set. This is readback only and adds
no MQTT publish path.

The installed dev17 build was verified after a Home Assistant restart. Regular
100-byte `241/44` reports included `plug_and_play` among their parsed keys, and
HA showed Plug-and-Play off with `switchBits=16`, Continuous charging on, Solar
mode, and a 6 A Solar minimum. MQTT diagnostics still reported `listen_only`.
An occasional 105-byte `241/44` variant in the same observation did not match
the required nested six-scalar shape and was therefore rejected with no parsed
keys. Normal 100-byte reports continued roughly once per second, so this did
not make the entities unavailable. The rejected variant remains unassigned
rather than being widened into the parser without controlled evidence.

At the dev17 stage, the same parameter object also contained unresolved
length-delimited fields `5`, `9`, `21`, and `31`, sized 16, 14, 6, and 10 bytes
in the inspected snapshot. The later controlled comparisons below resolve
field `31` as the Smart block. Fields `5` and `9` remain unnamed. Field `21`
remains a strong fast display-settings candidate, but it must be paired against
controlled screen/LED changes before being decoded as readback.

## 2026-08-24: dev18 bundled mappings and experimental phase control

Controlled direct `241/44 -> 1.4.8` comparisons completed the phase mapping:
field `7` is `0` Auto, `1` one phase, and `2` three phase. Custom-mode field
`8` changed from `60` at 6 A to `110` at 11 A and back to `60`, confirming a
0.1 A scale. Both fields updated in roughly 0.7-1.8 seconds, substantially
faster than the provider fallback.

Smart settings are nested in field `31`: subfield `1` is the ready-by Unix
timestamp, subfield `2` selects `1` energy or `2` distance, subfield `3` is the
energy value in Wh, and subfield `4` is the distance in km. Energy mode changed
30,000 to 40,000 Wh while the related distance changed 200 to 266. Distance
mode at 200 and 300 km produced calculated values of 30,000 and 45,000 Wh,
respectively, consistent with 150 Wh/km. The EcoFlow app rejected a target
when the chosen ready-by time was too soon, and its edit dialog incorrectly
initialised the time to approximately now plus 24 hours even though the
overview and device readback retained 08:00 (+1).

dev18 introduces one disabled-by-default experimental `select` for phase
choice. It uses only the captured `241/102 -> 4.5` route. The command is sent
through the single linked PowerOcean client, reuses the opaque 21-byte
accessory descriptor learned from the direct device report, and requires both
a same-sequence `set_reply` and matching direct `241/44` phase readback. This
was the first HA-originated write implementation and was pending live hardware
validation at the dev18 candidate stage. The following section records its
successful live validation; later sections add the other captured settings
controls. Start/Stop remains unimplemented.

## 2026-08-24: live HA phase writes and battery flag

The installed dev18 phase `select` was tested from Auto to one phase, then
three phase, and finally back to Auto. The three HA-originated commands carried
`4.5=1`, `4.5=2`, and `4.5=0`. Their same-sequence replies arrived after about
127 ms, 144 ms, and 141 ms. Direct readback followed within roughly 0.5-1.3
seconds, and the EcoFlow app displayed every resulting value. This completes
live validation of the first integration write control.

A subsequent official-app battery test identified another settings flag.
Enabling "Disable battery discharge" changed `4.1` and direct field `1` from
`16` to `17`; disabling it returned `17` to `16`. The replies arrived after
about 128 ms and 67 ms, while Continuous charging remained enabled and
Plug-and-Play remained disabled. This bidirectionally identifies bit `0x01` as
battery-discharge blocking. dev19 exposes this and the already confirmed
Continuous, maximum-current, and Solar-minimum-current paths as additional
disabled-by-default controls with acknowledgement and direct-readback gates.

Immediately after a restart, no `2/34` settings report had arrived while the
direct `241/44` report was already flowing roughly once per second. Its opaque
field `21` contained bytes `01 01 19 19 02 00`; the first four values align
with the simultaneously known screen on, LED on, screen brightness 25%, and
LED brightness 25%, while the final zero aligns with battery blocking off.
This is recorded only as a candidate for later controlled comparisons; dev19
does not parse field `21` or use this unconfirmed assignment for readback.

## 2026-08-24: observed charging-state write constraints

The captures contain no Start/Stop request either without a vehicle or with one
connected. A SET reply alone would confirm transport correlation rather than
the physical result, so independent charging-state readback is required.

The official app prevents at least operating-mode and phase-selection changes
while charging is active. The evidence does not identify the complete locked
set. Current follow-up and completion criteria are maintained only in the
[project backlog](backlog.md).

## 2026-08-24: complete operating-mode capture for dev20

Two no-vehicle app sequences captured both directions across every mode. The
first sequence was Solar -> Fast -> Custom 7 A -> Custom 16 A -> Smart 30 kWh
-> Smart distance -> Solar. The reverse sequence was Solar -> Smart 40 kWh at
08:00 (+1) -> Smart 200 km -> Custom 6 A -> Fast -> Solar.

The retained requests confirmed `4.2=1` Fast with no companion field,
`4.2=3` Custom with `4.6=60/70/160`, and `4.2=2` Solar with `4.1=0` plus
`4.4=60`. Smart used `4.1=0`, `4.2=4`, and nested `4.7`: field 1 was the full
ready-by Unix timestamp, field 2 selected energy `1` or distance `2`, field 3
held 30,000/40,000 Wh or calculated distance energy, and field 4 held `0` for
energy or 200/300 km for distance. Replies arrived in approximately 60-141 ms,
and fast direct readback confirmed every resulting mode and value.

dev20 implements these as disabled-by-default, user-triggered controls. Smart
mode is never built from guessed defaults: the coordinator remembers the last
device-reported ready-by and target block and refuses the write if required
values are absent. All writes keep the existing reply and direct-readback gate.

The first installed dev20 test exposed a safe bootstrap edge case. After a
restart in Solar mode with a stored distance target, the provider supplied the
ready-by timestamp and a zero energy target but not the target type or distance.
The integration correctly refused to invent the missing Smart block. Once the
app entered Smart mode, direct readback supplied distance 200 km and calculated
energy, but no historical non-zero energy target. Both target-value controls
therefore remain writable in Smart mode and atomically select their own type;
the type-only selector is available only after both reusable target values have
been observed.

After installing the bootstrap fix, the complete HA-originated Smart sequence
also succeeded. Setting 40 kWh from the initial distance state atomically
selected energy and supplied the missing non-zero target. Subsequent
40 -> 30 -> 40 kWh, energy -> distance, and 200 -> 300 -> 200 km changes all
received replies and matching direct readback. Republishing the unchanged
ready-by timestamp exercised the nested time write without altering the user's
schedule; the coordinator accepted it only after a fresh direct report. The
final HA mode write restored Solar. Together with the earlier installed tests,
dev20 is now live-confirmed for Fast, Solar, Custom, Smart, Custom 6/7 A,
Plug-and-Play, all Smart target controls, and ready-by transport in the
no-vehicle state.

## 2026-08-24: display-control capture requires bounded byte diagnostics

A bundled app sequence confirmed screen and LED enable plus 25/50/75/100%
brightness readback, including an additional accidental LED off/on pair before
the final return to 25%. Eight retained `241/102` requests all received matching
replies after approximately 72-202 ms. Unlike charging settings, their top-level
field `4` contained a nine-byte non-numeric nested block; the privacy-safe
inspector retained only size and runtime fingerprint, so the payload cannot yet
be rebuilt safely.

The follow-up diagnostic exposes only top-level command field `4` when it is at
most 16 bytes, as a numeric byte list. Descriptor field `1` and every other
opaque byte field remain hidden. A repeated app sequence can therefore isolate
the four display bytes without weakening identifier redaction.
The per-command bucket is expanded from eight to sixteen bounded samples so the
complete screen-plus-LED sequence fits in one capture.

The repeated capture exposed the complete nested block as
`4.21 = [LED enabled, screen enabled, LED brightness, screen brightness, 0, 0]`.
LED off/on changed byte 1 between 0/1; LED levels changed byte 3 through
25/50/75/100; and screen levels changed byte 4 through 25/50/75/100. Earlier
screen off/on readback plus the stable companion values identify byte 2 as the
screen-enable flag. All retained requests received same-sequence replies in
54-158 ms and matching device readback. dev21 therefore exposes four
disabled-by-default controls, preserving the complete six-byte block on every
write. Each brightness control is unavailable while its corresponding display
is off.

The installed dev21 controls were subsequently exercised directly from Home
Assistant. Screen off/on, screen 25 -> 50 -> 25%, LED off/on, and LED
25 -> 50 -> 25% each completed only after acknowledgement and matching
readback. When either display was off, its corresponding Number entity became
unavailable and returned when switched on. Final state was restored to screen
on at 25% and LED on at 25%.

## 2026-08-25: idle-period readback false negative and dev22

After several idle hours, two HA writes sent `241/102 -> 4.1=19` at
04:26:49 and 04:27:06 UTC. Both received same-sequence replies in 89-93 ms,
while MQTT remained connected without a reconnect. dev21 nevertheless raised
its readback error because no fresh direct `241/44` report arrived inside five
seconds. The coalesced provider refresh completed at 04:27:09 and independently
confirmed settings bitmask 19, proving the writes had succeeded.

dev22 keeps direct device readback as the preferred confirmation, waits briefly
for it, and then actively requests provider snapshots. A provider confirmation
is accepted only when a snapshot completed after the SET and its raw response
actually contains the expected key and value; a value preserved only by the
merge cache cannot confirm a write. Up to three bounded provider attempts cover
cloud propagation delay. A recent raw provider match also makes an already-met
request a no-op. Integration-owned replies no longer cause a redundant delayed
passive refresh, and diagnostics count direct, provider, and no-op outcomes.

The first installed dev22 check issued the already-requested battery-blocking
state twice. Both commands received matching replies and fresh direct readback
in about 0.4-0.6 seconds, with `control_readback_counts.direct=2`. No delayed
passive refresh was left active or pending, confirming that integration-owned
replies do not duplicate the new synchronous verification. The direct device
was awake during this test, so it did not exercise the provider fallback. That
remaining validation is tracked in the [project backlog](backlog.md).

## 2026-08-26: genuine idle test and dev23 readback boundary

After several idle hours, the PowerPulse MQTT connection and PowerOcean command
path were still live, but the direct `241/44` settings bucket was absent. Every
retained `241/102` request in the inspected sequence had a matching reply. The
integration nevertheless logged fifteen readback failures between 00:05 and
00:19 local time.

The timing isolates provider propagation rather than command transport as the
cause for mode and flag controls. Representative requests were acknowledged in
about 60–236 ms; dev22 returned its readback error approximately 9.1 seconds
after publication, while HA received the requested mode or bitmask after about
12.2–14.9 seconds. Four earlier writes in the same runtime had already completed
through provider confirmation. dev23 therefore preserves the raw, post-command
key/value test but adds bounded provider checks at approximately 2, 5, 10, 15,
and 20 seconds after publication. A 32-entry identifier-free trace records each
attempt without serials or expected values.

Phase cannot safely use that fallback yet. The requests at 00:19:10 and
00:19:45 received matching replies after about 142 ms and 62 ms, but no direct
phase report or normal phase-state transition followed. The provider parser
retains `phaseSpecified` only as `phase_specified_raw`; its value mapping is not
confirmed and it cannot satisfy an expected `phase_mode`. dev23 therefore makes
phase control available only while a recent direct `241/44` report supplies one
of the confirmed `auto`/`one_phase`/`three_phase` values. All other settings
controls continue to use the general acknowledged transport plus direct-or-raw-
provider confirmation.

Post-install verification loaded manifest version `0.1.0-dev23` and exposed the
new, initially empty `recent_provider_attempts` diagnostic list. Restart also
awakened direct reporting: the phase Select and normal sensor both became
`one_phase`, while the raw direct field was `1`. This independently confirms
that an earlier acknowledged phase command had reached the charger even though
no acceptable readback arrived before dev22 returned its error. The verification
itself performed no write and therefore does not resolve provider
`phaseSpecified` semantics.

## 2026-08-26: dev24 subscription-renewal and app-GET instrumentation

The idle symptom is narrower than an MQTT disconnect. During the inspected
runtime both C376 and HJ31 clients remained connected with zero reconnect
attempts, while earlier evidence showed that direct C376 `241/44` reporting can
still disappear. A separate installed `ecoflow_energy` 1.18.0 integration was
live in Enhanced WSS mode for the HJ31, and a local Modbus integration addressed
the inverter at TCP port 502. Repeated HJ31 `96/97` EnergyStreamSwitch requests
are therefore external to this integration's listen-only MQTT clients; MQTT
does not expose which other account client published them.

Because restarting HA reconnects several cloud clients simultaneously, restart
recovery cannot isolate the wake trigger. dev24 provides a no-publish test path:
it sends fresh MQTT SUBSCRIBE packets only for the existing direct C376 quota,
property, and GET-reply topics. If the stream was stale, the coordinator waits
ten seconds for a later `241/44` frame and records `confirmed`,
`no_direct_report`, or `subscription_failed` with safe local result codes and
confirmation latency. A fresh stream produces `already_active` and no renewal,
preventing an inconclusive action during normal reporting.

App GET publishes are now classified separately as `observed_get`, excluded
from telemetry parsing, and retained in `mqtt_request_frames`. JSON requests
expose only an allow-listed source, operation type, module type, version, and
parameter key names; generic Protobuf GETs expose only source/destination,
sequence, and the literal `app` marker. Raw request content and request IDs are
always omitted. This instrumentation does not yet establish a wake command; the
controlled stale-stream result remains an open evidence item in the canonical
backlog.

Post-install verification of HACS commit `875b532` found both diagnostic
entities in the registry. After enabling them and reloading only the config
entry, the connectivity sensor was `on`; the button was available but remained
unpressed because the stream was already fresh. Therefore this check validates
the installation and freshness exposure, not the stale-stream SUBSCRIBE
experiment. No new PowerPulse integration error appeared after the reload and
no device command was published.

The subsequent stale-stream test produced the first causal exclusion. The last
`241/44` report had arrived at `04:04:03Z`. At `05:56:50Z`, the diagnostic
button renewed the C376 quota, property, and GET-reply subscriptions; every
local Paho result was `0`. No later direct report arrived during the ten-second
confirmation window, so the attempt ended as `no_direct_report`. Concurrent
C376 `96/54` and `96/34` property frames showed that the connection and broader
charger message path were still active.

The official app was then opened directly to the PowerPulse overview without a
setting change. Direct `241/44` reporting resumed at approximately
`05:58:38Z` and continued about once per second. No C376 GET entered
`mqtt_request_frames`, and no C376 SET appeared in the observed command list.
The visible HJ31 `96/97` requests cannot be used as the trigger because they
were already repetitive and their publisher is not encoded in the shared
topic. The supported conclusion is therefore narrow: app opening wakes the
direct stream, whereas re-subscribing from HA does not. The actual trigger may
be an app-client connection or subscription, a topic outside the current
capture, or an HTTP/backend request and remains unresolved.

The next idle cycle showed that the device detail page is not required. Opening
only the general EcoFlow home/device list restarted C376 `241/44` at about
`08:52:06Z`, again without a captured C376 GET or SET. HJ31 `96/114`, `96/22`,
and `96/97` requests began in the retained command window at `08:52:11Z`, after
the direct stream had already resumed, and therefore do not establish the
trigger. Phase voltage from heartbeat `2/33` changed at `08:52:53Z`, roughly 47
seconds later. In the preceding app-open test that heartbeat followed the
direct stream after roughly 54 seconds. App opening therefore revives both
C376 report families with different startup cadence; the earlier conclusion
that heartbeat remained asleep was a snapshot taken just before it resumed.

This makes a no-publish C376 WSS client rebuild with a new Client ID the next
controlled step. It differs materially from the failed re-subscription test by
creating a fresh cloud session while still avoiding any guessed device command.

## 2026-08-26: dev25 isolated C376 session-rebuild instrumentation

dev25 implements that controlled step without making it automatic. A second
disabled diagnostic button calls the existing full WSS rebuild for only the
C376 client. WSS client creation generates a fresh Client ID and the normal
connect callback restores passive subscriptions. The client's `listen_only`
guard prevents every automatic request, including `get-all`, `latestQuotas`,
and `EnergyStreamSwitch`; no charger-setting payload is involved. The bounded
attempt trace now labels `resubscribe` and `wss_reconnect` separately and keeps
only an ISO timestamp, four-character device prefix, prior freshness, outcome,
and optional confirmation latency.

A second disabled connectivity sensor records receipt time of parsed C376
heartbeat `2/33` frames independently of field-value changes. Its 90-second
window covers the observed roughly one-minute cadence and avoids treating an
unchanged phase voltage as proof that no frames arrived. Diagnostic schema 9
adds the same identifier-free heartbeat timestamp summary. Whether a fresh WSS
session actually restarts `241/44` or the later heartbeat remains open until a
genuine stale-stream live test.

Installed validation loaded manifest `0.1.0-dev25`. After enabling the two new
registry-disabled entities and reloading only this config entry, direct
`241/44` was immediately fresh and the first parsed heartbeat `2/33` arrived
within the following normal cycle, switching its independent sensor to fresh.
The reconnect button was available but was deliberately not pressed because
the direct stream was active; `last_reactivation` remained empty. No new
PowerPulse runtime error was logged.

The subsequent genuine stale test confirmed the session hypothesis. Both
diagnostic sensors were `off`; the last direct `241/44` frame had arrived at
`11:31:17.706252Z` and the last heartbeat `2/33` at `11:31:11.052485Z`. At
`12:05:08.416675Z`, the user pressed only the dev25 WSS-reconnect button while
the EcoFlow app remained closed and no setting was changed. The privacy-safe
trace recorded `method=wss_reconnect`, `direct_was_fresh=false`,
`status=confirmed`, and `seconds_to_direct_report=1.779`. Heartbeat `2/33`
followed at `12:05:13.424549Z`; both sensors were then fresh and `241/44`
continued reporting.

This establishes that a fresh C376 WSS client session and normal passive
subscriptions are sufficient to restart both server-delivered report families.
No MQTT publish, guessed device command, app detail page, or PowerOcean command
is required. The next implementation step is conservative automatic recovery
with a sustained-stale threshold, cooldown, and loop protection; a second idle
cycle should validate that policy before treating it as production behavior.

## 2026-08-26: dev26 bounded automatic stream recovery

dev26 implements the confirmed session rebuild as a deliberately conservative
watchdog. Eligibility requires that both `241/44` and `2/33` were observed in
the current coordinator runtime; missing initial timestamps never cause a
reconnect. Both last-receipt times must then be at least 300 seconds old. This
avoids treating the normal ten-second direct freshness display or a single late
heartbeat as a recovery trigger.

When eligible, the coordinator records the attempt time before any network
operation, fully rebuilds only the C376 WSS client, and waits for direct
confirmation through the already tested path. Every automatic attempt starts a
1,800-second cooldown even if reconnect or confirmation fails, preventing a
30-second coordinator-poll loop. The trace method is
`automatic_wss_reconnect`; diagnostic schema 10 exposes the fixed thresholds.
The MQTT client's existing hard `listen_only` guard and its fresh-client-ID
publish-regression test remain unchanged. A genuine idle window is still needed
to validate automatic scheduling and cooldown behavior in Home Assistant.

Installed validation loaded manifest `0.1.0-dev26` and diagnostic schema 10.
Runtime diagnostics reported automatic recovery enabled with
`stale_seconds=300`, `cooldown_seconds=1800`, and an empty attempt list. Both
independent stream sensors were fresh after startup, so no reconnect was due or
performed. The current error log contained only Home Assistant's standard
untested-custom-integration warning and no new PowerPulse runtime error.

## 2026-08-27: app navigation while display settings were unavailable

The user opened the EcoFlow app at 18:03 local time, the PowerPulse page at
18:04, general settings at 18:05, and the display/indicator settings page only
at approximately 18:06, without changing or saving anything. The retained
observer capture showed a short burst of new request/reply activity beginning
at `16:03:35Z`, which can be attributed to the app/PowerPulse navigation but not
specifically to the display page. It included matched `211/100`, `96/127`, and
`96/145` pairs plus request-only `96/37` and `96/22` traffic. No distinct
display-page request has been isolated yet.

The HA display/indicator entities remained unavailable after the navigation.
Therefore the app traffic was not automatically merged into the coordinator's
PowerPulse state. A dedicated refresh action must not be implemented until one
of these requests is correlated with a complete display-settings report and its
read-only behavior is confirmed.

The controlled LED-only change supplied that missing correlation. The app sent
four matched `241/102` request/reply pairs between `16:13:25Z` and `16:14:06Z`
(18:13:25–18:14:06 local); no other PowerPulse setting was changed. The existing
confirmed-settings gate then completed two delayed provider refreshes, with the
last one at `16:14:26Z`. HA subsequently received `LED-Helligkeit=75%`,
`Bildschirmhelligkeit=25%`, `LED-Anzeige=on`, and `Bildschirm=off`.

This proves that the display block becomes available after a confirmed app
settings write followed by the existing delayed provider refresh. It does not
yet prove that a standalone read-only request can cause the same backend
response; the `241/102` payload is a write and must not be reused as a refresh
button command.

As a read-only negative control, the integration was reloaded with the app
closed after the values had been populated. After approximately 90 seconds,
all display/indicator entities were again `unavailable`, while direct `241/44`
and heartbeat `2/33` streams remained fresh. The passive-refresh diagnostics
showed no confirmed settings reply and no completed refresh. Ordinary provider
polling therefore does not restore the display block by itself; the next safe
candidate must be a separately identified read request or a session/app
trigger, not a generic coordinator refresh.

The follow-up app-open test was then performed without changing any setting and
without saving (the app sends changes immediately). After the display settings
page was opened and the test window elapsed, all six display/indicator entities
remained `unavailable`; the direct and heartbeat streams stayed fresh, and
passive-refresh diagnostics still showed zero confirmed replies and zero
completed refreshes. Menu navigation alone therefore does not restore the
values. Current evidence narrows the trigger to a confirmed settings write (or
an as-yet-unidentified app request coupled to that write), not page opening.

Inspection of a current, independently received C376 `241/44` frame revealed a
better read-only path. Its previously unassigned `paramSet` field `21` contained
the six bytes `[1, 0, 75, 25, 2, 0]`. The first four values exactly matched the
independently observed state after the LED test: LED enabled, screen disabled,
LED brightness 75%, and stored screen brightness 25%. This is the same byte
layout already confirmed for app writes at `241/102 -> 4.21`, but it arrives in
the normal high-frequency device report and requires no publish or refresh.

The integration currently ignores this direct field, which explains why the
entities become unavailable after a reload even though `241/44` remains fresh.
One additional controlled display transition should confirm the live byte
change; the next build can then decode the bounded six-byte block directly and
likely eliminate the need for a display-refresh button.

## 2026-08-27: dev27 direct display/LED readback

The controlled transition from LED brightness 75% to 100% confirmed the fast
mapping. With the integration left running, consecutive C376 `241/44` reports
changed field `1.4.8.21` from `[1, 0, 75, 25, 2, 0]` to
`[1, 0, 100, 25, 2, 0]`; the other bytes remained stable. This independently
confirms byte 1 as LED enable, byte 2 as screen enable, byte 3 as LED brightness,
and byte 4 as stored screen brightness.

dev27 decodes only an unambiguous six-byte field with boolean first bytes and
brightness values restricted to the four observed levels. The last two bytes
remain unassigned and are ignored. The four decoded keys join the freshness-
gated direct settings set so a slower provider snapshot cannot replace them
while `241/44` is fresh. This adds no request, publish, or reconnect path.

Installed validation after a full Home Assistant restart, with the EcoFlow app
closed and without a device write, restored the direct and heartbeat streams
and reported LED enabled at 100%, screen disabled, and stored screen brightness
25%. Both read-only brightness sensors were available. The writable screen-
brightness number correctly remained unavailable because the screen was off;
the LED-brightness number was available at 100%. This completes the dev27
readback validation and confirms that a separate display-refresh button is not
needed for this data source.

## 2026-08-27: first connected-vehicle session and dev28 safety work

The first available vehicle session started automatically in Solar mode with
Continuous charging enabled at 6 A. Heartbeat readback first changed from
`unplugged` to `charging`, followed by approximately 1.29 kW, 5.75 A at 231.6 V,
59 seconds duration, and raw session energy `19`. The later completed first
segment reported 21 min 08 s and raw energy `451`. Integrating the observed
approximately 1.28-1.29 kW over that duration closely matches 451 Wh, adding
independent evidence that heartbeat field `42` is measured in Wh.

At `17:24:34.365Z` the official app Stop action sent a PowerOcean-observed
`241/100` SET to the linked `HJ31` inverter. Sequence 118 received a matching
reply after about 0.199 seconds. At `17:24:36.135Z` heartbeat readback changed
to `charge_complete`, charging became false, and final session values were
reported. At `17:26:02.630Z` app Start sent the same `241/100` tuple with
sequence 128; its reply arrived after about 0.093 seconds. Heartbeat changed to
`charging` at `17:26:06.587Z`, and by `17:27:05.837Z` reported 1.288 kW,
5.75 A, one minute, and raw energy `20`. The new session counters reset rather
than continuing the stopped segment.

Both actions used a 25-byte command body, but diagnostic schema 10 did not
allow-list `241/100`, so the differing selector was not retained. dev28 adds
only this confirmed tuple to the bounded observer inspector. It retains small
numeric protobuf fields, runtime-keyed fingerprints, sizes, and routing data;
the accessory descriptor and all opaque raw content remain omitted.

The schema-11 repeat at `17:45:40.256Z` (Stop, sequence 237) and
`17:46:26.748Z` (Start, sequence 243) isolated protobuf field 2 as the action
selector: value `1` is Stop and value `2` is Start. Field 1 remained the same
21-byte accessory descriptor in both frames. The Stop reply arrived after
about 0.156 seconds and heartbeat changed to `charge_complete`; final counters
were 19 min 36 s and raw energy `419`. The Start reply arrived after about
0.089 seconds, heartbeat changed to `charging` roughly 4.3 seconds later, and
the new session reset to zero before returning to approximately 1.29 kW. This
completes the wire-level selector discovery; HA controls still require guarded
implementation and live validation.

The active-session app UI locked operating mode, phase selection, maximum
output current, Solar minimum current, and Continuous charging. Plug-and-Play,
battery-discharge blocking, screen, LED, and brightness remained usable.
Controlled writes confirmed Plug-and-Play as shared flags `18 -> 16 -> 18` and,
with Plug-and-Play retained, battery blocking as `18 -> 19 -> 18`; charging
continued throughout. dev28 applies the five confirmed locks both to entity
availability and immediately before publishing, failing closed when charging
state is missing or unknown. It does not generalize the rule to untested
mode-specific controls.

## 2026-08-27: dev29 guarded Start/Stop implementation

dev29 implements two disabled-by-default buttons from the repeated schema-11
evidence. Both reuse the validated 21-byte accessory descriptor but construct a
separate `241/100` body: protobuf field 1 contains the descriptor and field 2
contains `1` for Stop or `2` for Start. Reply waiters now include device,
command function, command ID, and sequence, preventing a `241/102` settings
reply or another command with the same short sequence from confirming the
action.

The transport acknowledgement is only the first gate. Before publishing, the
coordinator requires a heartbeat no older than 90 seconds and a state in which
the requested action is valid. Start fails closed for `unplugged`, unknown, or
already charging states; Stop is limited to `charging` or `paused`. After the
matching reply, the coordinator waits up to 15 seconds for a newer heartbeat.
Start is confirmed only by `charging` or `paused`, covering Solar mode without
surplus; Stop is confirmed only by `plugged_in`, `charge_complete`, or
`standby`.

The reversible HA-button test completed at `23:03Z` on 2026-08-27. Pressing
Stop at `23:03:55.446Z` returned successfully after the matching reply and a
new heartbeat changed to `charge_complete` at `23:03:56.975Z`. The completed
session showed 2 h 50 min and raw energy `3685`. The Start button became
available while Stop became unavailable. Pressing Start at `23:04:13.425Z`
returned successfully after a new heartbeat changed to `charging` at
`23:04:17.769Z`; the session counters reset to zero and button availability
reversed. At `23:05:16.698Z`, physical telemetry reported 1.304 kW, 5.77 A,
233.3 V, one minute, and raw session energy `20`. This completes `CTRL-01`.

## 2026-08-28: dev30 energy and duration entities

History from the connected-vehicle test closes the remaining scale question
for heartbeat field 9. Across 357 numeric samples from 19:00 to 01:09 local
time, `total_energy_raw` increased from `1364918` to `1372690` without a
single decrease, including across multiple Stop/Start transitions and session
counter resets. While charging at approximately 1.29 kW, it increased by
21–22 raw units per minute, matching Wh. It is therefore a cumulative Wh
counter and dev30 exposes it as an enabled-by-default kWh energy sensor with
`state_class=total_increasing`. The raw diagnostic entity remains unchanged.

Field 42 is now also exposed as an enabled-by-default per-session kWh energy
sensor. Its Wh interpretation is supported by the app comparison `1815` raw
versus `1.82 kWh`, by `451` after 21 min 08 s at approximately 1.29 kW, by
`3685` after 2 h 50 min, and by `20` after one minute in a newly reset session.
Its `total_increasing` state class intentionally accommodates the observed
reset at the beginning of each new charging session. The raw entity remains a
disabled diagnostic.

The existing `session_duration_s` entity keeps its key and unique ID but no
longer converts the numeric heartbeat value to text. It now exposes seconds
with `device_class=duration` and `state_class=measurement`, and is enabled by
default. This lets Home Assistant perform display-unit conversion and supports
numeric dashboards, history, and automations.

Installed validation loaded HACS commit `d8f07d5` without an integration log
error. The cumulative pair reported `1372926` raw and `1372.926 kWh`; the
session pair reported `343` raw and `0.343 kWh`. Both normal sensors exposed
`device_class=energy`, `state_class=total_increasing`, and `kWh`. The preserved
duration entity exposed `device_class=duration` and
`state_class=measurement`; Home Assistant converted the native 960 seconds to
the configured display/state unit as approximately `0.2667 h`.

## 2026-08-28: 0.1.0 release branding and versioning

The live-validated dev30 code becomes the first regular release as `0.1.0`.
Subsequent releases follow Semantic Versioning; intentional preview builds use
an explicit prerelease identifier such as `-beta.1` instead of continuing the
historical `-devNN` counter. Remaining protocol research does not block the
regular release, but the supported topology and evidence gates remain
unchanged.

The user-approved integration icon is an original, AI-assisted illustration
derived from the supplied front-facing PowerPulse 2 product photo. It preserves
the silver/black charger silhouette and adds a restrained cyan connection arc
and green energy accent. The local brand directory contains transparent
`icon.png` at 256×256 and `icon@2x.png` at 512×512 for Home Assistant's local
brand mechanism.
No Home Assistant branding is incorporated.

The `0.1.0` candidate commit `4c94ab8` was installed through HACS on Home
Assistant Core 2026.8.3, whose local custom-integration brand support covers
these files. The config entry returned to `loaded`, configuration validation
passed, HACS reported the exact installed/available commit with no pending
update, and no matching system-log error appeared. The authenticated frontend
visual check remains explicitly tracked as `REL-01`.

The final annotated `v0.1.0` tag points to candidate-validation commit
`4882e7c`. Its GitHub release contains the versioned installation ZIP with
SHA-256 `316d9f89432c995baad81d73560bdc24de3b5fda1808051ba74f85c2ea97a4fa`.
After refreshing HACS release metadata, HACS reported both installed and
available version `v0.1.0` with no pending update. Home Assistant Core
2026.8.3 restarted with the config entry in `loaded` state; the current log
contained only Home Assistant's expected generic warning for an unverified
custom integration, not an integration-specific runtime error.

The authenticated visual check subsequently confirmed the bundled icon is
rendered correctly under **Settings > Devices & services**. In the HACS 2.0.5
downloads list, the same repository still showed "Icon not available". This
matches the open upstream HACS frontend reports `hacs/integration#5223` and
`#5402`: that view still resolves custom-integration icons through the legacy
public Brands CDN instead of Home Assistant's authenticated local-brand proxy.
The repository layout and packaged assets therefore remain unchanged; the
remaining HACS presentation gap is tracked only as `REL-01` in the backlog.

## 2026-08-28: post-release phase readback sequence

With no vehicle connected and the EcoFlow app closed, the phase selector was
changed in Home Assistant from Auto to one phase, then to three phase, and
finally back to Auto. All three `241/102` SET requests received matching
replies and were confirmed through a newer direct C376 settings report. The
direct field `1.4.8.7` followed `0 -> 1 -> 2 -> 0`, independently reconfirming
`0` as Auto, `1` as one phase, and `2` as three phase. Device readback arrived
in approximately 0.8 to 1.4 seconds for the observed transitions.

The coordinator diagnostics ended with six direct control confirmations and
zero provider confirmations. The normal phase sensor changed at the same time
because it consumes the coordinator's merged value; it is not independent
evidence of provider readback. Diagnostics from the concurrently installed
EcoFlow Energy integration contained the MQTT frames but no current raw
provider/quota snapshot exposing `phaseSpecified`. Its provider mapping
therefore remains unresolved under `PHASE-01`; the direct-only safety gate is
still required.

An unreleased diagnostic-only change now keeps three observations separate:
direct C376 `241/44`, the parent PowerOcean accessory provider report, and the
wallbox device-detail provider report. For each source it records the last
snapshot timestamp, whether `phase_specified_raw` and `phase_mode` were present
in that snapshot, and the timestamp/value of the last valid observation. Only
the four-character product prefix is retained. This does not map a provider
value, alter merged coordinator data, expose a new entity, or relax the phase
control gate; it supplies the evidence needed for the next controlled app
sequence.

The same controlled phase sequence also tested the remaining unassigned fast
report byte fields. Sixteen direct frames were retained for each of Auto, one
phase, three phase, and the final return to Auto (64 decoded frames total).
Field `1.4.8.7` changed as expected through `0 -> 1 -> 2 -> 0`, while fields
`1.4.8.5` and `1.4.8.9` remained byte-identical in all four samples. Field `5`
retained two equal four-byte strings and two varints with value `15`; field `9`
retained its mixture of empty byte fields and zero varints. This is a controlled
negative result only: it excludes both fields as the direct phase-selection
value but does not assign their positive meaning. `DATA-02` remains open.

## 2026-08-29: one-phase real-power comparison

A connected vehicle charged in Solar mode with phase selection set to Auto;
the observed voltage and current identify the active session as one-phase.
Six simultaneous direct samples from approximately 2.4 to 3.2 kW showed the
direct power field consistently about 2.8-3.0% below voltage multiplied by
current. During the later stable interval, direct power was `1246.9 W`, the
provider `chargingPwr` value was `1244 W` and had last been reported 26 seconds
earlier, while `229.3 V * 5.62 A` equalled `1288.7 VA`. The two power fields
therefore differed by only about 0.23%, whereas the voltage/current product
remained about 3.3% higher.

This supports the direct field and `chargingPwr` as real-power readings and the
simple voltage/current product as apparent power with a power factor near
`0.97`. Earlier larger discrepancies are consistent with the paths' different
cadences during changing Solar output: provider reports arrived approximately
every 20-30 seconds, while the direct power/voltage/current set arrived about
once per minute.

A controlled follow-up stopped charging, selected three phases, restarted the
session, collected two complete direct reports, and then restored Auto plus an
active charging session. The two direct samples were `4070.7 W` at `231.6 V`
and `5.95 A`, and `4066.5 W` at `231.7 V` and `5.95 A`. Multiplying the summary
voltage and current by three produced `4134.1 VA` and `4135.8 VA`, for power
factors of about `0.985` and `0.983`. Provider `chargingPwr` was `4135 W` during
the first sample, but its timestamp preceded the direct sample by about 30
seconds. This confirms the intended three-phase scale for this balanced
session, while also confirming that a naive `U * I * 3` entity would represent
an apparent-power estimate rather than a more accurate real-power replacement.
It does not establish whether provider `chargingPwr` itself is real or apparent
power: the paths are asynchronous and the exposed voltage/current values are
the maxima of their phase arrays rather than three individually aligned pairs.
No replacement sensor is justified; `DATA-07` is complete and has been removed
from the canonical backlog.

The Home Assistant Start service also exposed a tooling nuance during the
test: the first synchronous MCP call returned `UNAVAILABLE` because the Start
button becomes unavailable immediately after a successful transition, but a
new heartbeat independently showed `charging`. A later non-waiting call
returned success and the same expected post-start button state. Device behavior
and the integration's heartbeat confirmation were correct.

## 2026-08-29: Custom and Smart charging-time interlocks

A connected-vehicle test completed the mode-specific part of the charging-time
control matrix. In Custom mode at 6 A, Home Assistant started charging and the
official app no longer displayed the Custom-current slider. The released HA
entity incorrectly remained available, proving that Custom current must use the
same charging interlock as mode, phase, and the two stored current limits.

After stopping, Smart mode was selected in the official app without changing
its retained target. HA received a ready-by timestamp and the retained 30 kWh
energy target, then started a confirmed charging session. During charging, the
official app allowed none of the Smart settings to be changed: ready-by time,
energy/distance target type, and the active target value were all locked. The
released HA ready-by and energy controls remained available, confirming the
second availability gap. The target-type control was already unavailable in
that particular snapshot because the integration had not retained both target
values; this is not evidence that its charging interlock was correct.

The `0.1.1-beta.1` correction adds `user_current_set_raw`, `ready_by_timestamp`,
`smart_target_type`, `smart_charge_target_wh`, and
`smart_target_distance_km` to the common charging-locked key set. Number,
select, and datetime availability uses the same keys, while the coordinator's
write path independently rejects direct service calls. The established
charging-time exceptions remain unchanged: Plug-and-Play, battery-discharge
blocking, screen, LED, and both brightness settings stay usable.

After the test, Solar mode and Auto phase were restored. A subsequent Start
request was accepted, but the user intentionally pressed Stop again before the
final state inspection because the vehicle should no longer charge. The later
`unknown`/zero-power snapshot is therefore not treated as evidence of a failed
Start request or a new charger-state mapping.

## 2026-08-29: 0.1.1-beta.1 validation bundle

The first post-0.1.0 preview bundles the source-separated phase readback
diagnostics with the completed Custom/Smart charging interlocks. It deliberately
does not change the selected charging-power source or phase-control fallback.
The versioned ZIP retains the standard
`custom_components/ecoflow_powerpulse2/...` layout. Live validation covers both
the new diagnostic observations and the UI/backend safety gates before a stable
0.1.1 release is considered.

The tagged prerelease was published with a 340,984-byte installation archive
whose local and GitHub asset SHA-256 both equal
`6f6e8aad10bb09f275ab73dce87c3d4c364ae06ffa94e8c8d7c44816730f9d3b`.
HACS installed the explicit `v0.1.1-beta.1` version while correctly continuing
to advertise stable `v0.1.0` as the normal latest version. After a valid config
check and Core restart, the config entry was loaded, both MQTT data streams were
active, and no `ecoflow_powerpulse2` system-log error was present.

With the vehicle stopped, Custom mode exposed its 6 A current control together
with maximum current and phase selection, confirming the new interlock did not
break idle availability. Smart mode could not be selected from HA after the
restart because the complete retained Smart block had not yet been republished;
the coordinator correctly failed closed instead of inventing companion values.
At this point active-session validation was still open; the 2026-08-30 section
below records its completion.

The phase diagnostic test selected one phase and three phases separately,
forced a provider refresh after each direct confirmation, and finally restored
Auto. The parent PowerOcean accessory source followed `phaseSpecified` raw
values `1`, `2`, and `0` respectively. The first three-phase provider poll still
held the earlier `1`; a second poll after ten seconds delivered `2`, demonstrating
why timestamped source separation is necessary. The wallbox device-detail source
reported neither the raw nor mapped phase field in every snapshot. This confirms
the parent-accessory mapping but does not yet change phase write confirmation.

Immediately after the Core restart, a fresh heartbeat and non-zero power showed
the charger active again even though the user had intentionally stopped it
earlier. No HA Start action was issued after restart. A new Stop reached
`charge_complete`; zero power/current followed and remained stable through the
phase tests. Because Plug-and-Play and Solar Continuous charging were both on,
the single observation is retained for controlled follow-up under `CTRL-03`
rather than attributed to the HA restart.

## 2026-08-29: beta Custom charging interlock validation

The active Custom portion of `SAFE-01` was run at the minimum bounded load:
maximum output current 6 A, Custom current 6 A, and one phase. A Start request
at `17:24:13.995781Z` reached a fresh `charging` heartbeat. Mode, phase,
maximum current, Custom current, Solar minimum current, and Continuous charging
all became unavailable in HA. Plug-and-Play, battery-discharge blocking,
screen, screen brightness, LED, and LED brightness remained available exactly
as established by the official-app matrix. Calling `number.set_value` on the
unavailable Custom-current entity produced no state result and no observable
change. Stop was issued at `17:24:53.448592Z`, limiting the active window to
about 39 seconds. This completes the Custom half of the beta interlock test;
Smart was completed in the subsequent 2026-08-30 test below.

## 2026-08-30: Continuous charging while Solar-paused

The user observed a distinct paused-state case. In Solar mode with Continuous
charging disabled and insufficient solar, the official app did not expose the
Continuous switch. HA did expose it because the current safety helper treats
`paused` as a known non-charging state. The user enabled Continuous charging
from HA. Readback changed to on at approximately `08:58:33` local time, and a
fresh heartbeat changed to `charging` at `08:59:32`, followed by roughly
`1289.6 W`. This strongly indicates that the device accepted the write and used
the stored 6 A Solar minimum to resume charging despite the app UI restriction.

This is not yet a decision to keep or remove the capability. A controlled
repeat must correlate SET, reply, direct/provider setting readback, and the
heartbeat transition with the app closed, and must test disabling as well as
enabling. `SAFE-02` in the canonical backlog owns that policy question so it is
not duplicated as an open item elsewhere.

## 2026-08-30: beta Smart charging interlock validation

The official app republished a complete usable Smart configuration before the
test: ready by 12:10 local time and 30 kWh. Before Start, HA showed the retained
ready-by timestamp as `2026-08-30T10:10:40+00:00` and the 30 kWh target. The
target-type entity remained unavailable because no retained distance companion
value was present; this is a separate completeness gate and did not weaken the
charging interlock.

Start at `07:12:03.195127Z` reached a fresh `charging` state. Mode, phase,
maximum current, Smart ready-by, Smart target type, Smart energy, and Smart
distance were all unavailable. Plug-and-Play, battery-discharge blocking,
screen, screen brightness, LED, and LED brightness remained available. A
same-value `number.set_value` call against the unavailable 30 kWh Smart-energy
entity returned an empty result. Diagnostics recorded only the expected
matched `241/100` Start (sequence 123) and Stop (sequence 208) commands during
the active interval and no `241/102` settings publish. Stop at
`07:12:46.799973Z` limited charging to about 44 seconds at one phase and the
minimum 6 A limit.

The wallbox was then restored to Solar mode, automatic phase selection, and a
16 A maximum output current. Continuous charging remains enabled as configured
by the user. The final state was `charge_complete`, charging off, and 0 W.
Together with the 39-second Custom test, this completes `SAFE-01`; the item has
therefore been removed from the canonical backlog.

## 2026-08-30: delayed Start confirmation and 0.1.1-beta.2

A later Start at `09:16:40.718512` local time produced a matched `241/100`
reply at `09:16:40.827214`, so command transport was acknowledged after about
109 ms. A newer heartbeat first reported `plugged_in` at `09:16:41.399626` and
only reached `charging` at `09:16:58.080104`, approximately 17.3 seconds after
the request. The previous 15-second readback window therefore raised a false
failure shortly before the successful state arrived.

Version `0.1.1-beta.2` gives Start a 30-second readback window while preserving
the 15-second Stop window. It does not weaken outcome validation: `plugged_in`
still cannot confirm Start, which continues to require a fresh `charging` or
`paused` heartbeat. The change affects only how long HA waits for the same
independent device evidence.

The same beta completes the code side of the Home Assistant metadata audit.
Current, energy, and distance Number controls now use native device classes and
unit constants; the Smart distance sensor uses native distance metadata; and
the screen/LED switches and brightness controls are device-configuration
entities. No measurement state class was added to targets, brightness values,
or raw diagnostics because they are configuration or protocol values rather
than physical measurement series. No protocol path, payload, or unique ID is
changed.
