# PowerPulse 2 data-path overview

This page provides a reader-friendly overview of the data paths observed for a
PowerPulse 2 connected to a PowerOcean system. It complements the detailed,
chronological evidence in [protocol_observations.md](protocol_observations.md).

The tables distinguish device readback from app-write observations. A fast
acknowledgement of an app request is not automatically a trustworthy state
value. Read entities therefore use confirmed device or provider reports. The
Version 0.1.0 settings controls are evidence-gated and require acknowledgement
plus either fresh direct device readback or a post-command raw provider
confirmation.
Phase selection is narrower: provider `phaseSpecified` is now mapped as
`0` Auto, `1` one phase, and `2` three phase, but provider cache lag means a
fresh HTTP poll is not automatically fresh device-state evidence. Phase control
therefore uses the Parent-Accessory value only through a dedicated source-aware
fallback: availability requires the field in the latest source snapshot and an
exact raw `0/1/2`; post-write confirmation additionally requires a transition
from a different pre-write value to the target. Generic Provider No-op is
disabled for phase.
Start/Stop uses its separate `241/100` route and requires a newer heartbeat with
an allowed physical charging state after the matching reply.

`—` means that no value has been identified on that path. Values marked
**raw** are intentionally not assigned a final unit or complete semantic
mapping yet.

## Confirmed read paths

| Value or function | Wallbox heartbeat `2/33` | Wallbox settings report `2/34` | Fast wallbox report `241/44 -> 1.4.8` | PowerOcean HTTP `pileChargingParamReport` |
| --- | --- | --- | --- | --- |
| Typical update | Continuous or event-driven | When a settings report is emitted | Approximately once per second | Normal poll every 30 seconds; the provider cache can lag |
| Charging state | Field `1` | — | — | `chargingStatus` |
| Charging power | Field `28`, consistent with real power. One-phase and balanced three-phase comparisons produced plausible power factors of about 0.97-0.98 against simultaneous voltage/current summaries | — | — | `chargingPwr`; matched direct power closely in a stable one-phase observation, while one time-offset three-phase value happened to match `3 * maximum voltage * maximum current`. Its exact calculation remains unresolved because the paths are asynchronous and the direct phase entities are maxima, not per-phase sums |
| Phase voltage | Field `29` | — | — | — |
| Phase current | Field `30` | — | — | — |
| Total charging energy | Field `9`, Wh. Across 357 history samples and several session resets it increased without a decrease; at about 1.29 kW it rose by 21–22 Wh/min. Exposed normally in kWh; raw diagnostics remain available | — | — | — |
| Session duration | Field `41`, seconds. Exposed as a numeric HA duration sensor | — | — | — |
| Charging-session energy | Field `42`, Wh. `1815` corresponded to about `1.82 kWh` in the app; live sessions produced `19` after 59 s, `451` after 21 min 08 s, and `3685` after 2 h 50 min. Exposed normally in kWh and resets per session; raw diagnostics remain available | — | — | — |
| Suspend reason, raw | Field `102` | — | — | — |
| Charge-current setpoint, raw | Field `17`; exact role still needs separation | — | — | — |
| Operating mode | — | — | `1.4.8.2`: `1` Fast, `2` Solar, `3` Custom, `4` Smart | `paramSet.workMode` |
| Continuous charging | — | — | Bit `0x10` in `1.4.8.1`; `16` means enabled when no other known bit is set | Bit `0x10` in `paramSet.switchBits` |
| Maximum output current | Field `18` as current limit | Field `9`; `160` = 16 A | `1.4.8.4`; `160` = 16 A | `paramSet.currentOuputMax` |
| Solar minimum current | — | — | `1.4.8.6`; `70` = 7 A and `60` = 6 A | `paramSet.solarCurrentMin` |
| Custom/user current | — | — | `1.4.8.8`; `60` = 6 A and `110` = 11 A | `paramSet.userCurrentSet` |
| Phase selection | — | Field `11`: `1` one phase, `2` three phase, `3` auto; separately diagnosed, not yet a write-confirmation source | `1.4.8.7`: `0` auto, `1` one phase, `2` three phase; authoritative while fresh | `paramSet.phaseSpecified`: `0` auto, `1` one phase, `2` three phase; source-qualified fallback with exact raw validation and transition-based post-write confirmation |
| Plug-and-Play | — | Field `2`: `0`/`1` | Bit `0x02` in `1.4.8.1`; confirmed by `16 -> 18 -> 16` | Bit `0x02` in `paramSet.switchBits` |
| LED enabled | — | Field `13`: `0`/`1` | `1.4.8.21`, byte 1: `0`/`1` | — |
| LED brightness | — | Field `14`, percent | `1.4.8.21`, byte 3: `25`/`50`/`75`/`100` | — |
| Screen enabled | — | Field `15`: `0`/`1` | `1.4.8.21`, byte 2: `0`/`1` | — |
| Screen brightness | — | Field `16`, percent | `1.4.8.21`, byte 4: `25`/`50`/`75`/`100` | — |
| Battery discharge disabled | — | Field `22`: `0`/`1` | — | — |
| Smart ready-by time | — | — | `1.4.8.31.1`, Unix timestamp | `paramSet.smartMode.timeToUseCar` |
| Smart target type | — | — | `1.4.8.31.2`: `1` energy, `2` distance | Inferred through the selected target |
| Smart energy target | — | — | Energy mode: `1.4.8.31.3`, Wh | `paramSet.smartMode.chargeTarget`; `30000` = 30 kWh |
| Smart distance target | — | — | Distance mode: `1.4.8.31.4`, km | Provider energy target becomes `0` in distance mode |
| Smart calculated energy | — | — | Distance mode: `1.4.8.31.3`; 300 km produced 45000 Wh | — |
| Vehicle consumption, raw | — | — | Unknown | `vehicleInfo.currentVehicleComsumption` |
| Unassigned content | — | Additional fields may exist | Byte fields `5` and `9`; both remained byte-identical across 64 decoded frames during an Auto/one-phase/three-phase/Auto comparison and are not the direct phase-selection field. Fields `21` and `31` are decoded for display and Smart settings | Other unassigned provider fields exist |

