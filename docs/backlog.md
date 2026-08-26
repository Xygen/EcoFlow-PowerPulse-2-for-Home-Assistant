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

Current implementation baseline: `0.1.0-dev26`.

## Live validation and control safety

| ID | Priority | Open work | Completion evidence |
| --- | --- | --- | --- |
| `LIVE-01` | Next | Live-validate the extended dev23 provider-readback window after another genuine multi-hour idle period. | Mode, battery, and Continuous writes without fresh direct `241/44` readback are confirmed by post-command raw provider snapshots without a false HA failure; the new attempt trace identifies when the match arrived. |
| `STREAM-01` | Next idle window | Live-validate dev26 automatic recovery. It requires both streams to have been observed, waits until both are stale for five minutes, rebuilds only the listen-only C376 WSS session, and applies a 30-minute cooldown. | The `automatic_wss_reconnect` trace confirms restoration of both streams without app activity, manual action, device publish, or repeated reconnect loop. |
| `PHASE-01` | Research | Establish the provider `phaseSpecified` mapping through controlled app changes so phase writes can eventually be confirmed while the direct path sleeps. Until then dev24 exposes phase control only with fresh direct `phase_mode` readback. | Auto, one-phase, and three-phase changes isolate every provider value and agree with independent app/device state before provider phase confirmation is implemented. |
| `CTRL-01` | Blocked by vehicle availability | Capture and implement Start and Stop separately, both without a connected vehicle and with one connected. | Official-app request/reply frames, exact target attribution, independent charger-state readback, and reversible HA tests distinguish unplugged, plugged-in, charging, paused, completed, and rejected outcomes where observed. |
| `SAFE-01` | Blocked by vehicle availability | Establish the charging-time interlock matrix for every writable setting. Operating mode and phase selection are already known to be locked while charging; the remaining controls are unclassified. | Each control has an idle/charging result and HA prevents predictably invalid MQTT publication through availability or local validation. |
| `CTRL-02` | After `SAFE-01` | Investigate dynamic charging-current or power control during an active session separately from the stored maximum-current setting. | A captured official-app command, acknowledgement, physical readback, limits, and charging-state constraints are confirmed before exposing a control. |

## Telemetry and protocol research

| ID | Priority | Open work | Completion evidence |
| --- | --- | --- | --- |
| `DATA-01` | Next non-zero sessions | Confirm whether heartbeat field `42` is session energy in Wh and determine its rounding across multiple sessions. | Several app/session comparisons support a stable unit and scaling; only then add a normal kWh entity while retaining raw diagnostics. |
| `DATA-02` | Research | Identify fast-report byte fields `5`, `9`, and `21` through controlled one-setting-at-a-time comparisons. Field `21` is the leading screen/LED candidate; Smart field `31` is already resolved and is not part of this item. | Paired direct reports isolate any mapping, value range, and unit without relying on byte length or coincidence. |
| `DATA-03` | Research | Resolve the exact role of heartbeat field `17` and the remaining unassigned bits in `switchBits`. | Controlled changes isolate each value or bit; unknowns remain raw until then. |
| `DATA-04` | Research | Confirm the unit and scaling of `vehicleInfo.currentVehicleComsumption` across additional Smart targets or vehicles. | Multiple comparisons establish a consistent physical meaning and scale. |
| `DATA-05` | Needs additional operating states | Map additional charger states and `suspend_reason` values. | Captures pair each numeric value with an independently observed app/device state. |
| `DATA-06` | Design | Decide how to expose the three individual phase voltages and currents instead of only their current aggregate summary. | The HA entity model is documented, implemented, and tested without breaking existing unique IDs. |

## Deferred and release work

| ID | Priority | Open work | Completion evidence |
| --- | --- | --- | --- |
| `REL-01` | Before first non-`-dev` release | Create and bundle a dedicated, original PowerPulse 2 Home Assistant integration icon. | Required HA/HACS sizes are present in the release and visibly verified in Home Assistant. |
| `PROTO-01` | Later | Investigate OCPP control only after the core PowerPulse controls and safety interlocks are stable. | Scope and protocol evidence are explicitly approved before implementation. |
