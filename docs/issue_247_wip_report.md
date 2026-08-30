# WIP findings for C376 / PowerPulse 2

> **WORK IN PROGRESS — protocol research and unresolved mappings remain
> ongoing even though the live-validated integration is now regularly released.**
>
> This report began with a deliberately read-only test integration. Later
> development builds add only evidence-gated, user-triggered controls whose
> official-app request shapes, replies, and independent readback were captured.
> An earlier summary has been posted to upstream issue #247. The results below
> come from privacy-redacted captures from one live C376 charger installed
> alongside a PowerOcean Plus, plus paired changes made in the official EcoFlow
> app and reversible Home Assistant tests.

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
| `paramSet.userCurrentSet` | Custom-mode current, tenths of A | Later direct comparisons confirmed `60` = 6 A and `110` = 11 A. |
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

## Historical implementation state through dev17

- At the dev17 stage, automatic MQTT operation remained read-only. The parser
  reads `enc_type` from field 6 and keeps field 11 as
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
- The parser had been exercised against live C376 frames. That stage passed 40
  tests, including direct `241/44` parameter decoding,
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

## Open work

Active investigations, safety tests, and release requirements are maintained
only in the [project backlog](backlog.md). This report retains the chronological
evidence behind those tasks rather than a second checklist.

Current dev22 already implements and live-validates operating mode, phase,
maximum/Solar/Custom current settings, battery blocking, Plug-and-Play,
Continuous charging, Smart targets/ready-by, and screen/LED controls. Automatic
MQTT activity remains listen-only; only explicit HA actions use the captured
settings commands. Start/Stop and charging-time interlocks remain intentionally
unimplemented.

## dev18 candidate update (2026-08-24)

The next bundled development build incorporates the completed controlled
comparisons rather than one test per build:

- fast phase mapping `0` Auto, `1` one phase, `2` three phase;
- Custom current field `8` scaled in 0.1 A, verified at 6 A and 11 A;
- Smart field `31` decoded into ready-by timestamp, energy/distance selector,
  Wh value and kilometre value; 200/300 km corresponded to calculated
  30,000/45,000 Wh in this configuration;
- normal Custom-current, Smart-target-type and Smart-distance entities;
- a disabled-by-default experimental phase `select` using the observed
  PowerOcean-routed `241/102 -> 4.5` command.

The phase write is deliberately narrower than the generic transport. It is
unavailable until a direct device frame supplies the exact opaque accessory
descriptor, refuses ambiguous installations with more than one PowerOcean
observer, and requires both the same-sequence SET reply and direct phase
readback. The official-app request/reply evidence is complete, but the first
HA-originated live write still has to be validated after installation. No
Start/Stop, current, mode, Smart, LED, screen, battery, or Plug-and-Play write
is exposed in dev18.

## dev19 candidate update (2026-08-24)

The dev18 phase control has now been live-tested end to end for Auto, one phase,
and three phases. All three HA commands received same-sequence replies, direct
wallbox readback, and matching EcoFlow-app display. Reply latency was about
127-144 ms and readback completed in approximately 0.5-1.3 seconds.

An official-app comparison additionally confirmed `switchBits & 0x01` as
"Disable battery discharge": the direct flags changed `16 -> 17 -> 16`, while
Continuous charging and Plug-and-Play were preserved. dev19 therefore adds
disabled-by-default switches for battery-discharge blocking and Continuous
charging plus whole-ampere number controls for maximum output current and
Solar minimum current. All retain unrelated flags, enforce known Solar-mode
constraints, serialize writes, and require both SET acknowledgement and direct
device readback. Start/Stop and all remaining settings stay out of scope.

At the dev19 stage, fast field `241/44.21` remained unconfirmed: its six-byte
value `01 01 19 19 02 00` aligns with the current screen/LED enable and 25%
brightness values plus battery blocking off, but no controlled byte-level
comparison has confirmed those positions. It remains unparsed in dev19.

## Observed charging-state constraints

The captured evidence contains no official-app Start/Stop request, either
without a connected vehicle or with one connected. A successful transport
acknowledgement would not prove that charging started or stopped; independent
charger-state readback must distinguish unplugged, plugged-in, charging,
paused, completed, and rejected operations where observed.

