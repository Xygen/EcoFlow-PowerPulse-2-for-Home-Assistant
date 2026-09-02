# PHASE-01: Analyse des Phasen-Readbacks

Stand: 2026-08-30  
Bezug: [Backlog `PHASE-01`](backlog.md)

## Ergebnis in Kurzform

Die grundlegende Ursache ist weiterhin eine Verfügbarkeitslücke im schnellen
Direct-Readback. Die Phasenzuordnung des bestätigten PowerOcean-Elternzubehör-
Pfads ist inzwischen ausreichend isoliert:

| Provider-/241/44-Rawwert | Bedeutung |
| ---: | --- |
| `0` | Auto |
| `1` | einphasig |
| `2` | dreiphasig |

Der Direct-Report `241/44 -> 1.4.8.7` verwendet dieselbe Codierung. Der ebenfalls
bestätigte CP307-Settings-Report `2/34`, Feld `11`, verwendet dagegen eine
andere Codierung:

| `2/34` Feld `11` | Bedeutung |
| ---: | --- |
| `1` | einphasig |
| `2` | dreiphasig |
| `3` | Auto |

Diese beiden Raw-Schemata dürfen nicht über dieselbe Mapping-Tabelle behandelt
werden.

Die bisherige Voranalyse war in einem entscheidenden Punkt zu optimistisch:
Ein **frisch ausgeführter Provider-Poll ist nicht automatisch ein frischer
Gerätezustand**. Beim kontrollierten Wechsel auf dreiphasig lieferte der erste
Provider-Poll nach dem Wechsel noch den vorherigen Wert `1`; erst ein späterer
Poll nach ungefähr zehn Sekunden lieferte `2`. Der PowerOcean-Provider kann
also einen aktuellen HTTP-Snapshot mit gecachtem älteren Gerätezustand liefern.

Daraus folgt: PHASE-01 ist **weitgehend analysiert, aber die Provider-
Bestätigungssemantik muss vor der Implementierung noch präzisiert werden**.
Insbesondere darf der Phase-Fallback nicht einfach in die bestehende generische
`_last_polled_settings`-/No-op-/Readback-Logik eingehängt werden.

## Gesicherter Ist-Zustand

### Direct `241/44`

Der C376-Settings-Report `241/44` liefert unter `1.4.8.7`:

```text
0 = auto
1 = one_phase
2 = three_phase
```

Der Coordinator speichert den Zeitpunkt des letzten Direct-Settings-Reports
und behandelt den Direct-Pfad nur für ein begrenztes Zeitfenster als frisch.
`phase_control_available()` verlangt derzeit deshalb einen frischen gültigen
`phase_mode`-Wert aus diesem Direct-Pfad.

### Direct `2/34`

Der CP307-Settings-Report `2/34`, Feld `11`, ist ebenfalls als
Phasen-Readback bestätigt, verwendet aber:

```text
1 = one_phase
2 = three_phase
3 = auto
```

Die Semantik ist bestätigt. Noch nicht ausreichend belegt ist, ob `2/34` nach
einem eigenen HA-Phase-Write zuverlässig und zeitnah emittiert wird. Deshalb
soll dieser Pfad noch nicht automatisch als Write-Confirmation-Fallback
eingestuft werden. Er gehört aber ausdrücklich in die Readback-Quellenanalyse.

### Provider `provider_parent_accessory`

Der PowerOcean-Elternzubehör-Pfad liefert `paramSet.phaseSpecified`. Ein
kontrollierter Auto -> einphasig -> dreiphasig -> Auto-Vergleich bestätigte:

```text
0 = auto
1 = one_phase
2 = three_phase
```

Der Elternzubehörwert folgte den Direct-Readbacks, allerdings mit sichtbarer
Provider-/Cache-Latenz. Beim Wechsel auf dreiphasig enthielt der erste erzwungene
Provider-Poll noch den früheren Wert `1`; erst der nachfolgende Poll lieferte
`2`.

Damit ist die **Bedeutung** des Providerfelds bestätigt, nicht aber die Annahme,
dass der Inhalt jedes neu abgefragten HTTP-Snapshots selbst neu erzeugte
Geräteevidenz darstellt.

