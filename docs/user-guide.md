# PowerPulse 2 user guide

This guide describes stable version **1.0.4**. The current release declaration is
maintained in the [documentation index](index.md). Test builds and their actual
validation status are recorded separately in [validation](validation.md#current-baseline).

## Supported setup

This integration supports **PowerPulse 2 with a linked PowerOcean system**.
First-generation PowerPulse and standalone PowerPulse 2 installations are out
of scope.

## Installation

### Recommended: Install through HACS

1. Open **HACS > Integrations** in Home Assistant.
2. Open the menu in the upper-right corner and select **Custom repositories**.
3. Enter the repository URL:

   `https://github.com/Xygen/EcoFlow-PowerPulse-2-for-Home-Assistant`

4. Select **Integration** as the repository category and add the repository.
5. Search for **EcoFlow PowerPulse 2** and install it.
6. Restart Home Assistant.
7. Add **EcoFlow PowerPulse 2** under **Settings > Devices & services**.

Until the repository is accepted into the HACS default list, the custom-
repository step is required. After acceptance, it can be installed directly
from the normal HACS integration list.

### Manual installation

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

### Choosing a power reading

Use the entity's displayed role/name to identify its source. Entity IDs can differ
with language, earlier installations or user renaming.

| Reading | What it means | Appropriate use |
| --- | --- | --- |
| Wallbox direct – Charging power | Power reported directly by the charger; updates can be slower than PowerOcean. | Compare against direct charging state and investigate actual charger reports. |
| PowerOcean – Charging power | The inverter's raw report for the linked charger. It can remain non-zero while the charger reports idle. | Source comparison and diagnostics; do not use a positive value alone as proof that charging is active. |
| Qualified PowerOcean – Charging power | PowerOcean power allowed through when a fresh Direct heartbeat reports charging; zero when a fresh Direct heartbeat reports an accepted idle state. | Prefer this over raw PowerOcean power when an automation needs the charging-state qualification, subject to the freshness limitation below. |

For example, if PowerOcean reports 1,400 W while fresh Direct data reports
`unplugged`, the qualified reading is 0 W. If Direct confirmation is missing,
too old or unrecognized, the qualified reading is `unknown`, not a guessed zero.
When Direct reports `charging`, a missing PowerOcean power value also remains unknown.

In 1.0.4, this qualification checks the age of the Direct heartbeat, **not an
independent timestamp for the PowerOcean power field**. A numeric reading is
therefore not a guarantee that both sources were just updated. See the
[validation boundaries](validation.md) and [central backlog](backlog.md) before
using it for decisions that require fresh power measurements.

In automations, require a valid numeric reading before comparing power with a
threshold. Treat `unknown` as insufficient information and `unavailable` as an
unusable entity/source; neither means the charger has stopped. Avoid converting
either to zero by default. Keep the selected energy/session source consistent
across charts and counters; do not add Direct and PowerOcean session energy
together, since they describe the same charger through different reporting paths.

### Missing readings and unavailable controls

`unknown` means the entity currently has no usable value. `unavailable` means its
required device, integration or source is unavailable, or a control's conditions
are not met. A read-only setting can still be visible while its matching control
is disabled. This is intentional: seeing a value does not mean it is safe to change it.

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

## Preparing and using a Smart charging plan

A Smart plan combines a ready-by date/time with either an energy target or a
distance target. Keep three things separate:

| Stage | Meaning |
| --- | --- |
| Draft in Smart configuration controls | Values saved locally by the integration, per charger, across reloads and restarts. A displayed draft is not proof that the charger uses it. |
| Current read-only Smart values | Values actually reported by the device/provider. Missing reports remain unknown; the integration does not fill them from the draft. |
| Activated configuration | A requested mode/settings change for which the command and the required readback have been confirmed. Check the reported mode and target after activation. |

1. Enable the Smart configuration controls and operating-mode selector you need
   in Home Assistant's entity settings.
2. While the charger is in Solar, Fast or Custom mode, enter a future ready-by
   date/time, choose Energy or Distance, and enter the selected target. Energy
   accepts whole kWh from 1 to 100; distance accepts whole km from 10 to 600.
   These edits save a local draft and do not send a charger command.
3. Select Smart as the operating mode to apply the complete plan. This is a device
   operation and still requires the control's connection and charging-state conditions.
   Missing required values are not invented. A saved draft can supply them without
   first having to activate Smart in the EcoFlow app; existing device-reported
   context may supply values that have not been entered locally.
4. Wait for the service result and check the reported mode and selected target.
   If confirmation fails, do not assume the charger stayed unchanged: inspect
   its current readings before retrying.

Once Smart mode is active, editing these controls requests a **live device change**,
subject to the applicable safety checks. The energy and distance targets are
alternatives; the selected target type determines which one is required. Distance
mode does not require a locally stored vehicle-consumption estimate.

Check the date before each activation. Stable 1.0.4 can retain an expired draft
and does not yet enforce that its deadline is in the future. A saved plan is not
automatically moved to the next day. Current limitations are tracked in the
[backlog](backlog.md); local preparation does not validate real charging behavior.

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
