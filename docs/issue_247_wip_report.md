# WIP findings for C376 / PowerPulse 2

> **WORK IN PROGRESS — please do not treat these mappings as complete or as a request to implement controls yet.**
>
> This is an interim report from a separate, deliberately read-only test
> integration. An earlier summary has been posted to upstream issue #247. The
> results below come from privacy-redacted captures from one live C376 charger
> installed alongside a PowerOcean Plus, plus paired changes made in the
> official EcoFlow app.

## Scope boundary

Both the first-generation wallbox named **PowerPulse** (without a version
number) and **PowerPulse 2** can theoretically operate standalone without a
PowerOcean inverter. This research and its test integration intentionally cover
only **PowerPulse 2 installed with a linked PowerOcean inverter/system**.
First-generation PowerPulse devices and standalone PowerPulse 2 installations
are not being tested or claimed as supported. The PowerOcean dependency in the
implementation is therefore a deliberate project-scope choice, not a general
hardware requirement of the wallbox.

The original “prefix only, no data” situation has moved forward. We can now
read useful C376 state from two complementary sources:

- direct C376 cloud-MQTT traffic contains CP307 protobuf status and settings
  reports;
- the provider detail for the linked PowerOcean contains a richer embedded
  `pileChargingParamReport` for the C376. The direct C376 provider-detail
  response is mostly empty.

The important implementation detail for the second path is to read
`/provider-service/user/device/detail?sn=<PowerOcean SN>`, find nested
`pileChargingParamReport` objects, and match each one back to the charger using
the embedded `devInfo.devSn`. A PowerOcean response contains fields from
multiple products, so a generic recursive match for names such as `workMode`
is unsafe.

## Direct C376 MQTT / CP307 details

The useful payload is in the normal EcoFlow protobuf envelope. In the envelope
header, field 8 is `cmd_func`, field 9 is `cmd_id`, field 6 is `enc_type`, and
field 14 is the sequence. With `enc_type=1`, `pdata` is XOR-decoded with
`sequence & 0xff`.

### `cmd_func=2`, `cmd_id=33`: heartbeat/status

The following fields are currently decoded:

| CP307 field | Current interpretation | Evidence/status |
| --- | --- | --- |
| 1 | system state | Live states seen and/or mapped: `1` unplugged, `2` plugged in, `3` charging, `4` paused, `6` charge complete, `7` standby, `8` updating. |
| 9 | total energy, raw | Value is retained raw; unit/scaling is not confirmed. |
| 17 | configured charge current, raw | Values such as `60` were observed, but it did **not** follow the Custom-mode 6 A to 11 A slider. The exact function should therefore remain unresolved. |
| 18 | current limit, raw | `160` was observed and is consistent with a 16 A limit, but the independently paired settings-report/provider fields below are the stronger evidence for the maximum-current setting. |
| 28 | charging power | Protobuf `float`; observed as watts. |
| 29 | phase voltages | Repeated/packed `float`; three phase values are present. The test integration currently exposes the maximum as a compact summary. |
| 30 | phase currents | Repeated/packed `float`; three phase values are present. The test integration currently exposes the maximum as a compact summary. |
| 41 | session duration | Seconds. Confirmed against a completed zero-energy session. |
| 42 | session energy, raw | Strong working hypothesis: Wh. A live raw value of `1815` corresponded to `1.82 kWh` in the app, but more sessions are needed before fixing the unit/scaling. |
| 102 | suspend reason, raw | Retained for diagnostics; value mapping is not yet established. |

One useful state-sequence check was done in Solar Mode without available solar
surplus. Starting from the app changed the heartbeat to state `4` (paused), and
stopping changed it to state `6` (charge complete). The final heartbeat reported
`session_duration=278` and zero session energy.

`cmd_func=2`, `cmd_id=133` was also emitted during that sequence. It behaves as
a charging-record report (`CHARGED_RECORD`), not as the Start/Stop request. Its
completed record ended 278 seconds after its start, independently agreeing with
heartbeat field 41.