### Provider `provider_device_detail`

Der direkte Wallbox-Geräte-Detailpfad liefert den Phasenwert nicht zuverlässig
und wird nicht als Control-Readback akzeptiert. Diese Trennung bleibt bestehen.

## Präzisierter Root-Cause

Der Root-Cause besteht aus zwei getrennten Problemen:

1. Die Phase-Control ist heute ausschließlich an einen frischen `241/44`-
   Readback gebunden und wird deshalb unnötig `unavailable`, obwohl eine zweite
   bestätigte Readback-Quelle existiert.
2. Die vorhandene generische Provider-Readback-Logik unterscheidet nicht stark
   genug zwischen **Zeitpunkt des HTTP-Polls** und **Alter des darin enthaltenen
   Gerätezustands** und verliert in `_last_polled_settings` außerdem die
   konkrete Provider-Herkunft eines Feldes.

Deshalb darf PHASE-01 nicht nur durch „Providerwert zusätzlich zulassen“ gelöst
werden. Es braucht eine source-aware, phase-spezifische Readback-Qualifikation.

## Warum die generische `_last_polled_settings`-Logik nicht genügt

Der Coordinator liest zunächst den direkten Wallbox-Provider-Snapshot und
mischt danach die Werte des PowerOcean-Elternzubehörs hinein. Der resultierende
kombinierte Snapshot wird anschließend in `_last_polled_settings` gespeichert.

Für allgemeine Settings ist das praktisch. Für PHASE-01 ist es zu schwach,
weil die später gespeicherte Struktur nicht mehr beweist, ob ein Phasenwert
ursprünglich aus:

- `provider_parent_accessory`,
- `provider_device_detail`,
- oder einem zusammengeführten älteren Zustand

stammt.

PHASE-01 verlangt aber ausdrücklich, dass nur der bestätigte
`provider_parent_accessory`-Pfad als Fallback qualifiziert werden darf.

Der neue Fallback sollte deshalb nicht allein auf `_last_polled_settings`
aufbauen, sondern auf einer source-qualified Phasenevidenz.

## Poll-Frische ist nicht Zustands-Frische

Für PHASE-01 müssen mindestens zwei Zeitbegriffe unterschieden werden:

```text
fetched_at
    Zeitpunkt, zu dem Home Assistant die HTTP-Antwort erhalten hat

state evidence age
    Vertrauenswürdigkeit, dass der enthaltene Phasenwert den aktuellen
    Gerätezustand repräsentiert
```

Der vorhandene Provider liefert keinen bekannten serverseitigen
`phaseSpecified`-Änderungszeitstempel. Deshalb kann ein neuer HTTP-Poll einen
alten Cachewert zurückgeben.

Eine Regel wie:

```text
poll after command + expected value == success
```

ist für Phase allein nicht ausreichend.

## Risiko 1: falscher No-op

Die bestehende Settings-Logik besitzt eine No-op-Optimierung: Wenn ein
hinreichend neuer Provider-Poll bereits den gewünschten Wert enthält, kann der
Write übersprungen werden.

Für einen cache-laggenden Phasenwert kann das falsch sein.

Beispiel:

```text
Gerät tatsächlich: one_phase
Provider-Cache:     auto
Benutzer fordert:   auto
```

Wenn der Provider-Poll lokal noch als frisch gilt, könnte ein generischer
No-op-Pfad den Write überspringen, obwohl der aktuelle Gerätezustand nicht dem
Ziel entspricht.

Daher gilt für PHASE-01:

> Die generische Provider-No-op-Optimierung darf nicht ungeprüft für Phase
> wiederverwendet werden.

Eine erste konservative Implementierung sollte den Provider-No-op für Phase
entweder vollständig deaktivieren oder nur unter deutlich stärkerer
source-aware Evidenz zulassen.

## Risiko 2: falsche Post-Write-Bestätigung durch Cache

Auch ein Provider-Poll **nach** dem SET beweist nicht automatisch, dass der
zurückgelieferte Zielwert durch diesen SET entstanden ist.

