# PowerPulse 2 validation status

This page records current, release-relevant validation. Historical test detail
and raw chronology remain in the evidence archives linked from the
[documentation index](index.md).

## Current baseline

The current installed baseline is `1.0.4`. Its scope and accepted limitations
are recorded in the [release record](backlog.md#v100-release-record). The
PowerOcean idle qualification added in `1.0.4` is installed and statically
tested; its vehicle-backed transition validation remains pending.

## Confirmed behavior

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

## Test principles

- A control is successful only after command acknowledgement **and** a newer
  qualified device/provider readback.
- Provider cache values and asynchronous source values are never assumed to be
  interchangeable with Direct device state.
- A live observation documents only the condition actually exercised; it does
  not prove behavior in an untested solar, battery, vehicle, or transport
  condition.
