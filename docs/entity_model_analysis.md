# ENTITY-03: Analyse des Entity-Modells

Stand: 2026-08-30  
Bezug: [Backlog `ENTITY-03`](backlog.md)

## Ergebnis in Kurzform

Die Grundentscheidung der bisherigen Analyse bleibt richtig: Read-only-
Beobachtung und schreibbare Control dürfen nicht allein deshalb zusammengelegt
werden, weil sie denselben fachlichen Einstellungswert darstellen. Ihre
Verfügbarkeits- und Sicherheitsverträge unterscheiden sich.

Die Voranalyse war aber noch nicht implementierungsreif. Insbesondere müssen
vor einem Entity-Umbau vier Punkte präzisiert werden:

1. Die Read-only-Entities verwenden heute **keine einheitliche
   `unknown`-/`unavailable`-Semantik**. Normale Sensoren und Setting-
   Binary-Sensoren verhalten sich unterschiedlich.
2. Für die Einstellungs-Entities fehlt eine systematische Entscheidung über
   `EntityCategory.CONFIG`, `EntityCategory.DIAGNOSTIC` oder primäre Entity.
3. „Letzten bekannten Wert weiter anzeigen“ ist ohne definierte Snapshot-/Delta-
   und Freshness-Semantik zu ungenau und kann stale Werte unbegrenzt als aktuell
   erscheinen lassen.
4. Aktuell beobachteter Zustand, letzter beobachteter Zustand, intern
   erinnerte Konfiguration und schreibbare Control sind unterschiedliche
   Begriffe und dürfen nicht in einen einzigen „kanonischen Wert“ fallen.

ENTITY-03 sollte deshalb derzeit als
**„Analysis mostly complete; entity classification and stale-state semantics
need refinement“** geführt werden.

## Home-Assistant-Semantik als Designgrenze

Die aktuellen Home-Assistant-Entwicklerregeln unterscheiden klar:

- Datenquelle/Gerät nicht erreichbar -> Entity `unavailable`;
- Quelle erfolgreich gelesen, einzelner Wert fehlt -> Entity bleibt verfügbar,
  Wert `unknown`;
- veränderbare Gerätekonfiguration -> `EntityCategory.CONFIG`, sofern die Entity
  keine primäre Gerätefunktion darstellt;
- read-only Konfigurations-/Diagnoseinformation -> typischerweise
  `EntityCategory.DIAGNOSTIC`, sofern sie keine primäre Funktion darstellt;
- weniger genutzte oder noisy Entities sollen standardmäßig deaktiviert sein,
  um State-Machine- und Recorder-Last zu vermeiden.

Referenzen:

- <https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/entity-unavailable/>
- <https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/entity-category/>
- <https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/entity-disabled-by-default/>
- <https://developers.home-assistant.io/docs/core/entity/>

Diese Regeln sind für ENTITY-03 wichtiger als eine möglichst kleine Anzahl von
Entities.

## Ist-Zustand

### Sensoren in `sensor.py`

`PowerPulse2Sensor` verwendet `telemetry_sensor_available()`. Die Availability
hängt ab von:

- Coordinator-Verfügbarkeit;
- Vorhandensein des Geräts im Coordinator;
- Verfügbarkeit der benötigten Quelle.

Die Anwesenheit des einzelnen Feldes ist absichtlich **kein**
Availability-Kriterium. `telemetry_sensor_value()` liefert bei fehlendem Feld
`None`, sodass Home Assistant den Zustand als `unknown` darstellen kann.

Dieses Verhalten entspricht der gewünschten Home-Assistant-Semantik.

### Setting-Binary-Sensoren weichen davon ab

Die Read-only-Binary-Sensoren für:

- `continuous_charging`;
- `plug_and_play`;
- `battery_discharge_disabled`;
- `screen_enabled`;
- `indicator_enabled`

verwenden derzeit dagegen:

```text
last_update_success
AND key in coordinator.data[serial]
```

Fehlt das einzelne Feld, wird die Entity dadurch `unavailable` statt
`unknown`.

Zusätzlich liefert `is_on` derzeit `bool(value)`. Würde lediglich die
Availability großzügiger gemacht, würde ein fehlender Wert dadurch zu `False`
und damit fälschlich zu `off` statt `unknown`.

Für eine Vereinheitlichung müssen daher **beide** Teile angepasst werden:

```text
available:
    Quelle/Gerät verfügbar, unabhängig von Feldanwesenheit

is_on:
    True/False bei explizitem Bool
    None bei fehlendem/ungültigem Wert
```

Die Voranalyse hatte fälschlich angenommen, die `unknown`-Semantik gelte schon
für alle Read-only-Settings.

### Controls

Numbers, Selects, Switches und DateTime-Entities besitzen zusätzliche Gates.
Abhängig vom Control können erforderlich sein:

- bestätigter Schreibpfad;
- genau ein geeigneter PowerOcean-Beobachter;
- verbundene MQTT-/WSS-Verbindung;
- zulässiger Lade-/Betriebszustand;
- erforderliche Ausgangswerte zur Erhaltung anderer Settings;
- frischer beziehungsweise qualifizierter Readback.

Eine Control darf deshalb `unavailable` sein, während eine unabhängige
Read-only-Beobachtung weiterhin sinnvoll lesbar ist.

Das ist kein unerwünschtes Duplikat, sondern ein anderer Entity-Vertrag.

## Warum Read-only und Control getrennt bleiben sollen

| Aspekt | Observation | Control |
| --- | --- | --- |
| Zweck | Gerätezustand beobachten | Gerätekonfiguration ändern |
| Availability | Datenquelle/Gerät | zusätzlich Transport- und Safety-Gates |
| fehlender Einzelwert | `unknown` | kann Write/Freigabe verhindern |
| Freshness-Anforderung | UI-/Monitoring-tauglich | control-grade, ggf. strenger |
| falscher stale Wert | irreführende Anzeige | unsicherer Write/Bestätigung |
| Backend-Service | keiner | muss Gates erneut prüfen |

Eine gemeinsame Entity würde mindestens eines dieser Modelle verwässern:

- entweder verschwindet ein lesbarer Wert, sobald Schreiben nicht möglich ist;
- oder eine scheinbar verfügbare Entity suggeriert Schreibbarkeit, obwohl
  Transport, Betriebszustand oder Readback nicht genügen.

Die Trennung bleibt daher das Zielmodell.

## Vier getrennte Zustandsbegriffe

ENTITY-03 sollte künftig vier Ebenen explizit unterscheiden.

### 1. Current observation

Der aktuell qualifizierte, von einer bekannten Quelle beobachtete
Gerätezustand.

Dieser Wert ist die Grundlage für eine normale Read-only-Entity.

### 2. Observation metadata

Interne Metadaten zur Beobachtung, zum Beispiel:

- konkrete Quelle;
- Zeitpunkt der letzten echten Beobachtung;
- Snapshot-/Delta-Semantik;
- Freshness-/Validity-Zustand.

Diese Metadaten dienen der korrekten State-Ermittlung und Diagnostik. Sie
sollten nicht automatisch als sich ständig ändernde normale Entity-Attribute
veröffentlicht werden.

### 3. Remembered configuration

Ein bewusst gespeicherter letzter Wert, der für eine spätere Operation benötigt
wird, aber **nicht notwendigerweise aktuell aktiv oder aktuell beobachtet** ist.

Das ist insbesondere für Smart relevant. `_last_smart_settings` bewahrt Werte,
um beim Wechsel zwischen Smart-Zieltypen einen vollständigen Payload bauen zu
können. Ein remembered Smart-Ziel darf deshalb nicht automatisch als aktueller
Read-only-Gerätezustand erscheinen.

### 4. Writable control

Eine getrennte Number-/Select-/Switch-/DateTime-Entity mit eigener
Availability- und Backend-Safety-Policy.

Observation-Freshness und Control-Confirmation-Freshness sind ausdrücklich
nicht dasselbe.

## Smart-Settings als konkretes Beispiel

Bei Smart existieren heute bereits unterschiedliche Wertebenen:

```text
aktuell berichteter Smart-Wert
remembered Smart-Wert aus _last_smart_settings
Control-native_value, das bei fehlendem aktuellen Smart-Wert auf remembered
zurückfallen kann
```

Dieses Verhalten ist für die Payload-Erhaltung nützlich. Für ENTITY-03 muss aber
festgelegt werden:

- ein Read-only-Sensor zeigt nur den aktuell qualifizierten Gerätezustand;
- ein remembered Wert ist kein Ersatz für einen fehlenden aktuellen Zustand;
- Controls dürfen intern remembered Konfiguration verwenden, sofern die
  jeweilige Write-Policy dies erlaubt;
