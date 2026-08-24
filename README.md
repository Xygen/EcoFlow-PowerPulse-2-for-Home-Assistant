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

- [Data-path overview](docs/data_paths_overview.md): reader-friendly tables
  showing which values have been found on each wallbox and PowerOcean path
- [Protocol observations](docs/protocol_observations.md): chronological live
  evidence and field mappings
- [Issue #247 WIP report](docs/issue_247_wip_report.md): current research state,
  limitations, and remaining work

## Current scope

Version `0.1.0-dev21` keeps automatic MQTT activity listen-only and provides
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
- a delayed, coalesced provider refresh after a `241/102` settings reply has
  been matched to its previously observed official-app request; this only reads
  fresh state and does not publish MQTT traffic. A recent direct `241/44`
  device report takes precedence for its nine derived keys; if that report is
  absent for ten seconds, the normal provider fallback resumes automatically

The MQTT transport retains its hard `listen_only` guard for every automatic
publish path. All controls are disabled in the entity registry
by default and use a separate, user-triggered path limited to observed
PowerOcean-routed `241/102 -> 4.*` commands. They become available only
after the charger supplies its opaque accessory descriptor, requires exactly
one connected PowerOcean source, and reports success only after both a matching
`set_reply` and direct device readback. Current controls accept whole values
from 6 through 16 A; Solar, Custom, and Smart controls additionally enforce
their applicable operating-mode conditions. Smart-mode selection requires
previously read device settings, avoiding guessed timestamps or targets.

## Planned controls

Further control targets are:

1. start and stop charging
2. charging-current/power limit while charging, including confirmed interlocks

The CP307 schema already identifies likely current parameters, but neither the
cloud command tuple nor the exact start/stop payload has been confirmed on
PowerPulse 2 hardware. Controls will only be exposed after comparing redacted
MQTT frames generated by the official EcoFlow app and verifying device replies.

The operating-mode control uses live-captured requests: `4.2=1` Fast charging,
`4.2=2` Solar, `4.2=3` Custom, and `4.2=4` Smart. Mode-specific companion fields
are included where the app included them and every command still needs matching
direct device readback.

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
general use. Phase, battery, Continuous, maximum-current, and Solar-current
writes have been live-tested from HA. The installed dev20 mode, Custom-current,
Plug-and-Play, and Smart controls have also completed reversible live tests with
SET acknowledgement and direct readback while no vehicle was connected.

## Capturing the missing protocol evidence

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
SET replies. `mqtt_frame_buckets` preserves samples separately by channel and
command tuple so frequent heartbeat frames cannot evict a rare command. The
`mqtt_subscriptions` result codes show whether the broker accepted each
identifier-free subscription label; a value of `0` means accepted.

## Acknowledgements and license

MQTT/authentication helpers are adapted from the MIT-licensed PowerGlow
integration. MQTT capture and routing design also references the MIT-licensed
[`ecoflow-energy-ha`](https://github.com/shuette42/ecoflow-energy-ha) project.
Protocol field research references the Apache-2.0-licensed
[`ha-ef-ble`](https://github.com/rabits/ha-ef-ble) project; no source from that
project is currently bundled. See [NOTICE](NOTICE) and [LICENSE](LICENSE).
