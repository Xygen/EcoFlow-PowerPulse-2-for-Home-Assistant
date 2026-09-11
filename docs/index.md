# PowerPulse 2 documentation

Current stable release: `1.0.4`.

Use this page as the entry point. It separates current product documentation
from the evidence archives created during protocol research.

## Current references

| Need | Source of truth |
| --- | --- |
| Install, configure, and use the integration | [User guide](user-guide.md) |
| Prepare a Smart draft and distinguish it from device settings | [Smart charging plans](user-guide.md#preparing-and-using-a-smart-charging-plan) |
| Choose a charging-power source for an automation | [Power readings and freshness limits](user-guide.md#choosing-a-power-reading) |
| Confirm supported entities, sources, and control safety | [Data-path overview](data_paths_overview.md) |
| Review test coverage, live validation, and release readiness | [Validation status](validation.md) |
| Work through the open acceptance steps in one pass | [Abnahmeliste](acceptance_checklist.md) |
| See active, deferred, and release work | [Project backlog](backlog.md) |
| Understand why the project works the way it does | [Decision log](decisions.md) |
| See how the two agents divide and hand over work | [Collaboration model](collaboration.md) |
| Review delivered changes | [Changelog](../CHANGELOG.md) |
| Review the 2026-09-09 integration audit | [Dated review](review_2026-09-09.md); planned work remains in the [backlog roadmap](backlog.md#roadmap-bis-version-20) |

## Evidence and research archives

These documents preserve the reasoning behind the implementation. Historical
versions, intermediate hypotheses, and superseded plans are expected here and
must not be read as the current product contract.

| Topic | Archive |
| --- | --- |
| Captured frames, field mappings, and live observations | [Protocol observations](protocol_observations.md) |
| Original upstream Issue #247 investigation | [Issue #247 WIP report](issue_247_wip_report.md) |
| Phase-control readback design | [PHASE-01 analysis](phase_control_analysis.md) |
| Entity model decisions | [ENTITY-03 analysis](entity_model_analysis.md) |
| Diagnostic capture design | [DIAG-01 analysis](diagnostics_analysis.md) |
| Phase measurement research | [DATA-06 analysis](phase_measurement_entities_analysis.md) |
| Smart-mode bootstrap research | [SMART-01 analysis](smart_mode_bootstrap_analysis.md) |
| Start/Stop readback and timeout analysis | [Issue #12 analysis](issue_12_charge_readback_analysis.md) |
| Bounded stream timeline: first readings, and the captured stall | [2026-09-11 observation](stream_timeline_observation_2026-09-11.md) |
| Authentication failure and re-authentication analysis | [Issue #16 analysis](issue_16_auth_analysis.md) |

## Documentation status and resolved contradictions

| Finding | Resolution |
| --- | --- |
| README named `0.1.1-beta.6`; the manifest and active backlog named `0.1.1-beta.8`. | Resolved before `1.0.0`; documents were aligned to `1.0.0` at that time. The current stable release is identified above. |
| README said phase control required fresh Direct `241/44` only. | It now describes the implemented, source-qualified Parent-Accessory fallback and links its remaining validation to `PHASE-01`. |
| The data-path overview both decoded field `21` as the display block and called it unassigned. | Field `21` is now consistently documented as the confirmed six-byte display block; only fields `5` and `9` remain unresolved. |
| Chronological records looked like current product documentation. | Protocol and Issue #247 files are explicitly labelled as evidence archives; this index points to the current references. |

## Maintenance rules

- Update the user guide and data-path overview when shipped behavior changes.
- Update validation status after a bounded test or live confirmation.
- Keep open and deferred work only in the backlog.
- Preserve evidence archives; label later findings rather than rewriting past
  observations as if they were current facts.
- Record a decision that shapes how the repository is built in the
  [decision log](decisions.md), and keep it pointing at the document that
  carries it in full.
- Write in English. Existing German passages are rewritten in English when
  they are edited for another reason, not converted for their own sake.
