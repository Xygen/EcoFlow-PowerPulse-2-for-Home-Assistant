# PowerPulse 2 project backlog

This is the **single authoritative list** of open work for this repository.
README files describe current scope, protocol documents retain evidence, and
the changelog records delivered changes; they must link here instead of keeping
parallel TODO or roadmap lists.

When an item is completed, remove it from this file, record the delivered change
in `CHANGELOG.md`, and add the supporting evidence to
`protocol_observations.md` and/or `issue_247_wip_report.md`. Every release must
review those two evidence documents; update `data_paths_overview.md` whenever a
path or field mapping changes.

Any upstream proposal must follow the upstream maintainer's chosen architecture.
This integration's direct C376 MQTT path with bounded PowerOcean HTTP fallback
is project evidence, not a prescription for another repository.

Current implementation baseline: `1.0.4`.

## Merge and release gates

Decided on 2026-09-10. `main` accepts finished work whose live acceptance is
still open, provided the automated gates pass: pytest, Ruff, the repository
consistency checks, HACS and Hassfest. Acceptance is a **release** gate, not a
merge gate.

The reason is that the two were previously the same gate, and the result was
that finished branches aged unmerged while waiting for a physical condition. It
produced the worst possible state for `V2-SAFE-02`: complete, reviewed, and in
no test build at all, so it could not be accepted even in principle.

What this does **not** change: no release declares a behaviour accepted without
the evidence named for it here and in the validation document. Code on `main`
is code that compiles, passes its tests and has been reviewed. It is not a
claim that it was observed working on the device. An item stays open until its
acceptance evidence exists, whether or not its branch has merged.


