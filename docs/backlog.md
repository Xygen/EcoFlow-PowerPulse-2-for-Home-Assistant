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

Current implementation baseline: `0.1.1-beta.8`.

## Live validation and control safety

| ID | Priority | Open work | Completion evidence |
| --- | --- | --- | --- |
| `PHASE-01` | Implemented in `0.1.1-beta.5`; partial live validation | Phase availability now prefers fresh valid `241/44` evidence and otherwise accepts only a fresh, explicit `provider_parent_accessory` raw value `0/1/2`; device-detail and unattributed merged values cannot qualify. Phase bypasses generic Provider No-op. Post-write Provider confirmation requires a source-qualified transition from a different pre-write phase to the target; an already-at-target cache cannot confirm. A newer post-write `241/44` remains authoritative, while `2/34` is separately diagnosed but not used for confirmation. Installed smoke validation and the 2026-09-02 live test confirmed the source separation, normal Direct write/readback in both directions, and safe restore. See [`docs/phase_control_analysis.md`](phase_control_analysis.md). | Still require a live test with stale `241/44`: capture the successful SET/reply path and Parent-Accessory catch-up from a different pre-value to the target. Separately test the provider-already-at-target edge case and confirm it publishes rather than No-ops and stays fail-closed without new Direct evidence. Verify charging-state/transport gates and bounded retries remain unchanged; then remove this item. |

## Telemetry and protocol research

| ID | Priority | Open work | Completion evidence |
| --- | --- | --- | --- |
| `DATA-09` | Implemented in `0.1.1-beta.8`; partial live validation | Preserve the original CP307 heartbeat telemetry under consistently named `Wallbox direct` entities and expose the coherent PowerOcean session subset under separate `PowerOcean` entities. Current reporter evidence identifies `241/3` as the PowerPulse 2 (`C376`) accessory-relay path; the equivalent `209/8` form is also decoded. Both require an exact charger-serial match and map only native status, power, session energy and duration; vehicle IDs are discarded and the new path cannot overwrite existing entity unique IDs. The 2026-09-02 charging-session samples confirmed all four PowerOcean entities from this integration, separate source-prefixed unique IDs, and independent in-session progress. A later active-session sample differed by `77 W` (`1285.0 W` Direct versus `1362 W` PowerOcean); the user observed that the PowerOcean value exactly matched the official app display. The sources must therefore remain distinct and must not be presented as interchangeable. | Let this or a later session end and verify a coherent reset for the next session. Then test that the four entities continue to work with the separate EcoFlow integration disabled; confirm the established Direct entity IDs remain unchanged and update independently. |

## Deferred and release work

| ID | Priority | Open work | Completion evidence |
| --- | --- | --- | --- |
| `SAFE-02` | Deferred after v1.0.0 | Paused Solar policy remains documented as a known limitation; no behavior change is required for v1.0.0. | Reopen only with controlled equivalent PV/battery conditions and paired App/HA evidence. |
| `CTRL-02` | Deferred after v1.0.0 | Dynamic active-session current/power control remains research-only. | Reopen only with an official-app capture, acknowledgement and physical readback. |
| `STREAM-02` | Deferred after v1.0.0 | Idle-first transport optimization is outside the v1.0.0 scope. | Reopen only with bounded wake-up, freshness and safety validation. |
| `DATA-02` | Deferred after v1.0.0 | Unknown fast-report fields 5 and 9 remain diagnostic-only. | Reopen only with paired state/setting captures. |
| `DATA-04` | Deferred after v1.0.0 | Smart vehicle-consumption semantics remain unresolved and are not required by current controls. | Reopen only with controlled comparisons across vehicle profiles. |
| `DATA-05` | Deferred after v1.0.0 | State labels are mapped; numeric `suspend_reason` semantics remain unresolved. | Reopen only with a fresh numeric reason paired to an independent device state. |
| `DATA-06` | Deferred after v1.0.0 | Aggregate phase telemetry remains supported; positional phase entities are deferred. | Reopen only after ordered multi-state field 29/30 captures. |
| `DATA-08` | Deferred after v1.0.0 | Historical PV/grid/battery session attribution is not part of the stable release. | Reopen only after identifying and reconciling the historical report path. |
| `DATA-10` | Deferred after v1.0.0 | Broad PowerOcean field completeness research is deferred. | Reopen only for a specifically scoped, privacy-reviewed field set. |

## v1.0.0 release gate

The release is ready when the active items `PHASE-01` and `DATA-09` are either
closed with evidence or explicitly recorded as known limitations, the existing
test suite passes, the manifest and documentation consistently identify
`1.0.0`, and the release contains no unverified new controls or guessed field
mappings.