- falls remembered Werte für Nutzer diagnostisch sichtbar werden sollen,
  benötigen sie eine klare Benennung und sollten standardmäßig deaktiviert
  sein.

## Stale-State-Problem im Coordinator-Merge

`merge_snapshot_after_read()` startet mit den zuletzt bekannten Werten und
überschreibt nur Felder, die im neuen Poll enthalten sind. Das schützt frische
MQTT-Werte vor langsamen oder leeren Providerantworten, bedeutet aber auch:

```text
neuer Snapshot enthält Feld X nicht
-> alter Wert X kann im Coordinator erhalten bleiben
```

Damit kann ein alter Einstellungswert zeitlich unbegrenzt wie ein aktueller
Wert aussehen, wenn die konkrete Reportsemantik nicht berücksichtigt wird.

Die frühere Formulierung „`unknown` oder als letzter bekannter Wert
gekennzeichnet“ ist für eine Implementierung zu offen.

## Snapshot- und Delta-Semantik zuerst definieren

Für jede Settings-Quelle muss geklärt werden, ob sie einen vollständigen
Snapshot oder ein partielles/Delta-Update liefert.

### Vollständiger Snapshot

Wenn eine Quelle nachweislich einen vollständigen Settings-Snapshot liefert:

```text
Snapshot erfolgreich
Feld fehlt
-> current observation = None
-> Read-only-Entity = unknown
```

Ein älterer Wert darf nicht nur wegen des Coordinator-Merges aktuell bleiben.

### Partieller/Delta-Report

Wenn eine Quelle Felder legitimerweise auslässt:

```text
Feld fehlt
-> vorherige Beobachtung darf zunächst erhalten bleiben
-> aber nur mit per-field observed_at / definierter Freshness
-> nach Ablauf der zulässigen Freshness -> unknown
```

Eine unbegrenzte Last-known-value-Semantik wird nicht empfohlen.

### Quelle nicht verfügbar

Wenn die benötigte Datenquelle selbst nicht mehr verwendbar ist:

```text
-> unavailable
```

Damit bleiben `unknown` und `unavailable` fachlich getrennt.

## Quellenmodell präzisieren

Die frühere Empfehlung `direct`, `provider` oder `powerocean` ist zu grob.
Inzwischen existieren Pfade mit unterschiedlichen Semantiken, Frequenzen und
Vertrauensniveaus.

Intern sollten Source-IDs hinreichend eindeutig sein, zum Beispiel:

```text
direct_heartbeat_2_33
direct_settings_2_34
direct_fast_settings_241_44
provider_parent_accessory
provider_device_detail
powerocean_session_241_3
```

Nicht jede Source-ID muss als eigene Entity sichtbar werden. Die interne
Trennung verhindert aber, dass ein Feld aus einer ungeeigneten Quelle durch
Merge oder generische Freshness-Regeln aufgewertet wird.

PHASE-01 benötigt beispielsweise strengere source-aware Confirmation-Regeln als
ENTITY-03 für eine reine Read-only-Anzeige.

## EntityCategory muss systematisch entschieden werden

Die bisherige Analyse empfahl pauschal „genau einen normal sichtbaren
Read-only-Sensor“ je Einstellung. Das ist zu breit.

Home Assistant unterscheidet primäre Gerätefunktionen von Konfiguration und
Diagnostik. Deshalb soll vor einer Entity-Änderung eine vollständige Matrix für
alle Setting-Entities erstellt werden.

### Entscheidungsregel

1. Würde ein typischer Nutzer diese Entity als Teil der Hauptfunktion auf einem
   normalen Dashboard verwenden? -> keine EntityCategory.
2. Verändert die Entity eine Gerätekonfiguration und ist nicht primäre
   Bedienfunktion? -> `EntityCategory.CONFIG`.
3. Zeigt die Entity nur einen Konfigurationsparameter, eine Rohinformation oder
   Diagnoseinformation und ist nicht primäre Gerätefunktion? ->
   `EntityCategory.DIAGNOSTIC`.

### Bereits eindeutige Fälle

- Raw-Sensoren bleiben `DIAGNOSTIC` und standardmäßig deaktiviert.
- Screen-/LED-Konfigurations-Controls sind bereits sinnvoll als `CONFIG`
  klassifiziert.
