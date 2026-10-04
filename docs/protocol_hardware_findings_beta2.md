# Beta.2 hardware findings and production controls

The maintainer completed controlled C376 hardware tests on 2026-10-04 with
`1.0.6-beta.2`. These tests establish firmware behavior beyond the restrictions
observed in the official app. Times below are local Europe/Berlin (CEST).

| Evidence | Single-field write and fresh confirmation | Consequence for normal controls |
| --- | --- | --- |
| [#480](https://github.com/shuette42/ecoflow-energy-ha/issues/480#issuecomment-5978850729) | Solar, Continuous OFF: field 4 = 70 at 11:37:50, then 60 at 11:39:15. Fast: field 4 = 70 at 11:39:45, then 60 at 11:41:08. Each received a matching SET reply and newer direct `241/44`; mode and flags stayed unchanged. | Store Solar minimum current using field 4 alone, without mode or Continuous enablement prerequisites. |
| [#481](https://github.com/shuette42/ecoflow-energy-ha/issues/481#issuecomment-5978853646) | Idle Solar: field 6 = 100 at 11:46:34, then 60 at 11:48:39. Matching replies and newer direct `241/44` confirmed both; Solar, flags 18 and Continuous ON stayed unchanged. | Store Custom current using field 6 alone, without switching to Custom. |
| [#482](https://github.com/shuette42/ecoflow-energy-ha/issues/482#issuecomment-5978861177) | During charging, field 5 = 2 at 11:52:27 changed configured Auto/raw 0 to three phase/raw 2, confirmed by reply and newer direct `241/44`. Active phase changed from single phase/raw 1 to three phase/raw 0 at approximately 11:52:34. | Permit configured phase selection during charging, using field 5 alone. |

The phase trace showed charging at 11:52:20, paused at 11:52:28, charging at
11:52:34, paused at 11:52:35 and charging at 11:52:44. The firmware temporarily
pauses and resumes while reconfiguring; no explicit Stop/Start was needed for
the observed transition. The research diagnostic `session_ended: true` means
the status temporarily left `charging`, not that the physical session ended.
Configured phase raw values and active phase raw values have different mappings.
Success confirms the configured setting; physical phase remains separate telemetry.
The test was subsequently stopped and configured Auto restored.

## Implementation and retained boundaries

`1.0.6-beta.3` applied these shapes to normal number/select entities.
Current values are stored independently of mode; editing them does not activate
that mode or Continuous Charging. Neither current write includes field 1 or 2,
so queued edits cannot restore old mode/flags. Normal current entities require
fresh, non-conflicting evidence for their stored target value. Availability and
the backend repeat the same checks under the transaction lock.

Phase selection retains fresh direct heartbeat/status qualification, qualified
phase readback, exactly one PowerOcean route and serialized writes. Unknown,
updating and stale state still fail closed. Matching SET replies and fresh
configured-setting confirmation remain necessary; the dedicated qualified
provider fallback and its transition requirement remain unchanged. The integration
does not automatically send Stop or Start when phase changes.

Beta.3 retained the charging locks for mode and all current controls. Candidate
`1.0.6-beta.4` corrects the intended scope: mode selection and minimum, maximum
and Custom current are available during charging, still requiring fresh known
direct status, qualified routing and confirmed readback. This is an explicitly
requested availability change, not additional hardware evidence. Continuous
Charging retains its Solar prerequisite and charging lock; Smart target interlocks
remain unchanged. Research actions remain available for explicitly scoped experiments,
with their stricter direct-only confirmation and bounded diagnostics.

## Evidence limits

The tests establish Solar current storage in idle Solar/Continuous OFF and Fast,
Custom current storage in idle Solar, and the observed Auto-to-three-phase
transition during charging. Custom-current storage in Fast and stored-current
edits in other idle modes were not separately captured; treating these fields
as independent storage is the implementation inference from the accepted partial
writes, not a claim that every mode was physically tested. Current edits during
charging, Continuous outside Solar, other firmware/hardware variants and every
possible active phase transition remain unvalidated. C374 behavior is not claimed.

This implementation has not itself been installed or exercised on the charger.
The canonical [backlog](backlog.md#telemetry-and-protocol-research) tracks the
remaining production-entity acceptance separately from the completed beta.2 tests.