### `cmd_func=2`, `cmd_id=34`: settings report

This command must not be parsed with the heartbeat schema: it reuses field
numbers with different meanings. The following mappings were confirmed by
changing one setting at a time in the app and comparing captures. All paired
C376 reports used schema marker `field 1 = 9`.

| CP307 field | Confirmed function |
| --- | --- |
| 2 | Plug-and-Play enabled (`0`/`1`) |
| 9 | maximum output current in tenths of an ampere (`150` = 15 A, `160` = 16 A) |
| 11 | phase selection: `1` one phase, `2` three phase, `3` auto |
| 13 | indicator/LED enabled (`0`/`1`) |
| 14 | indicator/LED brightness in percent |
| 15 | screen enabled (`0`/`1`) |
| 16 | screen brightness in percent |
| 22 | battery discharge disabled (`0`/`1`) |

An earlier parser incorrectly treated `2/34` as `2/33`, which briefly produced
nonsensical current/status entities. Routing by `(cmd_func, cmd_id)` fixes that
class of error.

There is also an important negative result: Solar continuous charging at 6 A
and Custom charging at both 6 A and 11 A produced byte-for-byte identical
decoded `2/34` bodies. The report is therefore not sufficient to infer the
mode/current write payload.

## Embedded provider fields from the linked PowerOcean

Within the matched C376 `pileChargingParamReport`:

| Provider field | Current interpretation | Evidence/status |
| --- | --- | --- |
| `chargingPwr` | charging power in W | Read-only telemetry. |
| `chargingStatus` | charger state | Uses the same state interpretation listed above. |
| `paramSet.workMode` | operating mode | Live-confirmed: `1` Fast, `2` Solar, `3` Custom, `4` Smart. |
| `paramSet.currentOuputMax` | maximum output current, tenths of A | The misspelling is present in the provider data. Paired values match CP307 `2/34` field 9. |
| `paramSet.userCurrentSet` | raw user-current setting | Retained raw; exact relationship to the different app current sliders is not yet established. |
| `paramSet.solarCurrentMin` | Solar minimum/continuous-current setting, tenths of A | A controlled `6 A -> 7 A -> 6 A` test produced `60 -> 70 -> 60`. The value also remained stored while Continuous charging was switched off and back on. |
| `paramSet.switchBits` | settings bitmask | `switchBits & 0x10` is live-confirmed as the Solar-mode Continuous charging switch; other bits remain unassigned. |
| `paramSet.phaseSpecified` | raw phase-selection field | Retained raw; the CP307 `2/34` field 11 mapping is currently better established. |
| `paramSet.smartMode.timeToUseCar` | ready-by time | Unix timestamp. Returning to Solar Mode reset it to `0`. |
| `paramSet.smartMode.chargeTarget` | Smart energy target in Wh | `30000` matched 30 kWh. In distance-target mode this field was `0`; the 200 km target is stored elsewhere. |
| `vehicleInfo.currentVehicleComsumption` | raw vehicle-consumption value | Retained raw; spelling is as received and unit/scaling is not confirmed. |

The parent PowerOcean MQTT stream also carries a PowerPulse accessory report
under `cmd_func=209` (observed with `cmd_id=8` during an earlier charging
session). Earlier versions of this report assigned body field 10 to operating
mode and field 18 to the settings bitmask from a provider-side comparison.
That comparison did not isolate either value within `209/8`, so both
assignments are withdrawn pending a controlled report diff. The no-car test
below contained no `209/8` frame at all. Raw parent payloads are retained only
through the upstream integration's privacy-masked diagnostic capture because
they can bundle charger, battery, and vehicle identifiers.

