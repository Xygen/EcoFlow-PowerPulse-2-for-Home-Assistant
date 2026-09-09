# PowerPulse 2 validation status

This page records current, release-relevant validation. Historical test detail
and raw chronology remain in the evidence archives linked from the
[documentation index](index.md).

## Current baseline

The current stable baseline is `1.0.4`. The installed test build is
`1.0.5-beta.1` (PR #22), as confirmed by HACS and the runtime diagnostics manifest
after restart on 2026-09-09. The stable baseline's scope and accepted limitations
are recorded in the [release record](backlog.md#v100-release-record). The
PowerOcean idle qualification added in `1.0.4` is installed and statically
tested; its vehicle-backed transition validation remains pending.

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

## Test principles

- A control is successful only after command acknowledgement **and** a newer
  qualified device/provider readback.
- Provider cache values and asynchronous source values are never assumed to be
  interchangeable with Direct device state.
- A live observation documents only the condition actually exercised; it does
  not prove behavior in an untested solar, battery, vehicle, or transport
  condition.