The EcoFlow app locks some settings during an active charging session. Operating
mode and phase selection are confirmed members of that locked set. The current
no-vehicle tests do not establish which current, Solar, battery, display, LED,
or other settings remain writable during charging. The authoritative test and
implementation criteria are tracked in the [project backlog](backlog.md).

## dev20 candidate update (2026-08-24)

Complete forward and reverse no-vehicle app sequences now confirm all four
operating-mode requests. Fast is `4.2=1`; Solar is `4.2=2` with flags and Solar
minimum; Custom is `4.2=3` with `4.6` in 0.1 A; Smart is `4.2=4` with flags and
the nested `4.7` ready-by/target block. Custom was captured at 6, 7, and 16 A.
Smart was captured at 30 and 40 kWh and at 200 and 300 km; the controlled final
ready-by value was 08:00 (+1). Every request received a same-sequence reply and
the fast direct report confirmed the resulting state.

dev20 adds disabled-by-default controls for operating mode, Custom current,
Plug-and-Play, Smart ready-by time, target type, energy, and distance. It keeps
the automatic transport listen-only, publishes only on explicit HA user action,
preserves unrelated flags and mode-specific companion fields, and requires
both acknowledgement and direct device readback. Charging-time availability
remains intentionally unresolved until a vehicle is available for interlock
tests.

The installed dev20 candidate also confirmed Fast, Custom, Custom 7 -> 6 A,
Solar, and Plug-and-Play on -> off from HA with device readback. Smart mode was
safely refused immediately after restart because the Solar-mode provider
snapshot omitted the stored distance type/value. Entering Smart once in the app
restored the direct 200 km block. The follow-up implementation keeps both Smart
value controls writable in Smart mode so either can atomically establish its
target type; type-only switching remains gated until both values are known.

The corrected installed build completed the remaining HA-originated tests:
distance 200 km -> energy 40 -> 30 -> 40 kWh, target type back to distance,
distance 200 -> 300 -> 200 km, and a same-value ready-by republish. Each
integration call returned only after its SET reply and fresh direct wallbox
readback. The sequence ended in Solar mode with Plug-and-Play off; Custom current
remained restored to 6 A and the stored Smart distance remained 200 km. This
validates the controls without a vehicle, but does not establish their
behaviour during an active charging session.

The first bundled screen/LED write capture produced eight retained `241/102`
requests and replies while direct entities confirmed both switches and all four
brightness levels. These requests use a nine-byte top-level settings block that
the existing privacy filter represented only by equality fingerprints. A narrow
diagnostic update now exports numeric bytes only for top-level settings field
`4` up to 16 bytes, while continuing to omit the accessory descriptor and all
other opaque content. One repeated bundled app sequence is required before the
four HA controls can be built from evidence rather than inferred positions.
The bounded per-command sample count is increased from eight to sixteen so the
entire repeated sequence can be retained in one run.

The repeat resolved nested field `4.21` as a six-byte display-settings block:
LED enable, screen enable, LED brightness percent, screen brightness percent,
and two observed zero bytes. The 25/50/75/100% values and LED off/on were
captured with acknowledgements and device readback. dev21 adds four
disabled-by-default HA controls that preserve the whole block; screen and LED
brightness become unavailable whenever the corresponding switch is off.

Live testing of the installed dev21 build from HA confirmed screen off/on,
screen 25 -> 50 -> 25%, LED off/on, and LED 25 -> 50 -> 25%, including
matching binary/sensor readback. Each brightness Number correctly became
unavailable while its display was off. Both displays were restored to on at
25% after the test.

## dev22 idle readback correction (2026-08-25)

Live diagnostics captured two false failures after several idle hours. Both
`4.1=19` SETs received matching replies in under 100 ms, MQTT was connected,
and the delayed provider poll subsequently confirmed bitmask 19. dev21 had
required a new direct `241/44` report within five seconds and ignored that
authoritative provider result.

dev22 retains the direct path first, then performs bounded immediate provider
reads. Only a post-command raw snapshot containing the expected key/value can
confirm the write; merged cache values are excluded. Fresh already-matching
provider values avoid redundant SETs. Readback source counts are included in
privacy-safe diagnostics for the next live validation.

