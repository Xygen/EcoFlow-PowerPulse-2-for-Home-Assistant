# Stream timeline observation, 2026-09-11

For users: this records a quiet window in which the charger stream never
faltered. It does not explain the interruptions seen on 2026-09-10, and it does
not show that they are gone.

First reading of the bounded stream timeline added for
[Issue #19](https://github.com/Xygen/EcoFlow-PowerPulse-2-for-Home-Assistant/issues/19).
It complements the recorder-history study in
[the 2026-09-10 investigation](stream_investigation_2026-09-10.md), which used a
different source and is not superseded by this.

## Scope and provenance

One read-only diagnostics query through the Home Assistant API, covering
**2026-09-11 06:11:19 through 08:26:35 UTC**, two hours and fifteen minutes.
The runtime manifest reported `1.0.5-beta.7`. The window opens at the restart
that installed that build; the timeline does not survive a reload, so it begins
there and nothing before it is available.

The payload reported `retention: current_runtime_only`, `limit: 2048`,
`dropped_events: 0`, `sample_interval_s: 300` and `watchdog_tick_s: 30`. No
command, reconnect, installation or restart was requested for this reading.

## What the window contains

Two connection events at the start, then 26 watchdog samples at 300-second
spacing:

| | |
| --- | --- |
| `06:11:19.85` | charger MQTT connected, reason code `0` |
| `06:11:20.36` | PowerOcean observer MQTT connected, reason code `0` |
| `06:11:34` … `08:26:34` | 26 samples, all `connected: true`, `settings_fresh: true`, `heartbeat_fresh: true`, cooldown `0` |

No gap, no recovery decision, no reconnect, and no dropped events. Settings
report ages ranged from 0.13 to 1.69 seconds against a 10-second freshness
threshold. Heartbeat ages ranged from 14.46 to 24.69 seconds against 90.

Every sample sat exactly 300 seconds after the previous one, which means the
30-second watchdog tick never found a change worth emitting an interim sample
for. **The fault under investigation did not reproduce in this window.**

## The heartbeat cadence is regular, and partly constrained

`heartbeat_age_s` fell monotonically across the steady samples, from 24.686 s
at `06:16:34.73` to 14.456 s at `08:26:34.91`. That is 26 intervals spanning
7800.185 s, so a mean sampling interval of 300.007 s and a mean age decrease of
0.3935 s per sample.

A sampling grid that is not a multiple of the heartbeat period walks slowly
through the period. The decrease therefore constrains the cadence to

```
k × P = 300.007 + 0.3935 = 300.40 s        for some whole number k
```

**It does not determine `P`.** Only about ten seconds of the cycle were
scanned, so every candidate that exceeds the largest observed age fits the
data: 30.04 s at `k = 10`, 60.08 s at `k = 5`, 75.10 s at `k = 4`. A 30-second
cadence is the most plausible of these and is consistent with a 90-second
freshness threshold, but this window does not establish it, and the figure
should not be quoted as measured.

A longer window resolves it without further work. When the age reaches zero it
wraps to the full period, and **the size of that jump is `P`**. At the observed
drift the wrap is roughly four hours away from the end of this window.

One sample broke the monotone fall, at `07:31:34`, rising 0.279 s above its
predecessor. A missed heartbeat would have added a whole period, so this is
jitter. Across the window no heartbeat was missed at all.

## The observer's freshness is never sampled

`_sample_stream_diagnostics` iterates `self.devices`. The MQTT clients are
built from `_mqtt_sources`, which is `{**self.devices, **self.observer_devices}`,
so the PowerOcean observer has a client and a status handler — its connection
events do reach the timeline, as the `06:11:20.36` entry shows — but it is
never sampled for report age or freshness.

A charger that is connected and silent is therefore visible. **An observer that
is connected and silent is not.** Issue #19 names "MQTT connected without data"
as a case to be tested separately, and for the observer this timeline cannot
evidence it either way.

This is a limit of what the instrumentation can show, not a fault in it. The
six intervals recorded on 2026-09-10 all correlated with the charger heartbeat,
which is what the sampler covers.

## What this establishes, and what it does not

Established: over 2 h 15 min on `1.0.5-beta.7` both sources connected cleanly
and the charger stream stayed fresh throughout, with no missed heartbeat and no
recovery decision taken.

Not established: anything about the cause of the 2026-09-10 intervals. A quiet
window is not evidence that a fault is fixed, and nothing in this build changed
recovery policy or freshness thresholds.

The next evidence still wanted is a **long window without a restart**, because
the three long intervals on 2026-09-10 fell at 01:36, 07:15 and 07:40 local
time. The retention limit is not the constraint: 2048 events at one sample per
300 seconds is about seven days. A reload is. The overnight window from
`1.0.5-beta.6` was discarded by the restart that installed `1.0.5-beta.7`.

## Later finding, second reading at 11:12 UTC: the fault reproduced

Added under [D-02](decisions.md#d-02--evidence-archives-are-preserved-not-rewritten).
The sections above stand as written. They describe this same runtime up to
08:26:35 UTC, and the window has since extended. Their headline — a quiet
window in which the charger stream never faltered — is true of what had been
read at the time and false of the run as a whole. At 09:56 UTC the stream
stalled.

### Provenance

A second read-only diagnostics query, same runtime, no reload in between:
`started_at` is unchanged at `2026-09-11T06:11:18.98Z` and `dropped_events` is
still 0. The window is now **06:11:19 through 10:52:05 UTC**, four hours and
forty-one minutes: two connection events, 58 watchdog samples and one recovery
check. Nothing was commanded, reconnected, installed or restarted for this
reading either.

### The stall

Four observations bracket it. Report ages are measured on the event loop, so
subtracting each age from its own timestamp reconstructs when frames actually
arrived.

| Observation | Time (UTC) | settings age | heartbeat age |
| --- | --- | --- | --- |
| last clean sample | `09:51:35.024` | 0.678 | 7.612 |
| sample | `09:56:35.029` | 18.063 | 67.217 |
| recovery check | `09:56:46.954` | 29.987 | 79.141 |
| first clean sample after | `09:57:05.029` | 0.345 | 10.682 |

That gives the frame times directly:

- **Settings frames**: last at `09:56:16.97`, next at `09:57:04.68`, a gap of
  **47.72 s**. Across the 57 other samples the settings age never once exceeded
  2.44 s.
- **Heartbeat frames**: last at `09:55:27.81`, next at `09:56:54.35`, a gap of
  **86.53 s**.

No disconnection was recorded. `connected` stayed true on every event, and no
`mqtt_connection` entry appears anywhere between the two at startup. This is
the connected-without-data case that Issue #19 asks to be tested separately,
caught on the charger.

### It came within eleven seconds of the reported symptom

`qualified_powerocean_charging_power_value` gates on `heartbeat_stream_active`,
which compares the heartbeat age against `_HEARTBEAT_STREAM_FRESH_SECONDS = 90`.
The age peaked at **79.141 s**. Eleven more seconds of silence and the
qualified PowerOcean charging-power sensor would have gone `unknown` — exactly
the symptom in the issue title.

It did not. The recorder holds a single state row for that sensor between 04:00
and 11:12 UTC, `0.0` unchanged, so no unknown interval occurred today up to
this reading.

The mechanism behind the reported intervals is therefore now visible: **a
silence in the charger's own frame stream while the MQTT session stays
connected**, long enough to exhaust a freshness window. The intervals of
roughly four, nine and thirty-four minutes recorded on 2026-09-10 are the same
shape at longer duration. Nothing here shows what causes the silence, and this
single instance does not establish that every earlier interval had the same
cause.

### The recovery policy cannot reach this failure mode

The check returned `settings_within_stale_limit` at a settings age of 29.987 s,
against `_AUTOMATIC_RECOVERY_STALE_SECONDS = 300`. Recovery requires *both*
proven streams stale for five minutes. This stall healed itself in 86.5 s.

Even a stall long enough to produce the symptom — over 90 s of heartbeat
silence — is more than three times short of eligibility. Every 2026-09-10
interval below five minutes was invisible to recovery by construction, and the
two longer ones would additionally have needed the settings stream stale for
the full five minutes, not the heartbeat alone.

> **Read too broadly.** True of this stall and of every short interval, but the
> long outages do satisfy both conditions and account for 96% of the unknown
> time; recovery was eligible in all of them. See
> [the third reading](#a-correction-to-this-mornings-reading-of-the-recovery-policy).

This is not an argument for lowering the threshold. The stream recovered
unaided, so a reconnect would have rebuilt a working session for nothing. It is
a statement of what the policy can and cannot see, which the issue asks for.

### The recovery check only runs after the stream has already gone quiet

One recovery check in four hours and forty-one minutes. That is not a
scheduling fault; it is the push-reset deadline, and the arithmetic is exact:

```
last frame of any kind          09:56:16.967
+ UPDATE_INTERVAL_SECONDS (30)  09:56:46.967
recovery check recorded at      09:56:46.954
```

Thirteen milliseconds apart. Incoming frames call `async_set_updated_data`,
which pushes the coordinator's refresh deadline forward, so while frames arrive
the polling cycle — and with it `_async_maybe_recover_direct_stream` — does not
run at all. It fires 30 s after the last frame, whatever kind it was.

This confirms the beta.5 scheduling finding from live data rather than from
reading the code, and sharpens it: **the recovery check cannot observe a
healthy stream, only one that has already been silent for 30 seconds.** The
independent 30-second watchdog added in beta.5 is what recorded the stall, and
without it this window would show a single recovery check and nothing else.

### The heartbeat cadence is down to two candidates

The first reading constrained the period to `k × P = 300.40 s` and listed
30.04, 60.08 and 75.10 s as fitting. **75.10 s is now excluded.**

Had nothing gone wrong, the age at `09:56:35` would have been 7.215 s: 7.612 at
the previous sample, less the drift of 0.3935 s per sample measured over 43
intervals. It was 67.217 s. The excess is **60.00 s of missing heartbeat**, and
a periodic sender can only lose whole beats.

| Candidate `P` | `k` | Beats lost in 60.00 s | Verdict |
| --- | --- | --- | --- |
| 75.101 s | 4 | 0.799 | excluded |
| 60.081 s | 5 | 0.999 | fits |
| 50.067 s | 6 | 1.198 | excluded |
| 37.551 s | 8 | 1.598 | excluded |
| 30.040 s | 10 | 1.997 | fits |
| 25.034 s | 12 | 2.397 | excluded |
| 20.027 s | 15 | 2.996 | excluded: below the largest age seen |
| 15.020 s | 20 | 3.995 | excluded: below the largest age seen |

The last two rows fall to a separate constraint: an age of 24.686 s was
observed at `06:16:34`, so the period cannot be shorter than that.

Between the two survivors the resume time decides, on the balance of evidence
rather than conclusively. Continuing the undisturbed grid from the last
heartbeat at `09:55:27.81` puts the next beats at `09:56:57.93` under 30.040 s
and at `09:57:27.97` under 60.081 s. The heartbeat actually returned at
`09:56:54.35`: **3.6 s early** under 30.040 s, **33.6 s early** under 60.081 s.
Jitter across the run was ±0.3 s. A 3.6-second shift after an interruption is a
plausible restart of the cadence; a 33.6-second one is not a cadence at all.

**30.040 s is the working value**, and it should carry that qualification until
the wrap measures it.

> **Corrected on the same day.** The period is 60.048 s, measured directly. The
> argument in this paragraph is unsound; see
> [the third reading](#correction-and-third-reading-2026-09-11-1154-utc-the-period-is-60-seconds). A 30-second cadence is also what a 90-second freshness
threshold implies, which is corroboration and not evidence.

Neither gap is a whole multiple of either candidate — 86.53 s is 2.88 periods
of 30.040 s and 1.44 of 60.081 s — so the sender resumed on a new phase instead
of skipping beats on a running timer. That points at something restarting on
the far side rather than at frames lost in transit, and it is the one inference
here that rests on the cadence being as regular between beats as it is across
the run.

### The wrap is due, and it is close

Drift after the stall is 0.4839 s per sample, from 10.682 s at `09:57:05` to
5.359 s at `10:52:05`. Extrapolating:

```
age reaches zero at about   11:47 UTC
the sample at               11:52:05 UTC  should read the full period
```

One diagnostics read after `11:52 UTC` settles `P` outright, at the cost of not
reloading before then. A reload discards the ring and the wrap is then another
run away.

> **Not needed after all.** The recorder holds the heartbeat arrival times
> directly, going back about ten days and across restarts. See
> [the third reading](#how-it-was-measured-and-why-no-waiting-was-needed).

### Corrections to the first reading

- "a quiet window in which the charger stream never faltered" holds for
  06:11–08:26 and not for the run, which stalled at 09:56.
- 75.10 s is no longer a candidate for the heartbeat period.
- The wrap was put "roughly four hours away from the end of this window"; it
  now falls at about 11:47 UTC, which is consistent.

The observer-freshness gap described above is unchanged. The PowerOcean
observer is still never sampled for report age, so the stall recorded here is
known only for the charger.

## Correction and third reading, 2026-09-11 11:54 UTC: the period is 60 seconds

Added under [D-02](decisions.md#d-02--evidence-archives-are-preserved-not-rewritten).

**The heartbeat period is 60.048 s. The working value of 30.040 s given in the
section above is wrong, and the reasoning that produced it was unsound.**

### How it was measured, and why no waiting was needed

The in-memory ring was never the only record. `heartbeat_stream_diagnostics`
exposes `last_heartbeat_report` as an attribute of the charger's heartbeat
binary sensor, and that attribute is rewritten on every heartbeat, so the Home
Assistant recorder has been storing the arrival series all along — for about ten
days, and across restarts, which the ring is not.

Fifteen consecutive intervals, `11:39:03.969` to `11:54:04.686` UTC:

```
59.995  60.422  60.009  60.010  60.022  60.388  59.805  59.974
59.954  60.016  60.011  60.073  60.428  59.693  59.918
```

Span 900.718 s over 15 intervals: **mean 60.048 s**, minimum 59.693, maximum
60.428. That is `k = 5` against the drift constraint of `k × P = 300.40 s`,
which predicted 60.081 s — agreement to 0.03 s, and the drift figure is the
more precise of the two.

### Why the earlier argument was wrong

The section above used two facts to choose between 30.040 s and 60.081 s:

1. Exactly 60.00 s of heartbeat went missing at the stall. This admits one lost
   beat at 60.081 s and two at 30.040 s, equally. It was not the deciding fact,
   and it was correct.
2. The heartbeat resumed at `09:56:54.35`, which continuing the pre-stall grid
   makes 3.6 s early under 30.040 s and 33.6 s early under 60.081 s.

The second argument is invalid, and the same section says why three paragraphs
later: it observes that neither gap is a whole multiple of either candidate and
concludes the sender resumed **on a new phase**. A sender that resets its phase
cannot then be located on the old grid. Having established that the phase does
not carry across the interruption, the resume time says nothing about the
period, and the honest position after the second reading was two candidates and
no discriminator — which is what the wrap was going to settle.

The lesson is not that the arithmetic slipped. It is that two conclusions in
one section contradicted each other and the contradiction was not noticed,
because each read well on its own.

### What the correct period changes

Everything, as it turns out. The freshness limit that gates the qualified
PowerOcean charging power is 90 s, so:

```
90 s / 60.048 s = 1.50 heartbeat periods
```

**One missed heartbeat is enough.** The age reaches 120.1 s, the sensor goes
`unknown`, and it clears when the next beat lands — an interval of
`2P − 90 = 30.1 s`. Under the wrong 30.040 s value a single miss would have
reached only 60 s and shown nothing at all, and two misses would have produced
an `unknown` lasting a tenth of a second. That prediction is not merely
different from what the recorder holds; it is excluded by it.

The margin is 29.95 s. Any hiccup that delays a heartbeat by more than about
thirty seconds past its due time produces a visible gap.

### The three-day record, in two populations

Qualified-power history for 2026-09-08 through 2026-09-10, twenty-two intervals,
139.3 minutes of `unknown` in total. They fall into two groups that do not
overlap:

**Twelve short ones, 6.7 s to 39.8 s, mean 28.0 s, totalling 5.6 minutes.**
Against a prediction of 30.1 s for a single missed beat, with five of them
between 29.3 and 30.6 s. The direct settings stream was unaffected or dipped
for a few seconds. This is the partial case in the issue title, and automatic
recovery is structurally unable to act on it: the heartbeat reaches 120 s
against a 300 s threshold, and the settings stream is not stale at all.

**Ten long ones, 4.0 to 35.4 minutes, totalling 133.7 minutes — 96% of all
`unknown` time.** Every one of them is a **total** silence. The direct stream
binary sensor goes `off` within a minute either side of each, and returns with
it:

| Unknown from | Length | Direct stream off | Length |
| --- | --- | --- | --- |
| 09-08 06:59 | 4.0 min | 06:58:02 – 07:03:10 | 5.1 min |
| 09-08 20:51 | 4.4 min | 20:50:14 – 20:55:02 | 4.8 min |
| 09-09 01:48 | 14.5 min | 01:47:51 – 02:02:49 | 15.0 min |
| 09-09 02:04 | 18.4 min | 02:03:49 – 02:22:33 | 18.7 min |
| 09-09 06:09 | 5.3 min | 06:08:37 – 06:13:35 | 5.0 min |
| 09-09 13:57 | 35.4 min | 13:57:18 – 14:32:52 | 35.6 min |
| 09-09 18:05 | 4.0 min | 18:04:34 – 18:09:11 | 4.6 min |
| 09-10 01:36 | 34.4 min | 01:35:41 – 02:10:28 | 34.8 min |
| 09-10 07:15 | 4.2 min | 07:14:39 – 07:19:10 | 4.5 min |
| 09-10 07:40 | 9.2 min | 07:39:42 – 07:49:13 | 9.5 min |

Times are local. The offset between the two columns is the two thresholds, 10 s
for the settings stream and 90 s for the heartbeat, not a difference in when
the streams stopped.

### A correction to this morning's reading of the recovery policy

The second reading said automatic recovery "cannot reach this failure mode".
That is true of the 86.5-second stall it was describing, and of every short
interval above. It is **not** true of the phenomenon as a whole, and the
sentence invited the wrong conclusion.

All ten long outages exceeded 300 s of silence on **both** streams. Every one
of them was therefore eligible under `recovery_reason`, and the coordinator's
poll deadline expires 30 s after the last frame, so the checks were running.
Recovery was not shut out of 96% of the unknown time; it had the opportunity
and the outages lasted up to thirty-five minutes anyway.

Which raises the question this evidence cannot answer.
`_async_maybe_recover_direct_stream` returns early with `disconnected` when the
client reports no session, leaving the matter to the separate reconnect loop.
So either the MQTT session dropped and recovery never ran, or the session held
and recovery ran without effect. Those call for opposite fixes, and nothing in
the recorder distinguishes them.

The stream timeline does: it records `mqtt_connection` events, `recovery_check`
reasons and `recovery_attempt` outcomes. **The next evidence wanted is one long
outage caught in the ring.** The short ones are frequent enough to be easy; the
long ones happen a few times a day and fell at 01:36, 02:04, 06:09, 07:15,
07:40, 13:57, 18:05 and 20:51 across these three days, so they are not confined
to the night.

### What this section does not establish

No cause for either failure mode. Nothing about whether the two are related.
Nothing about the PowerOcean observer, whose report ages are still never
sampled. And the 2026-09-09 and 2026-09-10 figures come from recorder history
rather than the instrumented timeline, so they show when streams were absent,
not why.
