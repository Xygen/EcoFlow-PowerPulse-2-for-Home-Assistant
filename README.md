# EcoFlow PowerPulse 2 for Home Assistant

Development-stage custom integration for EcoFlow PowerPulse 2 EV chargers.
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

- [Project backlog](docs/backlog.md): the single authoritative list of open
  work and release documentation rules
- [Data-path overview](docs/data_paths_overview.md): reader-friendly tables
  showing which values have been found on each wallbox and PowerOcean path
- [Protocol observations](docs/protocol_observations.md): chronological live
  evidence and field mappings
- [Issue #247 WIP report](docs/issue_247_wip_report.md): chronological research
  state, evidence, and limitations

## Current scope

Version `0.1.0-dev24` keeps automatic MQTT activity listen-only and provides
disabled-by-default, user-triggered controls:

- EcoFlow app-account login and PowerPulse discovery
- listen-only cloud MQTT connection (WSS)
- charging state and charging power from known CP307 heartbeat fields
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
- normal Ampere presentation of the Custom-mode current and fast phase enum
  readback
- controls for operating mode, phase selection, Plug-and-Play,
  battery-discharge blocking, Solar Continuous charging, maximum output
  current, Solar minimum current, and Custom-mode current
- Smart controls for ready-by date/time, energy/distance target type and the
  selected target value; Smart writes preserve the captured nested settings
  block rather than inventing missing defaults
- maximum output current, Plug-and-Play, phase selection, battery-discharge
  blocking, screen/LED state, and both brightness settings from the live-
  confirmed CP307 settings report
- optional voltage, current, duration, and raw diagnostic values when reported
- human-readable session duration while retaining numeric seconds internally
- redacted MQTT frame capture grouped by channel and `(cmd_func, cmd_id)`
- passive observation of app-auth and device-facing SET candidate topics
- separate bounded capture of app-auth GET requests, retaining only safe JSON
  operation metadata or Protobuf routing fields and never the raw GET payload
- privacy-safe structural inspection of the small PowerOcean `96/97`
  background command and the acknowledged `241/102` Solar-current route,
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
- disabled-by-default diagnostic entities showing whether the direct C376
  settings stream is fresh and renewing only its existing read subscriptions;
  this experimental action sends MQTT SUBSCRIBE packets but no device publish
- a delayed, coalesced provider refresh after a matched official-app
  `241/102` settings reply; explicit HA writes instead verify synchronously,
  preferring direct `241/44` readback and then requesting bounded fresh provider
  snapshots. Cached merged values never confirm a write

The MQTT transport retains its hard `listen_only` guard for every automatic
publish path. All controls are disabled in the entity registry
by default and use a separate, user-triggered path limited to observed
PowerOcean-routed `241/102 -> 4.*` commands. They become available only
after the charger supplies its opaque accessory descriptor, requires exactly
one connected PowerOcean source, and reports success only after both a matching
`set_reply` and either fresh direct or raw provider readback. Current controls
accept whole values from 6 through 16 A; Solar, Custom, and Smart controls
additionally enforce their applicable operating-mode conditions. Smart-mode
selection requires previously read device settings, avoiding guessed timestamps
or targets. Phase selection is additionally available only while a fresh direct
`241/44` phase value exists, because the provider phase mapping is not yet
confirmed.

## Open work

The current roadmap, protocol investigations, safety tests, and release
requirements are maintained only in the [project backlog](docs/backlog.md).
Start/Stop and active-session controls remain unavailable until their captured
commands, physical readback, and charging-state interlocks satisfy that list.

The operating-mode control uses live-captured requests: `4.2=1` Fast charging,
`4.2=2` Solar, `4.2=3` Custom, and `4.2=4` Smart. Mode-specific companion fields
are included where the app included them and every command still needs matching
fresh direct or raw provider readback.

## Build the test ZIP

Run from the repository root:

```powershell
pwsh -File scripts/build_release.ps1
```

The versioned archive is written to `dist/`. It contains
`custom_components/ecoflow_powerpulse2/` and excludes Python cache files.

## Test installation

Extract the generated ZIP directly into the Home Assistant `config` directory.
The resulting path must be
`config/custom_components/ecoflow_powerpulse2/manifest.json`. Restart Home
Assistant, then add **EcoFlow PowerPulse 2** under
**Settings > Devices & services**.

Use a development/test Home Assistant instance. The telemetry parser has been
validated against live C376 MQTT frames, but the integration is not ready for
general use. All settings controls exposed through dev21 have completed
reversible live tests from HA with SET acknowledgement and matching readback
while no vehicle was connected. dev23 extends strict raw-provider confirmation
to cover the 12–15 second propagation observed after an idle period and records
privacy-safe details for each attempt. Its live-validation status is tracked in
the [project backlog](docs/backlog.md).

dev24 adds a separate idle-stream experiment. Its diagnostic button renews the
three existing C376 read subscriptions and waits up to ten seconds for a new
direct `241/44` report. It does not publish `get-all`, `latestQuotas`,
`EnergyStreamSwitch`, or a charger setting. The result and timing are retained
in privacy-safe diagnostics. This mechanism is not considered validated until
it is exercised after a genuine idle period.

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