Beispiel:

```text
Provider vor dem Write: three_phase
Gerät tatsächlich:      one_phase
Benutzer fordert:        three_phase
SET_REPLY:               erfolgreich
Provider-Poll danach:    weiterhin three_phase aus Cache
```

Ein reiner Test auf:

```text
polled_at > issued_at
AND value == expected
```

würde diesen Fall fälschlich bestätigen.

Für Phase muss deshalb die Readback-Strategie den **Pre-write-Zustand** und die
Provider-Cache-Problematik berücksichtigen.

Starke Provider-Evidenz ist insbesondere dann vorhanden, wenn nach dem Write
eine zuvor andere Provider-Phase auf den Zielwert wechselt. Ein bereits vor dem
Write identischer Providerwert ist dagegen als alleinige Post-Write-Bestätigung
schwächer und sollte in der ersten Implementierung nicht als eindeutiger
Transition-Beweis behandelt werden.

## PhaseReadbackTracker: Diagnosewert ist nicht automatisch Controlwert

Der vorhandene `PhaseReadbackTracker` trennt die Quellen sinnvoll und bewahrt
für jede Quelle:

- `last_snapshot_at`;
- ob `phase_specified_raw` im letzten Snapshot vorhanden war;
- `last_raw_at`;
- den letzten gültigen Rawwert.

Wenn ein neuer Snapshot kein Phasenfeld enthält, bleibt der ältere Rawwert
absichtlich für Diagnostik erhalten, während
`raw_present_in_last_snapshot = false` gesetzt wird.

Das ist für Diagnose korrekt, darf für Control-Freigaben aber nicht zu einer
Freshness-Verwechslung führen. Ein Provider-Fallback muss deshalb mindestens
fordern:

```text
source == provider_parent_accessory
AND raw_present_in_last_snapshot == true
AND last_raw_at == last_snapshot_at
AND raw_value is exactly one of {0, 1, 2}
```

Ein älterer bewahrter Diagnosewert darf nicht durch einen späteren Snapshot,
der das Feld gar nicht enthält, implizit wieder „frisch“ werden.

## Validierung des Providerwerts

Die bisherige Formulierung „numerisch gültig und in `0..2`“ ist zu breit.
Für einen Control-Fallback soll gelten:

- kein `bool`;
- kein Float-Zwischenwert wie `1.5`;
- kein `NaN`/`Inf`;
- ausschließlich semantisch exakte Werte `0`, `1`, `2`.

Die Normalisierung soll source-spezifisch erfolgen:

```text
provider_parent_accessory / direct 241/44:
0 -> auto
1 -> one_phase
2 -> three_phase

CP307 2/34 field 11:
1 -> one_phase
2 -> three_phase
3 -> auto
```

## Präzisierte Quellenpriorität

Die Priorität sollte nicht pauschal „bei jedem Konflikt fail-closed“ lauten.
Der Provider ist nachweislich langsamer und kann hinterherhinken. Ein frischer,
gültiger Direct-Wert darf deshalb nicht allein durch einen abweichenden
Provider-Cache entwertet werden.

Empfohlene Priorität:

1. **Frischer gültiger Direct-Readback `241/44`** ist authoritative für die
   Phase-Control. Ein abweichender älterer/cached Providerwert ist diagnostisch,
   sperrt den Direct-Pfad aber nicht automatisch.
2. Falls `241/44` nicht qualifiziert ist, kann ein frischer und source-aware
   qualifizierter `provider_parent_accessory`-Wert als Fallback dienen.
3. `2/34` bleibt zunächst zusätzliche bestätigte Direct-Evidenz, bis sein
   Emissionsverhalten nach eigenen Writes ausreichend belegt ist.
4. `provider_device_detail` ist kein Fallback.
5. Ist keine Quelle ausreichend qualifiziert, bleibt die Control
   `unavailable` beziehungsweise die Write-Bestätigung fail-closed.

Ein Konflikt ist besonders relevant, wenn Direct nicht mehr frisch genug für
Autorität ist, aber noch jüngere widersprüchliche Evidenz gegen den
Provider-Fallback vorliegt. Dieser Fall muss explizit getestet werden.

