# PowerPulse 2 project backlog

This is the **single authoritative list** of open work for this repository.
README files describe current scope, protocol documents retain evidence, and
the changelog records delivered changes; they must link here instead of keeping
parallel TODO or roadmap lists.

When an item is completed, remove it from this file and record the delivered
change in `CHANGELOG.md`. Acceptance and release evidence goes to
`validation.md`; protocol captures and field findings go to
`protocol_observations.md`. `issue_247_wip_report.md` is a closed historical
archive and takes no new evidence. Every release must review `validation.md`
and `protocol_observations.md`; update `data_paths_overview.md` whenever a path
or field mapping changes.

Any upstream proposal must follow the upstream maintainer's chosen architecture.
This integration's direct C376 MQTT path with bounded PowerOcean HTTP fallback
is project evidence, not a prescription for another repository.

Current implementation baseline: `1.0.5`.

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
| [`ISSUE-86`](https://github.com/Xygen/EcoFlow-PowerPulse-2-for-Home-Assistant/issues/86) | Medium | Keep Start and Stop button availability stable across ordinary charging-state changes, moving the state check from entity availability into the existing command guard, which already refuses an invalid action before publish. The pending-action interlock from #11 must stay. **Undecided:** whether a stale Direct heartbeat also leaves availability — under the #19 finding a single missed heartbeat makes it stale for about thirty seconds, so keeping it there would reintroduce the churn this item removes. | Charge-state changes alone do not change button availability; an invalid Start or Stop is refused before publish with a message naming the state; tests prove no command is published; the pending interlock and genuine loss of control still make both buttons unavailable; release notes describe the change for automations that watch these entities. |

## Telemetry and protocol research

| ID | Priority | Open work | Completion evidence |
| --- | --- | --- | --- |
_No open items. `ISSUE-13` was delivered and accepted live on 2026-09-12 and
its row is removed from this table; see
[the validation record](validation.md#live-session-on-2026-09-12-on-105-beta12)._

**One loose end is deliberately untracked.** Why the PowerOcean relay reports
non-zero values such as `1352` or `4380 W` while Direct and `allocatedPower`
stay at zero is still unexplained. The 2026-09-12 session caught it twice, at
707 W and 3664 W, so the behaviour is real and reproducible. Nothing
user-facing depends on it any more: the qualified sensor refuses those values
and the raw entities remain available to anyone who wants to investigate. It
carries no issue, on purpose — raising one would imply work is planned. If that
changes, this paragraph is where the decision was recorded.

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

Completed work is not kept in this file. The dated entries written during the
completion phase from 2026-09-10 to 2026-09-13 are preserved unchanged in
[the completion log](backlog_completion_log_2026-09.md); current evidence for
each item is in [validation.md](validation.md).

Planungsstand: 2026-09-09. Vollständige Befunde und Validierungsgrenzen:
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
| `V2-DATA-01` | P2 / M | Einheitlicher Vertrag für flüchtige Telemetrie und den Lade-Binärsensor. Die PowerOcean-Leistung selbst ist mit #13 umgesetzt und live abgenommen: eigenes Alter, Zuordnung je Ladegerät und Observer, `unknown` bei alter oder fehlender Leistung während des Ladens. Offen ist der Rest. F03. | Status ohne Evidenz wird nicht als gesichert „aus“ ausgegeben. Zähler dürfen separat als letzter bekannter Stand behandelt werden, wenn ausdrücklich gekennzeichnet. |

`V2-SAFE-01` (#14), `V2-SAFE-02` (#15), `V2-QA-01` (#17) und `V2-DOC-01` (#20)
sind umgesetzt, geschlossen und hier entfernt; ihre Nachweise stehen in
[validation.md](validation.md), ihre Änderungen im `CHANGELOG.md` unter `1.0.5`.

**Gate A:** reproduzierbare Code-Gegenfälle F01/F02 abgesichert — **erfüllt**:
beide umgesetzt und am 2026-09-12 in einer Fahrzeugsitzung abgenommen. Keine neue
Steuerfunktion vor diesen Korrekturen. Änderungen am Steuerpfad benötigen
anschließend einen kontrollierten Fahrzeugtest. Fehlendes Fahrzeug ist eine
offene Abnahmebedingung, kein durch Unit-Tests ersetzbarer Nachweis.

### Meilenstein B – Ausfallerholung und HA-Lebenszyklus, Ziel 1.1/1.2

| ID | Prio / Aufwand | Verbesserung und Grundlage | Abnahmekriterium |
| --- | --- | --- | --- |
| `V2-LIFE-01` | P1 / M | Setupfehler, Unload, wartende Transaktionen, Reply-Waiter und verzögerte Aufgaben einheitlich aufräumen. F06. | Plattformfehler hinterlässt keine MQTT-Clients; Reload während Lock-Warten, Publish, ACK und Readback beendet Aufgaben kontrolliert; nach Unload entsteht kein neuer Publish. |
| `V2-QA-02` | P1 / L | Echten HA-Testaufbau für Config Flow, Plattformen, Service-/Entity-Aufrufe, Registry, Store, Reload und Coordinator ergänzen; Coverage zunächst messen. F05. | Kritische Steuer- und Lebenszykluspfade laufen gegen HA-Fixtures; keine bloßen AST- oder Helper-Tests als Ersatz. Unterstützte Mindestversion und aktuelle HA-Version getestet; offene Coverage-Lücken bewertet, keine unbelegte Prozentzusage. |
| `V2-HTTP-01` | P2 / M | Provider-Lesezeit und Fehler nach Quelle begrenzen; 401/403, 429, 5xx, ungültiges JSON und verzögerten Cache unterscheidbar machen. F04/F06. | Wiederholte Fehler haben Backoff und nachvollziehbaren Diagnosegrund; lange Provider-Abfragen blockieren keine unabhängigen frischen MQTT-Werte. HTTP-Empfangszeit wird nicht als garantierte Geräteaktualität interpretiert. |

Abhängigkeiten: `V2-QA-01` ist umgesetzt und keine offene Voraussetzung mehr
für `V2-QA-02`; die umgesetzten `V2-SAFE-01/02` bleiben Regressionsvorgaben für
alle Lebenszyklus- und Transportänderungen.

`V2-AUTH-01` (#16) und `V2-STREAM-01` (#19) sind geschlossen und hier entfernt.
Ein Kriterium aus `V2-STREAM-01` wurde dabei **nicht** umgesetzt: getrennte Tests
für einen oder beide fehlenden Streams sowie für geschlossene App bei verbundenem
MQTT ohne Daten. Die abschließenden Bedingungen von #19 verlangten stattdessen die
Klassifikation eines vollständig erfassten langen Ausfalls. Wer diese Tests will,
braucht einen eigenen Eintrag; sie gelten nicht stillschweigend als erledigt.
**Gate B:** Netz-/Auth-/Reload-Fehlerszenarien im Testaufbau nachgewiesen;
begrenzter Live-Erholungsnachweis bei einer gesondert autorisierten Testphase.

### Meilenstein C – Alltag, Energie und verständliche Bedienung, Ziel 1.2/1.3

| ID | Prio / Aufwand | Verbesserung und Grundlage | Abnahmekriterium |
| --- | --- | --- | --- |
| `V2-UX-01` | P2 / M | Sperrgründe übersetzt anzeigen: kein Fahrzeug, falscher Modus, fehlende Quelle, alter Bericht. Die Anzeige der wartenden Bestätigung ist mit #11 umgesetzt: beide Knöpfe sind währenddessen gesperrt, eine zweite Aktion wird abgelehnt. Nächster Schritt ist [#86](https://github.com/Xygen/EcoFlow-PowerPulse-2-for-Home-Assistant/issues/86), das zustandsbedingte Sperren durch eine Ablehnung mit benanntem Zustand ersetzt. F07. | Anwender kann aus HA den konkreten Grund und nächsten sinnvollen Schritt erkennen; „ACK erhalten“ ist von physisch bestätigt getrennt. Diagnose erzeugt keine sekündlich wechselnden Altersattribute. |
| `V2-ENERGY-01` | P2 / M | Statistik- und Resetvertrag für Gesamt- und Sitzungsenergie definieren; Quellenwahl für Energy Dashboard, Tageszähler und Historie dokumentieren. F10 und untersuchte Helfer. | Mehrere Sessions, Reset, verspätete Werte und Neustart erzeugen keine Doppelzählung/negative Artefakte. Direct und PowerOcean werden nicht unbemerkt kombiniert. Migration bestehender Helfer bleibt eine ausdrücklich ausgewählte Benutzeraktion. |
| `V2-DOC-02` | P2 / M | Kompakte DE/EN-Anleitung mit Entity-/Quellenmatrix, Beispieldashboard, Automationsbeispielen, Troubleshooting, Diagnoseanleitung, Update-/Rollback-Ablauf. F07/F08. | Beispiele verwenden stabile tatsächlich vorhandene Entity-Rollen, behandeln `unknown`/`unavailable` und unterscheiden lokale Smart-Entwürfe von Writes. Protokolldetails sind verlinkt statt Voraussetzung für tägliche Bedienung. |
| `V2-TOPO-01` | P2 / M | Unterstützte Topologien bei Einrichtung erkennbar prüfen; Gerätauswahl, Wiedererkennung und bestätigte Elternzuordnung gestalten. F10. | Ein unterstütztes Paar funktioniert unverändert; kein/mehre Elternsysteme führen zu verständlicher Begrenzung und keinem geratenen Write-Ziel. Multi-Pair-Support nur nach Zuordnungs- und Cross-Device-Tests. |

`V2-SMART-01` (#18) ist umgesetzt, samt bestätigter echter Smart-Aktivierung, und
hier entfernt.

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