Die [Roadmap bis Version 2.0](#roadmap-bis-version-20) ergänzt die bestehenden
Arbeitsitems. Grundlage ist die Gesamtprüfung vom 2026-09-09 einschließlich
lesender MCP-Prüfung der verbundenen Home-Assistant-Instanz.

## Live validation and control safety

| ID | Priority | Open work | Completion evidence |
| --- | --- | --- | --- |
| [`ISSUE-12`](https://github.com/Xygen/EcoFlow-PowerPulse-2-for-Home-Assistant/issues/12) | High | Source-atomic availability/confirmation and bounded timing diagnostics are released and live-validated. Keep the current deadlines until another delayed Start near the 30-second gate provides evidence for, or against, a bounded progress extension. PowerOcean remains diagnostic-only. | Two live Start/Stop pairs and exported bounded records confirm Direct-only outcomes; stale, ambiguous, or conflicting readback remains fail-closed. A delayed Start must be observed before changing deadline policy. |

## Telemetry and protocol research

| ID | Priority | Open work | Completion evidence |
| --- | --- | --- | --- |
| [`ISSUE-13`](https://github.com/Xygen/EcoFlow-PowerPulse-2-for-Home-Assistant/issues/13) | High | Qualify fast PowerOcean charging power/status against fresh Direct idle evidence without removing raw source-qualified diagnostics. Determine why the PowerOcean relay reports non-zero `1352`/`4380 W` and `charging` while Direct and `allocatedPower` stay at zero. | A cable-connected Direct-idle window cannot expose non-zero automation-safe charging power; real charging retains the PowerOcean update cadence; raw PowerOcean observations remain inspectable; no control behavior changes. |

## Deferred and release work

| ID | Priority | Open work | Completion evidence |
| --- | --- | --- | --- |
| `PHASE-01` | Known limitation accepted for `v1.0.0` | Normal Direct phase selection and source separation are validated. A stale Direct `241/44` stream was not reproducible while the car was connected and the stopped wallbox continued to emit fresh Direct reports, so the provider-fallback transition and provider-already-at-target edge case remain unvalidated. The implementation remains fail-closed. | Live `auto → one_phase → auto` test on 2026-09-05 produced fresh Direct readback `raw 1` and `raw 0`; no unverified behavior or relaxed safety gate is introduced. Reopen only with a reproducible stale-Direct condition. |
| `SAFE-02` | Deferred after v1.0.0 | Paused Solar policy remains documented as a known limitation; no behavior change is required for v1.0.0. | Reopen only with controlled equivalent PV/battery conditions and paired App/HA evidence. |
| `CTRL-02` | Deferred after v1.0.0 | Dynamic active-session current/power control remains research-only. | Reopen only with an official-app capture, acknowledgement and physical readback. |
| `STREAM-02` | Deferred after v1.0.0 | Idle-first transport optimization is outside the v1.0.0 scope. | Reopen only with bounded wake-up, freshness and safety validation. |
| `DATA-02` | Deferred after v1.0.0 | Unknown fast-report fields 5 and 9 remain diagnostic-only. | Reopen only with paired state/setting captures. |
| `DATA-04` | Deferred after v1.0.0 | Smart vehicle-consumption semantics remain unresolved and are not required by current controls. | Reopen only with controlled comparisons across vehicle profiles. |
| `DATA-05` | Deferred after v1.0.0 | State labels are mapped; numeric `suspend_reason` semantics remain unresolved. | Reopen only with a fresh numeric reason paired to an independent device state. |
| `DATA-06` | Deferred after v1.0.0 | Aggregate phase telemetry remains supported; positional phase entities are deferred. | Reopen only after ordered multi-state field 29/30 captures. |
| `DATA-08` | Deferred after v1.0.0 | Historical PV/grid/battery session attribution is not part of the stable release. | Reopen only after identifying and reconciling the historical report path. |
| `DATA-10` | Deferred after v1.0.0 | Broad PowerOcean field completeness research is deferred. | Reopen only for a specifically scoped, privacy-reviewed field set. |

`DATA-09` is complete: a 2026-09-05 session ended cleanly, the next HA
Start reset both Direct and PowerOcean session energy/duration to `0`, and the
PowerOcean entities continued reporting while the separate `EcoFlow Energy`
integration was disabled. The existing Direct entity IDs remained unchanged.

## v1.0.0 release record

The `1.0.0` release meets this gate: every v1.0.0 item in this backlog is either closed
with evidence or explicitly recorded as a known limitation, the existing test
suite passes, the manifest and documentation consistently identify `1.0.0`,
and the release contains no unverified new controls or guessed field mappings.

## Roadmap bis Version 2.0

### Completion phase (2026-09-10)

Update 2026-09-11: documentation/diagnostic consolidation is merged, including
PR #27/#28 and the A1–A3 evidence from PR #35. Only Issue #16 remains active.
Real HA functional tests reproduced three credential-renewal defects; focused
fixes now pass those counterexamples. See
[functional acceptance](validation.md#issue-16-functional-authentication-acceptance).
PR #36 is merged and beta.7 is installed. Runtime version and both MQTT streams
were verified after restart on 2026-09-11. Retain the explicitly unobserved
provider-expiry, repaired-password recovery and differing-broker cases as open live evidence. Do not repeat
A1–A3 or start another issue while completing this acceptance.

Issue #16 was closed on 2026-09-11; V2-SMART-01 / Issue #18 is the item in
progress, owned by Claude. Issues #14/#15 and PR #22/#23 form the next joint
control review and vehicle-acceptance block; include relevant #13 power tests
in that session. Issue #11 follows on its own; #25 is deferred. Keep #12's
accepted deadlines unless a newly captured delayed action justifies revisiting
them.

Work on 2026-09-12: Issue #19 closed as explained rather than fixed. An overnight
capture on `1.0.5-beta.9` caught both `unknown` intervals with `connected: true`
on every sample, refuting the reconnection hypothesis. Cadence is about sixty
seconds and `_HEARTBEAT_STREAM_FRESH_SECONDS` is ninety, so one missed heartbeat
puts the next at about a hundred and twenty and leaves thirty seconds of
`unknown`. The budget tolerates no skip. No threshold was changed: the same
constant gates charging-control freshness, and the observed cost is a gap at
zero watts on an idle charger. Revisit if the gaps recur during an actual
charging session. See
[the validation record](validation.md#cause-established-on-2026-09-12-from-a-105-beta9-overnight-capture).

Work on 2026-09-11: Issue #11, owned by Claude. Both charging buttons go
unavailable while a Start or Stop awaits confirmation, and a second action is
refused rather than queued behind the control lock, which serialises without
refusing. The marker is set before the lock and cleared in a `finally` on every
exit path. Confirmation windows, error reporting and the reported charging
state are unchanged; no optimistic mutation was introduced. Eleven tests
against three mutations. The live check of the visible button state needs a
vehicle and stays open. See
[the validation record](validation.md#unreleased-pending-charging-action).

Work on 2026-09-11: Issue #25. The charger heartbeat's field 21 is published as
`direct_active_phase_raw`, a disabled-by-default diagnostic carrying the raw
number. The field was confirmed present in all eleven captured frames before
any code was written, but its value cannot be read from the capture, which
redacts direct payloads; the reporter's single/three-phase mapping is therefore
recorded as a claim rather than implemented. The configured-selection sensor
the issue also asks for already exists as `phase_mode`, so the issue's premise
did not hold here. Interpreting the number needs a three-phase observation and
belongs with the vehicle session in #13. See
[the validation record](validation.md#unreleased-active-phase-reading).

Accepted live on 2026-09-11 on `1.0.5-beta.9`: a Smart activation and return
under explicit authorization produced two unusable reported fields,
`smart_charge_target_wh` and `ready_by_timestamp`, both counted in diagnostics,
with no warning logged and the draft intact including the 30.0 kWh energy
target. A valid field surviving alongside an invalid one in the same report is
covered by tests but not yet by live evidence; that needs the plan changed in
the EcoFlow app during a Smart window. See
[the validation record](validation.md#confirmed-live-on-2026-09-11-on-105-beta9).

Work on 2026-09-11: Issue #53, found while accepting #18. A charger report
carrying one unusable field no longer discards the whole report. `update` and
`update_from_device` now state which provenance they serve; user edits keep
their all-or-nothing rule. Unusable reported fields are counted in diagnostics
rather than logged as a warning. Ten tests, seven verified against a mutation.
The provider parser that produced the zero is deliberately unchanged, because
no evidence about its payload schema was collected. See
[the validation record](validation.md#unreleased-device-report-field-handling).

Accepted live on 2026-09-11 on `1.0.5-beta.8`: the refusal, its German
message naming the refused time, the preserved draft and the absence of any
publish were all confirmed on the maintainer's instance against the expired
draft the item was raised for. `control_readback_counts` stayed at zero on all
three paths, so no settings write was published. The real-device Smart
activation criterion stays open and carries `needs:maintainer`. See
[the validation record](validation.md#confirmed-live-on-2026-09-11-on-105-beta8).

Work on 2026-09-11: V2-SMART-01 / Issue #18 refuses to activate a Smart plan
whose ready-by time has passed, or is more than 366 days ahead. The draft is
kept and never rolled forward, the message names the refused time, and the
check sits on the publish path so a plan waiting on the control lock is
re-checked when it reaches dispatch. Nineteen tests, ten of them verified
against a mutation that disables the rule. The real-device activation criterion
stays open. See [the validation record](validation.md#unreleased-smart-deadline-handling).

Issue #19 is observation-only for 24–48 hours on the installed beta.5. Evaluate
one bounded export, then decide whether a demonstrated failure warrants a fix
or the item waits for reproduction. No new gap is not proof of recovery.
New research and unrelated features are paused during this completion phase.

Completed on 2026-09-10: V2-DOC-01 / Issue #20 was accepted through
[PR #26](https://github.com/Xygen/EcoFlow-PowerPulse-2-for-Home-Assistant/pull/26),
merge `678303a`. Smart drafts, source selection, field 17 and stable/beta scope
are documented. V2-QA-01 / Issue #17 was completed through
[PR #24](https://github.com/Xygen/EcoFlow-PowerPulse-2-for-Home-Assistant/pull/24),
merge `7f09767`, including the version declarations and translation-key fix.
Quality, HACS and Hassfest passed on both merge commits. See
[automated checks](validation.md#automated-repository-checks).

Observation on 2026-09-11, second reading: the same runtime stalled at
09:56 UTC. The charger stayed connected while its own frames stopped: 86.5 s
without a heartbeat and 47.7 s without a settings report, with no disconnection
recorded. The heartbeat age reached 79.1 s against the 90 s limit that gates
the qualified PowerOcean charging power, so it came within eleven seconds of
the reported symptom and the recorder confirms no unknown interval occurred.
Automatic recovery needs both streams stale for 300 s and could not have fired;
the single recovery check in the window ran exactly 30 s after the last frame,
which is the push-reset deadline, not a schedule. The heartbeat period was then measured at
60.048 s from recorder history, correcting the working value given earlier that
day, and the three-day record separates twelve short single-miss gaps from ten
total outages that account for 96% of the unknown time and were all eligible
for automatic recovery. See
[the observation](stream_timeline_observation_2026-09-11.md#later-finding-second-reading-at-1112-utc-the-fault-reproduced).

Observation on 2026-09-11: the bounded timeline was read for the first time on
`1.0.5-beta.7`. Two hours and fifteen minutes without a gap, no missed
heartbeat, no recovery decision. It constrains the heartbeat cadence to
`k x P = 300.40 s` without determining `P`, and records that the observer's
freshness is never sampled, so "connected without data" cannot be evidenced for
it. A quiet window is not evidence that the fault is gone; the next requirement
is a long window without a restart, because a reload discards the timeline and
the long intervals fell overnight. See
[the observation](stream_timeline_observation_2026-09-11.md).

Investigation on 2026-09-10: V2-STREAM-01 / Issue #19 remains open.
[A new 24-hour idle observation](stream_investigation_2026-09-10.md) correlates
six qualified-power gaps with heartbeat freshness: three short gaps near
integration loads and three longer paired-stream gaps. Next, capture a bounded
connection/recovery timeline with report ages and integration start time before
changing recovery policy. Current snapshots cannot establish connectivity or
recovery decisions during earlier gaps; no vehicle is required for this step.

Implementation for Issue #19: diagnostics now include an in-memory
stream timeline with connection callbacks, recovery reasons, report ages and
reconnect outcomes. See [the diagnostic contract](validation.md#stream-timeline-diagnostics).
The independent sampler correction is included. Beta.5 is installed and its
startup and five-minute observations were live-verified. A new idle-gap
observation remains pending. Main does not yet include the separate safety/readback
changes in PR #22/#23; the installed beta preserves PR #22 and excludes PR #23.
Persistence across reload/restart is not implemented; export before restarting.
Closed 2026-09-11: [V2-AUTH-01 / Issue #16](https://github.com/Xygen/EcoFlow-PowerPulse-2-for-Home-Assistant/issues/16)
is delivered in both stages and released in `1.0.5-beta.7`. A refused
credential is distinguishable from an unreachable endpoint, Home Assistant
offers re-authentication and reconfiguration without replacing the config
entry, an expired session is renewed once before the user is asked, the MQTT
layer's expired-certificate detection is consumed, and the broker address comes
from the credential response. PR #36 added Home Assistant fixture tests that
found three renewal defects, all fixed.

Five acceptance steps were observed live: the wrong-password sign-in on
`1.0.5-beta.3`, the account guard, the entry update and the broker address on
`1.0.5-beta.6`, and the outage report on `1.0.5-beta.7`. Both directions of the
no-false-report claim are therefore evidenced. The outage step also found that
the `cannot_connect` text still blended connection and sign-in, corrected in
PR #45.

Three steps are accepted as **not tested**, not as passed. The repair trigger
was deliberately skipped because invalidating the account password would
invalidate the EcoFlow app and four other integrations on this account; its
mechanism is covered by fixtures and EcoFlow's real refusal is evidenced
separately, so only the seam between them is unproven. The renewal cannot be
forced and waits on a real expiry. A differing broker host is not reachable
from an account EcoFlow serves from this region.

Findings, the classification rule, the comparison with `ecoflow-energy-ha` and
the limits are in [the analysis](issue_16_auth_analysis.md); the observations
and what each does not establish are in
[the validation status](validation.md#closed-on-2026-09-11-with-three-steps-accepted-as-unobserved).

Planungsstand: 2026-09-09. Vollständige Befunde und Validierungsgrenzen:
Implementierungsstand: 2026-09-09.
`V2-SAFE-01` / [Issue #14](https://github.com/Xygen/EcoFlow-PowerPulse-2-for-Home-Assistant/issues/14)
ist lokal implementiert; 193 Tests bestehen, davon 31 neue Coordinator-Transaktionstests.
Die Review ergänzte eine Sendesperre bei neueren widersprüchlichen Begleitwerten
oder Modus-/Freigabewerten aus einer niedriger priorisierten Quelle.
`1.0.5-beta.1` ist per HACS installiert und nach HA-Neustart geladen.
Der Display-Test 100 → 75 → 100 % wurde zweimal per Direct-Readback bestätigt;
Begleitwerte blieben erhalten. Die fahrzeuggestützte Abnahme steht aus
(Live-Status `unplugged`). PR #22 ist am 2026-09-10 nach `main` gemergt;
das Item bleibt bis zur fahrzeuggestützten Abnahme offen.
Details zur Aussagegrenze: [Validierung](validation.md#unreleased-control-transaction-hardening).

Stand 2026-09-10: `V2-SAFE-02` / [Issue #15](https://github.com/Xygen/EcoFlow-PowerPulse-2-for-Home-Assistant/issues/15)
ist über PR #23 am 2026-09-10 nach `main` gemergt.
Feldbezogene Bestätigung, Konfliktsperren, vollständige Provider-No-ops und
überlappende Providerabrufe sind geprüft; die speziellen Phasen-Übergangsregeln
bleiben erhalten. Diese Änderung war in keiner Beta enthalten und ist auch in
`1.0.5-beta.4` nicht enthalten, muss also zuerst in einen Testbuild gelangen,
bevor sie überhaupt abgenommen werden kann. Das Item bleibt offen.
Nachweise: [Validierung](validation.md#unreleased-field-qualified-readback).

Vollständige Befunde und Validierungsgrenzen:
[Prüfbericht](review_2026-09-09.md). Diese Roadmap ist ein Vorschlag zur
Umsetzungsreihenfolge, keine Aussage über bereits gelieferte Funktionen.
Bestehende IDs oben bleiben maßgeblich und werden unten nur zugeordnet.
Die verlinkten Roadmap-IDs führen zu den zugehörigen GitHub-Issues.
`V2-UX-01` verweist auf das bestehende Issue #11 für die Teilaufgabe der
Start/Stop-Bedienung während laufender Bestätigung; die übrigen UX-Ziele
bleiben im Roadmap-Item. `V2-DATA-01` verweist auf Issue #13 für die
PowerOcean-Qualifikation; allgemeinere Status-/Zählerregeln bleiben hier.

Zielbild: zuverlässige, nachvollziehbare Telemetrie und Steuerung für
**PowerPulse 2 mit PowerOcean**, verständliche HA-Bedienung und reproduzierbare
Releases. Bestehende Entity-IDs, Benutzeraktivierungen, Historie und lokale
Smart-Entwürfe sind zu erhalten. Automatischer Transport bleibt listen-only;
neue Controls bleiben opt-in und evidenzgebunden.

Prioritäten: **P1** = hohe Korrektheits-/Zuverlässigkeitsrelevanz;
**P2** = Produktqualität und Wartbarkeit; **P3** = optionale Erweiterung.
Aufwand relativ: **S** etwa 1–2, **M** 3–5, **L** 6–10 konzentrierte
Entwicklungstage einschließlich Tests/Dokumentation, ohne Wartezeiten auf
Fahrzeug, PV-Bedingungen oder Protokollbelege. Das sind erste Schätzbereiche,
keine Termin- oder Gesamtaufwandszusage.

### Meilenstein A – Sichere Basis in zeitnahen 1.0.x-/1.1-Releases

Kompatible Sicherheitskorrekturen sollen nicht bis zum Major-Release warten.

| ID | Prio / Aufwand | Verbesserung und Grundlage | Abnahmekriterium |
| --- | --- | --- | --- |
| [V2-SAFE-01](https://github.com/Xygen/EcoFlow-PowerPulse-2-for-Home-Assistant/issues/14) | P1 / M | Ladezustand, Modus, Datenfrische und Transport unmittelbar vor Publish innerhalb der Befehlssperre erneut prüfen. Begleitwerte/Bitmasken erst dort aus qualifizierter Evidenz zusammenstellen. F01. | Wartender Befehl wird nach zwischenzeitlichem Ladebeginn, Moduswechsel oder Frischeverlust vor Publish abgelehnt; zwei parallele Display-/Flag-Änderungen überschreiben keine unabhängige Einstellung. Tests auf tatsächlichem Coordinator-Pfad. |
| [V2-SAFE-02](https://github.com/Xygen/EcoFlow-PowerPulse-2-for-Home-Assistant/issues/15) | P1 / L | Allgemeine Bestätigung und Provider-No-op an Wert, exakte Quelle und Feldzeitpunkt koppeln; widersprechendes Direct-Readback berücksichtigen. F02. | Neuer Bericht ohne Zielfeld bestätigt keinen alten Wert; Provider im Ziel bei widersprechendem Direct verhindert keinen notwendigen SET und meldet keinen Scheinerfolg. Teilberichte, Konflikte und alle bestehenden Control-Familien getestet. |
| [V2-DATA-01](https://github.com/Xygen/EcoFlow-PowerPulse-2-for-Home-Assistant/issues/13) | P1 / M | Eigene Frische und Serienzuordnung für PowerOcean-Leistung; einheitlicher Vertrag für flüchtige Telemetrie und Lade-Binary-Sensor. Auf vorhandener Feldbeobachtung aufbauen. F03. | Frisches Direct `charging` plus alte/fehlende PowerOcean-Leistung ergibt `unknown`; fremder Observer macht keine Quelle gültig. Status ohne Evidenz wird nicht als gesichert „aus“ ausgegeben. Zähler dürfen separat als letzter bekannter Stand behandelt werden, wenn ausdrücklich gekennzeichnet. |
| [V2-QA-01](https://github.com/Xygen/EcoFlow-PowerPulse-2-for-Home-Assistant/issues/17) | P1 / S | Bestehende pytest- und Ruff-Prüfung in CI aufnehmen; Versions-, Übersetzungs- und lokale Linkkonsistenz ergänzen. F05/F08. | PR mit fehlschlagendem bestehenden Test, Lintfehler oder fehlendem Übersetzungsschlüssel scheitert im Workflow; Release-Gate referenziert genau diesen Commit. HACS/Hassfest bleiben erhalten. |
| [V2-DOC-01](https://github.com/Xygen/EcoFlow-PowerPulse-2-for-Home-Assistant/issues/20) | P1 / S | README, Index und User Guide an 1.0.4, lokale Smart-Entwürfe und rohe/qualifizierte Leistung angleichen; DATA-03-Text und fehlenden `strings.json`-Schlüssel korrigieren. F08. | Alle aktuellen Einstiegspunkte beschreiben dieselbe veröffentlichte Basis und geben eine eindeutige Quellenwahl für Automationen an; historische Versionsangaben bleiben als solche erkennbar. |

Bestehendes [ISSUE-13](https://github.com/Xygen/EcoFlow-PowerPulse-2-for-Home-Assistant/issues/13): Der qualifizierte Sensor ist bereits implementiert und
installiert. In diesem Meilenstein stehen dessen reale Lade-/Idle-Übergänge
und die Wirkung der zusätzlichen Quellenfrische aus `V2-DATA-01` zur Abnahme
an; die Ursache des rohen Relay-Verhaltens kann separat offen bleiben.
Bestehendes [ISSUE-12](https://github.com/Xygen/EcoFlow-PowerPulse-2-for-Home-Assistant/issues/12): aktuelle Deadlines beibehalten; nur ein neuer passend
erfasster verzögerter Start rechtfertigt eine Änderung der Wartepolitik.

**Gate A:** reproduzierbare Code-Gegenfälle F01/F02 abgesichert; keine neue
Steuerfunktion vor diesen Korrekturen. Änderungen am Steuerpfad benötigen
anschließend einen kontrollierten Fahrzeugtest. Fehlendes Fahrzeug ist eine
offene Abnahmebedingung, kein durch Unit-Tests ersetzbarer Nachweis.

### Meilenstein B – Ausfallerholung und HA-Lebenszyklus, Ziel 1.1/1.2

| ID | Prio / Aufwand | Verbesserung und Grundlage | Abnahmekriterium |
| --- | --- | --- | --- |
| [V2-AUTH-01](https://github.com/Xygen/EcoFlow-PowerPulse-2-for-Home-Assistant/issues/16) | P1 / L | Authfehler von Netzwerk-/Providerfehlern unterscheiden; begrenzte Token- und MQTT-Credential-Erneuerung sowie UI-Reauth/Reconfigure ergänzen. Bestehende Login-Nutzlast erhalten. F04. | Abgelaufene Credentials erholen sich begrenzt oder starten den richtigen Reauth-Flow; falsches Passwort erzeugt keine Endlosschleife, temporärer HTTP-Ausfall keine falsche Passwortmeldung. IDs und Entwürfe bleiben nach Neu-Anmeldung erhalten. |
| `V2-LIFE-01` | P1 / M | Setupfehler, Unload, wartende Transaktionen, Reply-Waiter und verzögerte Aufgaben einheitlich aufräumen. F06. | Plattformfehler hinterlässt keine MQTT-Clients; Reload während Lock-Warten, Publish, ACK und Readback beendet Aufgaben kontrolliert; nach Unload entsteht kein neuer Publish. |
| `V2-QA-02` | P1 / L | Echten HA-Testaufbau für Config Flow, Plattformen, Service-/Entity-Aufrufe, Registry, Store, Reload und Coordinator ergänzen; Coverage zunächst messen. F05. | Kritische Steuer- und Lebenszykluspfade laufen gegen HA-Fixtures; keine bloßen AST- oder Helper-Tests als Ersatz. Unterstützte Mindestversion und aktuelle HA-Version getestet; offene Coverage-Lücken bewertet, keine unbelegte Prozentzusage. |
| [V2-STREAM-01](https://github.com/Xygen/EcoFlow-PowerPulse-2-for-Home-Assistant/issues/19) | P1 / M | Neun beobachtete `unknown`-Intervalle mit Heartbeat, Einstellungen, MQTT-Verbindung und Recovery-Timings korrelieren; einzelne/nie gestartete Streams gesondert behandeln. F06 und Live-Historie. | Ursache oder klar eingegrenzter Ausfalltyp je reproduziertem Fall; getrennte Tests für einen/beide fehlenden Streams, App geschlossen und MQTT verbunden ohne Daten. Recovery begrenzt, ohne automatische Gerätebefehle und ohne blinde Lockerung der Frische. |
| `V2-HTTP-01` | P2 / M | Provider-Lesezeit und Fehler nach Quelle begrenzen; 401/403, 429, 5xx, ungültiges JSON und verzögerten Cache unterscheidbar machen. F04/F06. | Wiederholte Fehler haben Backoff und nachvollziehbaren Diagnosegrund; lange Provider-Abfragen blockieren keine unabhängigen frischen MQTT-Werte. HTTP-Empfangszeit wird nicht als garantierte Geräteaktualität interpretiert. |

Abhängigkeiten: `V2-QA-01` vor `V2-QA-02`; `V2-SAFE-01/02` bleiben
Regressionsvorgaben für alle Lebenszyklus- und Transportänderungen.
**Gate B:** Netz-/Auth-/Reload-Fehlerszenarien im Testaufbau nachgewiesen;
begrenzter Live-Erholungsnachweis bei einer gesondert autorisierten Testphase.

### Meilenstein C – Alltag, Energie und verständliche Bedienung, Ziel 1.2/1.3

| ID | Prio / Aufwand | Verbesserung und Grundlage | Abnahmekriterium |
| --- | --- | --- | --- |
| [V2-UX-01](https://github.com/Xygen/EcoFlow-PowerPulse-2-for-Home-Assistant/issues/11) | P2 / M | Sperrgründe und Befehlsfortschritt übersetzt anzeigen: kein Fahrzeug, falscher Modus, fehlende Quelle, alter Bericht, wartende Bestätigung. F07. | Anwender kann aus HA den konkreten Grund und nächsten sinnvollen Schritt erkennen; „ACK erhalten“ ist von physisch bestätigt getrennt. Diagnose erzeugt keine sekündlich wechselnden Altersattribute. |
| [V2-SMART-01](https://github.com/Xygen/EcoFlow-PowerPulse-2-for-Home-Assistant/issues/18) | P1 / M | Entwurf, wirksame Gerätekonfiguration und Aktivierungsfähigkeit erklären; vergangene/ungültige Termine beim Aktivieren behandeln. F07. | Alten Entwurf speichern erlaubt, aber Aktivierung mit abgelaufenem Termin wird vor Publish verständlich abgelehnt oder ausdrücklich neu terminiert. Tests für Zeitzonen, Sommerzeit, Grenzwerte und Reload; echte Smart-Aktivierung separat bestätigt. |
| `V2-ENERGY-01` | P2 / M | Statistik- und Resetvertrag für Gesamt- und Sitzungsenergie definieren; Quellenwahl für Energy Dashboard, Tageszähler und Historie dokumentieren. F10 und untersuchte Helfer. | Mehrere Sessions, Reset, verspätete Werte und Neustart erzeugen keine Doppelzählung/negative Artefakte. Direct und PowerOcean werden nicht unbemerkt kombiniert. Migration bestehender Helfer bleibt eine ausdrücklich ausgewählte Benutzeraktion. |
| `V2-DOC-02` | P2 / M | Kompakte DE/EN-Anleitung mit Entity-/Quellenmatrix, Beispieldashboard, Automationsbeispielen, Troubleshooting, Diagnoseanleitung, Update-/Rollback-Ablauf. F07/F08. | Beispiele verwenden stabile tatsächlich vorhandene Entity-Rollen, behandeln `unknown`/`unavailable` und unterscheiden lokale Smart-Entwürfe von Writes. Protokolldetails sind verlinkt statt Voraussetzung für tägliche Bedienung. |
| `V2-TOPO-01` | P2 / M | Unterstützte Topologien bei Einrichtung erkennbar prüfen; Gerätauswahl, Wiedererkennung und bestätigte Elternzuordnung gestalten. F10. | Ein unterstütztes Paar funktioniert unverändert; kein/mehre Elternsysteme führen zu verständlicher Begrenzung und keinem geratenen Write-Ziel. Multi-Pair-Support nur nach Zuordnungs- und Cross-Device-Tests. |

**Gate C:** überarbeitete Benutzerwege und Energiebeispiele nachvollziehbar;
bestehende Automationen, IDs, explizit deaktivierte Entitäten und Smart-Entwürfe
bleiben erhalten. Zusätzliche Hardwareunterstützung ist kein implizites Ziel.

### Meilenstein D – Wartbarkeit und ausgewählte Erweiterungen, Ziel 1.x bis 2.0-beta

| ID | Prio / Aufwand | Verbesserung und Grundlage | Abnahmekriterium |
| --- | --- | --- | --- |
| `V2-ARCH-01` | P2 / L | Coordinator schrittweise in Transport-/Quellenverwaltung, Beobachtung und Steuertransaktionen aufteilen. Vorhandene reine Module weiterverwenden. F09. | Kleine verhaltensgleiche Schritte mit HA-Regressionssuite; zentrale Verträge für Feldwert/Quelle/Zeitpunkt und Befehlsablauf; kein vollständiger Neuaufbau auf einmal. |
| `V2-PERF-01` | P2 / M | Frame-Verarbeitung, HA-Updates, Recorder-Attribute und HTTP-Last messen; identische UI-Werte entkoppeln, ohne interne Frische/ACK-Verarbeitung zu verlieren. F09. | Vorher/Nachher-Messung für Idle und aktive Sitzung dokumentiert; weniger unnötige Updates, gleiche Control-Frische und keine verlorenen seltenen Frames. Keine Optimierung allein aus Dateigröße ableiten. |
| `V2-DIAG-01` | P2 / M | Kompakte Diagnosezusammenfassung und versionierten Export anbieten; Legacy-Duplikate geordnet abbauen, Fehlertexte auf unbeabsichtigte Identifikatoren prüfen. F09. | Leerer, normaler und voller Capture bleiben begrenzt und redigiert; bestehende Auswerter haben dokumentierten Übergang. Zusammenfassung erklärt Quelle, Frische und letzten Fehler ohne Rohdump. |
| `V2-PARSER-01` | P2 / M | Reale redigierte Frame-Fixtures und generative Grenzfalltests für Teilberichte, Trunkierung, unbekannte Felder, übergroße/verschachtelte Daten und Zahlen ergänzen. F05/F07. | Ungültige Eingaben führen weder zu erfundenen aktuellen Werten noch unbegrenzter Verarbeitung; bestätigte Mappings und Datenschutzinvarianten bleiben erhalten. |

Bestehende Forschungsitems werden nicht doppelt erfasst:

| Bestehende ID | Einordnung auf dem Weg zu 2.0 | Entscheidung |
| --- | --- | --- |
| `PHASE-01` | Weiterer Nachweis der vorhandenen Funktion | Nur bei reproduzierbarem stale-Direct-Fall; ansonsten bekannte fail-closed Einschränkung beibehalten. |
| `SAFE-02` | Priorisierte Produktentscheidung vor neuen Solar-Controls | Paused-Solar-Regel mit vergleichbaren PV-/Batteriebedingungen prüfen; dokumentierte Einschränkung ist zulässig, ungeprüfte Lockerung nicht. |
| `STREAM-02` | Optionale Optimierung nach `V2-STREAM-01` und `V2-PERF-01` | Idle-first nur bei messbarem Nutzen und belegtem Wake-up-Verhalten. |
| `DATA-06` | Bevorzugte optionale Telemetrieerweiterung, P3 | Phasenpositionen erst nach geordneten Mehrzustandsbelegen; bestehende Maxima und IDs erhalten. |
| `DATA-05`, `DATA-04` | Optionale gezielte Status-/Smart-Forschung, P3 | Pausengrund bzw. Verbrauch nur mit unabhängig zugeordneten Zuständen/Profilen erklären. |
| `CTRL-02` | Optionale spätere Steuererweiterung, P3 | Aktiver Sollstrom erst nach App-SET, Reply und physischem Readback; kein Versprechen einer dynamischen PV-/Tarifregelung für 2.0. |
| `DATA-08` | Optionale spätere Energieerweiterung, P3 | PV-/Netz-/Batterieanteile erst nach Abgleich eines bestätigten Historienpfads. |
| `DATA-02`, `DATA-10` | Zurückgestellt, P3 | Nur eng begrenzte neue Fragestellung; keine vollständige Feldsuche als Release-Gate. |

**Gate D:** keine neue Entity-/Control-Semantik ohne Beleg und Migrationsregel;
unerfüllte Forschungsbedingungen dürfen explizit nach 2.0 verschoben werden.

### Meilenstein E – 2.0-beta, Release Candidate und stabile Freigabe

| ID | Prio / Aufwand | Verbesserung | Abnahmekriterium |
| --- | --- | --- | --- |
| `V2-REL-01` | P1 / M | Build und Freigabe vom geprüften Commit ableiten; Manifest/Tag/Archiv, Mindest-HA-Version, Paketinhalt und Hash automatisch prüfen. F05. | Sauberer Checkout, grüne CI, installierbares ZIP mit Brand/Übersetzungen, eindeutiger Commit und SHA256; exakt dieses Paket wird in HACS/HA geprüft. |
| `V2-MIG-01` | P1 / M | Kompatibilitätsvertrag und gegebenenfalls notwendige Migration für 2.0 festlegen. | Upgrade von 1.0.4 und letzter 1.x-Version erhält IDs, Statistikzuordnung, Benutzeraktivierungen und Entwürfe; Rückweg per getesteter Sicherung dokumentiert. Ohne beabsichtigten Vertragsbruch nochmals prüfen, ob eine 1.x-Version semantisch genügt. |
| `V2-ACCEPT-01` | P1 / L | Gemeinsame Abnahmematrix und begrenzte Beta-Phase durchführen. | Alle zugesagten Funktionen mit Test-/Live-Evidenz oder ausdrücklich akzeptierter Einschränkung; kein offenes P1-Korrektheitsproblem. Mindestens sieben Tage Beta-Beobachtung mit App geschlossen, mehreren realen Sitzungen, Sitzungswechseln, freigegebenem Reload-/Netzausfalltest und mindestens zwei unabhängigen unterstützten Installationen oder explizit engerem Supportumfang. |

Die Abnahmematrix umfasst mindestens Solar, Fast, Custom und Smart, jeweils
die relevanten Zustände nicht verbunden / verbunden-idle / ladend / pausiert /
abgeschlossen; dazu Direct-/PowerOcean-Ausfälle und Quellkonflikte.
Nicht jede Kombination muss künstlich erzeugt werden: fehlende reale
Bedingungen werden als ungetestet ausgewiesen und entsprechend aus einer
allgemeinen Funktionszusage ausgenommen.

Ein 2.0-Release ist erreicht, wenn die vereinbarten Pflichtpunkte abgenommen,
P3-Erweiterungen bewusst enthalten oder verschoben, Dokumentation und Paket
konsistent und Upgrade sowie Wiederherstellung geprüft sind. Forschung ohne
reproduzierbare Voraussetzungen ist kein Grund für einen unbegrenzten
Release-Aufschub.