- reine Stream-/Connectivity-Diagnostik bleibt `DIAGNOSTIC` und
  standardmäßig deaktiviert.

### Noch systematisch zu entscheiden

Unter anderem:

- Operating mode Observation/Control;
- Phase Observation/Control;
- Maximum output current Observation/Control;
- Solar minimum current Observation/Control;
- Custom current Observation/Control;
- Smart target type/energy/distance/ready-by Observation/Control;
- Continuous charging;
- Plug-and-Play;
- Battery discharge blocking;
- read-only Screen-/LED-Zustände und Helligkeiten.

Die Entscheidung darf nicht allein davon abhängen, ob eine passende Control
existiert. Eine Einstellung kann je nach Nutzerbedeutung eine primäre Funktion
sein und deshalb bewusst ohne Kategorie bleiben.

## Default Enablement und Ressourcen

Die schreibbaren Controls sind heute bereits überwiegend
`entity_registry_enabled_default = False`. Deaktivierte Entities werden von
Home Assistant nicht als laufende Entity hinzugefügt und erzeugen damit
standardmäßig keine normale State-/Recorder-Last.

Daher ist eine aggressive Reduktion der Control-Entities **nicht** aus
Performancegründen erforderlich.

Wichtiger ist die Frage, welche Read-only-Entities standardmäßig aktiv sein
müssen. Für wenig genutzte Konfigurationsspiegel oder Diagnosewerte kann
`entity_registry_enabled_default = False` sinnvoller sein.

### Keine laufenden Age-Attribute

Per-field Freshness soll intern gespeichert werden. Nicht empfohlen wird ein
öffentliches Attribut wie:

```text
age_seconds = 1, 2, 3, 4, ...
```

oder ein bei jedem Poll erneuerter Timestamp an jeder Setting-Entity, wenn sich
der fachliche Wert nicht geändert hat. Solche Attribute erzeugen unnötige
State-/Recorder-Änderungen.

Falls Zeit-/Source-Diagnostik sichtbar sein soll, sollte sie gebündelt,
standardmäßig deaktiviert und möglichst nur bei tatsächlichen Beobachtungs- oder
Source-Wechseln aktualisiert werden.

## UX: gleiche Werte, gleiche Namen, unterschiedliche Rollen

Mehrere Read-only-/Control-Paare besitzen aktuell identische oder nahezu
identische Anzeigenamen, beispielsweise:

- Maximum output current;
- Solar minimum charging current;
- Custom charging current;
- Operating mode;
- Phase setting;
- Smart target type;
- Screen brightness;
- LED brightness.

Solange Controls deaktiviert sind, fällt das wenig auf. Nach Aktivierung können
auf der Device-Seite jedoch zwei gleich benannte Entities mit unterschiedlicher
Rolle erscheinen.

ENTITY-03 soll deshalb zusätzlich prüfen, ob:

- EntityCategory bereits genug visuelle Trennung erzeugt;
- oder Übersetzungen die Observation-/Control-Rolle klarer machen sollten.

Bestehende Unique IDs dürfen dabei nicht geändert werden. Eine reine
Übersetzungs-/Display-Name-Änderung ist gegenüber einer Unique-ID-Migration zu
bevorzugen.

## Zielmodell für Observation-Entities

Für jede fachliche Einstellung soll genau **eine kanonische Observation**
definiert werden, aber nicht zwingend eine normal sichtbare primäre Entity.
Die Matrix muss mindestens enthalten:

| Feld | Bedeutung |
| --- | --- |
| canonical key | fachlicher Observation-Key |
| entity type | sensor/binary_sensor/... |
| primary/config/diagnostic | HA-Klassifikation |
| default enabled | ja/nein |
| valid sources | zulässige Read-Pfade |
| precedence | Source-Priorität |
| snapshot semantics | full/delta/unknown |
| freshness rule | wann Observation veraltet |
| missing-field rule | unknown vs retain-with-TTL |
| remembered value | getrennt ja/nein |
| control counterpart | zugehörige Write-Entity |
| control freshness | ausdrücklich separate Policy |

Erst nach dieser Matrix sollte geprüft werden, ob einzelne technische
Duplikate entfernt werden können.

## Empfohlene Implementierungsreihenfolge

### 1. Entity-Inventar klassifizieren

Alle Setting-Observation- und Control-Entities in einer statischen Tabelle
auflisten und für jede Entity Rolle, Kategorie und Default-Enablement festlegen.