Later live diagnostics also captured 24 frames on the linked PowerOcean's
official-app property-SET topic. Their envelope headers consistently contained
`cmd_func=96`, `cmd_id=97`, and a two-byte `pdata`; several sequences were
repeated. No matching SET-reply bucket was present. These frames began after,
not simultaneously with, the final Continuous-charging test, so they cannot yet
be attributed to that setting or even to the PowerPulse. The privacy guard
correctly omitted the parent payload. This is a candidate route for a future
paired capture, not write-command evidence.

Development build `0.1.0-dev11` adds a deliberately narrow diagnostic for this
candidate. It XOR-decodes only the exact `96/97` tuple when the decoded body is
at most 16 bytes. Small protobuf varints can be retained for comparison;
opaque fields expose only their length, larger numeric values are omitted, and
no decoded or raw bytes are stored. A separate bounded view groups requests,
retries, and replies by source and sequence. This instrumentation still does
not attribute the tuple to the PowerPulse and never publishes MQTT traffic.

The first live dev11 baseline showed that the decoded two-byte body is not a
protobuf message. The tuple also appeared without a user action in pairs about
20 seconds apart and still had no SET reply, making background PowerOcean
traffic more likely than a PowerPulse-setting command. For the controlled test,
dev11 therefore adds a runtime-keyed HMAC fingerprint for equality comparison.
The random key is never exported, so the small body cannot be recovered by
offline brute force; fingerprints are intentionally comparable only until the
integration restarts.

The subsequent controlled `6 A -> 7 A -> 6 A` test separated the relevant
traffic from that baseline:

- Saving 7 A was followed by a PowerOcean `cmd_func=241`, `cmd_id=102` SET with
  a same-sequence SET reply about 64 ms later. The next provider snapshot
  changed `solarCurrentMin` from `60` to `70`.
- Saving 6 A produced the same `241/102` request/reply pair, with the reply
  about 119 ms later. The provider snapshot returned from `70` to `60`.
- `switchBits=16`, Continuous charging enabled, and Solar Mode remained
  unchanged throughout.
- `96/97` continued periodically and in short retry bursts without replies, so
  it is not the current-setting command candidate.

This strongly identifies `241/102` as the route used while saving the Solar
minimum current in this PowerOcean-linked installation. The 31-byte request and
23-byte reply bodies are still privacy-omitted. Their safe structure and exact
acknowledgement semantics must be compared before any write implementation.

Development build `0.1.0-dev12` adds that narrow comparison instrument. It
accepts only the exact `241/102` tuple up to 64 decoded bytes, traverses at most
three nested protobuf levels and 32 total fields, and retains only field/wire
metadata, sizes, and varints up to 255. Runtime-keyed fingerprints identify
changed byte fields during one HA runtime without revealing their contents.
The existing `96/97` path keeps its stricter 16-byte limit. No MQTT publish path
is added.

The completed live dev12 `6 A -> 7 A -> 6 A` comparison initially appeared to
produce:

- sequence 88 for 7 A, with a 31-byte request, a same-sequence 23-byte reply
  after approximately 139 ms, and provider `solarCurrentMin=70`;
- sequence 96 for the restored 6 A, with the same sizes, a reply after
  approximately 83 ms, and provider `solarCurrentMin=60`;
- different runtime fingerprints for both target requests and both replies;
- `opaque_non_protobuf` for all four supposedly decoded bodies.

The opaque classification was a decoder error rather than a protocol result.
The observer used header field 11 (`need_ack`) as `enc_type`, while EcoFlow's
header places `enc_type` in field 6. Because these SET requests ask for an
acknowledgement, plaintext protobuf was XOR-mutated before inspection. The
upstream raw diagnostic remains structurally decodable and exposes the nested
field paths listed in the no-car capture section below. This correction still
does not turn the observed app write into an approved control template.

## Controlled no-car settings capture requested in issue #247

**WIP caveat:** the changes were left approximately one minute apart rather
than the requested roughly two minutes. The diagnostic was downloaded
immediately after the final change. It reports 13 `241/102` SET frames and 13
same-command SET replies, but time-slot sampling retained only seven complete
pairs.