The installed build retained the fast path: two acknowledged same-state writes
were each confirmed by fresh direct readback within roughly 0.4-0.6 seconds.
Diagnostics showed two direct confirmations, zero provider/no-op confirmations,
and no active or pending delayed refresh. The PowerPulse direct path had been
awakened by the restart, so this run did not exercise provider-fallback
confirmation. The remaining live validation is tracked in the
[project backlog](backlog.md).

## dev23 extended idle confirmation and phase safety (2026-08-26)

The genuine idle test produced the evidence dev22 was designed to collect. The
fast `241/44` settings report was absent while MQTT remained connected. Fifteen
acknowledged HA writes were reported as unconfirmed between 00:05 and 00:19
local time. Mode and flag changes nevertheless appeared in HA roughly 12–15
seconds after their SETs, usually 3–6 seconds after dev22 had already returned
its error at about 9 seconds. Diagnostics also retained four successful provider
confirmations, proving that the fallback path works but has variable latency.

dev23 keeps the same strict post-command raw-key/value requirement and extends
the bounded provider checks through approximately 20 seconds. It additionally
records a 32-entry identifier-free attempt trace containing the retry number,
delay, refresh result, expected-key presence, post-command freshness, and match
result.

Phase selection is a separate case. Two HA phase SETs at 00:19:10 and 00:19:45
received replies in about 142 ms and 62 ms, but neither produced direct phase
readback or a normal phase-state change. The provider currently retains only
raw `phaseSpecified`; it does not supply the confirmed `phase_mode` expected by
the control. dev23 therefore separates general settings availability from phase
availability: provider-backed controls remain usable after idle, while phase is
available only during a fresh direct `241/44` phase report. Provider phase
mapping remains an explicit controlled-research item in the central backlog.

The installed dev23 manifest and HACS state both reported the new build. Its
fresh diagnostics contained the new empty `recent_provider_attempts` list. The
direct path awakened during restart and reported `phase_mode=one_phase` through
the Select, normal sensor, and raw field `1`. At least one earlier acknowledged
phase SET therefore did apply; dev22's failure was lack of confirmable readback,
not proof of device rejection. No setting was changed during this verification.

## dev24 direct-stream wake investigation (2026-08-26)

Live inspection separated three concurrent paths. The PowerPulse integration
held connected listen-only MQTT clients for the C376 and linked HJ31 without
reconnect attempts. A separate installed `ecoflow_energy` 1.18.0 entry ran in
Enhanced cloud-push mode for the HJ31, while the PowerOcean Modbus integration
used only local TCP port 502. Regular `96/97` EnergyStreamSwitch requests on the
HJ31 SET topic therefore cannot originate from the hard-listen-only PowerPulse
client or the local Modbus connection; the exact cloud publisher identity is
not carried by the shared MQTT topic.

The HA restart had reconnected both cloud integrations at nearly the same time,
so the subsequently revived C376 `241/44` stream does not yet prove whether a
C376 subscription, a PowerOcean initial request, or another cloud-session event
caused it. dev24 adds a narrower controlled experiment: a disabled-by-default
button renews only the C376 quota, property, and GET-reply subscriptions and
never calls an MQTT publish path. It records whether a new direct settings
report arrives within ten seconds. A companion diagnostic binary sensor exposes
stream freshness.

dev24 also classifies app GET topics as `observed_get` and retains them in a
separate bounded view so frequent property telemetry cannot evict the evidence.
Only safe JSON operation metadata or generic Protobuf routing fields survive;
raw GET bodies and request IDs are omitted. The required stale-stream live test
remains centralized in the project backlog.

Installed validation loaded HACS commit `875b532` and manifest version
`0.1.0-dev24`. The disabled-by-default connectivity sensor and reactivation
button were both present and were explicitly enabled in the entity registry.
After a targeted reload, the sensor reported a fresh direct stream and the
button was available. Its action was not invoked because the coordinator would
correctly classify that state as `already_active` without sending a new
SUBSCRIBE. The error log contained no new PowerPulse integration error after
the reload, and this verification did not publish a device command or alter a
charger setting.

The first genuine stale-stream experiment then separated subscription renewal
from app activity. The last direct report before the test was at
`04:04:03Z`. At `05:56:50Z`, the HA button renewed all three C376 read
subscriptions with local result code `0`, but no `241/44` arrived within ten
seconds and the recorded outcome was `no_direct_report`. Other C376 property
messages continued, so neither the MQTT connection nor all charger traffic was
asleep.

