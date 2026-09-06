# Issue #12 charge-action readback analysis

Status: pre-analysis complete; implementation step 1 (source correctness and
diagnostics) is implemented locally and statically tested. Live validation is
still pending.

Issue: [#12 Avoid false-negative Start/Stop failures when direct readback arrives late](https://github.com/Xygen/EcoFlow-PowerPulse-2-for-Home-Assistant/issues/12)

## Executive conclusion

The 2026-09-06 evidence confirms one genuine false-negative **Start** result:
the service timed out after 30 seconds and the Direct heartbeat reached
`charging` about 2.9 seconds later. It does **not** establish that PowerOcean
status is a useful success fallback. In every comparable transition recorded
that day, the source-qualified PowerOcean MQTT status followed the Direct
status by roughly 0.6 to 1.7 seconds.

The analysis also found a more important source-consistency defect. Charge
availability and confirmation combine `_last_heartbeat_at`, which belongs to
Direct CP307 heartbeat `2/33`, with the canonical `charging_status`. That
canonical value can be overwritten by an HTTP provider snapshot. The timestamp
and state can therefore describe different sources. This must be corrected
before adding another confirmation source.

Recommended order:

1. make Direct charge evidence source-atomic and use it for availability;
2. add privacy-safe per-action timing diagnostics;
3. use post-command transitional evidence only to grant a bounded Start
   extension, not as success;
4. evaluate PowerOcean as an independent success source only if a future
   capture shows that it can lead or replace missing Direct evidence safely.

A blanket timeout increase or immediate PowerOcean-success fallback is not the
preferred first change.

## Implementation status

### Step 1a: Direct source correctness

Implemented locally:

- action availability and both pre-command validity checks use
  `direct_charging_status` instead of the provider-mergeable canonical status;
- confirmation requires the source-qualified Direct state and a Direct
  heartbeat received after command publication;
- the Direct heartbeat monotonic and UTC timestamps now come from the same
  received frame sample;
- pure unit tests cover canonical/provider divergence and reject a matching
  Direct state when its heartbeat is not newer than the command.

This intentionally does not change the 30-second Start deadline, the 15-second
Stop deadline, or accepted success states. It also does not add a PowerOcean
success fallback.

### Step 1b: Bounded action diagnostics

Implemented locally:

- retain at most 16 completed attempts plus any currently active attempt;
- export only the device product prefix, action, UTC issue time, known
  source-qualified states, result classifications, and relative timings;
- distinguish publish rejection/error, SET-reply timeout, Direct readback
  timeout, cancellation, and successful Direct confirmation;
- capture the first post-command Direct and exact-serial PowerOcean states
  independently; PowerOcean remains diagnostic evidence and cannot confirm an
  action;
- expose the records in the Home Assistant diagnostic download under
  `charge_action_readback`.

`progress_extension_granted` is present but remains `false` until a later
implementation slice explicitly adds and validates that policy.

Still pending:

- deployment and reversible live Start/Stop validation of step 1.

### Live validation correction: provider merge

The first live Stop test on 2026-09-06 confirmed Direct `charge_complete`
promptly, but the Start button subsequently became `unknown` while the Direct
heartbeat was still fresh. The `v1.0.2` source-selection change exposed that a
provider poll could remove `direct_charging_status` from the merged snapshot.

The follow-up correction preserves that alias whenever its Direct heartbeat is
fresh. It does not preserve or promote the provider's canonical state, and it
does not relax any action-confirmation requirement. The Start half of the live
test remains pending until this correction is installed.

## Pre-implementation control path

At the time of the pre-analysis, `coordinator.py` performed these gates:

1. require a recent Direct heartbeat and a startable/stoppable canonical state;
2. serialize the write with `_control_lock` and repeat the state check;
3. publish the captured PowerOcean-routed `241/100` command;
4. require the matching `(observer, 241, 100, sequence)` SET reply within five
   seconds;
5. wait 30 seconds for Start or 15 seconds for Stop;
6. report success only when `_last_heartbeat_at > issued_at` and the current
   canonical `charging_status` belongs to an accepted outcome.

Accepted Direct outcomes are:

| Action | Valid pre-command state | Confirming state |
| --- | --- | --- |
| Start | `plugged_in`, `paused`, `charge_complete`, `standby` | `charging`, `paused` |
| Stop | `charging`, `paused` | `plugged_in`, `charge_complete`, `standby` |

The SET reply correctly proves transport correlation only. It does not prove
that the wallbox or vehicle reached the requested state.

## Available state sources

| Source | Stored value | Freshness tracked at pre-analysis | Suitability for charge confirmation |
| --- | --- | --- | --- |
| Direct CP307 heartbeat `2/33` | canonical `charging_status` and source alias `direct_charging_status` | `_last_heartbeat_at` / UTC timestamp | Authoritative current source. The pre-analysis implementation read the mergeable canonical key; step 1a changes availability and confirmation to the source alias. |
| PowerOcean MQTT `241/3` or compatible `209/8` | `powerocean_charging_status` | Step 1b retains the receive time only for the first report during an active action | Exact charger serial is matched before merge. The new timestamp is diagnostic only and does not qualify PowerOcean as a success source. |
| HTTP device/parent snapshot | canonical `charging_status` | combined poll-completion timestamp only | Key provenance and device-generation time are not retained; unsuitable as a new charge-success source in the current representation. |
| `241/100` SET reply | no physical status | command tuple and sequence | Transport acknowledgement only; never sufficient for success. |

The PowerOcean MQTT source has a useful independent namespace and exact target
serial routing. It needs its own observation timestamp before control code can
use it. The HTTP provider path is less suitable because the combined snapshot
can overwrite canonical keys and does not preserve per-key source identity.

## Reconstructed live timeline

The timeline below combines Home Assistant recorder history and the two
deduplicated service errors. Times are local (`Europe/Berlin`). Durations are
relative to the button press.

| Action | Button press | Direct evidence | PowerOcean MQTT evidence | HA result | Assessment |
| --- | ---: | --- | --- | --- | --- |
| Stop A | 11:06:16.403 | `charge_complete` at 11:06:18.111 (+1.709 s) | `finishing` at 11:06:19.802 (+3.399 s) | Success | Normal; Direct led PowerOcean. |
| Stop B | 11:06:50.987 | A new heartbeat at 11:07:18.226 (+27.240 s) still described `charge_complete`; Direct power was 0 W | Source-specific state remained `finishing` and power remained 0 W | Error at 11:07:06.257 (+15.271 s) | Not proven to be a physical Stop transition; the button had become available from divergent canonical state. |
| Start A | 11:07:22.498 | `plugged_in` +1.279 s, `paused` +3.812 s, `charging` +12.513 s | `preparing` +2.322 s, `suspended_charger` +4.884 s, `charging` +13.339 s | Success | Current accepted `paused` state confirmed early; PowerOcean followed. |
| Stop C | 11:08:22.741 | `charge_complete` +1.731 s | `finishing` +3.161 s | Success | Normal; Direct led PowerOcean. |
| Start B | 11:08:47.813 | `plugged_in` +1.540 s, `charging` +33.602 s | `preparing` +2.075 s, `charging` +34.159 s | Error at 11:09:18.491 (+30.677 s) | Genuine false negative; final Direct confirmation arrived about 2.925 s after the error. |

### Stop B source divergence

Stop A changed both source-qualified status sensors to stopped states. At
11:06:24.860 the generic charging binary sensor nevertheless changed to `on`,
the Stop button became available, and the Start button became unavailable.
Neither source-qualified status changed back to charging, and the PowerOcean
power remained 0 W. This aligns with the static finding that availability uses
the mergeable canonical `charging_status` rather than the Direct alias paired
with `_last_heartbeat_at`.

Consequently, Stop B must not be used as evidence that a 15-second Stop timeout
is too short. It first demonstrates that source and timestamp must be coupled.

### PowerOcean timing result

PowerOcean MQTT did not lead an accepted Direct outcome in any comparable
transition:

- Stop A: PowerOcean followed Direct by about 1.69 seconds.
- Start A: `suspended_charger` followed Direct `paused` by about 1.07 seconds;
  final `charging` followed by about 0.83 seconds.
- Stop C: PowerOcean followed Direct by about 1.43 seconds.
- Start B: PowerOcean `charging` followed Direct by about 0.56 seconds.

Using PowerOcean `charging`/`finishing` with the same deadline would therefore
not have prevented the observed errors. `preparing` appeared quickly, but it is
a transitional state and does not prove a completed Start outcome.

## Root-cause assessment

### Confirmed

- Start B exceeded the validated 30-second Direct confirmation window.
- The error was raised by the physical-readback gate, not by MQTT publication
  or SET-reply correlation.
- Direct heartbeat freshness and the checked canonical status are not stored as
  one source-atomic observation.
- PowerOcean MQTT status lacks a dedicated observation timestamp for control
  qualification.
- Existing tests cover pure state and timeout constants but not coordinator
  timing, source races, or the asynchronous confirmation loop.

### Not confirmed

- That Stop requires a longer timeout. Stop B did not show a source-qualified
  transition from charging to stopped.
- That PowerOcean can confirm earlier than Direct. The captured transitions
  show the opposite.
- That `preparing` should count as Start success. It proves progress only.
- That HTTP provider data is generated after the command rather than returned
  from a current server-side cache.

## Recommended design

### 1. Source-atomic Direct evidence

Introduce a small charge-evidence record containing at least:

- normalized state;
- source name;
- monotonic receive timestamp;
- UTC diagnostic timestamp.

Record Direct evidence from the same parsed `2/33` frame and use that record for
both action availability and confirmation. At minimum, pair
`direct_charging_status` with `_last_heartbeat_at`; do not pair a Direct
timestamp with canonical `charging_status`.

The pre-lock and in-lock validity checks must use the same source-qualified
evidence. This prevents a provider poll from enabling an action that contradicts
the latest Direct heartbeat.

### 2. Independent PowerOcean evidence

When a serial-matched `241/3` or `209/8` report contains
`powerocean_charging_status`, record a separate evidence object using the MQTT
frame receive time. Do not derive freshness from entity `last_changed`, because
repeated reports with the same state do not change that timestamp.

HTTP parent/device snapshots should remain excluded from charge-action success
until their per-key source and post-command freshness can be demonstrated.

### 3. Bounded progress extension for Start

Retain 30 seconds as the normal Start window. If a source-qualified,
post-command transition proves progress but not final success, allow one bounded
extension to an absolute deadline such as 45 seconds.

Candidate progress states:

- Direct `plugged_in` only when it is a post-command transition from a different
  pre-command state;
- PowerOcean `preparing` only as post-command, exact-serial progress evidence.

Neither state may itself return success. With no post-command progress, the
operation still fails at the normal 30-second boundary. This would have covered
Start B without delaying the earlier no-new-heartbeat failure case.

The exact 45-second ceiling is a design candidate, not yet a validated constant.
It should be confirmed with several bounded Start samples.

### 4. PowerOcean success fallback remains conditional

A fresh PowerOcean final state could eventually be accepted independently only
after tests define:

- Start mappings, likely `charging` and the validated paused counterpart
  `suspended_charger`;
- Stop mappings, including the observed `finishing` state;
- stale and conflicting-source behavior;
- whether a newer contradictory Direct state always wins;
- behavior when Direct is absent for the entire action.

Current evidence gives this fallback no latency benefit, so it should not be
the first production change.

### 5. Per-action diagnostics

Step 1b adds a bounded, identifier-free attempt record similar to settings
readback diagnostics. It retains:

- action and UTC issue time;
- SET-reply latency/result;
- pre-command Direct state and age;
- first post-command Direct and PowerOcean states plus relative latency;
- selected confirmation source;
- whether a progress extension was granted;
- final outcome and elapsed seconds.

This removes reliance on recorder state changes, which omit same-state
heartbeats and cannot expose monotonic source generations.

## Test plan

Prefer extracting the evidence decision into a pure helper so it can be tested
without a full Home Assistant runtime.

Required unit cases:

- a provider-overwritten canonical state cannot make Direct evidence startable
  or stoppable;
- a stale matching Direct state cannot confirm a new command;
- a new Direct accepted state confirms immediately;
- a repeated same-state heartbeat is still a new observation where that state
  is an accepted outcome;
- PowerOcean `preparing` can extend Start but cannot confirm it;
- Direct `plugged_in` only extends when it is a real post-command transition;
- an extension is granted at most once and respects an absolute deadline;
- stale or wrong-serial PowerOcean data is rejected;
- a newer conflicting Direct state prevents PowerOcean success;
- no SET reply and no qualified readback preserve the existing errors;
- Stop keeps its 15-second deadline until separate evidence justifies a change.

Required bounded live validation:

1. run several reversible Start/Stop pairs with the app closed;
2. capture the new per-action diagnostics after every operation;
3. include at least one Solar-paused Start if naturally reproducible;
4. verify that PowerOcean does not falsely confirm stale or conflicting state;
5. verify the separate pending-button behavior from #11;
6. restore the original charging configuration after the test.

## Proposed implementation slices

1. **Source correctness and diagnostics** — implemented locally: Direct-based
   availability, source-coupled confirmation, pure helper tests, and bounded
   attempt records. No timeout or success-policy change. Live validation is
   pending.
2. **Start progress extension** — implement only after the new diagnostics
   confirm the transition timing; retain the absolute ceiling and fail-closed
   result.
3. **Optional PowerOcean success fallback** — defer until a live case shows an
   actual benefit and validates conflict handling.

Issue #11 can be implemented independently. It should consume a shared pending
flag, while this issue determines which evidence completes that pending action.