No `209/8` frame was present anywhere in the recording. Fields 5, 10 and 18
therefore have no before/after values in this test; the report was absent, not
stable. Field 31 is not treated as part of `209/8`: the upstream maintainer's
recording does not contain fields 30 and above in that message and attributes
those numbers to a neighbouring message. This capture supplies no isolated
before/after evidence for that neighbouring field 31 either. The negative
`209/8` result applies only to the no-car condition and does not establish what
the report carries during a plugged-in or active charging session.

The retained app writes on the existing PowerOcean MQTT connection decode as
a top-level accessory descriptor in field 1 and a settings object in field 4:

| Inner path | Function supported by this capture | Retained values |
| --- | --- | --- |
| `4.1` | `switchBits` | `16`, `18`, `0`; Plug-and-Play adds bit `0x02`, Continuous charging uses bit `0x10` |
| `4.2` | work mode | `4` Smart, `3` Custom, `2` Solar |
| `4.3` | maximum output current | `110` = 11 A |
| `4.4` | Solar minimum/continuous current | `60` = 6 A |
| `4.5` | phase selection | `2` three phase, `0` auto |
| `4.6` | Custom current | `60` = 6 A |
| `4.7` | Smart settings | nested timestamp/selector/target values, including `30000` Wh |

The retained bodies do not include the 16 A, Fast, return-to-Solar,
Plug-and-Play-off, Continuous-charging-on or one-phase changes. Their frames
contribute to the seen counts but were removed by sampling, so those missing
bodies are not reconstructed or inferred here.

## Current state of the test implementation

- Development build `0.1.0-dev17` includes the dev13 header correction and
  remains read-only. The parser reads `enc_type` from field 6 and keeps field 11 as
  `need_ack`; acknowledgement-requesting plaintext bodies are no longer
  XOR-mutated. The upstream diagnostic confirms nested protobuf.
- A direct C376 `241/44` parameter report was found in the installed dev15
  diagnostics. It arrives roughly once per second, uses XOR encryption keyed by
  the sequence low byte, and exposes its scalar parameter object at protobuf
  path `1.4.8`. One live snapshot matched fields `1/2/4/6/7/8` to
  `switchBits/workMode/currentOuputMax/solarCurrentMin/phaseSpecified/`
  `userCurrentSet` as `16/2/160/70/0/60`. dev16 parses only that exact,
  bounded six-field shape.
- dev16 gives these direct settings priority over a cached provider snapshot
  only while the report is at most ten seconds old. HTTP and the dev15 delayed
  refresh remain automatic fallbacks, and no MQTT request is published.
- The installed dev16 build was validated live by restoring the Solar minimum
  current from 7 A to 6 A. The app SET carrying `4.4=60` was acknowledged after
  approximately 152 ms, and the HA entities changed to `60`/`6.0 A`
  approximately 1.77 seconds after the SET. The provider fallback did not
  complete until about 20.26 seconds after the SET, independently confirming
  that direct `241/44` readback produced the fast entity update.
- A controlled Plug-and-Play off-on-off test then changed direct `241/44`
  field `1` from `16 -> 18 -> 16`, while Solar mode, Continuous charging, and
  the 6 A Solar minimum remained stable. The direct transitions followed their
  SET requests after approximately 1.47 s and 1.69 s. This bidirectionally
  confirms bit `0x02`; dev17 uses it for the existing Plug-and-Play binary
  sensor without adding a publish path.
- Installed dev17 was verified after restart: regular 100-byte `241/44` frames
  parsed `plug_and_play`, and HA showed Plug-and-Play off, `switchBits=16`,
  Continuous charging on, Solar mode, and 6 A. An intermittent 105-byte variant
  of the same tuple did not match the strict six-scalar shape and was ignored;
  normal frames continued roughly once per second and MQTT remained
  `listen_only`.
- The completed live dev13 `6 A -> 7 A -> 6 A` comparison decoded path `4.4`
  as `70 -> 60`, while `4.1=16` and Solar mode `4.2=2` remained stable. The
  same-sequence replies arrived after approximately 144 ms and 226 ms and
  contained the matching accessory descriptor but no settings readback.