### 2. Read-only-Availability vereinheitlichen

Insbesondere die Setting-Binary-Sensoren auf dieselbe Grundsemantik bringen:

```text
Quelle verfügbar + Feld fehlt -> unknown
Quelle nicht verfügbar -> unavailable
```

Dabei `is_on=None` für fehlende/ungültige Werte sicherstellen; fehlende Werte
dürfen nicht als `off` interpretiert werden.

### 3. Source-aware Observation-State einführen

Intern pro Einstellung nur die tatsächlich benötigten Metadaten führen:

- current value;
- source;
- observed_at;
- snapshot/freshness status.

Keine neue Polling-Quelle einführen; vorhandene Direct-/Provider-Daten nutzen.

### 4. Snapshot-/Delta-Regeln pro Quelle definieren

Alte gemergte Werte nicht unbegrenzt als current observation behandeln.

### 5. Smart remembered state explizit trennen

`_last_smart_settings` bleibt für Payload-Erhaltung nutzbar, darf aber nicht
stillschweigend Read-only-Observation ersetzen.

### 6. EntityCategory und Default Enablement umsetzen

Erst nach der Inventarentscheidung. Kategorien nicht pauschal auf alle
Settings anwenden.

### 7. Technische Duplikate zuletzt prüfen

Nur entfernen, wenn nachweislich keine Observation-, Diagnose-, Source- oder
Freshness-Information verloren geht und bestehende Unique IDs sauber behandelt
werden.

## Erforderliche Tests vor Abschluss

1. normaler Sensor: Quelle verfügbar + Feld vorhanden -> Wert verfügbar;
2. normaler Sensor: Quelle verfügbar + Feld fehlt -> `unknown`, nicht
   `unavailable`;
3. Setting-Binary-Sensor: Quelle verfügbar + Feld fehlt -> `unknown`, nicht
   `unavailable` und nicht `off`;
4. benötigte Quelle oder Coordinator ausgefallen -> `unavailable`;
5. vollständiger Snapshot ohne zuvor vorhandenes Feld -> alter current value
   wird `unknown`;
6. partieller Report ohne Feld -> Wert bleibt nur entsprechend definierter
   per-field Freshness erhalten;
7. abgelaufene Freshness -> `unknown`, sofern die Quelle selbst weiterhin
   erreichbar ist;
8. stale Provider-Wert überschreibt keinen frischeren bevorzugten Direct-Wert;
9. Control `unavailable` -> unabhängige Observation bleibt entsprechend ihrer
   eigenen Quelle lesbar;
10. sichtbare Observation macht einen gesperrten Backend-Write nicht möglich;
11. remembered Smart-Wert ersetzt keinen fehlenden aktuellen Read-only-Wert;
12. Smart-Control darf remembered Werte nur gemäß eigener Safety-/Write-Policy
   verwenden;
13. alle Setting-Entities besitzen die beschlossene EntityCategory;
14. Raw-/Diagnose-Entities bleiben standardmäßig deaktiviert;
15. weniger wichtige neue Observation-/Freshness-Diagnostik ist standardmäßig
   deaktiviert;
16. keine kontinuierlich hochzählenden Freshness-Attribute erzeugen Recorder-
   Churn;
17. bestehende Unique IDs bleiben unverändert;
18. Controls und Observations bleiben bei gleicher fachlicher Einstellung für
   Nutzer eindeutig unterscheidbar.

## Ergebnis für ENTITY-03

Die Annahme „Read-only- und Control-Entities sind unnötige Duplikate“ bleibt
verworfen. Die Trennung ist fachlich und sicherheitstechnisch sinnvoll.

Die nächste Umsetzung sollte jedoch **nicht** sofort zusätzliche
Freshness-Attribute an alle Entities hängen oder Entities entfernen. Zuerst
müssen:

1. das vollständige Entity-Inventar klassifiziert werden;
2. `unknown`/`unavailable` insbesondere für Setting-Binary-Sensoren
   vereinheitlicht werden;
3. Snapshot-/Delta- und per-field Freshness-Regeln definiert werden;
4. Current Observation und Remembered Configuration getrennt werden;
5. die EntityCategory-/Default-Enablement-Matrix beschlossen werden.

Danach können source-aware Observation-State und gezielte Entity-Bereinigungen
mit geringem Risiko und ohne unnötige Recorder- oder Polling-Last umgesetzt
werden.
