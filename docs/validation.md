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

## Unreleased authentication failure handling

Credential handling now distinguishes a refused credential from an unreachable
endpoint, and the config flow offers re-authentication and reconfiguration.
See [the analysis](issue_16_auth_analysis.md) for the verified previous
behaviour and the classification rule.

What the automated suite covers: the classification decisions, including the
rule that a rejection is only reported when every attempted endpoint rejected;
sign-in, certification, discovery and provider-detail error mapping against a
doubled network boundary; and the config flow's structural contract, meaning
its step, error and abort keys all exist in `strings.json`, both repair paths
update the config entry rather than replacing it, and both refuse credentials
belonging to a different EcoFlow account.

What it does not cover: the flow's Home Assistant runtime behaviour. Home
Assistant is not a test dependency in this repository, so the dialog itself,
the reload after a repair and the survival of entity IDs are established by the
live test below, not by unit tests. Closing that gap is roadmap item
`V2-QA-02`.

A refused request is not shown to the user directly. The stored credentials
are tried once first, at most every five minutes, because the token is obtained
once at setup and never renewed on its own, which makes an expired session the
likely cause rather than a wrong password. Only a refused sign-in opens the
repair dialog.

Failure reasons carry the response status and result code only. The server's
free-text message stays at debug level, because a reason reaches the Home
Assistant interface and the warning log, and this integration cannot vouch for
what EcoFlow writes there. A test enforces that rule against both transport
modules.

Not implemented in this change: MQTT credential refresh and proactive renewal
before expiry. The MQTT layer still detects an expired certificate and logs
that a refresh is scheduled, but nothing consumes that signal, and existing
MQTT clients keep the certificate they connected with.

### Confirmed on 2026-09-10 on `1.0.5-beta.3`

| Item | Test | Result |
| --- | --- | --- |
| `V2-AUTH-01` sign-in | Deliberately wrong password while adding the integration. | Confirmed. The form reported rejected credentials, not a connection problem. |

This confirms the credential-endpoint classification and that the translated
`invalid_auth` string is wired through. It does not confirm the opposite
direction: that an unreachable endpoint is *not* reported as a credential
problem is a separate observation, and both are needed before the no-false-prompt
claim is established.

### Open, and how to reach each one

The reconfigure dialog is reachable at any time from the integration menu and
runs the same sequence as the repair dialog: `async_set_unique_id`,
`_abort_if_unique_id_mismatch`, the credential check, then
`async_update_reload_and_abort` with the same data. Only the entry lookup, the
step id and the abort reason differ. Two of the open items can therefore be
observed without invalidating any credential.

| Item | Test without a vehicle | Passing result |
| --- | --- | --- |
| `V2-AUTH-01` account guard | Reconfigure, entering a different EcoFlow account. | Aborts with the wrong-account reason and leaves the entry untouched. Same code path as the repair dialog, so this settles the guard for both. |
| `V2-AUTH-01` entry update | Reconfigure, re-entering the current credentials. | Reports credentials updated, the entry reloads, and every entity ID, recorded history, user activation and local Smart draft is unchanged. Covers everything the repair dialog does except the trigger. |
| `V2-AUTH-01` outage | Add the integration while the host cannot reach EcoFlow, for example with the internet uplink briefly disconnected. | The form reports a connection problem and never asks whether the password is correct. |
| `V2-AUTH-01` renewal | Let the integration run until EcoFlow refuses the token, without changing the account password. | The log records a renewed session and data returns on a later cycle. No dialog appears, because the stored credentials still work. Cannot be forced; it waits for a real expiry. |
| `V2-AUTH-01` repair trigger | Change the EcoFlow account password so the stored one is refused. | Home Assistant offers the repair dialog instead of retrying. This is the one step that needs an invalidated credential, and after the two reconfigure observations above it is the only untested part of the repair path. |

Changing the account password invalidates the EcoFlow app and any other
integration using it until each is signed in again.

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
