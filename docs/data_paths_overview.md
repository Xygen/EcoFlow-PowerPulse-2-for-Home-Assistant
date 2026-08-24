# PowerPulse 2 data-path overview

This page provides a reader-friendly overview of the data paths observed for a
PowerPulse 2 connected to a PowerOcean system. It complements the detailed,
chronological evidence in [protocol_observations.md](protocol_observations.md).

The tables distinguish device readback from app-write observations. A fast
acknowledgement of an app request is not automatically a trustworthy state
value. The integration therefore remains read-only and uses only confirmed
device or provider reports for Home Assistant entity state.

`—` means that no value has been identified on that path. Values marked
**raw** are intentionally not assigned a final unit or complete semantic
mapping yet.

## Confirmed read paths

| Value or function | Wallbox heartbeat `2/33` | Wallbox settings report `2/34` | Fast wallbox report `241/44 -> 1.4.8` | PowerOcean HTTP `pileChargingParamReport` |
| --- | --- | --- | --- | --- |
| Typical update | Continuous or event-driven | When a settings report is emitted | Approximately once per second | Normal poll every 30 seconds; the provider cache can lag |
| Charging state | Field `1` | — | — | `chargingStatus` |
| Charging power | Field `28` | — | — | `chargingPwr` |
| Phase voltage | Field `29` | — | — | — |
| Phase current | Field `30` | — | — | — |
| Total energy, raw | Field `9` | — | — | — |
| Session duration | Field `41`, seconds | — | — | — |
| Session energy, raw | Field `42`; `1815` corresponded to about `1.82 kWh` in one app display | — | — | — |
| Suspend reason, raw | Field `102` | — | — | — |
| Charge-current setpoint, raw | Field `17`; exact role still needs separation | — | — | — |
| Operating mode | — | — | `1.4.8.2`: `1` Fast, `2` Solar, `3` Custom, `4` Smart | `paramSet.workMode` |
| Continuous charging | — | — | Bit `0x10` in `1.4.8.1`; `16` means enabled when no other known bit is set | Bit `0x10` in `paramSet.switchBits` |
| Maximum output current | Field `18` as current limit | Field `9`; `160` = 16 A | `1.4.8.4`; `160` = 16 A | `paramSet.currentOuputMax` |
| Solar minimum current | — | — | `1.4.8.6`; `70` = 7 A and `60` = 6 A | `paramSet.solarCurrentMin` |
| Custom/user current, raw | — | — | `1.4.8.8`; currently observed as `60` | `paramSet.userCurrentSet` |
| Phase selection | — | Field `11`: `1` one phase, `2` three phase, `3` auto | `1.4.8.7`; only `0` = auto has been paired so far | `paramSet.phaseSpecified`, raw |
| Plug-and-Play | — | Field `2`: `0`/`1` | Bit `0x02` in `1.4.8.1`; confirmed by `16 -> 18 -> 16` | Bit `0x02` in `paramSet.switchBits` |
| LED enabled | — | Field `13`: `0`/`1` | — | — |
| LED brightness | — | Field `14`, percent | — | — |
| Screen enabled | — | Field `15`: `0`/`1` | — | — |
| Screen brightness | — | Field `16`, percent | — | — |
| Battery discharge disabled | — | Field `22`: `0`/`1` | — | — |
| Smart ready-by time | — | — | Possibly contained in an unnamed byte field; not decoded | `paramSet.smartMode.timeToUseCar` |
| Smart energy target | — | — | Possibly contained in an unnamed byte field; not decoded | `paramSet.smartMode.chargeTarget`; `30000` = 30 kWh |
| Smart distance target | — | — | Unknown | Stored in another, still unidentified provider field |
| Vehicle consumption, raw | — | — | Unknown | `vehicleInfo.currentVehicleComsumption` |
| Unassigned content | — | Additional fields may exist | Byte fields `5`, `9`, `21`, and `31`, with observed sizes 16, 14, 6, and 10 bytes | Other unassigned provider fields exist |

The installed dev16 build confirmed the practical difference between the two
main settings read paths. Restoring the Solar minimum from 7 A to 6 A updated
the Home Assistant entities after about 1.77 seconds through `241/44`; the
provider fallback completed only about 20.26 seconds after the app SET.

## Observed write and research paths

These paths are useful for protocol research but are not currently used as
authoritative Home Assistant state.

| Value or function | App-write path `241/102 -> 4.*` | PowerOcean accessory report `209/8` | Unassigned `96/97` traffic |
| --- | --- | --- | --- |
| Role | App sends settings; a same-sequence reply confirms transport correlation but does not echo the settings | Possible additional read path | Likely periodic PowerOcean background traffic |
| Settings bitmask | `4.1`; observed values include `16`, `18`, and `0` | Earlier field assignments were withdrawn pending controlled evidence | Not assigned |
| Operating mode | `4.2` | Not confirmed | — |
| Maximum output current | `4.3`, 0.1 A | Not confirmed | — |
| Solar minimum current | `4.4`, 0.1 A | Not confirmed | — |
| Phase selection | `4.5` | Not confirmed | — |
| Custom-mode current | `4.6`, 0.1 A | Not confirmed | — |
| Smart settings | Nested block `4.7` | Not confirmed | — |
| Observed response | Same-sequence reply after about 50-226 ms | Unknown | No assigned reply |
| Suitable as HA state | No; it is an observed request, not device readback | Still under investigation | No current evidence |

## Fast-path coverage and next candidates

Every confirmed scalar currently decoded from `241/44 -> 1.4.8` is already
used by at least one Home Assistant entity:

| Fast field | Current HA use | Further useful work |
| --- | --- | --- |
| `1` settings bitmask | Continuous-charging and Plug-and-Play binary sensors plus the raw settings-flags sensor | Investigate only the remaining unassigned bits through controlled comparisons |
| `2` operating mode | Operating-mode enum sensor | Already fully used for the four confirmed modes |
| `4` maximum output current | Normal Ampere sensor plus disabled-by-default raw sensor | Already fully used |
| `6` Solar minimum current | Normal Ampere sensor plus disabled-by-default raw sensor | Already fully used and live-validated at 6 A and 7 A |
| `7` phase selection | Disabled-by-default raw phase sensor | Confirm one-phase, three-phase, and auto values, then feed the normal phase enum sensor from this fast path |
| `8` Custom/user current | Disabled-by-default raw user-current sensor | Pair at least two Custom-mode slider values, then add a normal Ampere sensor if 0.1 A scaling is confirmed |

The unnamed byte fields `5`, `9`, `21`, and `31` are the remaining candidates
for additional fast values. Controlled one-setting-at-a-time comparisons are
needed before parsing them. Smart ready-by/target settings are the strongest
first test because they are already known on the slower provider path and can
be compared without guessing. Screen, LED, battery, vehicle, and other values
may or may not be present in those blocks.
