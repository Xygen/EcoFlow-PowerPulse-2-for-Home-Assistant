# WIP findings for C376 / PowerPulse 2

> **WORK IN PROGRESS — please do not treat these mappings as complete or as a request to implement controls yet.**
>
> This is an interim report from a separate, deliberately read-only test
> integration. Nothing has been posted upstream yet. The results below come
> from privacy-redacted captures from one live C376 charger installed alongside
> a PowerOcean Plus, plus paired changes made in the official EcoFlow app.

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
header, field 8 is `cmd_func`, field 9 is `cmd_id`, field 11 is `enc_type`, and
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
under `cmd_func=209` (observed with `cmd_id=8`). In its protobuf body, field 10
tracks the operating-mode value and field 18 tracks the settings bitmask. We
currently keep this route diagnostic-only because the matched provider detail
is easier to attribute safely and contains more named fields. Raw parent
payloads are intentionally not retained because they can bundle charger,
battery, and vehicle identifiers.

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

## Current state of the test implementation

- The current development build is `0.1.0-dev11` and remains read-only. Its
  controlled 6 A to 7 A to 6 A test is complete and identifies `241/102` as
  the acknowledged current-setting route candidate.
- MQTT uses a hard `listen_only` guard; automatic get-all/stream activation and
  every other publish path are suppressed.
- The new `Kontinuierlich laden` binary sensor was verified live in both
  directions: `switchBits=0` produced `off`, `switchBits=16` produced `on`, and
  `solarCurrentMin=60` remained stored throughout the test.
- The parser has been exercised against live C376 frames. The current local
  suite passes 28 tests, including XOR envelope decoding, packed phase values,
  command-specific `2/33` vs `2/34` routing, settings fields, matching an
  embedded PowerPulse report to its exact serial, privacy-safe `96/97`
  inspection, runtime-keyed opaque-body comparison, and command-sequence
  correlation.
- This is not proposed as production-ready code or as a ready-made patch for
  `ecoflow-energy-ha` yet. The useful output at this stage is the field and
  data-source evidence above.

## Still to do

1. Confirm session-energy field 42 across more non-zero sessions, including
   rounding and whether raw units are consistently Wh.
2. Pair additional app changes with provider/MQTT snapshots to separate
   `userCurrentSet`, heartbeat fields 17/18, the remaining `switchBits`, and
   `phaseSpecified` cleanly.
3. Locate the Smart distance target and confirm the unit/scaling of
   `currentVehicleComsumption`.
4. Check additional operating states and map `suspend_reason` values.
5. Decide how best to represent the three individual phase voltages/currents
   upstream instead of only exposing an aggregate maximum.
6. Adapt the two-source model (direct C376 MQTT plus the linked PowerOcean
   provider detail) to `ecoflow-energy-ha` without allowing unrelated parent
   `workMode` or other similarly named fields to leak into the charger device.
7. For any future controls, capture the actual request envelope **and** device
   acknowledgement first. No PowerPulse-attributable SET or SET-reply frame was
   observed during the paired Start/Stop, mode, target, or current changes. The
   controlled current test identifies acknowledged `241/102` traffic in both
   directions, but its request and reply bodies remain privacy-omitted. Their
   structure, changed fields, target attribution, and acknowledgement semantics
   must be confirmed before considering a write. Start/Stop or other settings
   may still use different commands, the provider HTTP API, or another
   transport.

For now I would suggest treating all of this as read-support research only,
with Start/Stop and current-setting controls explicitly out of scope until the
write path is observed rather than inferred.
