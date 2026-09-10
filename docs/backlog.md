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

Issue #19 follow-up: beta.4 live verification confirms connection events but
exposes polling-dependent diagnostic starvation under frequent MQTT pushes.
Beta.5 adds a separate, read-only sampler while preserving beta.4 safety
and authentication changes. See [the evidence and contract](validation.md#independent-observations-in-beta5).
Beta.5 is installed and independent observations were verified in HA after
restart. Next gate: observe a new idle gap and compare observation samples with
actual recovery-check/attempt events before changing recovery scheduling.
Recovery scheduling starvation is a separate remaining investigation item;
this change does not enable extra recovery attempts or close Issue #19.

Completed on 2026-09-10: V2-DOC-01 / Issue #20 was accepted through
[PR #26](https://github.com/Xygen/EcoFlow-PowerPulse-2-for-Home-Assistant/pull/26),
merge `678303a`. Smart drafts, source selection, field 17 and stable/beta scope
are documented. V2-QA-01 / Issue #17 was completed through
[PR #24](https://github.com/Xygen/EcoFlow-PowerPulse-2-for-Home-Assistant/pull/24),
merge `7f09767`, including the version declarations and translation-key fix.
Quality, HACS and Hassfest passed on both merge commits. See
[automated checks](validation.md#automated-repository-checks).

Investigation on 2026-09-10: V2-STREAM-01 / Issue #19 remains open.
[A new 24-hour idle observation](stream_investigation_2026-09-10.md) correlates
six qualified-power gaps with heartbeat freshness: three short gaps near
integration loads and three longer paired-stream gaps. Next, capture a bounded
connection/recovery timeline with report ages and integration start time before
changing recovery policy. Current snapshots cannot establish connectivity or
recovery decisions during earlier gaps; no vehicle is required for this step.

Implementation prepared for Issue #19: diagnostics now include an in-memory
stream timeline with connection callbacks, recovery reasons, report ages and
reconnect outcomes. See [the diagnostic contract](validation.md#stream-timeline-diagnostics).
PR #28 review is complete; `1.0.5-beta.2` combines this timeline with the
previously installed PR #22 safety changes. PR #23 is not included. Deployment
and a new idle-gap observation remain pending until separately verified below.
Persistence across reload/restart is not implemented; export before restarting.

Implementierungsstand: 2026-09-09.
`V2-SAFE-01` / [Issue #14](https://github.com/Xygen/EcoFlow-PowerPulse-2-for-Home-Assistant/issues/14)
ist lokal implementiert; 193 Tests bestehen, davon 31 neue Coordinator-Transaktionstests.
Die Review ergänzte eine Sendesperre bei neueren widersprüchlichen Begleitwerten
oder Modus-/Freigabewerten aus einer niedriger priorisierten Quelle.
`1.0.5-beta.1` ist per HACS installiert und nach HA-Neustart geladen.
Der Display-Test 100 → 75 → 100 % wurde zweimal per Direct-Readback bestätigt;
Begleitwerte blieben erhalten. Die fahrzeuggestützte Abnahme steht aus
(Live-Status `unplugged`); das Item und PR #22 bleiben offen.
Details zur Aussagegrenze: [Validierung](validation.md#unreleased-control-transaction-hardening).

Stand 2026-09-10: [V2-AUTH-01 / Issue #16](https://github.com/Xygen/EcoFlow-PowerPulse-2-for-Home-Assistant/issues/16)
ist in Stufe 1 über [PR #29](https://github.com/Xygen/EcoFlow-PowerPulse-2-for-Home-Assistant/pull/29)
umgesetzt und in `1.0.5-beta.3` enthalten: abgelehnte Zugangsdaten sind von einem
nicht erreichbaren Endpunkt unterscheidbar, und Home Assistant bietet
Neuanmeldung und Rekonfiguration an, ohne den Config-Eintrag zu ersetzen. Ein
abgelaufener Token schaltet den PowerOcean-Fallback nicht mehr lautlos ab,
sondern führt zu einem begrenzten erneuten Login: höchstens alle fünf Minuten,
und nur abgelehnte Zugangsdaten erreichen den Nutzer als Dialog. Stufe 2 ist über [PR #30](https://github.com/Xygen/EcoFlow-PowerPulse-2-for-Home-Assistant/pull/30)
umgesetzt und in `1.0.5-beta.4` enthalten: die Erkennung abgelaufener
Zertifikate in der MQTT-Schicht wird verarbeitet, ein abgelehntes oder
gealtertes Zertifikat wird begrenzt ersetzt und an die laufenden Clients
übergeben, und die Broker-Adresse stammt aus der Credential-Antwort statt aus
einer Konstante. Lokal bestehen 286 Tests. Befunde, Klassifikationsregel, der
Vergleich mit `ecoflow-energy-ha` und die Aussagegrenzen stehen in
[der Analyse](issue_16_auth_analysis.md); die fahrzeugunabhängigen
Abnahmeschritte in der
[Validierung](validation.md#unreleased-authentication-failure-handling).
Abnahmestand 2026-09-10 auf `1.0.5-beta.3`: Ein falsches Passwort bei der
Einrichtung meldet abgelehnte Zugangsdaten statt eines Verbindungsproblems.
Damit sind die Klassifikation am Credential-Endpunkt und die Übersetzung
belegt, nicht jedoch die Gegenrichtung. Offen bleiben Ausfallmeldung,
Erneuerung und der Auslöser des Reparaturdialogs; Kontoschutz und
Eintragsaktualisierung sind über den Rekonfigurationsdialog ohne ungültige
Zugangsdaten prüfbar, weil beide Flows dieselbe Sequenz durchlaufen.
Einzelheiten: [Validierung](validation.md#open-and-how-to-reach-each-one).
Das Issue bleibt offen.

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