The installed dev16 build confirmed the practical difference between the two
main settings read paths. Restoring the Solar minimum from 7 A to 6 A updated
the Home Assistant entities after about 1.77 seconds through `241/44`; the
provider fallback completed only about 20.26 seconds after the app SET.

## Separate direct-wallbox and PowerOcean session entities

The existing CP307 heartbeat sensors remain separate and keep their established
unique IDs. Their displayed names now share the `Wallbox direct` / `Wallbox
direkt` prefix so the source is explicit. Provider polls may still update the
coordinator's canonical values for control safety, but cannot overwrite the
new `direct_*` source aliases used by these entities.

The linked PowerOcean's PowerPulse 2 accessory-relay report `241/3` is exposed
as a second, consistently named `PowerOcean` group. Its nested
`pileChargingParamReport` contains one coherent session snapshot rather than a
lifetime meter. The parser also understands the equivalent `209/8`
`EVChargingParamReport` used by the other PowerPulse route:

| PowerOcean entity | PowerPulse 2 `241/3` field | Compatible `209/8` field | Unit / mapping |
| --- | --- | --- | --- |
| Charging power | `4.6` (`charging_pwr`) | `8` (`ev_pwr`) | W; native reported real power |
| Charging status | `4.4` (`charging_status`) | `6` (`charging_status`) | Native EVSE states: none, available, preparing, charging, suspended by charger/vehicle, finishing, faulted |
| Session energy | `4.8.5` (`order_charging_energy`) | `9` (`ev_charging_energy`) | Wh on the wire, presented as kWh; resets with a new session |
| Session duration | `4.8.6` (`order_time`) | `11` (`order_time`) | seconds; resets with a new session |

Fields for the charger serial, vehicle IDs, operating mode, Plug-and-Play,
timestamps, grid preference and settings flags also exist in the report. They
are deliberately not added as entities: serials are used only internally for
routing, vehicle IDs are privacy-sensitive, and the remaining fields are
redundant or need more local validation. Other `209` or `241` command IDs are
not accepted as this coherent session report.

## Observed write and research paths

These paths are useful for protocol research but are not currently used as
authoritative Home Assistant state.

