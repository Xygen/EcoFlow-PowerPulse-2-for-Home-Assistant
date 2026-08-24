# WIP findings for C376 / PowerPulse 2

> **WORK IN PROGRESS — please do not treat these mappings as complete or as a request to implement controls yet.**
>
> This is an interim report from a separate, deliberately read-only test
> integration. Nothing has been posted upstream yet. The results below come
> from privacy-redacted captures from one live C376 charger installed alongside
> a PowerOcean Plus, plus paired changes made in the official EcoFlow app.

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
| `paramSet.solarCurrentMin` | raw Solar minimum/continuous-current setting | Retained raw pending more paired captures. |
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

## Current state of the test implementation

- The local WIP is `0.1.0-dev10` and remains read-only.
- MQTT uses a hard `listen_only` guard; automatic get-all/stream activation and
  every other publish path are suppressed.
- The parser has been exercised against live C376 frames. The current local
  suite passes 24 tests, including XOR envelope decoding, packed phase values,
  command-specific `2/33` vs `2/34` routing, settings fields, and matching an
  embedded PowerPulse report to its exact serial.
- This is not proposed as production-ready code or as a ready-made patch for
  `ecoflow-energy-ha` yet. The useful output at this stage is the field and
  data-source evidence above.

## Still to do

1. Confirm session-energy field 42 across more non-zero sessions, including
   rounding and whether raw units are consistently Wh.
2. Pair additional app changes with provider/MQTT snapshots to separate
   `userCurrentSet`, `solarCurrentMin`, heartbeat fields 17/18, the remaining
   `switchBits`, and `phaseSpecified` cleanly.
3. Locate the Smart distance target and confirm the unit/scaling of
   `currentVehicleComsumption`.
4. Check additional operating states and map `suspend_reason` values.
5. Decide how best to represent the three individual phase voltages/currents
   upstream instead of only exposing an aggregate maximum.
6. Adapt the two-source model (direct C376 MQTT plus the linked PowerOcean
   provider detail) to `ecoflow-energy-ha` without allowing unrelated parent
   `workMode` or other similarly named fields to leak into the charger device.
7. For any future controls, capture the actual request envelope **and** device
   acknowledgement first. No SET or SET-reply frame was observed on the known
   exact or wildcard MQTT routes during Start/Stop, mode, target, or current
   changes. Those writes may use the provider HTTP API or another transport.

For now I would suggest treating all of this as read-support research only,
with Start/Stop and current-setting controls explicitly out of scope until the
write path is observed rather than inferred.