Opening only the PowerPulse overview in the official app, without changing a
setting or entering a settings page, restarted direct `241/44` reporting at
approximately `05:58:38Z`. The dedicated request capture remained empty and no
C376 SET appeared on the subscribed topics. HJ31 `96/97` traffic continued in
parallel, but that traffic was already known to be repetitive and its publisher
cannot be identified from the MQTT topic. The result therefore proves an
app-open side effect, but not whether its cause is the app's own MQTT session or
subscription, an unobserved topic, or an HTTP/backend request.

A second idle cycle narrowed the app action further. Opening only the general
EcoFlow home/device list, without selecting PowerPulse, restarted direct
`241/44` at approximately `08:52:06Z`. No C376 GET or SET was captured. HJ31
commands `96/114`, `96/22`, and `96/97` appeared from `08:52:11Z`, after the
first renewed direct report, so they cannot be treated as its trigger from this
timing alone. Heartbeat `2/33` updated phase voltage at `08:52:53Z`, about 47
seconds after `241/44`. The earlier app-open run showed the same ordering with
about 54 seconds between the two streams; the prior snapshot describing phase
voltage as still asleep was therefore only premature, not a lasting split.

The next safe discriminator is a full reconnect of only the C376 WSS client
with a new Client ID and normal subscriptions, while retaining the hard no-
publish guarantee. If that wakes both streams, a fresh client session is
sufficient; otherwise the missing action is app-specific or outside the
currently observed MQTT topics.

## dev25 C376 session-rebuild diagnostic (2026-08-26)

dev25 turns the next discriminator into a disabled-by-default manual diagnostic
instead of an automatic recovery policy. It fully replaces only the C376 Paho
WSS client, thereby generating a fresh Client ID, and restores the normal
passive subscriptions. The connection remains hard `listen_only`: reconnect
cannot publish `get-all`, `latestQuotas`, `EnergyStreamSwitch`, or a charger
command. Its bounded privacy-safe trace distinguishes `wss_reconnect` from the
already disproven `resubscribe` experiment and records the outcome and optional
time to a new `241/44` report.

The build also adds a separate disabled connectivity sensor for actual parsed
heartbeat `2/33` receipt, fresh for 90 seconds. This measures frame arrival
rather than waiting for phase voltage to change and allows the next idle test
to compare the two C376 report families directly. The live result remains an
open item only in `docs/backlog.md`.

The installed dev25 manifest and both new entity-registry entries were verified
in Home Assistant. Following a targeted integration reload, the direct sensor
was fresh and the heartbeat sensor became fresh on the next `2/33` cycle. The
manual reconnect action was not invoked in this non-stale state, its attempt
trace remained empty, and no new integration error appeared.

The first controlled stale-stream run then confirmed the missing mechanism.
Both `241/44` and heartbeat `2/33` freshness sensors were off before the test.
Pressing only the listen-only C376 WSS-reconnect action at
`12:05:08.416675Z`, with the official app closed and no setting change,
produced a new direct report after 1.779 seconds. The independent heartbeat
stream resumed by `12:05:13.424549Z`. The recorded outcome was
`wss_reconnect / confirmed`; both streams remained active afterward.

Therefore a new C376 cloud MQTT session with a fresh Client ID and normal
subscriptions is sufficient to wake these reports. Re-subscribing an existing
session is not. Because the client remains hard `listen_only`, this result does
not depend on `get-all`, `latestQuotas`, `EnergyStreamSwitch`, or a device SET.
The canonical backlog now carries the bounded automatic-recovery work.

## dev26 bounded automatic recovery (2026-08-26)

dev26 promotes only the confirmed fresh-session mechanism into automatic
recovery. It does not infer failure from an unchanged voltage: actual receipt
timestamps for both parsed `241/44` and `2/33` frames must exist, and both must
be at least five minutes old. The normal disconnected-client watchdog remains
separate.

An eligible attempt rebuilds only the C376 hard-listen-only WSS client and is
tagged `automatic_wss_reconnect` in the bounded trace. A 30-minute cooldown is
recorded before reconnect starts, so even a failed broker operation cannot run
again on the integration's 30-second polling interval. No new publish path or
device command is introduced. The next idle window must confirm the scheduler
and loop protection; that active validation is maintained only in the canonical
backlog.