| Value or function | App-write paths routed through PowerOcean | PowerOcean accessory report `209/8` | Unassigned `96/97` traffic |
| --- | --- | --- | --- |
| Role | Settings use `241/102 -> 4.*`; Start/Stop uses `241/100`. A same-sequence reply confirms transport correlation but does not itself prove device state | Possible additional read path | Likely periodic PowerOcean background traffic |
| Settings bitmask | `4.1`; bit `0x01` battery-discharge blocking, `0x02` Plug-and-Play, `0x10` Continuous charging | Earlier field assignments were withdrawn pending controlled evidence | Not assigned |
| Operating mode | `4.2` | Not confirmed | — |
| Maximum output current | `4.3`, 0.1 A | Not confirmed | — |
| Solar minimum current | `4.4`, 0.1 A | Not confirmed | — |
| Phase selection | `4.5` | Not confirmed | — |
| Custom-mode current | `4.6`, 0.1 A | Not confirmed | — |
| Smart settings | Nested block `4.7` | Not confirmed | — |
| Screen/LED settings | Nested bytes `4.21`: LED enable, screen enable, LED %, screen %, `0`, `0` | Not confirmed | — |
| Start/Stop | Official-app actions use `241/100` with a 25-byte body addressed to the linked PowerOcean: protobuf field 2 is `1` for Stop and `2` for Start; field 1 is the unchanged accessory descriptor. Both selectors were confirmed by matching replies and heartbeat state transitions | Not confirmed | — |
| Observed response | Same-sequence reply after about 50-226 ms | Unknown | No assigned reply |
| Suitable as HA state | No; SET observations are not state. Controls require separate fresh direct or provider readback | Still under investigation | No current evidence |

dev23 uses confirmed app-write fields only for disabled-by-default controls:
`4.1` for battery, Plug-and-Play, and Continuous flags; `4.2` for all four
operating modes; `4.3` for maximum current; `4.4` for Solar minimum current;
`4.5` for phase selection; `4.6` for Custom current; and nested `4.7` for Smart
ready-by and target settings; nested `4.21` controls screen and LED state plus
their 25/50/75/100% brightness. Every write requires a same-sequence reply and
then either matching direct `241/44` readback or a post-command raw provider
snapshot that explicitly contains the expected key and value. Cached merged
state alone never confirms a write. Phase is stricter: it never uses generic
Provider No-op, ignores Device-Detail and merged state, and accepts Parent-
Accessory confirmation only after a different pre-write value transitions to
the requested target.

Version 0.1.0 retains the dev29 disabled-by-default Start and Stop buttons. Their
`241/100` reply waiter is keyed by command tuple and sequence. Availability
requires a recent heartbeat; the backend repeats the state check immediately
before publishing and then waits up to 15 seconds for a newer heartbeat that
confirms the action. A SET reply alone is never treated as success.

Both buttons completed a reversible live HA test with a connected vehicle.
Stop changed the heartbeat from `charging` to `charge_complete` in about 1.53
seconds. Start changed it back to `charging` in about 4.34 seconds, reset the
session counters, and produced 1.304 kW, 5.77 A, 233.3 V, and raw session energy
`20` after one minute.

## Charging-time control matrix

The first connected-vehicle session confirmed the following official-app
behavior while the charger reported `charging`:

| Control | Official app while charging | dev29 Home Assistant behavior |
| --- | --- | --- |
| Operating mode | Locked | Unavailable; backend rejects bypass attempts |
| Phase selection | Locked | Unavailable; backend rejects bypass attempts |
| Maximum output current | Locked | Unavailable; backend rejects bypass attempts |
| Solar minimum current | Locked | Unavailable; backend rejects bypass attempts |
| Continuous charging | Locked | Unavailable; backend rejects bypass attempts |
| Plug-and-Play | Allowed and live-tested | Available |
| Battery discharge disabled | Allowed and live-tested | Available |
| Screen/brightness | Allowed and live-tested | Available subject to screen-on brightness rule |
| LED/brightness | Allowed and live-tested | Available subject to LED-on brightness rule |
| Start charging | Not applicable while already charging | Unavailable while charging; also unavailable while unplugged |
| Stop charging | Allowed and live-tested | Available while charging or paused; requires fresh heartbeat confirmation |

The app tests changed shared `switchBits` from `16` to `18` for Plug-and-Play
and from `18` to `19` for battery-discharge blocking, then restored `18`.
Charging continued at approximately 1.29 kW throughout.

