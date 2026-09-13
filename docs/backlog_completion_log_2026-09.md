# Backlog completion log, 2026-09

Evidence archive. These entries were written into the
[project backlog](backlog.md) while the items they describe were being
completed, between 2026-09-10 and 2026-09-13, and were moved here unchanged on
2026-09-14 so that the backlog lists open work only. They are in the order the
backlog held them, which is mostly newest first; several describe a state that
later entries supersede. Read them as a dated record, not as current status.
The current acceptance record for each item is in [validation.md](validation.md).

Update 2026-09-11: documentation/diagnostic consolidation is merged, including
PR #27/#28 and the A1–A3 evidence from PR #35. Only Issue #16 remains active.
Real HA functional tests reproduced three credential-renewal defects; focused
fixes now pass those counterexamples. See
[functional acceptance](validation.md#issue-16-functional-authentication-acceptance).
PR #36 is merged and beta.7 is installed. Runtime version and both MQTT streams
were verified after restart on 2026-09-11. Retain the explicitly unobserved
provider-expiry, repaired-password recovery and differing-broker cases as open live evidence. Do not repeat
A1–A3 or start another issue while completing this acceptance.

Issue #16 was closed on 2026-09-11; V2-SMART-01 / Issue #18 is the item in
progress, owned by Claude. Issues #14/#15 and PR #22/#23 form the next joint
control review and vehicle-acceptance block; include relevant #13 power tests
in that session. Issue #11 follows on its own; #25 is deferred. Issue #12's
2026-09-12 vehicle session captured two delayed Starts and supports one
progress-qualified extension from the normal 30-second deadline to an absolute
50-second ceiling. Live acceptance of that implementation remains a release
gate.

Work on 2026-09-12: Issue #25. The active-phase mapping was established from a
vehicle session in `auto` mode: four transitions of heartbeat field 21, each
agreeing within seven milliseconds with an unrelated second integration, and
corroborated by 9695 W drawn against a 16 A limit. `0` is three-phase and `1` is
single-phase — the inverse of the configured-selection encoding, which would
have produced the wrong answer had it been reused. `direct_active_phase` now
carries the name, the raw diagnostic stays, and its doubled display name is
fixed. The named sensor has not yet run on the instance. See
[the validation record](validation.md#unreleased-active-phase-mapping).

Accepted live on 2026-09-12 on `1.0.5-beta.12`, both from one authorized vehicle
session. Issue #13 is complete: the relay was caught claiming 707 W and 3664 W
while the charger reported idle, and the qualified sensor read zero through
both, reaching zero within three and one milliseconds of the status change. Over
three minutes of cable-connected idle produced no oscillation, and genuine
charging kept a largest update gap of about eleven seconds. Issue #12 recorded
three confirmed actions with the progress extension granted on real hardware;
the extension was not needed on that Start, so the rescue case rests on the
45.686-second Start observed the same day on beta.10. See
[the validation record](validation.md#live-session-on-2026-09-12-on-105-beta12).

Work on 2026-09-12: Issue #13, owned by Claude. The PowerOcean charging-power
reading now has an age of its own, tracked per charger and per reporting
observer, so a relay that goes quiet during genuine charging reads unknown
rather than holding the last watts. Fresh Direct idle still reports zero without
any relay report. `_POWEROCEAN_POWER_FRESH_SECONDS` is 120, measured against a
24.5-second largest gap between value changes during the 2026-09-12 session, and
is deliberately separate from the ninety-second control gate. Ten tests against
two mutations. The vehicle-backed validation of charging followed by
cable-connected idle stays open. See
[the validation record](validation.md#unreleased-relay-power-age).

Work on 2026-09-13: Issue #81 closed. On beta.14, a Start from `paused` received
a fresh `paused` heartbeat 0.336 s after dispatch — which the pre-#83 rule would
have reported as a successful Start while the charger charged nothing — and the
change refused it, ending `unchanged_state` with the honest message. The latent
false positive is now observed and suppressed. A Start ending in `paused` and a
Stop from `charging` still confirmed. A Start from `paused` resuming to
`charging` was not observed; the maintainer closed the item without it, since
that transition is behaviourally unchanged and its tests fail under the rejected
rule. See
[the validation record](validation.md#the-unfounded-confirmation-observed-and-refused-on-105-beta14).

Work on 2026-09-13: Issue #81 step 2. A Start from `paused` that stays `paused`
still fails, but now says the charger was already paused and showed no change,
and records `unchanged_state` instead of `readback_timeout`, so a live capture can
tell it from a genuine timeout. A genuine Start timeout keeps the original message.
Two mutations; forcing the new branch on fails four tests including two existing
extension tests. One pre-existing timing fragility in an extension test was seen
once and did not recur in ten full runs; recorded rather than fixed in passing.

Work on 2026-09-13: Issue #81 step 1. A Start or Stop now confirms only when the
Direct state changed from where it was before the command, closing the latent
false positive in which an ignored Start from `paused` passed whenever a
periodic heartbeat landed inside the window. The recommendation first written
into #81 would have broken resuming a paused charge; it was caught by checking
every case before coding, and a mutation substituting it fails the two resume
tests. Start's allowed and confirming states meet only in `paused` and Stop's do
not meet, and a test pins both. Thirteen tests against two mutations; not yet
observed live. See
[the validation record](validation.md#unreleased-a-confirmation-must-show-a-change).

Work on 2026-09-13: Issue #12 closed on its stated criterion. Codex captured a
Start rescued by the extension on beta.13 — confirmed by fresh Direct `paused`
at 48.190 s after the normal deadline would have failed it — and Claude verified
every Direct transition against the recorder within two milliseconds. The same
capture contains a Solar-paused Start that timed out at 30.193 s with no Direct
observation while PowerOcean briefly reported `charging`: a false negative the
extension cannot reach. Its mechanism is certain rather than suspected — the
thirty-second window fell entirely between two sixty-second periodic heartbeats,
and a Start ending in its starting state fires no transition report. Tracked as
Issue #81. See
[the validation record](validation.md#the-start-rescue-case-accepted-on-2026-09-13-on-105-beta13).

Work on 2026-09-13: Issue #19 closed. The long-outage scope reopened on
2026-09-12 is resolved by one event captured end to end on beta.12, with zero
dropped events. Both MQTT sessions died on keep-alive timeout, reason code 141,
thirty-six seconds apart, and reconnected on their own backoff after 4 min 33 s
and 6 min 03 s; the integration's recovery path declined to act while
disconnected, which is its design. The qualified sensor tracked the event in
three stages to the second. The EcoFlow app was closed throughout, so app
activity is not the trigger. No change was made: nothing behaved incorrectly,
and shortening the reconnect would trade a conservative backoff for a reconnect
storm against a broker that had just timed us out. See
[the validation record](validation.md#the-long-outage-classified-on-2026-09-13-from-a-105-beta12-capture).

Work on 2026-09-12: Issue #19 closed as explained rather than fixed. An overnight
capture on `1.0.5-beta.9` caught both `unknown` intervals with `connected: true`
on every sample, refuting the reconnection hypothesis. Cadence is about sixty
seconds and `_HEARTBEAT_STREAM_FRESH_SECONDS` is ninety, so one missed heartbeat
puts the next at about a hundred and twenty and leaves thirty seconds of
`unknown`. The budget tolerates no skip. No threshold was changed: the same
constant gates charging-control freshness, and the observed cost is a gap at
zero watts on an idle charger. Revisit if the gaps recur during an actual
charging session. See
[the validation record](validation.md#cause-established-on-2026-09-12-from-a-105-beta9-overnight-capture).

Scope correction on 2026-09-12: Issue #19 was reopened. The capture above
explains the short, single-missed-heartbeat population only. The three-day
record also contains ten total-silence outages lasting 4.0 to 35.4 minutes;
they account for 133.7 of 139.3 minutes of `unknown` time and none was captured
by the bounded timeline. At least one such outage must still be classified from
complete connection and recovery events before the issue can close. The
specific evidence requirements are recorded in
[the validation correction](validation.md#scope-correction-the-long-outage-population-remains-open).

Work on 2026-09-11: Issue #11, owned by Claude. Both charging buttons go
unavailable while a Start or Stop awaits confirmation, and a second action is
refused rather than queued behind the control lock, which serialises without
refusing. The marker is set before the lock and cleared in a `finally` on every
exit path. Confirmation windows, error reporting and the reported charging
state are unchanged; no optimistic mutation was introduced. Eleven tests
against three mutations. The live check of the visible button state needs a
vehicle and stays open. See
[the validation record](validation.md#unreleased-pending-charging-action).

Work on 2026-09-11: Issue #25. The charger heartbeat's field 21 is published as
`direct_active_phase_raw`, a disabled-by-default diagnostic carrying the raw
number. The field was confirmed present in all eleven captured frames before
any code was written, but its value cannot be read from the capture, which
redacts direct payloads; the reporter's single/three-phase mapping is therefore
recorded as a claim rather than implemented. The configured-selection sensor
the issue also asks for already exists as `phase_mode`, so the issue's premise
did not hold here. Interpreting the number needs a three-phase observation and
belongs with the vehicle session in #13. See
[the validation record](validation.md#unreleased-active-phase-reading).

Accepted live on 2026-09-11 on `1.0.5-beta.9`: a Smart activation and return
under explicit authorization produced two unusable reported fields,
`smart_charge_target_wh` and `ready_by_timestamp`, both counted in diagnostics,
with no warning logged and the draft intact including the 30.0 kWh energy
target. A valid field surviving alongside an invalid one in the same report is
covered by tests but not yet by live evidence; that needs the plan changed in
the EcoFlow app during a Smart window. See
[the validation record](validation.md#confirmed-live-on-2026-09-11-on-105-beta9).

Work on 2026-09-11: Issue #53, found while accepting #18. A charger report
carrying one unusable field no longer discards the whole report. `update` and
`update_from_device` now state which provenance they serve; user edits keep
their all-or-nothing rule. Unusable reported fields are counted in diagnostics
rather than logged as a warning. Ten tests, seven verified against a mutation.
The provider parser that produced the zero is deliberately unchanged, because
no evidence about its payload schema was collected. See
[the validation record](validation.md#unreleased-device-report-field-handling).

Accepted live on 2026-09-11 on `1.0.5-beta.8`: the refusal, its German
message naming the refused time, the preserved draft and the absence of any
publish were all confirmed on the maintainer's instance against the expired
draft the item was raised for. `control_readback_counts` stayed at zero on all
three paths, so no settings write was published. The real-device Smart
activation criterion stays open and carries `needs:maintainer`. See
[the validation record](validation.md#confirmed-live-on-2026-09-11-on-105-beta8).

Work on 2026-09-11: V2-SMART-01 / Issue #18 refuses to activate a Smart plan
whose ready-by time has passed, or is more than 366 days ahead. The draft is
kept and never rolled forward, the message names the refused time, and the
check sits on the publish path so a plan waiting on the control lock is
re-checked when it reaches dispatch. Nineteen tests, ten of them verified
against a mutation that disables the rule. The real-device activation criterion
stays open. See [the validation record](validation.md#unreleased-smart-deadline-handling).

Issue #19 is observation-only for 24–48 hours on the installed beta.5. Evaluate
one bounded export, then decide whether a demonstrated failure warrants a fix
or the item waits for reproduction. No new gap is not proof of recovery.
New research and unrelated features are paused during this completion phase.

Completed on 2026-09-10: V2-DOC-01 / Issue #20 was accepted through
[PR #26](https://github.com/Xygen/EcoFlow-PowerPulse-2-for-Home-Assistant/pull/26),
merge `678303a`. Smart drafts, source selection, field 17 and stable/beta scope
are documented. V2-QA-01 / Issue #17 was completed through
[PR #24](https://github.com/Xygen/EcoFlow-PowerPulse-2-for-Home-Assistant/pull/24),
merge `7f09767`, including the version declarations and translation-key fix.
Quality, HACS and Hassfest passed on both merge commits. See
[automated checks](validation.md#automated-repository-checks).

Observation on 2026-09-11, second reading: the same runtime stalled at
09:56 UTC. The charger stayed connected while its own frames stopped: 86.5 s
without a heartbeat and 47.7 s without a settings report, with no disconnection
recorded. The heartbeat age reached 79.1 s against the 90 s limit that gates
the qualified PowerOcean charging power, so it came within eleven seconds of
the reported symptom and the recorder confirms no unknown interval occurred.
Automatic recovery needs both streams stale for 300 s and could not have fired;
the single recovery check in the window ran exactly 30 s after the last frame,
which is the push-reset deadline, not a schedule. The heartbeat period was then measured at
60.048 s from recorder history, correcting the working value given earlier that
day, and the three-day record separates twelve short single-miss gaps from ten
total outages that account for 96% of the unknown time and were all eligible
for automatic recovery. See
[the observation](stream_timeline_observation_2026-09-11.md#later-finding-second-reading-at-1112-utc-the-fault-reproduced).

Observation on 2026-09-11: the bounded timeline was read for the first time on
`1.0.5-beta.7`. Two hours and fifteen minutes without a gap, no missed
heartbeat, no recovery decision. It constrains the heartbeat cadence to
`k x P = 300.40 s` without determining `P`, and records that the observer's
freshness is never sampled, so "connected without data" cannot be evidenced for
it. A quiet window is not evidence that the fault is gone; the next requirement
is a long window without a restart, because a reload discards the timeline and
the long intervals fell overnight. See
[the observation](stream_timeline_observation_2026-09-11.md).

Investigation on 2026-09-10: V2-STREAM-01 / Issue #19 remains open.
[A new 24-hour idle observation](stream_investigation_2026-09-10.md) correlates
six qualified-power gaps with heartbeat freshness: three short gaps near
integration loads and three longer paired-stream gaps. Next, capture a bounded
connection/recovery timeline with report ages and integration start time before
changing recovery policy. Current snapshots cannot establish connectivity or
recovery decisions during earlier gaps; no vehicle is required for this step.

Implementation for Issue #19: diagnostics now include an in-memory
stream timeline with connection callbacks, recovery reasons, report ages and
reconnect outcomes. See [the diagnostic contract](validation.md#stream-timeline-diagnostics).
The independent sampler correction is included. Beta.5 is installed and its
startup and five-minute observations were live-verified. A new idle-gap
observation remains pending. Main does not yet include the separate safety/readback
changes in PR #22/#23; the installed beta preserves PR #22 and excludes PR #23.
Persistence across reload/restart is not implemented; export before restarting.
Closed 2026-09-11: [V2-AUTH-01 / Issue #16](https://github.com/Xygen/EcoFlow-PowerPulse-2-for-Home-Assistant/issues/16)
is delivered in both stages and released in `1.0.5-beta.7`. A refused
credential is distinguishable from an unreachable endpoint, Home Assistant
offers re-authentication and reconfiguration without replacing the config
entry, an expired session is renewed once before the user is asked, the MQTT
layer's expired-certificate detection is consumed, and the broker address comes
from the credential response. PR #36 added Home Assistant fixture tests that
found three renewal defects, all fixed.

Five acceptance steps were observed live: the wrong-password sign-in on
`1.0.5-beta.3`, the account guard, the entry update and the broker address on
`1.0.5-beta.6`, and the outage report on `1.0.5-beta.7`. Both directions of the
no-false-report claim are therefore evidenced. The outage step also found that
the `cannot_connect` text still blended connection and sign-in, corrected in
PR #45.

Three steps are accepted as **not tested**, not as passed. The repair trigger
was deliberately skipped because invalidating the account password would
invalidate the EcoFlow app and four other integrations on this account; its
mechanism is covered by fixtures and EcoFlow's real refusal is evidenced
separately, so only the seam between them is unproven. The renewal cannot be
forced and waits on a real expiry. A differing broker host is not reachable
from an account EcoFlow serves from this region.

Findings, the classification rule, the comparison with `ecoflow-energy-ha` and
the limits are in [the analysis](issue_16_auth_analysis.md); the observations
and what each does not establish are in
[the validation status](validation.md#closed-on-2026-09-11-with-three-steps-accepted-as-unobserved).

Implementierungsstand: 2026-09-09.
`V2-SAFE-01` / [Issue #14](https://github.com/Xygen/EcoFlow-PowerPulse-2-for-Home-Assistant/issues/14)
ist lokal implementiert; 193 Tests bestehen, davon 31 neue Coordinator-Transaktionstests.
Die Review ergänzte eine Sendesperre bei neueren widersprüchlichen Begleitwerten
oder Modus-/Freigabewerten aus einer niedriger priorisierten Quelle.
`1.0.5-beta.1` ist per HACS installiert und nach HA-Neustart geladen.
Der Display-Test 100 → 75 → 100 % wurde zweimal per Direct-Readback bestätigt;
Begleitwerte blieben erhalten. Die fahrzeuggestützte Abnahme steht aus
(Live-Status `unplugged`). PR #22 ist am 2026-09-10 nach `main` gemergt;
das Item bleibt bis zur fahrzeuggestützten Abnahme offen.
Details zur Aussagegrenze: [Validierung](validation.md#unreleased-control-transaction-hardening).

Stand 2026-09-10: `V2-SAFE-02` / [Issue #15](https://github.com/Xygen/EcoFlow-PowerPulse-2-for-Home-Assistant/issues/15)
ist über PR #23 am 2026-09-10 nach `main` gemergt.
Feldbezogene Bestätigung, Konfliktsperren, vollständige Provider-No-ops und
überlappende Providerabrufe sind geprüft; die speziellen Phasen-Übergangsregeln
bleiben erhalten. Diese Änderung war in keiner Beta enthalten und ist auch in
`1.0.5-beta.4` nicht enthalten, muss also zuerst in einen Testbuild gelangen,
bevor sie überhaupt abgenommen werden kann. Das Item bleibt offen.
Nachweise: [Validierung](validation.md#unreleased-field-qualified-readback).