Installed validation confirmed dev26, diagnostic schema 10, the exact
300-second/1,800-second limits, and an initially empty recovery trace. Both
report families were fresh after restart, correctly preventing an immediate
automatic reconnect. No new integration error was logged.

## dev27 direct display/LED readback (2026-08-27)

A live LED 75% -> 100% transition isolated the previously unassigned direct
`241/44 -> 1.4.8.21` block. It changed from
`[1, 0, 75, 25, 2, 0]` to `[1, 0, 100, 25, 2, 0]`, matching LED enabled,
screen disabled, LED brightness, and stored screen brightness. dev27 decodes
the first four bytes from this normal read-only report with strict length,
boolean, and four-level brightness validation. It introduces no MQTT publish
and restores the display/indicator entities after an integration restart
without an app settings write. Installed validation with the app closed showed
LED enabled at 100%, screen disabled with stored brightness 25%, and both
direct and heartbeat streams active. The screen-brightness control remained
unavailable as designed while the screen was off, while its read-only sensor
still exposed the stored 25% value.

## dev28 connected-vehicle evidence and charging interlocks (2026-08-27)

A real vehicle session confirmed the complete telemetry path at approximately
1.29 kW and 5.75 A. Heartbeat field 42 advanced to `19` after 59 seconds and
the completed first segment reached `451` after 21 min 08 s. Both observations
fit Wh at the measured power and strengthen the earlier `1815` versus 1.82 kWh
app comparison; the field remains raw pending the backlog's rounding check.

Official-app Stop at `17:24:34.365Z` and Start at `17:26:02.630Z` both used an
acknowledged `241/100` command addressed to the linked `HJ31` PowerOcean. Stop
was followed by `charge_complete`; Start created a new zeroed session and then
returned to approximately 1.29 kW. Schema 10 omitted both 25-byte bodies, so
dev28/schema 11 adds a privacy-safe structural inspector for that exact tuple.
The schema-11 repeat isolated protobuf field 2: value `1` stopped charging and
value `2` started it. The field-1 accessory descriptor was structurally
unchanged and remains opaque/redacted. Sequences 237 and 243 each received a
matching reply, while independent heartbeat reports confirmed
`charge_complete` and `charging` respectively. The selector is therefore ready
for a guarded HA implementation, but no Start/Stop control is exposed yet.

The app locked operating mode, phase selection, maximum output current, Solar
minimum current, and Continuous charging while active. It allowed
Plug-and-Play, battery-discharge blocking, screen, LED, and brightness.
Plug-and-Play and battery writes were acknowledged and read back without
interrupting charging, isolating shared flags `16 -> 18` and `18 -> 19 -> 18`.
dev28 enforces the five confirmed locks in both entity availability and the
backend write path; untested mode-specific cases remain in the canonical
backlog.

## dev29 guarded Start/Stop controls (2026-08-27)

dev29 turns the repeated `241/100` evidence into two disabled-by-default HA
buttons. Stop emits field 2 value `1`; Start emits value `2`; both preserve the
validated opaque field-1 accessory descriptor. Waiters are matched on the full
command tuple and sequence, and the acknowledgement cannot by itself report
success.

The backend requires a recent heartbeat and rechecks the current state while
holding the control lock. Start is blocked when unplugged and is confirmed only
by a newer `charging` or `paused` heartbeat. Stop is offered for `charging` or
`paused` and is confirmed only by a newer `plugged_in`, `charge_complete`, or
`standby` heartbeat. The confirmation window is 15 seconds. This implements the
known safe envelope.

The subsequent reversible HA test completed both directions. Stop at
`23:03:55.446Z` was confirmed by `charge_complete` at `23:03:56.975Z`. Start at
`23:04:13.425Z` was confirmed by `charging` at `23:04:17.769Z`, reset the
session, and returned to 1.304 kW, 5.77 A, and 233.3 V after one minute. Button
availability followed the physical state in both directions. `CTRL-01` is
therefore complete and has been removed from the canonical backlog.

## dev30 energy and duration entities (2026-08-28)

