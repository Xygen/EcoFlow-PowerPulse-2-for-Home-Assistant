# PowerPulse 2 protocol observations

These observations come from privacy-redacted cloud MQTT diagnostics captured
from a live C376 charger. They document evidence only; they are not permission
to transmit inferred commands.

## 2026-08-23: Solar-mode start and stop

Conditions:

- The charger was in Solar Mode with no available solar surplus.
- Starting in the EcoFlow app created a paused session with zero charging power.
- Stopping in the EcoFlow app ended that session without delivering energy.

Observed results:

- No frame arrived on the subscribed official-app `set` or `set_reply` topics.
- Start correlated with a CP307 heartbeat `(cmd_func=2, cmd_id=33)` changing to
  `system_state=4` (`paused`).
- Start also correlated with `cmd_func=2, cmd_id=133` (`CHARGED_RECORD`). Its
  start and end timestamps were initially identical and its meter values were
  unchanged.
- Stop correlated with a heartbeat changing to `system_state=6`
  (`charge_complete`) and further `CHARGED_RECORD` reports.
- The completed heartbeat reported `session_duration_s=278`,
  `session_energy_raw=0`, and identical start/end meter energy values.
- The completed charging record's end timestamp was 278 seconds after its
  start timestamp, independently confirming the heartbeat duration.

Conclusion:

- The telemetry state and duration fields are confirmed for a paused,
  zero-energy Solar Mode session.
- `cmd_id=133` is a charging-record report, not evidence of the control write.
- The actual app Start/Stop request remains unobserved. It may use another MQTT
  topic or another transport. Do not implement `CHARGE_CTRL` writes until the
  request envelope and acknowledgement are captured.

## 2026-08-23: Solar continuous-charging option

- Solar Mode exposes an optional "Continuous charging" setting. Its 6-16 A
  value is the current allowed even without solar production; it is not the
  charger's separately configured maximum current.
- Enabling the option at 6 A and saving produced a CP307 `cmd_func=2`,
  `cmd_id=34` parameter report. Disabling and saving produced the same command
  type in the opposite state.
- dev3 incorrectly treated that `2/34` message as a `2/33` heartbeat, briefly
  exposing `15`, `15`, and `unknown` as current/status values. The next real
  heartbeat restored `60`, `160`, and `unplugged`.
- No frame appeared on the eight exact SET/SET-reply topics subscribed by
  dev3. The setting may use another MQTT route or a non-MQTT API.
- dev4 routes envelopes by command type and adds passive discovery filters;
  the `2/34` field meanings remain intentionally undecoded until paired
  captures establish them.