## Availability und Write-Confirmation trennen

Die bisherige Analyse vermischte teilweise die Frage „darf der Benutzer einen
Write auslösen?“ mit „womit wird ein Write anschließend bestätigt?“.

Diese beiden Entscheidungen sollten getrennt modelliert werden.

### Availability

Die Phase-Control darf nur verfügbar sein, wenn:

1. der bestätigte Settings-Schreibpfad über genau einen PowerOcean-Beobachter
   verfügbar ist;
2. der aktuelle Ladezustand eine Phasenänderung erlaubt;
3. eine sichere Readback-Strategie verfügbar ist:
   - bevorzugt frischer gültiger `241/44`, oder
   - qualifizierbarer `provider_parent_accessory`-Fallback;
4. keine für den Fallback relevante unaufgelöste Quelleninkonsistenz vorliegt.

### Write-Confirmation

Nach dem Write bleiben folgende Anforderungen unverändert:

1. passendes `241/102` SET wurde gesendet;
2. passendes same-sequence SET_REPLY wurde empfangen;
3. anschließend muss unabhängige Zustands-Evidenz den Zielwert bestätigen.

Die **Transport- und Safety-Gates bleiben erhalten**. Die bisherige generische
No-op- und Readback-Qualifikation muss für Phase jedoch source-aware erweitert
oder separat implementiert werden.

## Empfohlene Confirmation-State-Machine

Konzeptionell:

```text
Pre-write phase evidence erfassen
        |
Safety-Gates unmittelbar vor Publish erneut prüfen
        |
241/102 SET
        |
matching SET_REPLY
        |
kurzes Direct-Fenster
        |
        +-- neuer 241/44 mit Zielwert --> bestätigt
        |
        +-- kein qualifizierter Direct-Readback
                |
                +-- provider_parent_accessory gezielt pollen
                        |
                        +-- Feld explizit vorhanden
                        +-- exakter Rawwert 0/1/2
                        +-- source-qualified Snapshot
                        +-- Cache-/Pre-write-Regeln erfüllt
                                |
                                +-- Zielwert --> bestätigt
                                +-- sonst --> weiter pollen / fail-closed
```

Der Provider-Fallback soll weiterhin nur in einem begrenzten Fenster mit
gebundenen Retry-Zeiten arbeiten und keine zusätzliche dauerhafte Polling-Last
erzeugen.

## Anzeige und Read-only-Zustand

Read-only-Anzeige und Control-Sicherheit dürfen unterschiedliche Freshness-
Anforderungen haben.

Für die Anzeige kann der letzte bekannte gültige Phasenwert weiterhin nützlich
sein, solange Quelle und Alter nachvollziehbar bleiben. Für einen Write oder
eine Bestätigung ist dagegen eine strengere control-grade Qualifikation
notwendig.

Ein fehlendes Phasenfeld in einem ansonsten erfolgreich gelesenen Snapshot
soll den Datenpfad nicht automatisch als `unavailable` markieren. Für Control-
Evidenz darf ein fehlendes Feld jedoch nicht als aktuelle Bestätigung gelten.

## Dokumentationskonsistenz

`data_paths_overview.md` enthält derzeit noch die ältere Aussage, der Provider-
Wert `phaseSpecified` sei unbestätigt und nicht für Confirmation geeignet.
Diese Aussage ist hinsichtlich **Mapping** inzwischen überholt:

```text
0 = auto
1 = one_phase
2 = three_phase
```

ist durch den kontrollierten Vergleich bestätigt.

Was weiterhin **nicht** vollständig freigegeben ist, ist die Verwendung des
Providerwerts als Control-Confirmation wegen Cache-/Freshness-Semantik. Das
Overview sollte deshalb bei nächster Bearbeitung zwischen „Mapping bestätigt“
und „Confirmation policy noch nicht implementiert“ unterscheiden.

## Erforderliche Tests vor Implementierung

Mindestens folgende Fälle müssen abgedeckt werden:

1. frischer `241/44`-Wert: Control verfügbar, Direct authoritative;
2. frischer Direct widerspricht gecachtem Provider: Direct bleibt nutzbar;
3. Direct veraltet, expliziter gültiger Parent-Accessory-Wert vorhanden:
   Fallback grundsätzlich möglich;
4. Provider-Geräte-Detailwert allein vorhanden: kein Fallback;
5. Providerwert fehlt im letzten Parent-Snapshot: alter Diagnosewert darf nicht
   als frisch gelten;
6. Providerwert `bool`, `1.5`, `NaN`, `Inf`, `<0`, `>2`: kein Fallback;
7. Provider `0/1/2` wird korrekt gemappt; `2/34` verwendet separat `1/2/3`;
8. generischer `_last_polled_settings`-Merge kann keinen nicht-attribuierten
   Phasenwert als Fallback bestätigen;
9. Phase-No-op wird nicht allein durch einen lokal frischen, möglicherweise
   gecachten Providerwert ausgelöst;
10. SET_REPLY plus bereits vor dem Write identischer Providerzielwert gilt
    nicht automatisch als eindeutiger Transition-Beweis;
11. SET_REPLY plus nachgewiesener Providerwechsel vom Vorwert zum Zielwert kann
    als starke Fallback-Evidenz qualifiziert werden;
12. neuer `241/44` nach dem Write mit Zielwert bestätigt weiterhin sofort;
13. neuer `241/44` nach dem Write mit abweichendem Wert lässt den Write
    fail-closed;
14. `2/34`-Readbacks werden separat diagnostiziert; eine spätere Nutzung als
    Confirmation benötigt eigene Emissions-/Freshness-Evidenz;
15. ein Control-Service kann bei gesperrter Availability weiterhin keinen
    Write erzwingen;
16. bestehende Source-Diagnostik bleibt getrennt und privacy-safe;
17. Provider-Retries bleiben zeitlich begrenzt und erzeugen keine dauerhafte
    zusätzliche Polling-Last.

## Erforderliche Live-Evidenz

Vor Abschluss von PHASE-01 sollte mindestens ein kontrollierter Test mit
schlafendem/stalem `241/44` erfolgen:

1. Ausgangsphase und letzter Providerwert dokumentieren;
2. Direct-Stream bewusst nicht als Confirmation verfügbar;
3. Phasenänderung über Home Assistant auslösen;
4. SET und same-sequence SET_REPLY dokumentieren;
5. mehrere Parent-Accessory-Polls mit Zeitstempel und Rohwert erfassen;
6. zeigen, ob und wann der Provider vom Vorwert auf den Zielwert wechselt;
7. bestätigen, dass die HA-Operation weder zu früh erfolgreich noch fälschlich
   fehlgeschlagen ist.

Zusätzlich ist ein No-op-Sonderfall sinnvoll, bei dem der Provider vor dem Write
bereits den Zielwert enthält. Dieser Test zeigt, ob der Cachewert allein eine
unsichere Write-Unterdrückung oder Bestätigung verursachen könnte.

## Empfehlung

PHASE-01 sollte derzeit geführt werden als:

> **Analysis mostly complete; provider confirmation semantics need refinement**

Empfohlenes weiteres Vorgehen:

1. Phase-Readback intern source-aware modellieren; nicht allein
   `_last_polled_settings` verwenden.
2. Provider-No-op für Phase zunächst konservativ deaktivieren oder separat
   streng qualifizieren.
3. Provider-Post-Write-Bestätigung gegen bekannte Cache-Latenz absichern und
   Pre-write-Evidenz berücksichtigen.
4. Frischen `241/44` weiterhin als authoritative behandeln; ein hinterherhinkender
   Providerwert soll einen frischen Direct-Readback nicht sperren.
5. `2/34` als bestätigte zusätzliche Direct-Quelle dokumentieren, aber erst nach
   gezielter Live-Evidenz als Write-Confirmation-Pfad freigeben.
6. Nach Implementierung die Fallback-Logik mit schlafendem `241/44` live
   validieren.