The 2026-08-26 idle test showed why the paths cannot share one blanket rule.
Mode and flag updates appeared in the provider snapshot about 12–15 seconds
after their SETs, so dev23 checks that strict raw path through approximately 20
seconds. Two acknowledged phase SETs produced no direct phase report, and at
that point the provider exposed only the not-yet-confirmed raw
`phaseSpecified` field. dev23 therefore kept the other controls usable with
provider fallback but made phase selection unavailable whenever recent direct
`phase_mode` readback was absent. After installing dev23 and restarting HA, the
revived direct path reported `one_phase`, proving that at least one earlier
acknowledged phase SET had been applied.

A later controlled phase diagnostic resolved the provider mapping. Selecting
one phase and three phases separately, forcing a provider refresh after each
direct confirmation, and finally restoring Auto showed parent-accessory
`phaseSpecified` raw values `1`, `2`, and `0` respectively. The first
three-phase provider poll still held the earlier `1`; a second poll roughly ten
seconds later delivered `2`. The mapping is therefore confirmed, while the
observed cache lag is exactly why PHASE-01 still requires source-aware
freshness, No-op, and post-write confirmation semantics before the provider is
used for phase-control confirmation. The wallbox device-detail source did not
reliably carry the phase field.

dev24 distinguishes the still-connected MQTT transport from freshness of the
direct report. A diagnostic binary sensor marks `241/44` fresh for ten seconds
after its latest frame. A separate disabled-by-default action can renew the
existing C376 quota, property, and GET-reply subscriptions without publishing
any device command. A controlled stale-stream test returned
`no_direct_report`: all three local subscribe calls succeeded, but no `241/44`
arrived during the ten-second window. Opening only the general home/device list
in the official app subsequently restarted `241/44` without a visible C376 GET
or SET on the subscribed topics; selecting PowerPulse itself was unnecessary.
Heartbeat `2/33`, including phase voltage, resumed about 47–54 seconds after
the direct settings stream in two observations. This points to an app-session
action, an unobserved topic, or an HTTP/backend request rather than simple topic
renewal.
dev25 exposes this distinction directly: the existing direct-stream sensor
tracks `241/44` for ten seconds, while a separate disabled-by-default heartbeat
sensor tracks receipt of `2/33` for 90 seconds. A second manual diagnostic
action rebuilds only the hard-listen-only C376 WSS client with a new Client ID
and its normal subscriptions. It does not send `get-all`, `latestQuotas`,
`EnergyStreamSwitch`, or any setting command.
The controlled stale test confirmed that this new WSS session restored
`241/44` after 1.779 seconds and `2/33` shortly afterward. dev26 reuses only
that verified session operation automatically after both previously observed
streams stay stale for five minutes. A 30-minute cooldown bounds failure
retries; the action remains hard listen-only.
The remaining isolation work is tracked only in the
[project backlog](backlog.md).

Official-app GET publishes now form a separate `observed_get` diagnostic path.
The capture retains a bounded summary of JSON operation metadata or generic
Protobuf routing fields, but omits raw request bodies and request IDs. This is
intended to distinguish an app GET from the possibility that merely opening
and subscribing in the app reactivates server-side delivery.

## Fast-path coverage and unresolved fields

Every confirmed scalar currently decoded from `241/44 -> 1.4.8` is already
used by at least one Home Assistant entity:

| Fast field | Current HA use | Mapping status |
| --- | --- | --- |
| `1` settings bitmask | Continuous-charging and Plug-and-Play binary sensors plus the raw settings-flags sensor | Some bits remain unassigned |
| `2` operating mode | Operating-mode enum sensor | Already fully used for the four confirmed modes |
| `4` maximum output current | Normal Ampere sensor plus disabled-by-default raw sensor | Already fully used |
| `6` Solar minimum current | Normal Ampere sensor plus disabled-by-default raw sensor | Already fully used and live-validated at 6 A and 7 A |
| `7` phase selection | Raw sensor, fast normal enum, and disabled-by-default phase control readback | Mapping confirmed for auto, one phase, and three phase |
| `8` Custom/user current | Raw sensor plus normal Ampere sensor | 6 A and 11 A confirmed the 0.1 A scaling |

The unnamed byte fields `5`, `9`, and `21` remain unassigned. Field `31` is
already decoded as the Smart block. The six-byte field `21` is the strongest
screen/LED candidate because the matching app-write display block is known,
but no direct mapping is confirmed. Planned comparisons are tracked only in the
[project backlog](backlog.md).
