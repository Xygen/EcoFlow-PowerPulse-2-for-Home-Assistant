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
| `PHASE-01` | Research | Establish the provider `phaseSpecified` mapping through controlled app changes so phase writes can eventually be confirmed while the direct path sleeps. Until then dev24 exposes phase control only with fresh direct `phase_mode` readback. | Auto, one-phase, and three-phase changes isolate every provider value and agree with independent app/device state before provider phase confirmation is implemented. |
| `SAFE-01` | Partially delivered in dev28 | Complete the charging-time interlock matrix for mode-specific controls not exercised in Solar mode. dev28 already blocks the five live-confirmed settings (mode, phase, maximum current, Solar minimum current, Continuous) in availability and the backend, while leaving the app-confirmed Plug-and-Play, battery, screen, and LED controls usable. | Every remaining control has an idle/charging result; HA prevents every predictably invalid publish while retaining controls proven valid during charging. |
| `CTRL-02` | After `SAFE-01` | Investigate dynamic charging-current or power control during an active session separately from the stored maximum-current setting. | A captured official-app command, acknowledgement, physical readback, limits, and charging-state constraints are confirmed before exposing a control. |

## Telemetry and protocol research

| ID | Priority | Open work | Completion evidence |
| --- | --- | --- | --- |
| `DATA-02` | Research | Identify the remaining fast-report byte fields `5` and `9` through controlled one-setting-at-a-time comparisons. Fields `21` (display/LED block) and `31` (Smart settings) are resolved and are not part of this item. | Paired direct reports isolate any mapping, value range, and unit without relying on byte length or coincidence. |
| `DATA-03` | Research | Resolve the exact role of heartbeat field `17` and the remaining unassigned bits in `switchBits`. | Controlled changes isolate each value or bit; unknowns remain raw until then. |
| `DATA-04` | Research | Confirm the unit and scaling of `vehicleInfo.currentVehicleComsumption` across additional Smart targets or vehicles. | Multiple comparisons establish a consistent physical meaning and scale. |
| `DATA-05` | Needs additional operating states | Map additional charger states and `suspend_reason` values. | Captures pair each numeric value with an independently observed app/device state. |
| `DATA-06` | Design | Decide how to expose the three individual phase voltages and currents instead of only their current aggregate summary. | The HA entity model is documented, implemented, and tested without breaking existing unique IDs. |

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