Die Analyse rechtfertigt **keine generelle Lockerung der Controls** und keinen
Fallback auf `provider_device_detail`. Die bestehenden Transport- und
Ladezustands-Safety-Gates bleiben erhalten; geändert werden muss gezielt die
source-aware No-op-/Readback-Qualifikation der Phase-Control.

## Implementierung

Die lokale Umsetzung folgt der konservativen Variante der Analyse:

- `PhaseReadbackTracker` speichert zusätzlich monotone Beobachtungszeitpunkte,
  ohne diese laufenden Werte in die öffentlichen Diagnosen aufzunehmen;
- Control-Evidenz aus `direct_241_44` und `provider_parent_accessory` verlangt,
  dass der letzte Snapshot das Rohfeld tatsächlich enthielt und der Rawwert
  ein exakter, nicht-boolescher Integer aus `0/1/2` ist;
- frisches `241/44` ist autoritativ. Ist es abgelaufen, blockiert eine jüngere,
  widersprüchliche Direct-Beobachtung einen älteren Provider-Fallback;
- `provider_device_detail` und zusammengeführte `_last_polled_settings` sind
  keine Phase-Control-Quellen;
- `direct_2_34` wird mit seinem bereits source-spezifisch normalisierten Modus
  separat diagnostiziert, bleibt aber außerhalb von Availability und
  Confirmation;
- der generische Provider-No-op wird für Phase vollständig übersprungen;
- vor dem Publish werden Transport, Ladezustand und qualifizierte
  Phase-Evidenz erneut geprüft;
- nach SET und same-sequence SET_REPLY bestätigt ein neuer passender `241/44`
  sofort. Ohne Direct-Bestätigung kann nur ein expliziter Parent-Accessory-
  Wechsel von einem frischen, abweichenden Pre-write-Wert zum Ziel bestätigen;
- ein bereits vor dem Write identischer Providerwert kann weder den Publish
  unterdrücken noch den Write allein bestätigen;
- die vorhandenen kurzen Direct-Wartezeiten und begrenzten Provider-Retries
  bleiben unverändert, sodass keine dauerhafte zusätzliche Polling-Last
  entsteht.

Die lokale Testmatrix deckt Direct-Priorität, Provider-Fallback, jüngere
widersprüchliche Direct-Evidenz, fehlende Felder, Device-Detail-Ausschluss,
exakte Rawvalidierung, getrenntes `2/34`, Provider-Transition, Already-at-target
und abweichende beziehungsweise passende Post-write-Directwerte ab. Die oben
beschriebene Live-Evidenz bleibt vor Abschluss von `PHASE-01` erforderlich.

## Live-Teilvalidierung (2026-09-02)

Der Test wurde mit verbundenem Fahrzeug und ohne laufenden Ladevorgang
durchgeführt. Der Ladevorgang wurde zuvor kontrolliert beendet; der Wallbox-
Status war anschließend `charge_complete`. Ausgangszustand war `auto`, der
Direct-Datenstrom war frisch und die Phase-Control verfügbar.

Der Wechsel `auto -> one_phase` über den HA-Phase-Select wurde erfolgreich
bestätigt. Der unabhängige HA-Sensor `Ausgewählte Phase Rohwert` wechselte auf
`1`, ebenso der lesende Phasen-Sensor auf `one_phase`. Die Integration meldete
die Operation erst nach ihrem normalen Write-/Readback-Pfad als erfolgreich.

Anschließend wurde `one_phase -> auto` ausgeführt und ebenfalls bestätigt. Der
Rohwert kehrte auf `0` zurück; der abschließende Wallbox-Status blieb
`charge_complete`. Die Integrationslogs enthielten im geprüften Zeitraum
keine Fehler.

Diese Teilvalidierung bestätigt den normalen frischen-Direct-Pfad und den
Restore. Sie schließt `PHASE-01` noch nicht ab: Während des Tests blieb
`241/44` aktiv und wurde nach dem Stopp weiterhin ungefähr sekündlich
aktualisiert. Deshalb konnte weder der Provider-Fallback bei stale `241/44`
noch der Already-at-target-Fall ohne neue Direct-Evidenz isoliert werden.
