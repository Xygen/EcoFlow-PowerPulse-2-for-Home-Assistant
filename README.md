# EcoFlow PowerPulse 2 for Home Assistant

Custom integration for EcoFlow PowerPulse 2 EV chargers.
It follows the independent Home Assistant integration structure of
[EcoFlow PowerGlow for Home Assistant](https://github.com/Xygen/EcoFlow-PowerGlow-for-Home-Assistant).

## Supported installation

EcoFlow PowerPulse wallboxes can in principle be operated without a
PowerOcean inverter. This applies both to the first-generation product named
**PowerPulse** (without a version number) and to **PowerPulse 2**.

This project deliberately supports and researches only **PowerPulse 2 used
with a linked PowerOcean inverter/system**. First-generation PowerPulse devices
and standalone PowerPulse 2 installations are out of scope and must not be
assumed to work with this integration. The linked PowerOcean is currently an
essential source for the richer provider snapshot and passive protocol
diagnostics.

## Documentation

- [Documentation index](docs/index.md): choose the right document for use,
  implementation, validation, or protocol research
- [User guide](docs/user-guide.md): installation, entities, controls, and
  known limits
- [Validation status](docs/validation.md): evidence-backed validation matrix
  and known v1.0.0 limitations
- [Project backlog](docs/backlog.md): the single authoritative list of active
  and deferred work
- [Data-path overview](docs/data_paths_overview.md): current technical
  reference for confirmed read and write paths
- [Protocol observations](docs/protocol_observations.md) and the
  [Issue #247 WIP report](docs/issue_247_wip_report.md): chronological
  evidence archives, not current product-status references

## Current scope

Version `1.0.0` keeps automatic MQTT activity listen-only and provides
disabled-by-default, user-triggered controls:

- EcoFlow app-account login and PowerPulse discovery
- listen-only cloud MQTT connection (WSS)
- a retained, explicitly named **Direct wallbox** telemetry group from the
  known CP307 heartbeat fields: charging state and power, phase voltage and
  current, session duration and energy, and cumulative charging energy
- a separate **PowerOcean** session group decoded from the linked inverter's
  coherent PowerPulse 2 accessory-relay report (`241/3`): charging power and
  state plus session duration and energy. The compatible `209/8` session form
  is also understood, but neither path overwrites the direct wallbox entities
- operating mode, Smart ready-by time, and Smart energy target from the
  provider snapshot when EcoFlow reports them
- Smart target type and distance from the fast direct report, including the
  calculated energy used by the charger in distance mode
- continuous-charging state in Solar mode, decoded from the live-confirmed
  provider flag while keeping the separately stored minimum current unchanged
- Solar minimum charging current as a normal Ampere sensor, converted from the
  live-confirmed tenths-of-an-ampere provider value; its raw diagnostic sensor
  remains available separately
- passive decoding of the direct C376 `241/44` parameter report, which arrives
  about once per second and provides the confirmed mode, Continuous-charging
  and Plug-and-Play flags, maximum output current, Solar minimum current,
  Custom current, and raw phase selection without waiting for the cached
  provider snapshot
- screen/LED state and stored brightness from the live-confirmed six-byte
  `241/44 -> 1.4.8.21` block, allowing these entities to recover after a reload
  without an app or Home Assistant settings write
- normal Ampere presentation of the Custom-mode current and fast phase enum
  readback
- controls for operating mode, phase selection, Plug-and-Play,
  battery-discharge blocking, Solar Continuous charging, maximum output
  current, Solar minimum current, and Custom-mode current
- charging-time interlocks for the five controls confirmed locked by the app:
  operating mode, phase selection, maximum output current, Solar minimum
  current, and Continuous charging. Availability and the backend write path
  both enforce the same live charging-state rule
- disabled-by-default Start and Stop buttons using the confirmed `241/100`
  selectors. They require a fresh heartbeat before publishing and a newer
  heartbeat with the expected physical state after the acknowledged command;
  Start is unavailable while no vehicle is connected
- Smart controls for ready-by date/time, energy/distance target type and the
  selected target value; Smart writes preserve the captured nested settings
  block rather than inventing missing defaults
- maximum output current, Plug-and-Play, phase selection, battery-discharge
  blocking, screen/LED state, and both brightness settings from the live-
  confirmed CP307 settings report
- optional direct-wallbox voltage, current, duration, and raw diagnostic values
  when reported
- cumulative and per-session charging energy as normal kWh sensors, converted
  from the confirmed Wh heartbeat fields while retaining their raw diagnostics
- numeric session duration in seconds with Home Assistant's duration metadata;
  Home Assistant can present it in a suitable user-selected time unit
- redacted MQTT frame capture grouped by channel and `(cmd_func, cmd_id)`
- passive observation of app-auth and device-facing SET candidate topics
- separate bounded capture of app-auth GET requests, retaining only safe JSON
  operation metadata or Protobuf routing fields and never the raw GET payload
- privacy-safe structural inspection of the small PowerOcean `96/97`
  background command, the acknowledged `241/102` settings route, and the
  observed `241/100` Start/Stop route,
  runtime-keyed opaque-field equality checks, and bounded request/retry/reply
  correlation by sequence number; EcoFlow header field 6 is treated as
  `enc_type` and field 11 as `need_ack`, allowing the nested `241/102` protobuf
  structure to be inspected while raw command bodies remain omitted
- identifier-free MQTT subscription result codes in diagnostics
- passive discovery and observation of a linked PowerOcean MQTT source, with
  parent payloads omitted and only privacy-safe numeric PowerPulse accessory
  fields retained for protocol comparison
- read-only provider-detail lookup on the linked PowerOcean, matched back to
  the embedded PowerPulse serial without retaining the raw provider response
- a coordinator watchdog that retries interrupted MQTT connections
- bounded automatic recovery when both previously observed C376 report
  families have remained stale for five minutes: only the listen-only WSS
  client is rebuilt, with a 30-minute retry cooldown and no MQTT publish
- disabled-by-default diagnostic entities showing whether the direct C376
  settings and heartbeat streams are fresh, renewing existing read
  subscriptions, and rebuilding the C376 WSS session with a new Client ID;
  both experimental actions send no MQTT publish or device command
- a delayed, coalesced provider refresh after a matched official-app
  `241/102` settings reply; explicit HA writes instead verify synchronously,
  preferring direct `241/44` readback and then requesting bounded fresh provider
  snapshots. Cached merged values never confirm a write

The MQTT transport retains its hard `listen_only` guard for every automatic
publish path. All controls are disabled in the entity registry
by default and use a separate, user-triggered path limited to observed
PowerOcean-routed `241/102 -> 4.*` settings commands and the separate confirmed
`241/100` Start/Stop command. They become available only
after the charger supplies its opaque accessory descriptor, requires exactly
one connected PowerOcean source, and reports success only after both a matching
`set_reply` and either fresh direct or raw provider readback. Current controls
accept whole values from 6 through 16 A; Solar, Custom, and Smart controls
additionally enforce their applicable operating-mode conditions. Smart-mode
selection requires previously read device settings, avoiding guessed timestamps
or targets. Phase selection prefers a fresh direct `241/44` value. When it is
stale, the control can use only the dedicated, source-qualified
Parent-Accessory provider fallback; stale merged or device-detail values cannot
qualify. The remaining live validation is tracked as `PHASE-01` in the backlog.

During a live charging session the EcoFlow app allowed Plug-and-Play,
battery-discharge blocking, screen, LED, and their brightness controls. dev28
keeps those available while preventing the five app-locked settings above from
being published. Other mode-specific charging-time combinations remain
evidence-gated in the project backlog.

## Open work

The current roadmap, protocol investigations, safety tests, and release
requirements are maintained only in the [project backlog](docs/backlog.md).
The dev29 Start/Stop controls completed a reversible live vehicle test from
Home Assistant. They remain disabled by default so users must still opt in to
device control. Version 0.1.0 added the confirmed cumulative/session energy and
numeric duration entities. Remaining protocol and safety work is tracked only
in the backlog.

The operating-mode control uses live-captured requests: `4.2=1` Fast charging,
`4.2=2` Solar, `4.2=3` Custom, and `4.2=4` Smart. Mode-specific companion fields
are included where the app included them and every command still needs matching
fresh direct or raw provider readback.

## Versioning and releases

This project uses Semantic Versioning. Regular releases use `MAJOR.MINOR.PATCH`
and matching Git tags such as `v0.1.0`. Patch releases contain compatible fixes;
minor releases add functionality. Intentional preview builds use explicit
prerelease identifiers such as `-beta.1`; the earlier sequential `-devNN`
scheme ended with dev30. Version `1.0.0` is the first stable release; its
scope and accepted limitations are recorded in the
[v1.0.0 release record](docs/backlog.md#v100-release-record).

## Build the release ZIP

Run from the repository root:

```powershell
pwsh -File scripts/build_release.ps1
```

The versioned archive is written to `dist/`. It contains
`custom_components/ecoflow_powerpulse2/` and excludes Python cache files.

## Installation

Extract the generated ZIP directly into the Home Assistant `config` directory.
The resulting path must be
`config/custom_components/ecoflow_powerpulse2/manifest.json`. Restart Home
Assistant, then add **EcoFlow PowerPulse 2** under
**Settings > Devices & services**.

Home Assistant 2026.3 and newer display the bundled integration icon from the
local `brand` directory. HACS 2.0.5 may still show "Icon not available" in its
downloads list despite a correct installation; this is the upstream HACS
frontend limitation tracked in
[`hacs/integration#5223`](https://github.com/hacs/integration/issues/5223), not
a missing file in this repository.

The telemetry parser and controls have been validated against live C376 MQTT
frames on the supported PowerPulse 2 plus PowerOcean topology. The protocol
remains reverse-engineered, so controls are disabled by default and require
explicit user opt-in. Current control gates, transport behavior, and remaining
validation are described in the [user guide](docs/user-guide.md),
[validation status](docs/validation.md), and [backlog](docs/backlog.md).

The direct transport is listen-only during automatic operation. If both
previously observed direct report families remain stale for five minutes, the
integration can rebuild only its listen-only WSS client under a bounded
cooldown; it does not publish a charger command. Chronological transport-test
evidence is retained in the [protocol observations](docs/protocol_observations.md).

## Diagnostic capture workflow

After the integration is connected, perform one action at a time:

1. Download diagnostics while the charger is idle.
2. Start charging in the EcoFlow app and download diagnostics again.
3. Change the charging limit once and download a third diagnostics file.
4. Stop charging and download a final diagnostics file.

Serial numbers and the EcoFlow user ID are replaced inside stored PowerPulse
payloads. Raw PowerOcean payloads are never included in diagnostics; only
numeric accessory fields and byte-field sizes are retained. Review diagnostics
before sharing them because reverse-engineered protocols may still expose
device-specific state.

In diagnostics, `mqtt_command_frames` contains only observed SET traffic and
SET replies. `mqtt_request_frames` separately retains observed GET requests;
raw request bodies and request IDs are omitted. `mqtt_frame_buckets` preserves
samples separately by channel and
command tuple so frequent heartbeat frames cannot evict a rare command. The
`mqtt_subscriptions` result codes show whether the local MQTT client accepted
each identifier-free subscription request for transmission; a value of `0`
does not independently prove a later broker SUBACK.

## Acknowledgements and license

MQTT/authentication helpers are adapted from the MIT-licensed PowerGlow
integration. MQTT capture and routing design also references the MIT-licensed
[`ecoflow-energy-ha`](https://github.com/shuette42/ecoflow-energy-ha) project.
Protocol field research references the Apache-2.0-licensed
[`ha-ef-ble`](https://github.com/rabits/ha-ef-ble) project; no source from that
project is currently bundled. See [NOTICE](NOTICE) and [LICENSE](LICENSE).
