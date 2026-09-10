# PowerPulse 2 validation status

This page records current, release-relevant validation. Historical test detail
and raw chronology remain in the evidence archives linked from the
[documentation index](index.md).

## Current baseline

The current stable release is `1.0.4`; README, index and user guide describe that
baseline. Its scope and accepted limitations are recorded in the
[release record](backlog.md#v100-release-record). PowerOcean idle qualification
was added in `1.0.4`; its vehicle-backed transition validation remains pending.

Separately, on 2026-09-09, HACS and the runtime diagnostics confirmed the installed
test build `1.0.5-beta.1` for [PR #22](https://github.com/Xygen/EcoFlow-PowerPulse-2-for-Home-Assistant/pull/22).
Its display test restored brightness from 100 to 75 to 100 percent with two
Direct confirmations and unchanged companion values. That is a dated partial
test, not a stable release or a completed vehicle-backed acceptance. The
documentation update for Issue #20 made no new installation or device change.

The `1.0.5-beta.2` candidate combines the same PR #22 control safety with the
PR #28 stream timeline and current documentation/CI. PR #23 is not included.
Deployment and runtime acceptance are recorded separately from build validation.

## Confirmed behavior

### Unreleased control transaction hardening

[V2-SAFE-01 / Issue #14](https://github.com/Xygen/EcoFlow-PowerPulse-2-for-Home-Assistant/issues/14)
is locally implemented and tested on 2026-09-09: 193 tests pass, including
31 new transaction tests importing the complete coordinator with real locks,
observation trackers and payload builders. HA services and network replies are
test doubles; these tests do not establish installed HA or vehicle behavior.
Coverage includes queued charging/freshness/transport changes, mode and enablement
changes, concurrent flags/display edits, active Smart companions and local drafts.
Review reproduced six cases where newer contradictory mode, enablement or flag
evidence from a lower-priority source was ignored. Control preparation now rejects
these conflicts; ordinary observation display retains its existing source priority.

Partial live acceptance: test build `1.0.5-beta.1`, commit `d2fc314`, installed
through HACS and loaded after restart. The restart call returned HTTP 504, but
subsequent integration and runtime manifest queries confirmed recovery. Screen
brightness changed 100 → 75 → 100 %, preserving LED brightness at 25 % and both
display switches on. Diagnostics recorded two confirmed SET replies, two Direct
readbacks, zero provider confirmations and zero no-ops. The final state was restored.
The ZIP's 45 files matched the source tree; SHA256:
`E8E393E188500B9132226D903D0F0931C120811026E6A1F09FB00A878728A04F`.

Vehicle-backed acceptance remains open in the [central backlog](backlog.md#roadmap-bis-version-20):
the charger reported `unplugged`, so rejection of a queued sensitive write after
actual charging starts has not been live-tested. Local concurrency tests do not
replace that evidence. PR #22 and Issue #14 remain open.
General readback source atomicity and provider no-op qualification remain the
separate scope of [Issue #15](https://github.com/Xygen/EcoFlow-PowerPulse-2-for-Home-Assistant/issues/15).

### Released baseline

| Area | Confirmed evidence | Status |
| --- | --- | --- |
| Direct telemetry | Charging state, power, voltage/current summaries, cumulative energy, session energy, and duration are decoded from direct heartbeat reports. | Confirmed |
| PowerOcean telemetry | Status, power, session energy, and session duration are decoded from the serial-matched `241/3` / compatible `209/8` report. A new session reset both source-specific energy/duration pairs to `0`, and the entities continued reporting with `EcoFlow Energy` disabled. | Confirmed |
| Qualified PowerOcean charging power | Fresh Direct `charging` preserves the fast PowerOcean power; fresh Direct idle states produce `0 W`; stale or unmapped Direct state produces `unknown`. All branches are unit-tested and the entity loaded in HA. | Vehicle-backed transition pending |
| Settings controls | Confirmed app routes, acknowledgement correlation, and qualified readback are required before HA reports success. | Confirmed |
| Start/Stop | Stop persistence with Plug-and-Play and Continuous charging, plus an app-closed Start confirmed after 22.8 seconds, were live-validated. | Confirmed |
| Phase control | Direct evidence, source separation, normal `auto → one_phase → auto` writes/readback, and safe restore were live-validated. | Confirmed with stale-Direct fallback accepted as a known limitation |
| Diagnostics | Privacy-safe capture schema and bounded diagnostics export were installed and validated. | Confirmed |

## Known v1.0.0 limitation

| Item | Needed evidence | Outcome if unavailable before release |
| --- | --- | --- |
| `PHASE-01` | Stale-Direct phase write with a qualified Parent-Accessory transition; provider-already-at-target edge case. | Accepted v1.0.0 limitation; retain fail-closed behavior and reopen only with a reproducible stale stream. |

## Pending live validation

| Item | Test when a vehicle is available | Passing result |
| --- | --- | --- |
| `ISSUE-13` | Observe the raw and qualified PowerOcean power during active charging, then with the cable connected but Direct reporting an idle state. Preserve the raw entities and do not write a charger setting. | During charging, the qualified entity follows the fast PowerOcean power. During a fresh Direct-idle interval, it is `0 W` even if the raw PowerOcean entity is non-zero. |

## Automated repository checks

The `Validate` workflow runs on pushes, pull requests, the daily schedule and
manual dispatch. `quality` uses Python 3.12 and runs pytest, Ruff over
`custom_components`, `tests` and `scripts`, and `scripts/check_consistency.py`.
The existing `validate-hacs` and `validate-hassfest` jobs remain in place.
Python setup follows the [official setup-python guidance](https://github.com/actions/setup-python).

The consistency checker runs offline. It compares translation leaf keys against
`strings.json`, validates local Markdown links/images (including reference links)
and heading anchors in root documents and `docs/`, and checks explicit
`Current stable release` declarations in README/index against the newest stable
changelog entry. The newest dated changelog entry must match the manifest, including
prereleases; a tag run additionally requires `v` plus the manifest version.
Historical version mentions are not treated as current declarations. External URLs
are not fetched. Fenced code and inline code examples are not treated as links.

Before merge/release, require green `quality`, `validate-hacs` and
`validate-hassfest` checks for the exact intended revision. Each quality run records
the checked Git SHA in its summary. Pull-request runs check GitHub's merge revision;
after a merge or any further edit, the resulting commit/tag needs its own green run.
An earlier green branch revision is not release evidence. These are documented
gates; branch protection/rulesets are not changed by this workflow implementation.

Local equivalents:

```shell
python -m pip install -r requirements_test.txt
python -m pytest -q
python -m ruff check custom_components tests scripts
python scripts/check_consistency.py
```

For Issue #17, 170 tests pass on the independent main-based branch (2026-09-10).
Negative fixtures verify rejection of failed assertions, undefined Python names,
wrong current versions/tags, missing/extra translation keys, missing files and
missing heading anchors. The larger suites on the separate #14/#15 branches are
not part of this branch. No device or Home Assistant deployment is involved.

## Stream timeline diagnostics

The unreleased Issue #19 implementation exposes
`data.passive_settings_refresh.stream_timeline` in integration diagnostics.
It records MQTT connected/disconnected callbacks, recovery eligibility reasons,
automatic attempts/results and WSS reconnect outcomes. Each entry includes a
runtime-local source alias and role, settings/heartbeat ages and freshness,
connection state and remaining automatic cooldown. It stores no message text,
topics, packet payloads, credentials or full device identifiers.

Recovery checks are recorded when the reason, connectivity or freshness changes,
and otherwise at most once every 300 seconds per charger. Connection and attempt
events are not coalesced. The shared ring retains at most 2,048 entries; its
`dropped_events` counter discloses eviction. It is **current-runtime only**:
`started_at` marks coordinator construction, not HA boot. Reload/restart clears
the ring. Source aliases are distinct within this runtime and are not stable
across reloads. Export before restarting; retention is a count limit, not a
guarantee of a complete 24-hour window.

UTC event timestamps describe observation on the HA event loop; callback delivery
can lag the transport event. Ages and cooldown use monotonic time. Samples are
not packet history, and a previous connected event does not prove uninterrupted
connectivity before the retained window. `returned` means the reconnect routine
returned, not that both streams recovered: consult the separate outcome and ages.
`confirmed` in the existing reconnect routine confirms only a new settings report.

Tests exercise bounded storage, alias privacy, transition sampling and production
coordinator methods with isolated HA boundaries, including disconnected and
never-started streams, error cooldown and callback queuing. These are not full
HA lifecycle fixtures or live outage acceptance. The policy still requires both
previously observed streams stale for 300 seconds and a 1,800-second cooldown.
This code has not been deployed; installed-beta and vehicle acceptance are
tracked in the [central backlog](backlog.md).

## Test principles

- A control is successful only after command acknowledgement **and** a newer
  qualified device/provider readback.
- Provider cache values and asynchronous source values are never assumed to be
  interchangeable with Direct device state.
- A live observation documents only the condition actually exercised; it does
  not prove behavior in an untested solar, battery, vehicle, or transport
  condition.
