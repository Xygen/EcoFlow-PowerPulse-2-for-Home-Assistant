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
- `paramSet.userCurrentSet`, `phaseSpecified`, and
  `vehicleInfo.currentVehicleComsumption`: retained raw pending further paired
  tests

Presentation backlog: expose `solarCurrentMin` additionally as a normal Ampere
sensor for the Solar-mode minimum current used when Continuous charging is
enabled (`raw / 10`), while retaining the raw diagnostic entity. The existing
maximum-output-current entity should default to zero decimal places because the
confirmed app setting uses whole amperes.

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

The same parameter object also contained length-delimited fields `5`, `9`,
`21`, and `31`, sized 16, 14, 6, and 10 bytes in the inspected snapshot. Their
contents and meanings are deliberately not retained or named. They are a
backlog for later controlled one-setting-at-a-time comparisons, especially
Smart-mode, vehicle, and other settings that still lack a fast confirmed
source. No entity should be created from these fields until such a comparison
isolates its value and unit.

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
is the first HA-originated write implementation and remains pending live
hardware validation; Start/Stop and all other controls remain unimplemented.

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

## 2026-08-24: charging-state write interlocks to investigate

Start and Stop must be captured both without a vehicle and with a vehicle
connected. Future control logic must require actual charging-state readback,
because a SET reply alone confirms transport correlation rather than the
physical result.

The official app prevents at least operating-mode and phase-selection changes
while charging is active. Additional locked settings remain to be identified.
Every exposed write should therefore receive a state-dependent availability or
local validation rule once its charging-time behaviour is known, preventing a
predictably invalid MQTT command from being sent at all.

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
