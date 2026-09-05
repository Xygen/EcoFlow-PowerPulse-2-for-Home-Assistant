# PowerPulse 2 user guide

## Supported setup

This integration supports **PowerPulse 2 with a linked PowerOcean system**.
First-generation PowerPulse and standalone PowerPulse 2 installations are out
of scope.

## Installation

Build the release ZIP from the repository root:

```powershell
pwsh -File scripts/build_release.ps1
```

Extract the archive into the Home Assistant configuration directory so the
manifest is at `custom_components/ecoflow_powerpulse2/manifest.json`. Restart
Home Assistant, then add **EcoFlow PowerPulse 2** under **Settings > Devices &
services**.

## What Home Assistant shows

The integration deliberately keeps two telemetry sources separate:

- **Wallbox direct**: Direct C376 heartbeat data for charging state, power,
  voltage/current summaries, and energy/duration counters.
- **PowerOcean**: The linked inverter's coherent charging-session report for
  status, power, session energy, and session duration.

The values can update at different times and are not interchangeable. If the
official EcoFlow app display is the intended reference for a session value, use
the explicitly named PowerOcean entity rather than assuming it equals the
Direct entity.

## Controls and safety

Controls are disabled by default in Home Assistant. Enable only the controls
you need and treat every control as device operation.

- Automatic MQTT behavior is listen-only; user-triggered controls have a
  separate evidence-gated write path.
- Settings writes require a matching acknowledgement plus a qualified fresh
  readback. An acknowledgement alone is not success.
- Start and Stop require fresh device-state confirmation. Start is unavailable
  when no vehicle is connected.
- Some settings are unavailable while charging because the official app locks
  them too. Plug-and-Play, battery-discharge blocking, screen, LED, and their
  brightness controls have different observed charging-time rules.
- Phase control prefers Direct settings evidence and has a narrow, guarded
  provider fallback. Its unvalidated stale-stream edge cases are documented as
  a fail-closed `v1.0.0` limitation in `PHASE-01`.

See the [data-path overview](data_paths_overview.md) for the complete source
and confirmation model.

## Known limits

- The protocol is reverse-engineered and controls remain opt-in.
- Direct and PowerOcean values may differ because they are independent sources
  with different reporting cadence and semantics.
- Detailed phase-position telemetry, dynamic active-session current control,
  and historical PV/grid/battery attribution are deferred beyond v1.0.0.
- Solar paused-state policy remains a documented limitation; see `SAFE-02` in
  the [backlog](backlog.md).

## Diagnostics

Use diagnostics to capture a bounded, privacy-filtered view of integration
activity. Raw PowerOcean payloads and raw observed GET bodies are omitted;
review a diagnostics export before sharing it. The detailed capture workflow is
in the [README](../README.md#diagnostic-capture-workflow).
