# PowerPulse 2 validation status

This page records current, release-relevant validation. Historical test detail
and raw chronology remain in the evidence archives linked from the
[documentation index](index.md).

## Current baseline

As verified on 2026-09-11, the installed test build is `1.0.5-beta.7`.
It includes the consolidated safety, field-qualified readback, authentication
and independent diagnostic sampling changes. Earlier beta.5 observations below
predate that consolidation.
Stable documentation remains at 1.0.4. Earlier installation records below
are historical observations, not the current installed version.

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
replace that evidence. PR #22 has merged; Issue #14 remains open for acceptance.
General readback source atomicity and provider no-op qualification remain the
separate scope of [Issue #15](https://github.com/Xygen/EcoFlow-PowerPulse-2-for-Home-Assistant/issues/15).

### Unreleased field-qualified readback

[V2-SAFE-02 / Issue #15](https://github.com/Xygen/EcoFlow-PowerPulse-2-for-Home-Assistant/issues/15)
is implemented locally on top of PR #22, with 270 passing tests on 2026-09-10.
Three regression tests first reproduced cached-field confirmation, provider
confirmation despite conflicting Direct evidence, and suppression of a required
write by a provider no-op. The replacement uses field-specific source observations.

The transaction matrix covers 18 generic settings cases (all setters plus mode
bundles) with Direct confirmation, provider confirmation, omitted-field rejection,
and a complete-provider repeat no-op. Additional tests cover newer and same-time
conflicts, unrelated fields/devices, evidence expiry, incomplete or mixed provider
bundles, in-flight reads started before the command, and late completion of an
older read. Three coordinator phase cases preserve Direct acceptance, provider
transition acceptance and rejection of provider-already-at-target confirmation.

Provider evidence is timed from request start as a conservative lower bound;
arrival of a late response cannot make it post-command evidence. A fresh conflicting
Direct value blocks provider fallback even when it predates the command. This can
reject an acknowledged write until Direct evidence catches up or expires; it must
not be reported as success based only on the provider target. Retry delays are unchanged.
Bounded diagnostics identify the exact field sources and whether their observations
are post-command and matching, without exporting their raw values.

These tests run the real coordinator with HA/network boundary doubles. The
implementation has since merged and is included in the installed `1.0.5-beta.6`.
Installation does not establish its remaining live acceptance, which stays
tracked in the [central backlog](backlog.md).

### Released baseline evidence

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

What it does not cover: the flow's Home Assistant runtime behaviour. This
suite runs without Home Assistant installed. PR #36 added a separate one in
`ha_tests/` that does run against real flow and config-entry fixtures, on its
own CI job, and it covers the authentication paths; the breadth `V2-QA-02`
asks for is still open. The dialog itself, the reload after a repair and the
survival of entity IDs remain established by the live steps below.

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

## Unreleased MQTT credential refresh

The transport's expired-certificate detection now has a consumer. A refusal
fetches a new certificate, renewing the session once if the endpoint refuses
it, and hands it to every live client. A certificate is also replaced once it
reaches a set age, so recovery does not depend on first observing a failure.
The broker address is taken from the credential response rather than a
compile-time constant.

What the automated suite covers: the broker address rules, including that an
unusable host, port or path falls back to the built-in default and that a port
quoted for a plaintext protocol is never dialled over TLS; that the client
dials the adopted address on both connect and force-reconnect; that a refused
certificate reaches the handler for reason codes 4, 5, 134 and 135 and no
others; and the coordinator's wiring, meaning setup passes the handler and
adopts the address, the transport callback hands its work to the event loop,
the refresh is rate limited and never raises, and an unchanged certificate at
an unchanged address does not rebuild the session.

What it does not cover: any of it against a real broker. The rate limits and
the replacement age are policy choices, not measurements; EcoFlow does not
state the real certificate lifetime, and the age used here follows the value
running in `ecoflow-energy-ha`.

| Item | Test without a vehicle | Passing result |
| --- | --- | --- |
| `V2-AUTH-01` certificate refresh | Observe a run long enough for the certificate to reach the replacement age, or for the broker to refuse one. | The log records a certificate refresh, and the stream continues or resumes without the config entry being reloaded and without a dialog. |
| `V2-AUTH-01` broker address, differing host | Only reachable with an account EcoFlow serves from another region. | The named host is dialled and the stream connects. Confirmed on 2026-09-11 that the built-in host is dialled and connects; a differing host remains unobserved. |

This is the item most likely to expose a wrong assumption in the field,
because it changes which host the integration connects to. The fallback path
is the previous behaviour, so a malformed or absent address cannot make things
worse than they were.


### Confirmed on 2026-09-10 on `1.0.5-beta.3`

| Item | Test | Result |
| --- | --- | --- |
| `V2-AUTH-01` sign-in | Deliberately wrong password while adding the integration. | Confirmed. The form reported rejected credentials, not a connection problem. |

This confirms the credential-endpoint classification and that the translated
`invalid_auth` string is wired through. It does not confirm the opposite
direction: that an unreachable endpoint is *not* reported as a credential
problem is a separate observation, and both are needed before the no-false-prompt
claim is established.

### Confirmed on 2026-09-11 on `1.0.5-beta.6`

Observed in the live instance, with the integration state read back through the
Home Assistant API rather than from the dialog alone.

| Item | Test | Result |
| --- | --- | --- |
| `V2-AUTH-01` account guard | Reconfigure with a different EcoFlow address. | Confirmed. Aborted with the wrong-account reason before any sign-in was attempted. The entry was untouched: unique id unchanged, state `loaded`, and `modified_at` still equal to `created_at`, so no write occurred at all. Both languages were seen: the English string with the instance in English, the German string after switching it back. |
| `V2-AUTH-01` entry update | Reconfigure with the current credentials. | Confirmed. Reported credentials updated and reloaded the entry. The Smart draft (ready-by `2026-09-01T11:00`, energy target `30.0`, distance target `200.0`, target type `distance`), the voice-assistant exposure set on the battery-discharge switch, the totals `1494.843` and `2.465`, and the operating mode `solar` all came back unchanged, with no new entity IDs. Recorded history spans the reload under the same entity ID. |
| `V2-AUTH-01` broker address | Debug log after a reload. | Confirmed. Two clients, the charger and the PowerOcean observer, both logged `Connecting to mqtt-e.ecoflow.com:8084 (WSS)`. Both stream sensors reported `on`, data arrived, and the system log recorded no warning or error from the component. |
| `V2-AUTH-01` outage | Both EcoFlow API hosts blocked at the firewall, then the integration added. | Confirmed on `1.0.5-beta.7`. The form reported a connection problem and never asked whether the password was correct. Together with the wrong-password step this settles both directions, which is what the claim needs. |
| `V2-AUTH-01` outage, running entry | The same block observed against the already loaded entry. | Confirmed. The entry stayed `loaded` with `reason` empty, no repair flow started, and the component logged neither warning nor error, while `powerocean` and `ecoflow_powerglow` both reported connection failures against `api-e.ecoflow.com`. |

The outage step also corrected an expectation. Entity states were predicted to
go unavailable and did not: the block covered the two API hosts and not the
MQTT broker, so the direct stream continued and the failed provider read was
treated as absent data rather than as an error. That is the intended
degradation, and it means an outage of the provider path alone is invisible in
the entity states — which is the right behaviour and worth knowing before
reading a future outage report.

It also exposed a defect that the classification itself did not have. The
`cannot_connect` text still read "Could not connect to EcoFlow **or sign in**",
written when the two were indistinguishable. Reporting the right outcome and
then describing it ambiguously puts back in words the doubt the classification
removes, so the string now names the outage and states that it says nothing
about the credentials.

Three limits of what these observations establish:

- The reconfigure used the **same** credentials, so the entry needed no change
  and `modified_at` did not move. This exercised the reload-and-preserve path,
  not the write of *different* credentials. That gap is closed by fixtures
  rather than live: `ha_tests/test_auth_flows.py` writes a different password
  through both the reauth and the reconfigure source and asserts the entry is
  updated rather than replaced, the unique id is unchanged, a user-disabled
  entity keeps its `disabled_by`, and the Smart staging store is byte-identical
  afterwards.
- EcoFlow named the **same** broker as the built-in constant for this account,
  so there was nothing to adopt. The address in use is right and the stream
  connects, but dialling an address that differs from the constant stayed
  unexercised, and cannot be forced from here. It concerns accounts served from
  another region.
- Data was `unknown` or `unavailable` for about 58 seconds after the reload
  (`00:06:27` to `00:07:26`) before every value returned. That is the update
  cycle plus the MQTT reconnect, not a fault, but a repair through the dialog
  carries the same gap and automations reading these entities have to tolerate
  `unknown`.

### Closed on 2026-09-11 with three steps accepted as unobserved

Five of the eight steps were observed live and are recorded above. The
maintainer closed the item on 2026-09-11 rather than hold it open for the
remaining three. What each of those does and does not leave unproven:

**Repair trigger — deliberately skipped, not tested.** It would have changed the
EcoFlow account password so the stored one is refused. That invalidates the
EcoFlow app and the four other integrations on this account until each is
signed in again, and the maintainer judged the cost higher than the remaining
evidence is worth.

The mechanism it would have exercised is covered by fixtures against real Home
Assistant objects. `ha_tests/test_auth_recovery.py` drives a refused stored
password and asserts a genuine reauth flow appears in
`hass.config_entries.flow.async_progress()` for that entry, and
`ha_tests/test_auth_flows.py` writes a changed password through both the reauth
and the reconfigure source with the preservation assertions named above. Live
evidence separately shows that EcoFlow's real refusal classifies as a
credential rejection rather than an outage, from the wrong-password step on
`1.0.5-beta.3`.

What stays unproven is the join: a stored credential going stale against the
real service and the dialog appearing on the device. Both halves are evidenced,
the seam between them is not.

**Renewal — not tested, cannot be forced.** It waits for EcoFlow to refuse a
token that was valid. Neither agent can hold an observation across sessions, so
this is recorded if it is ever seen, not scheduled.

**Broker address, differing host — not tested, not reachable here.** EcoFlow
names the built-in host for this account. Only an account served from another
region would exercise the adoption of a different address; the fallback to the
constant is the previous behaviour and is observed.

None of the three is recorded as passed. A step whose condition was not
produced is not testing evidence, and closing the item does not convert it
into any.

## Unreleased Smart deadline handling

Publishing a Smart plan and storing one are separated. `validate_smart_bundle`
still accepts a complete bundle whose deadline has passed, so a draft survives
editing and reload; `validate_smart_activation` adds the deadline rule and runs
only where a bundle becomes a frame, in `_smart_settings_payload`.

That function is the single choke point. Both publish paths reach it —
`_async_set_work_mode_locked` when Smart is selected, and
`_async_write_smart_setting` for edits made while Smart is already active — and
both build the payload after acquiring `_control_lock`, with no await between
the check and the write. The re-validation at dispatch is therefore the same
call, not a second one.

| Rule | Covered by |
| --- | --- |
| A deadline at or before now is refused | `tests/test_smart_staging.py`, both the past and the exact-now boundary |
| A deadline one second ahead is published | `tests/test_coordinator_transactions.py`, asserting field 1 of the sent block |
| A deadline beyond 366 days is refused | both files, with the last accepted value tested too |
| A queued activation is re-checked when it reaches dispatch | `test_a_queued_smart_activation_is_rechecked_when_it_reaches_dispatch`, which advances the clock while the operation waits on the lock |
| The draft survives the refusal | asserted after the refusal, since usually only the hour is wrong |
| The draft is never reported as device state | `test_an_expired_draft_is_never_reported_as_device_state` |
| An out-of-range timestamp is reported rather than crashing the message | `test_an_unformattable_timestamp_is_reported_rather_than_raising` |
| Local time, and both daylight-saving transitions | three tests on absolute seconds: the same instant written two ways, the night that is nine hours long, and the wall-clock hour that happens twice |

The ten tests that carry the rule were checked against a mutation that disables
both deadline comparisons. All ten fail under it. The tests that still pass
under the mutation are the ones asserting acceptance, which is correct.

### Confirmed live on 2026-09-11 on `1.0.5-beta.8`

The refusal was observed on the maintainer's instance. The runtime manifest
reported `1.0.5-beta.8`. No draft was prepared for the test: the entry already
held the expired plan this item was raised for.

Starting state, read before the attempt: mode `solar`, ready-by
`2026-09-01T11:00:00+00:00`, target type `distance`, distance 200.0 km, energy
30.0 kWh. The bundle was complete, which matters — `validate_smart_bundle` runs
first, so an incomplete draft would have reported a missing target instead and
the deadline rule would never have been reached.

`select.powerpulse_2_betriebsmodus` was set to `smart`. Home Assistant reported,
in German:

> Die gespeicherte Smart-Zielzeit (2026-09-01 11:00 UTC) liegt in der
> Vergangenheit. Lege eine neue Zielzeit fest und wechsle danach erneut in den
> Smart-Modus. Der gespeicherte Entwurf bleibt erhalten und wird nicht
> eigenmächtig auf einen anderen Tag verschoben.

| Read back after the attempt | Result |
| --- | --- |
| The refused time in the message | `2026-09-01 11:00 UTC`, matching the stored draft exactly |
| Translation | Resolved to German. The raw key `smart_ready_by_expired` did not reach the user, which is the failure the HA fixture test was written for |
| `select.powerpulse_2_betriebsmodus` history | `solar` → `unavailable` at the restart → `solar`. **Never `smart`**, so the refusal preceded any state change |
| `sensor.powerpulse_2_betriebsmodus` | `solar`, one row, unchanged across the whole window |
| The four draft values | All unchanged, including the deadline. Nothing was rolled forward |
| Config entry `modified_at` | Unchanged from `created_at`, so no entry write |
| Component entries in the system log | None, neither warning nor error |
| `control_readback_counts` | `{"direct": 0, "provider": 0, "noop": 0}` |

That last row is the evidence that nothing reached the charger, and it is worth
saying why rather than leaving it as a number. Every settings write goes through
`_async_write_settings_locked`, which always waits for a readback and increments
one of those three counters. All three standing at zero for the whole runtime
means no settings write was published at all — a stronger statement than the
mode merely having stayed `solar`, which a failed write would also produce.

This accepts the refusal, the message, the preserved draft and the
draft/observation separation.

### A valid Smart activation, accepted the same day

Authorized separately and performed by the maintainer. Reconstructed from the
recorder rather than reported, so the times are the instance's own.

| Time (local) | What the entities show |
| --- | --- |
| `14:35:53` | Draft deadline set to `2026-09-12T11:00Z`, then |
| `14:35:57` | corrected to `2026-09-12T06:00Z`. **No device observation moved**, so both edits stayed local: the staging path published nothing |
| `14:36:26` | Mode set to `smart`. Four device observations changed in the same millisecond: mode `smart`, ready-by `2026-09-12T06:00Z` (from `unknown`), target type `distance`, distance `200` |
| `14:37:26` | Back to `solar` |

The four observations moving together is the acceptance: those entities read
`setting_observation_value`, which carries only what the charger reported, so
the device acknowledged the complete bundle it was sent. `control_readback_counts`
ended at `{"direct": 2, "provider": 0, "noop": 0}` — the activation and the
return to `solar`, both confirmed on the direct stream with no provider
fallback and no no-op.

The two draft edits producing no device observation, and the activation
producing four, is the draft/observation separation demonstrated in one
sequence rather than argued.

**Every acceptance criterion for this item is now met.**

### What the same sequence exposed

The activation logged one warning:

```
Smart device configuration was not persisted:
Smart energy target must be 1 to 100 whole kWh
```

The charger reported `smart_charge_target_wh` as `0`, which the recorder
confirms: the device-observation energy sensor read `0` while the calculated
energy read `30000`. That is the documented protocol behaviour for a distance
target, already noted in `_smart_settings_payload` — the app sends field 3 as
zero and the device reports its own calculated energy instead.

`_async_update_smart_staging_from_device` passes that report through
`SmartStaging.update`, which validates every key with `_validated_value`, the
rule written for **user input**. A zero energy target is invalid input and a
perfectly ordinary device report, so the update raises and the whole batch is
discarded — including the ready-by, target type and distance in the same
report, which were all valid.

`SmartStaging.load` already gets this right: it validates per key and skips the
bad ones, isolating a malformed value instead of losing the record. The
asymmetry is the defect, and it is the same shape as the authentication
classification fault found in stage 1 of V2-AUTH-01: one validator serving two
different provenances.

Nothing broke here, because the draft already matched what the device reported.
The consequence when it does not is reasoned rather than observed: a plan
changed in the EcoFlow app would not refresh the local draft, and the two would
diverge silently apart from that warning. Tracked separately in Issue #53; this
build is not affected in a way that changes its acceptance.

Two limits, and one choice worth naming.

The 366-day horizon is a **chosen guard, not an observed device limit**. The
protocol carries the deadline as a varint and no upper bound has been read off
the charger. It is deliberately generous: refusing a deadline a user meant
costs more than accepting an odd one.

Editing only the energy or distance target while Smart is already active
republishes the whole bundle, so that edit now fails as well when the deadline
in effect has passed. This is wider than the activation case the issue names,
and it is intended — the publish would otherwise re-activate an expired plan —
but it is a behaviour change and is recorded as one.

**Not covered: a valid Smart activation on the real charger.** That is the
issue's last acceptance criterion, needs the maintainer and a separately
authorized test, and no fixture substitutes for it. The daylight-saving tests
use explicit `+01:00` and `+02:00` offsets rather than a named zone, so they
state what a local time resolves to instead of depending on the IANA database
and on the EU keeping its current rules.

## Unreleased device-report field handling

Storing what a user typed and storing what a charger said are different
problems, and `_validated_value` was serving both. It answers "may a user enter
this", so a distance-target report carrying an energy target of zero was read
as a rejected entry, `SmartStaging.update` raised, and the whole report was
discarded — ready-by time, target type and distance included.

The split is now explicit. `update` stays all-or-nothing, because a user
submitting one bad value should be told so rather than have half an edit
applied. `update_from_device` judges each field on its own and reports which it
could not use, exactly as `load` has always judged a stored record.

A skipped field leaves the stored draft as it was. For the unused half of a
target pair that is the right outcome rather than merely a safe one: the user's
own energy figure survives a distance-target session and is there when they
switch back.

| Rule | Covered by |
| --- | --- |
| A report with one unusable field stages the rest | `tests/test_smart_staging.py` and `tests/test_coordinator_transactions.py`, both using the report the charger actually sent on 2026-09-11 |
| The unusable field leaves the user's value alone | asserted against a staged 30 kWh energy draft |
| A wholly malformed report stages nothing and names every field | `test_a_wholly_malformed_report_stages_nothing_and_names_every_field` |
| A repeated report does not rewrite the store | asserted on the `Store` double |
| User input is still refused whole | two tests, one at the staging boundary and one through the coordinator |

Ten tests, of which seven were checked against a mutation that restores the
all-or-nothing behaviour. All seven fail under it. The three that still pass
are the ones asserting the user-input path is unchanged, which is what they
should do.

The warning is gone, deliberately. A user can do nothing about what the charger
reports, so a repeated field is counted in `unusable_device_smart_fields` under
`passive_settings_refresh` and named once at debug level. The count makes a
persistent problem visible without putting a line in the log for ordinary
telemetry.

### Confirmed live on 2026-09-11 on `1.0.5-beta.9`

Performed on the maintainer's instance under explicit authorization, because the
sequence commands the charger. The vehicle was unplugged throughout, so Smart
mode could not start a charge.

Before: runtime manifest `1.0.5-beta.9`, entry `loaded`, both stream sensors
`on`, charger `unplugged`, `unusable_device_smart_fields` empty, and the draft
holding ready-by `2026-09-12T06:00Z`, target type `distance`, distance 200.0 km,
energy 30.0 kWh.

`select.powerpulse_2_betriebsmodus` was set to `smart`, held for about ninety
seconds, then set back to `solar`. While Smart was active the device
observations confirmed the whole bundle: mode `smart`, ready-by
`2026-09-12T06:00Z`, target type `distance`, distance `200`, calculated energy
`30000`. The device-reported energy target stayed `unknown`, which is the
direct parser declining to map field 3 for a distance target.

| Read back afterwards | Result |
| --- | --- |
| Component entries in the system log | **None.** The previous build logged `Smart device configuration was not persisted` at this point |
| `unusable_device_smart_fields` | `{"smart_charge_target_wh": 1, "ready_by_timestamp": 1}` |
| The four draft values | All unchanged, energy target still 30.0 kWh |
| Mode | `solar`, as found |

Two skipped fields rather than the one expected, and the second is worth
keeping. Back in Solar the charger has no Smart deadline and reports
`ready_by_timestamp` as zero, which is as invalid an *entry* as the zero energy
target and as ordinary a *report*. The previous build would have discarded that
report whole, with a warning, on either field alone.

**What this establishes:** the per-field rule runs on real charger reports, the
skip is counted where it can be inspected, and the warning is gone.

**What it does not establish:** a valid field surviving in the same report as an
invalid one. Both fields the counter names were invalid, and the diagnostics do
not record which valid fields that report also carried. The draft was already in
agreement with the device, so nothing would have moved visibly either way.
Demonstrating the adoption still needs the plan changed in the EcoFlow app
during a Smart window, so that the charger reports something the draft does not
hold. The unit and coordinator tests cover the mixed report; live evidence for
it is still outstanding.

**Not covered: the provider path that produced the zero.** The direct MQTT
parser is already careful here — it maps field 3 to `smart_charge_target_wh`
only when the selector says energy. The provider parser copies `chargeTarget`
unconditionally, which is where the zero came from. Whether the provider
payload even carries a target-type field is unknown, and no evidence for it was
collected, so nothing in the parser was changed on speculation. This fix is a
backstop at the staging boundary and holds whichever path reports.

## Unreleased active phase reading

Issue #25 asks for the effective phase mode to be exposed separately from the
configured selection, and reports it at `2/33` field 21.

Half of that request was already met and the issue's premise did not hold for
this integration. `phase_mode` here has never been the effective mode: it comes
from the settings reports, `2/34` field 11 and `241/44` field 7, and carries
what the user asked for — `auto`, `one_phase` or `three_phase`. The separate
configured sensor the issue asks for is the one already shipping. What was
missing is the effective reading.

Field 21 was checked against the live instance before any code was written.
`mqtt_capture.unmapped_fields` shows it present in all eleven captured `2/33`
frames, wire type 0. **Its value could not be read**: the capture policy
redacts direct payloads length-preservingly, and a one-byte varint carries no
information once its bytes are replaced. So the field exists and its meaning is
still the reporter's claim rather than an observation.

It is therefore published as `direct_active_phase_raw`, a diagnostic sensor
disabled by default, carrying the number itself. Naming a value single- or
three-phase before seeing one would put a guess where a reading belongs, which
is the same rule that keeps a missing reading `unknown` rather than zero.

| Rule | Covered by |
| --- | --- |
| Field 21 reaches the entity as its raw value | `tests/test_parser.py`, for two different values |
| A heartbeat without field 21 publishes nothing | so older firmware leaves the sensor unknown rather than at zero |
| A value above 15 is withheld | a large number means the field is something else on that firmware |
| The rest of the heartbeat is undisturbed | asserted alongside |
| The heartbeat never writes `phase_mode` or `phase_specified_raw` | the configured selection must not be overwritten by what the charger is doing at that moment; `auto` would be the first casualty |

Both halves of the change were checked against mutations — unmapping field 21,
and disabling the range guard — and the matching tests fail under each.

**What remains.** Interpreting the number needs two observations: one while the
charger runs single-phase and one while it runs three-phase. The second needs a
vehicle drawing three-phase, so it belongs with the vehicle-backed session in
Issue #13 rather than to a separate test. Until then the raw sensor is the
honest form, and the reporter's mapping is recorded as a claim.

A useful cross-check is available meanwhile: the instance runs a second,
unrelated EcoFlow integration whose own effective-phase entity reads
`single_phase`. Comparing that against the raw number while the configured
selection stays `auto` corroborates the direction without establishing the
mapping.

## Automated repository checks

### Issue #16 functional authentication acceptance

The isolated `auth-ha` CI job uses Python 3.14 and
`pytest-homeassistant-custom-component==0.13.364` / HA Core 2026.9.1.
It runs `ha_tests` against the real flow manager, config entries and entity
registry. EcoFlow requests are mocked; no real account or internet outage is
required. This is separate from the portable unit suite.

The first recovery counterexamples reproduced three failures: a successful
login followed by another certificate refusal started reauthentication; a new
certificate password at the same account/broker did not rebuild the session;
and a request exceeding the retry interval allowed an overlapping refresh.
CI run `34567772496` recorded 3 failures and 13 passes. After the focused fixes,
run `34567907053` passed all 16 HA cases and the normal validation jobs.
The final expanded suite passed 18 HA cases and 420 portable tests in
[run `34568064061`](https://github.com/Xygen/EcoFlow-PowerPulse-2-for-Home-Assistant/actions/runs/34568064061),
along with Ruff, documentation consistency, HACS and Hassfest.

Cases cover rejected credentials versus network failure in all three forms,
wrong-account rejection before sign-in, changing stored credentials while keeping
the config entry/entity registry/Smart storage, real HA reauth creation on refused
sign-in, expired-session renewal, cooldown and slow concurrent requests.
The reload call is mocked in the form tests; actual device reconnection, recorder
continuity and real provider expiry are not established by those cases.
Startup-at-zero and shutdown-during-fetch cases additionally guard timer and
late-result boundaries.

Deployment verified on 2026-09-11 at 08:12 Europe/Berlin: HACS installed
`v1.0.5-beta.7`, and runtime diagnostics reported `1.0.5-beta.7` after a full
Home Assistant restart. Direct and heartbeat stream entities both returned `on`
with post-restart updates; charging status remained `unplugged`. The release ZIP
contains 48 source-identical files, SHA256
`f1d976f2cedd696866a4664168afd3a28415417f247c7ba57f176390f55ec13f`.
This confirms installation and startup connectivity, not natural credential
expiry, real repaired-password recovery or a differing-broker transition.
Earlier beta.6 acceptance remains historical evidence.

### Portable and repository checks

The `Validate` workflow runs on pushes, pull requests, the daily schedule and
manual dispatch. `quality` uses Python 3.12 and runs pytest, Ruff over
`custom_components`, `tests` and `scripts`, and `scripts/check_consistency.py`.
The existing `validate-hacs` and `validate-hassfest` jobs remain in place.

The suite also checks the coordinator transaction harness against the
coordinator itself: every Home Assistant name the coordinator imports must be
stubbed. Without that check the gap appears only where both files meet, which
is at a merge, and reports itself as an unexplained `ImportError`.
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

Independent sampling is installed in beta.5. Frequent MQTT pushes can defer
coordinator polling, so a separate HA timer observes report ages every 30 seconds
without provider calls, reconnects or device commands. `watchdog_sample` entries
are observations, distinct from actual `recovery_check` decisions; the two event
types coalesce separately. The timer starts after platform setup and is cancelled
on unload. The recovery scheduler itself is unchanged.

Live acceptance on 2026-09-10 confirmed beta.5 loaded, both streams fresh,
independent observations after startup and another unchanged-state observation
five minutes later. This establishes sampling, not long-outage recovery.
The installed release commit `57e9f49` passed 325 tests and tag CI run
`34526135571`; its 48-file archive matched SHA256
`80c18c02316db70274af76e4843b942bf205887e9fb3175895c5c48aff90b048`.

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
Diagnostics are deployed in beta.5; remaining recovery and vehicle acceptance are
tracked in the [central backlog](backlog.md).

## Test principles

- A control is successful only after command acknowledgement **and** a newer
  qualified device/provider readback.
- Provider cache values and asynchronous source values are never assumed to be
  interchangeable with Direct device state.
- A live observation documents only the condition actually exercised; it does
  not prove behavior in an untested solar, battery, vehicle, or transport
  condition.
