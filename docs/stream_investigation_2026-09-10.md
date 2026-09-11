# Idle stream investigation, 2026-09-10

For users: the qualified power reading sometimes becomes unknown because fresh
charger confirmation is missing. This investigation distinguishes short startup
gaps from longer interruptions. It does not establish that charging failed.
Implementation and remaining acceptance are tracked in the
[central backlog](backlog.md) and
[Issue #19](https://github.com/Xygen/EcoFlow-PowerPulse-2-for-Home-Assistant/issues/19).

**Later finding, 2026-09-11:** the bounded timeline this document asks for
exists and was read for the first time. It records a quiet two-hour window and
constrains the heartbeat cadence without determining it. See
[the 2026-09-11 observation](stream_timeline_observation_2026-09-11.md). Nothing
below is revised by it.

## Scope and provenance

Read-only Home Assistant MCP queries covered **2026-09-09 17:10 UTC through
2026-09-10 17:10 UTC**. The runtime manifest at query time reported
`1.0.5-beta.1`; stable main was `1.0.4`, merge commit `678303a`.
The manifest snapshot does not prove which build ran throughout the window.
No command, reconnect, installation, restart or logger change was requested
as part of this investigation.

Recorder state-change history was retrieved in ascending order with a limit of
1,000 per entity. All five queried entities returned `has_more: false`:
qualified power (13 records), settings stream (9), heartbeat stream (13),
Direct charging state (7), and PowerOcean charging state (3). The first record
is the state at the window boundary, not necessarily an event at that instant.
Recorder states show reported freshness, not every packet or connection event.

## Observed intervals

All times below are Europe/Berlin (UTC+02:00). Every qualified-power `unknown`
interval began and ended within 0.05 seconds of the heartbeat stream changing
off/on. Qualified power was otherwise zero in this recorded window.

| Start | End | Duration | Settings stream during the gap |
| --- | --- | --- | --- |
| Sep 9, 21:50:17 | 21:50:24 | 6.7 s | Recorded on throughout |
| Sep 10, 01:36:41 | 02:11:06 | 34 min 24.8 s | Off 01:35:41–02:10:28 |
| Sep 10, 07:15:41 | 07:19:51 | 4 min 9.7 s | Off 07:14:39–07:19:11 |
| Sep 10, 07:40:42 | 07:49:53 | 9 min 10.8 s | Off 07:39:42–07:49:14 |
| Sep 10, 12:41:48 | 12:42:20 | 32.7 s | Recorded on throughout |
| Sep 10, 13:09:12 | 13:09:24 | 12.0 s | Recorded on throughout |

One additional settings-only interruption at 03:52:57–03:53:02 lasted 5.3 seconds
without a qualified-power gap. Direct charging state was `unplugged` except
for `unknown` during the three short heartbeat-only gaps. Its retained value
during the long gaps does not establish fresh charger state then.
PowerOcean charging state was `available` except 21:50:17–21:51:43 on Sep 9;
that state alone does not establish fresh raw power or continuous MQTT connectivity.

## Startup and transport evidence

The bounded log query covered approximately Sep 9 20:30 through Sep 10 19:10
in HA's displayed log times. Matching loader warnings occurred shortly before
the three short gaps: Sep 9 21:49:52, Sep 10 12:41:18 and 13:08:45.
This is consistent with integration loading/startup contributing to those gaps,
but is not proof of the cause or an exact HA restart timeline. The query returned
only generic custom-integration loader warnings for this domain. Older logs
remained outside the fetched window; absent debug messages are not evidence
that no reconnect happened.

At 17:10 UTC, diagnostics showed both MQTT sources connected, successful
subscriptions, a fresh settings report and fresh heartbeat. The recent automatic
reactivation list was empty. These are current-runtime snapshots, not a historical
connection trace. Integration loads can discard in-memory evidence. Moreover,
the MQTT reconnect-attempt counter resets on successful connection, so a zero
counter cannot exclude previous outages.

## Policy comparison and conclusion

The inspected recovery policy is identical in stable main and the installed
beta's source commit `d2fc314`. It requires both report families to have been
observed, both last reports to be at least 300 seconds old, a connected client,
and a 1,800-second cooldown. Settings freshness is 10 seconds; heartbeat
freshness is 90 seconds. Entity off durations therefore are not the same as
report ages and must not be compared directly with the 300-second threshold.

The three short heartbeat-only gaps do not demonstrate a need for reconnecting
a single stream. The longer paired gaps are the stronger investigation target,
especially the 34-minute interval. Available history cannot determine whether
recovery was skipped, attempted unsuccessfully, inhibited by a disconnected
client/cooldown, or followed by renewed reports. No cause or recovery fix has
been established, and no freshness threshold was relaxed.

The next evidence requirement is a bounded, privacy-safe timeline of MQTT
connect/disconnect events, integration start time, recovery decisions/attempts
and both report ages. It should survive long enough to correlate a new idle gap.
App-open/closed status and the never-started-stream case are not established
by this dataset. The backlog remains the sole implementation plan; this file
records this observation only.
