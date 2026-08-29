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

Current implementation baseline: `0.1.0`.

## Live validation and control safety

| ID | Priority | Open work | Completion evidence |
| --- | --- | --- | --- |
| `LIVE-01` | Next | Live-validate the extended dev23 provider-readback window after another genuine multi-hour idle period. | Mode, battery, and Continuous writes without fresh direct `241/44` readback are confirmed by post-command raw provider snapshots without a false HA failure; the new attempt trace identifies when the match arrived. |
| `STREAM-01` | Next idle window | Live-validate dev26 automatic recovery. It requires both streams to have been observed, waits until both are stale for five minutes, rebuilds only the listen-only C376 WSS session, and applies a 30-minute cooldown. | The `automatic_wss_reconnect` trace confirms restoration of both streams without app activity, manual action, device publish, or repeated reconnect loop. |
| `STREAM-02` | Research | Evaluate an idle-first strategy: allow the listen-only MQTT/WSS connection to sleep when the wallbox is unused and reactivate it on demand (for charging, a control request, or an app/session trigger), while clearly exposing the paused state and refreshing settings before writes. | A bounded design is validated against stale phase/settings readback, wake-up latency, control safety, and at least one real charging-session scenario before changing the default recovery behavior. |
| `PHASE-01` | Research; instrumentation staged | Establish the provider `phaseSpecified` mapping so phase writes can eventually be confirmed while the direct path sleeps. A 2026-08-28 HA sequence reconfirmed the direct mapping (`0` Auto, `1` one phase, `2` three phase) with roughly one-second device readback, but produced six direct and zero provider confirmations. Unreleased diagnostics now retain the direct, parent-accessory provider, and device-detail provider observations separately with timestamps; they still require installation and a controlled app sequence. Until the provider values are isolated, 0.1.0 exposes phase control only with fresh direct `phase_mode` readback. | Install the diagnostic build, then isolate Auto, one-phase, and three-phase provider values through controlled app changes and verify them against independent app/device state before provider phase confirmation is implemented. |
| `SAFE-01` | Partially delivered in dev28 | Complete the charging-time interlock matrix for mode-specific controls not exercised in Solar mode. dev28 already blocks the five live-confirmed settings (mode, phase, maximum current, Solar minimum current, Continuous) in availability and the backend, while leaving the app-confirmed Plug-and-Play, battery, screen, and LED controls usable. | Every remaining control has an idle/charging result; HA prevents every predictably invalid publish while retaining controls proven valid during charging. |
| `CTRL-02` | After `SAFE-01` | Investigate dynamic charging-current or power control during an active session separately from the stored maximum-current setting. | A captured official-app command, acknowledgement, physical readback, limits, and charging-state constraints are confirmed before exposing a control. |

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
