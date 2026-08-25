# PowerPulse 2 data-path overview

This page provides a reader-friendly overview of the data paths observed for a
PowerPulse 2 connected to a PowerOcean system. It complements the detailed,
chronological evidence in [protocol_observations.md](protocol_observations.md).

The tables distinguish device readback from app-write observations. A fast
acknowledgement of an app request is not automatically a trustworthy state
value. Read entities therefore use confirmed device or provider reports. The
dev22 controls are evidence-gated and require acknowledgement plus either
fresh direct device readback or a post-command raw provider confirmation.

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
| Custom/user current | — | — | `1.4.8.8`; `60` = 6 A and `110` = 11 A | `paramSet.userCurrentSet` |
| Phase selection | — | Field `11`: `1` one phase, `2` three phase, `3` auto | `1.4.8.7`: `0` auto, `1` one phase, `2` three phase | `paramSet.phaseSpecified`, raw |
| Plug-and-Play | — | Field `2`: `0`/`1` | Bit `0x02` in `1.4.8.1`; confirmed by `16 -> 18 -> 16` | Bit `0x02` in `paramSet.switchBits` |
| LED enabled | — | Field `13`: `0`/`1` | — | — |
| LED brightness | — | Field `14`, percent | — | — |
| Screen enabled | — | Field `15`: `0`/`1` | — | — |
| Screen brightness | — | Field `16`, percent | — | — |
| Battery discharge disabled | — | Field `22`: `0`/`1` | — | — |
| Smart ready-by time | — | — | `1.4.8.31.1`, Unix timestamp | `paramSet.smartMode.timeToUseCar` |
| Smart target type | — | — | `1.4.8.31.2`: `1` energy, `2` distance | Inferred through the selected target |
| Smart energy target | — | — | Energy mode: `1.4.8.31.3`, Wh | `paramSet.smartMode.chargeTarget`; `30000` = 30 kWh |
| Smart distance target | — | — | Distance mode: `1.4.8.31.4`, km | Provider energy target becomes `0` in distance mode |
| Smart calculated energy | — | — | Distance mode: `1.4.8.31.3`; 300 km produced 45000 Wh | — |
| Vehicle consumption, raw | — | — | Unknown | `vehicleInfo.currentVehicleComsumption` |
| Unassigned content | — | Additional fields may exist | Byte fields `5`, `9`, and `21`; field `31` is now decoded for Smart settings | Other unassigned provider fields exist |

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
| Settings bitmask | `4.1`; bit `0x01` battery-discharge blocking, `0x02` Plug-and-Play, `0x10` Continuous charging | Earlier field assignments were withdrawn pending controlled evidence | Not assigned |
| Operating mode | `4.2` | Not confirmed | — |
| Maximum output current | `4.3`, 0.1 A | Not confirmed | — |
| Solar minimum current | `4.4`, 0.1 A | Not confirmed | — |
| Phase selection | `4.5` | Not confirmed | — |
| Custom-mode current | `4.6`, 0.1 A | Not confirmed | — |
| Smart settings | Nested block `4.7` | Not confirmed | — |
| Screen/LED settings | Nested bytes `4.21`: LED enable, screen enable, LED %, screen %, `0`, `0` | Not confirmed | — |
| Observed response | Same-sequence reply after about 50-226 ms | Unknown | No assigned reply |
| Suitable as HA state | No; SET observations are not state. Controls require separate fresh direct or provider readback | Still under investigation | No current evidence |

dev22 uses confirmed app-write fields only for disabled-by-default controls:
`4.1` for battery, Plug-and-Play, and Continuous flags; `4.2` for all four
operating modes; `4.3` for maximum current; `4.4` for Solar minimum current;
`4.5` for phase selection; `4.6` for Custom current; and nested `4.7` for Smart
ready-by and target settings; nested `4.21` controls screen and LED state plus
their 25/50/75/100% brightness. Every write requires a same-sequence reply and
then either matching direct `241/44` readback or a post-command raw provider
snapshot that explicitly contains the expected key and value. Cached merged
state alone never confirms a write.

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