The accumulated live history resolves the remaining energy-scale questions.
Heartbeat field 9 rose from `1364918` to `1372690` across 357 samples without
a decrease, including several session resets. Its 21–22 unit/minute increase
at approximately 1.29 kW identifies the raw unit as Wh. Heartbeat field 42 is
also confirmed as per-session Wh by several independent power/time checks and
the EcoFlow app comparison. dev30 therefore adds enabled-by-default kWh energy
sensors for both fields while retaining the raw diagnostic entities. The
cumulative and per-session sensors use `state_class=total_increasing`; the
latter's resets coincide with new charging sessions.

The existing `session_duration_s` entity retains its entity identity and now
publishes numeric seconds with Home Assistant duration and measurement
metadata instead of preformatted text. Home Assistant is responsible for the
human-readable display unit.

Live validation loaded exact HACS commit `d8f07d5` with the integration in the
`loaded` state and no matching system-log entry. The normal/raw energy pairs
were `1372.926 kWh` / `1372926` and `0.343 kWh` / `343`. Their HA metadata was
energy, kWh, and total-increasing. The existing duration entity remained
present and reported numeric duration/measurement metadata; HA presented its
native 960 seconds in the selected hour unit as approximately `0.2667 h`.

## 0.1.0 release transition and branding (2026-08-28)

The live-validated dev30 implementation is promoted unchanged to the first
regular `0.1.0` release. Future versions use Semantic Versioning, with explicit
beta prereleases only when another test cycle is needed. The WIP status of this
document now refers to continuing protocol research rather than to the release
status of the integration.

The approved project icon is bundled locally at the required 256×256 and
512×512 sizes. It is an AI-assisted, product-specific illustration based on
the user-supplied PowerPulse 2 photo, with transparent outer corners and
restrained connection/energy accents designed for small UI presentation.

Candidate commit `4c94ab8` was then installed on Home Assistant Core 2026.8.3.
The integration loaded without a matching system-log error, configuration
validation passed, and HACS reported the exact commit with no pending update.
The remaining frontend-only visual confirmation is kept in the canonical
backlog rather than duplicated here.

The final annotated `v0.1.0` tag targets validation commit `4882e7c`, and the
public GitHub release includes the versioned installation ZIP. HACS refreshed
to the release channel and, after installation and a Home Assistant Core
2026.8.3 restart, reported installed and available version `v0.1.0` with no
pending update. The config entry was `loaded`; no PowerPulse-specific runtime
error appeared in the current startup log.

The user then visually confirmed the approved icon on Home Assistant's
**Devices & services** page. HACS 2.0.5 continued to display its generic
placeholder. This is consistent with the open upstream HACS local-brand proxy
gap and does not indicate a missing release asset. The only remaining branding
work is therefore the upstream-dependent `REL-01` entry in the canonical
backlog.

## Post-release phase confirmation check (2026-08-28)

A no-vehicle HA test changed the phase selector through Auto, one phase, three
phase, and back to Auto while the EcoFlow app remained closed. Each write was
acknowledged and confirmed by a fresh direct C376 settings report in roughly
one second. Direct field `1.4.8.7` again mapped `0/1/2` to
Auto/one-phase/three-phase.

This did not close the provider question. Runtime diagnostics counted six
direct confirmations and zero provider confirmations, and the installed
EcoFlow Energy diagnostic export did not include a usable live
`phaseSpecified` provider snapshot. `PHASE-01` therefore remains open and the
released phase control continues to require fresh direct readback.

The next unreleased diagnostic revision records direct `241/44`, parent
accessory provider, and device-detail provider phase observations separately.
It stores only source, field-presence flags, raw/mapped values when valid,
timestamps, and the four-character device prefix. The feature is deliberately
diagnostic-only: no entity, merge precedence, write confirmation, or safety
gate changes before the three provider values are independently validated.

The controlled Auto/one-phase/three-phase/Auto sequence additionally retained
16 direct frames per state. Across all 64 decoded frames, field `1.4.8.7`
followed `0/1/2/0`, while unassigned byte fields `1.4.8.5` and `1.4.8.9`
remained byte-identical. This excludes them as the direct phase selector but
does not establish their meaning; that research remains solely in `DATA-02`.

## One-phase power comparison (2026-08-29)

