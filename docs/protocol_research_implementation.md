# Protocol research implementation report

Date: 2026-10-04. Version: `1.0.6-beta.1` → `1.0.6-beta.2`.
Code and portable verification are complete. Installation, live action visibility
and hardware acceptance are tracked in the [canonical backlog](backlog.md#telemetry-and-protocol-research).
No integration installation, device command, hardware test or release publication
was performed during implementation.

## Actions and safety boundaries

All action names below use the `ecoflow_powerpulse2` domain. Each action requires
one registry `device_id` and explicit boolean `confirm_protocol_test: true`.
No generic raw-write service exists.

| Action | Exact fields | Research-only bypass |
| --- | --- | --- |
| `protocol_test_solar_minimum_field_only` | `{4: amps * 10}` | Solar/Continuous enablement restriction and normal fields 1/2 bundle. Idle gate retained; only explicitly expected Solar/Fast is permitted. |
| `protocol_test_custom_current_field_only` | `{6: amps * 10}` | Custom-mode restriction and normal field 2 bundle. Idle gate retained; only explicitly expected Solar/Fast is permitted. |
| `protocol_test_phase_while_charging` | `{5: 0/1/2}` | Production phase charging lock, only for fresh confirmed active charging. Qualified phase evidence and actual configured transition remain required. |

Normal entity availability, normal control methods, `CHARGING_LOCKED_SETTING_KEYS`,
`control_allowed_for_status()`, `charging_sensitive_control_available()`,
`phase_control_available()` and `_validate_setting_write()` retain their gates.
Normal Solar still requires Solar + Continuous ON, Custom still requires Custom,
and Phase remains blocked while charging. Existing normal companion payloads,
phase transition rules and provider fallback/no-op behavior are preserved.

Research uses the same `_control_lock`, revalidates after acquiring it, requires
the existing accessory descriptor and exactly one qualified connected PowerOcean
route, and uses the common payload/publish/SET-reply executor. Research never uses
the normal provider no-op or provider confirmation fallback. A matching SET reply
and newer direct `241/44` target/required companion evidence are both required.
Unexpected enforced companion changes raise errors without rollback. Physical
phase observation is bounded to 15 seconds and distinguishes insufficient fresh
telemetry from an unchanged phase. No background timer, polling, MQTT connection,
recorder entity or persistent storage was added. History is bounded to 20 tests,
with prefixes instead of full serials, and optional HA response data is supported.

## Changed files

Paths are relative to the repository root. New files are marked **new**.

- `custom_components/ecoflow_powerpulse2/__init__.py`: global registration from `async_setup()`.
- `custom_components/ecoflow_powerpulse2/services.py` **new**: strict schemas, registry/loaded-entry resolution, handlers and optional responses.
- `custom_components/ecoflow_powerpulse2/services.yaml` **new**: restricted device selector, values and explicit confirmation.
- `custom_components/ecoflow_powerpulse2/protocol_research.py` **new**: narrow guards, direct confirmation, invariants, physical observation and bounded history.
- `custom_components/ecoflow_powerpulse2/coordinator.py`: shared transaction executor and bounded history initialization; reply waiters cleaned on failure/cancellation.
- `custom_components/ecoflow_powerpulse2/diagnostics.py`: research history included in existing sanitized export.
- `custom_components/ecoflow_powerpulse2/manifest.json`: beta revision increment.
- `custom_components/ecoflow_powerpulse2/strings.json`: canonical English action/field descriptions.
- `custom_components/ecoflow_powerpulse2/translations/en.json`: matching English descriptions.
- `custom_components/ecoflow_powerpulse2/translations/de.json`: matching German descriptions.
- `tests/test_protocol_research.py` **new**: 84 portable cases using real coordinator locks, trackers, payload encoder and real voluptuous schemas.
- `tests/test_coordinator_transactions.py`: additional HA validation-exception boundary stub; existing assertions unchanged.
- `ha_tests/test_protocol_research_services.py` **new**: six real-HA cases for global registration, validation errors and translation loading.
- `requirements_test.txt`: voluptuous for actual action-schema validation.
- `CHANGELOG.md`: beta changes and pending hardware acceptance.
- `docs/backlog.md`: current candidate and canonical acceptance item.
- `docs/data_paths_overview.md`: separate research route and direct-only confirmation semantics.
- `docs/protocol_observations.md`: exact payloads, restrictions and separate manual experiment plan.
- `docs/validation.md`: local evidence and pending runtime/hardware acceptance.
- `docs/protocol_research_implementation.md` **new**: this report.

## Verification

Local Windows/Python 3.12 verification on 2026-10-04:

```powershell
.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp='C:\Users\User\Documents\Codex\PowerPulse2\.venv\protocol-research-pytest-20261004c'
# 595 passed in 23.13s
.venv\Scripts\python.exe -m ruff check custom_components tests scripts ha_tests
# All checks passed!
.venv\Scripts\python.exe scripts/check_consistency.py
# Version, translation and local Markdown checks passed.
git diff --check
# Passed.
```

The full pytest suite includes all existing production safety/serialization
regressions and the 84 new cases. New tests cover exact field-only frames,
explicit confirmation, range/mode/state rejection, stale direct evidence,
provider echoes and no-op suppression, pre-command versus post-command evidence,
unexpected companions, queued mutable-state checks, active-session phase guards,
physical observations and session termination, bounded private history, failed
publishes, reply timeout, device/entry ambiguity and strict service schemas.

Windows sandbox ACLs prevented pytest's temporary directories from being read.
The final successful suite ran outside that sandbox using a fresh dedicated
temporary directory; no production safety test was skipped or rewritten.

The isolated real-HA suite requires Linux/Python 3.14 and was not executable in
this local Windows/Python 3.12 environment (no WSL distribution is available).
Its six new cases and existing `ha_tests` remain for the configured CI job.
Hassfest/HACS checks also remain CI checks. There is no separate type-checker
command configured in the repository workflow.

## Interpretation limits

`unexpected_companion_change` is the single canonical side-effect outcome.
Missing newer companion evidence cannot establish unchanged invariants. A newer
direct target mismatch at timeout is recorded as `device_rejected`; this describes
failed settings acceptance and does not claim a decoded negative SET-reply code.
No physical phase change observed during the bounded window proves only that
window's observation, not that Stop/Start is required. Existing aggregate direct
phase current is recorded when available; positional phase currents are not added.
No firmware support is claimed until the separately initiated hardware captures
establish it.
