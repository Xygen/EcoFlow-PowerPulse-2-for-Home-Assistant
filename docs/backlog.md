# PowerPulse 2 project backlog

This is the **single authoritative list** of open work for this repository.
README files describe current scope, protocol documents retain evidence, and
the changelog records delivered changes; they must link here instead of keeping
parallel TODO or roadmap lists.

When an item is completed, remove it from this file, record the delivered change
in `CHANGELOG.md`, and add the supporting evidence to
`protocol_observations.md` and/or `issue_247_wip_report.md`. Every release must
review those two evidence documents; update `data_paths_overview.md` whenever a
path or field mapping changes.

Any upstream proposal must follow the upstream maintainer's chosen architecture.
This integration's direct C376 MQTT path with bounded PowerOcean HTTP fallback
is project evidence, not a prescription for another repository.

Current implementation baseline: `0.1.1-beta.1`.

## Live validation and control safety

| ID | Priority | Open work | Completion evidence |
| --- | --- | --- | --- |
| `LIVE-01` | Next | Live-validate the extended dev23 provider-readback window after another genuine multi-hour idle period. | Mode, battery, and Continuous writes without fresh direct `241/44` readback are confirmed by post-command raw provider snapshots without a false HA failure; the new attempt trace identifies when the match arrived. |
| `STREAM-01` | Next idle window | Live-validate dev26 automatic recovery. It requires both streams to have been observed, waits until both are stale for five minutes, rebuilds only the listen-only C376 WSS session, and applies a 30-minute cooldown. | The `automatic_wss_reconnect` trace confirms restoration of both streams without app activity, manual action, device publish, or repeated reconnect loop. |
| `STREAM-02` | Research | Evaluate an idle-first strategy: allow the listen-only MQTT/WSS connection to sleep when the wallbox is unused and reactivate it on demand (for charging, a control request, or an app/session trigger), while clearly exposing the paused state and refreshing settings before writes. | A bounded design is validated against stale phase/settings readback, wake-up latency, control safety, and at least one real charging-session scenario before changing the default recovery behavior. |
| `PHASE-01` | Mapping confirmed; implementation pending | Version `0.1.1-beta.1` isolated the parent PowerOcean accessory value against fresh direct readback while stopped: `0` Auto, `1` one phase, and `2` three phase. Forced provider polls preserved each selected state after the slower path caught up; the wallbox device-detail source omitted both raw and mapped phase fields. Phase control still requires fresh direct readback until the confirmed parent-accessory value is deliberately added as a fallback. | Implement parent-accessory provider phase confirmation without accepting absent/stale device-detail data, cover source precedence and freshness in tests, and live-validate a write after the direct path has slept. |
| `SAFE-01` | Beta idle validation complete; charging validation pending | Custom- and Smart-mode charging tests completed the app-side interlock matrix. Version `0.1.1-beta.1` blocks Custom current and all Smart setting keys in both entity availability and the backend. After installation, the stopped Custom-current, maximum-current, and phase controls remained correctly available. Smart idle validation still requires the app to republish its complete retained Smart block after restart. | During active Custom and Smart sessions, verify every locked HA entity is unavailable, direct service calls fail closed, and Plug-and-Play, battery, screen, LED, and brightness controls remain available. |
| `CTRL-02` | After `SAFE-01` | Investigate dynamic charging-current or power control during an active session separately from the stored maximum-current setting. | A captured official-app command, acknowledgement, physical readback, limits, and charging-state constraints are confirmed before exposing a control. |
| `CTRL-03` | Research | Determine whether a user-requested Stop remains persistent with Plug-and-Play and Solar Continuous charging enabled. During beta installation the charger was observed charging again after an earlier Stop and a Home Assistant restart, but the observation does not prove that the restart caused the resume. | Controlled Stop tests isolate Plug-and-Play, Continuous charging, elapsed time, and HA reload/restart while recording command, fresh heartbeat transitions, and any automatic resume before changing control semantics. |

## Telemetry and protocol research