A connected-vehicle Solar-mode session provided simultaneous direct power,
voltage, and current samples plus provider `chargingPwr`. Across six changing
load samples the direct power remained about 2.8-3.0% below `voltage * current`.
At stable load, direct power was `1246.9 W`, provider `chargingPwr` was `1244 W`
(reported 26 seconds earlier), and `229.3 V * 5.62 A` was `1288.7 VA`. This
supports both reported power fields as real power and the simple product as
apparent power with a power factor near 0.97. Different 20-30-second provider
and roughly 60-second direct cadences explain misleading comparisons while
Solar output changes.

The controlled three-phase follow-up then produced `4070.7 W` at `231.6 V`
and `5.95 A`, followed by `4066.5 W` at `231.7 V` and `5.95 A`. Three times
voltage times current was `4134.1 VA` and `4135.8 VA`, corresponding to power
factors near `0.985` and `0.983`; provider `chargingPwr` was `4135 W` about 30
seconds before the first direct sample. Charging was stopped only for the phase
change and the original Auto plus charging state was restored afterward. This
completes the replacement-sensor question: the direct field is the appropriate
real-power sensor and a naive calculation would add an apparent-power estimate,
not a more accurate replacement. The provider field's exact real/apparent
semantics are not inferred from this time-offset comparison, especially because
the exposed phase voltage/current entities are maxima rather than per-phase
pairs. `DATA-07` is therefore closed without an implementation change.

## Mode-specific charging interlocks (2026-08-29)

Connected-vehicle tests completed the remaining Custom- and Smart-mode safety
matrix. The official app removes the 6-16 A Custom-current slider during an
active Custom session. During an active Smart session it also prevents changes
to ready-by time, target type, and the selected energy or distance value. The
released HA entities did not yet mirror all of those restrictions.

The `0.1.1-beta.1` implementation routes Custom current and every Smart setting
through the same fail-closed charging-state helper already used for mode,
phase, maximum current, Solar minimum current, and Continuous charging. This is
enforced both in entity availability and immediately before publishing, so a
direct service call cannot bypass the UI interlock. The full local suite passes
with 78 tests. The live validation that was pending at this point was completed
on 2026-08-30 and is summarized below.

## 0.1.1-beta.1 validation bundle (2026-08-29)

The beta packages two independently useful test blocks: privacy-safe,
source-separated phase observations and the completed Custom/Smart
charging-time interlocks. No provider phase mapping, charging-power source, or
runtime dependency on another EcoFlow integration is introduced. The release
keeps the standard custom-component archive layout and is intended for one
combined Home Assistant validation cycle before promotion to stable 0.1.1.

The published GitHub prerelease and its installation ZIP were hash-verified,
then HACS installed the explicit beta version. Home Assistant loaded the entry
after restart with both PowerPulse streams active and no matching integration
error. Stopped-state validation kept the Custom-current, maximum-current, and
phase controls available. The subsequent active-session results are recorded
below.

The new diagnostic separation produced a complete provider mapping from the
parent PowerOcean accessory report: raw `0`, `1`, and `2` aligned with fresh
direct Auto, one-phase, and three-phase readback. The device-detail report did
not contain the phase field. One deliberately repeated three-phase poll also
captured the slower provider path retaining the preceding one-phase value before
it advanced to `2`, validating the need for per-source timestamps and freshness
checks. The mapping is now established, but it is not yet used as a phase-write
fallback.

## Completed Custom and Smart interlocks (2026-08-30)

Live validation completed both charging-time safety branches at the lowest
practical load: one phase and a 6 A maximum. The Custom session lasted about
39 seconds and the Smart session about 44 seconds. During charging, mode,
phase, maximum current, the relevant mode-specific values, Solar minimum
current, and Continuous charging were unavailable. Plug-and-Play,
battery-discharge blocking, screen, LED, and both brightness controls remained
available, matching the established official-app behavior.

Direct service calls against unavailable Custom and Smart number entities
returned no state result. The Smart interval contained only its matched
`241/100` Start and Stop commands and no `241/102` settings publish. After the
test, Solar mode, automatic phase selection, and the 16 A maximum were restored;
Continuous charging remained enabled by user choice, with charging stopped and
power at 0 W. `SAFE-01` is complete and has been removed from the canonical
backlog.
