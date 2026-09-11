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