- Independent provider snapshots confirmed `solarCurrentMin=70 -> 60`. The HA
  entity followed about 31 s and 36 s after the corresponding MQTT SET frames,
  demonstrating that acknowledgement latency and provider/entity refresh
  latency are separate measurements.
- dev14 tested a two-second delayed provider read after a `241/102` reply was
  matched to its previously observed request by source and sequence. Both live
  directions still returned the preceding value at that time. Readback later
  followed after about 25-29 seconds in the measured cases.
- dev15 therefore performs one coalesced provider read after 20 seconds instead.
  Duplicate, unmatched, direct-device, and unrelated-command replies cannot
  trigger it; the normal 30-second poll remains intact and may update earlier.
  Observed app-request values are not applied optimistically because the reply
  does not echo or explicitly confirm the settings object.
- The normal Solar minimum charging current is now presented in Ampere via
  `solarCurrentMin / 10`, while its raw diagnostic entity remains available.
  The maximum-output-current entity defaults to zero decimal places, and the
  screen translations now group `Screen`/`Screen brightness` and
  `Bildschirm`/`Bildschirmhelligkeit`.
- MQTT uses a hard `listen_only` guard; automatic get-all/stream activation and
  every other publish path are suppressed.
- The new `Kontinuierlich laden` binary sensor was verified live in both
  directions: `switchBits=0` produced `off`, `switchBits=16` produced `on`, and
  `solarCurrentMin=60` remained stored throughout the test.
- The parser has been exercised against live C376 frames. The current local
  suite passes 40 tests, including direct `241/44` parameter decoding,
  Plug-and-Play bit derivation, strict
  command/range rejection, selected fresh-MQTT merge priority, XOR envelope
  decoding, packed phase values,
  command-specific `2/33` vs `2/34` routing, settings fields, matching an
  embedded PowerPulse report to its exact serial, privacy-safe `96/97` and
  `241/102` inspection, runtime-keyed opaque-field comparison, and
  command-sequence correlation plus passive refresh gating/coalescing.
- This is not proposed as production-ready code or as a ready-made patch for
  `ecoflow-energy-ha` yet. The useful output at this stage is the field and
  data-source evidence above.

## Still to do

1. Confirm session-energy field 42 across more non-zero sessions, including
   rounding and whether raw units are consistently Wh.
2. Investigate the currently unnamed length-delimited `241/44` parameter
   fields `5`, `9`, `21`, and `31` using controlled one-setting-at-a-time
   comparisons. Their observed sizes alone are not semantic evidence.
3. Pair additional app changes with provider/MQTT snapshots to separate
   `userCurrentSet`, heartbeat fields 17/18, the remaining unassigned
   `switchBits`, and `phaseSpecified` cleanly.
4. Locate the Smart distance target and confirm the unit/scaling of
   `currentVehicleComsumption`.
5. Check additional operating states and map `suspend_reason` values.
6. Decide how best to represent the three individual phase voltages/currents
   upstream instead of only exposing an aggregate maximum.
7. Keep upstream proposals aligned with the maintainer's selected architecture.
   The latest diagnostic showed no PowerPulse 2 readback on the PowerOcean in
   the no-car state, so direct C376 MQTT is now being considered as the only
   observed hardware-readback source rather than a duplicate source. The
   provider-detail path remains research and fallback evidence unless the
   maintainer explicitly chooses to include HTTP polling.
8. For any future controls, retain the captured request **and** same-sequence
   reply evidence, but separately confirm target attribution, acknowledgement
   semantics, complete value mappings and safety constraints. `241/102` is an
   observed app-write path, not a readback source. Start/Stop may still use a
   different command or transport.

For now I would suggest treating all of this as read-support research only,
with Start/Stop and current-setting controls explicitly out of scope until the
write path is observed rather than inferred.
