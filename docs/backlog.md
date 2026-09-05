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

Current implementation baseline: `1.0.0`.

## Live validation and control safety

| ID | Priority | Open work | Completion evidence |
| --- | --- | --- | --- |

## Telemetry and protocol research

| ID | Priority | Open work | Completion evidence |
| --- | --- | --- | --- |

## Deferred and release work

| ID | Priority | Open work | Completion evidence |
| --- | --- | --- | --- |
| `PHASE-01` | Known limitation accepted for `v1.0.0` | Normal Direct phase selection and source separation are validated. A stale Direct `241/44` stream was not reproducible while the car was connected and the stopped wallbox continued to emit fresh Direct reports, so the provider-fallback transition and provider-already-at-target edge case remain unvalidated. The implementation remains fail-closed. | Live `auto → one_phase → auto` test on 2026-09-05 produced fresh Direct readback `raw 1` and `raw 0`; no unverified behavior or relaxed safety gate is introduced. Reopen only with a reproducible stale-Direct condition. |
| `SAFE-02` | Deferred after v1.0.0 | Paused Solar policy remains documented as a known limitation; no behavior change is required for v1.0.0. | Reopen only with controlled equivalent PV/battery conditions and paired App/HA evidence. |
| `CTRL-02` | Deferred after v1.0.0 | Dynamic active-session current/power control remains research-only. | Reopen only with an official-app capture, acknowledgement and physical readback. |
| `STREAM-02` | Deferred after v1.0.0 | Idle-first transport optimization is outside the v1.0.0 scope. | Reopen only with bounded wake-up, freshness and safety validation. |
| `DATA-02` | Deferred after v1.0.0 | Unknown fast-report fields 5 and 9 remain diagnostic-only. | Reopen only with paired state/setting captures. |
| `DATA-04` | Deferred after v1.0.0 | Smart vehicle-consumption semantics remain unresolved and are not required by current controls. | Reopen only with controlled comparisons across vehicle profiles. |
| `DATA-05` | Deferred after v1.0.0 | State labels are mapped; numeric `suspend_reason` semantics remain unresolved. | Reopen only with a fresh numeric reason paired to an independent device state. |
| `DATA-06` | Deferred after v1.0.0 | Aggregate phase telemetry remains supported; positional phase entities are deferred. | Reopen only after ordered multi-state field 29/30 captures. |
| `DATA-08` | Deferred after v1.0.0 | Historical PV/grid/battery session attribution is not part of the stable release. | Reopen only after identifying and reconciling the historical report path. |
| `DATA-10` | Deferred after v1.0.0 | Broad PowerOcean field completeness research is deferred. | Reopen only for a specifically scoped, privacy-reviewed field set. |

`DATA-09` is complete: a 2026-09-05 session ended cleanly, the next HA
Start reset both Direct and PowerOcean session energy/duration to `0`, and the
PowerOcean entities continued reporting while the separate `EcoFlow Energy`
integration was disabled. The existing Direct entity IDs remained unchanged.

## v1.0.0 release record

The `1.0.0` release meets this gate: every v1.0.0 item in this backlog is either closed
with evidence or explicitly recorded as a known limitation, the existing test
suite passes, the manifest and documentation consistently identify `1.0.0`,
and the release contains no unverified new controls or guessed field mappings.