| ID | Priority | Open work | Completion evidence |
| --- | --- | --- | --- |
| `DATA-02` | Research | Identify the remaining fast-report byte fields `5` and `9` through controlled one-setting-at-a-time comparisons. A 2026-08-28 Auto/one-phase/three-phase/Auto sequence produced 64 decoded direct frames: field `7` followed `0/1/2/0`, while fields `5` and `9` remained byte-identical in every state. They are therefore not the direct phase-selection field. Fields `21` (display/LED block) and `31` (Smart settings) are resolved and are not part of this item. | Paired direct reports isolate any mapping, value range, and unit without relying on byte length or coincidence. |
| `DATA-03` | Research | Resolve the exact role of heartbeat field `17` and the remaining unassigned bits in `switchBits`. | Controlled changes isolate each value or bit; unknowns remain raw until then. |
| `DATA-04` | Research | Confirm the unit and scaling of `vehicleInfo.currentVehicleComsumption` across additional Smart targets or vehicles. | Multiple comparisons establish a consistent physical meaning and scale. |
| `DATA-05` | Needs additional operating states | Map additional charger states and `suspend_reason` values. | Captures pair each numeric value with an independently observed app/device state. |
| `DATA-06` | Design | Decide how to expose the three individual phase voltages and currents instead of only their current aggregate summary. | The HA entity model is documented, implemented, and tested without breaking existing unique IDs. |
| `DATA-08` | Research | Investigate the EcoFlow app's historical charging-session report, which attributes delivered energy to PV, grid, and battery. Determine whether the data comes from the already observed `CHARGED_RECORD` family or a separate API/MQTT path, and evaluate a privacy-safe Home Assistant representation without assuming that historical records are live telemetry. | Controlled captures identify the request/response path, session identifier and timestamps, PV/grid/battery fields, units and scaling. Multiple sessions verify that the source contributions reconcile with the reported session energy before any entities, events, or statistics are designed. |
| `DIAG-01` | Design | Evaluate and selectively adapt the mature diagnostics patterns from `shuette42/ecoflow-energy-ha`: per-message-type long-term sampling, reserved SET/SET-reply capacity, received/retained/dropped counts, explicit truncation markers, an `app_writes_watched` indicator, connection-versus-data-freshness reporting, unknown-Protobuf-field summaries, and one final export-wide privacy-redaction pass. The installed EcoFlow Energy integration may be used through Home Assistant diagnostics as an optional independent observer during controlled research, but PowerPulse 2 must not depend on that integration at runtime. | A bounded design identifies which parts improve the existing PowerPulse 2 frame buckets without duplicating its current command correlation and redaction. Tests prove memory bounds, preservation of rare reports and writes, privacy-safe length-preserving masking, truthful empty-capture metadata, and standalone operation when EcoFlow Energy is absent. |

## Home Assistant entity model

| ID | Priority | Open work | Completion evidence |
| --- | --- | --- | --- |
| `ENTITY-01` | High | Review generic sensor availability semantics tracked in issue #4 so a temporarily absent field becomes `unknown` where appropriate instead of making a healthy charger entity `unavailable`. | Tests distinguish healthy value, healthy-but-missing field, and genuinely unavailable coordinator/source states without introducing stale-value ambiguity. |
| `ENTITY-02` | High | Complete the entity-metadata cleanup tracked in issue #5: add missing native device classes/unit constants, classify screen/LED controls as configuration where appropriate, and review measurement state classes. | Entity descriptions use Home Assistant-native metadata consistently; UI grouping and units are verified without changing protocol semantics or existing unique IDs. |
| `ENTITY-03` | After control validation | Reduce duplicate read-only and control entities as tracked in issue #6 once the corresponding controls are stable enough to act as canonical setting entities. | One canonical entity represents each validated setting where practical, raw diagnostics remain available, migrations preserve existing installations, and charging status + charging binary sensor remain intentionally separate. |

## Deferred and release work

| ID | Priority | Open work | Completion evidence |
| --- | --- | --- | --- |
| `REL-01` | Upstream HACS frontend | Track HACS support for Home Assistant's authenticated local-brand proxy. The approved icon is confirmed visible under HA 2026.8.3 **Devices & services**, but HACS 2.0.5 still shows its placeholder because its downloads view uses the legacy public Brands CDN (upstream `hacs/integration#5223` and `#5402`). Do not duplicate or relocate the valid integration-local assets as a workaround. | A released HACS frontend uses the authenticated local-brand endpoint and visibly shows the bundled PowerPulse 2 icon without repository changes. |
| `PROTO-01` | Later | Investigate OCPP control only after the core PowerPulse controls and safety interlocks are stable. | Scope and protocol evidence are explicitly approved before implementation. |
