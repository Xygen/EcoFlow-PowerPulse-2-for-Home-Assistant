# DATA-06: Analyse der Einzelwerte für Phasenspannung und Phasenstrom

> **Status: deferred nach v1.0.0.** Die Analyse begründet, warum weiterhin nur
> die bestätigten Aggregatwerte veröffentlicht werden. Positionsstabile
> Phasenentitäten benötigen zusätzliche Mehrzustands-Evidenz; Details stehen im
> [Backlog](backlog.md).

Stand: 2026-08-30  
Bezug: [Backlog `DATA-06`](backlog.md)

## Ergebnis in Kurzform

Der Direct-Heartbeat `2/33` enthält Protobuf-Feld `29` als wiederholte bzw.
gepackte Floatwerte für Spannungen und Feld `30` entsprechend für Ströme. Der
aktuelle Parser sammelt die gültigen Werte in Listen und veröffentlicht danach
nur den jeweils größten Wert:

- `phase_voltage_v = max(phase_voltages)`;
- `phase_current_a = max(phase_currents)`.

Damit gehen die Einzelwerte verloren. Das bisherige Maximum soll aus
Kompatibilitätsgründen erhalten bleiben, eine Erweiterung um Einzelwerte ist
aber weiterhin sinnvoll.

Die vorherige DATA-06-Analyse war an einer Stelle zu weitgehend: Aus dem
Vorhandensein mehrerer Werte folgt noch nicht, dass daraus bereits sichere
`phase_1`- bis `phase_3`-Entities abgeleitet werden können. Vor einer
Implementierung müssen zusätzlich drei Eigenschaften mit realen Heartbeats
belegt werden:

1. ob Feld `29` und Feld `30` pro `2/33` jeweils vollständige Snapshots oder
   möglicherweise Teil-/Delta-Updates darstellen;
2. ob die Positionen innerhalb der beiden wiederholten Felder über Zeit und
   Betriebszustände stabil bleiben;
3. ob `voltage[i]` und `current[i]` tatsächlich dieselbe physische
   Leiter-/Phasenposition beschreiben.

Außerdem muss der Parser vor einer positionsbezogenen Auswertung geändert
werden: Nicht-finite Werte dürfen nicht einfach aus der Liste entfernt werden,
weil dadurch nachfolgende Werte ihre Position verschieben würden.

DATA-06 ist deshalb **weitgehend analysiert, aber noch nicht
implementierungsbereit**. Zuerst ist eine kleine Evidenz- und Parserphase
notwendig.

## Gesicherter Ist-Zustand

### Parser

Der Parser akzeptiert für Feld `29` und `30` sowohl einzelne `fixed32`-Floats
als auch die gepackte Protobuf-Form. In beiden Fällen werden nur finite Werte
in zwei Python-Listen übernommen:

- Feld `29` -> `phase_voltages`;
- Feld `30` -> `phase_currents`.

Danach setzt der Parser aktuell nur die Maxima. Diese Werte werden zusätzlich
als `direct_phase_voltage_v` und `direct_phase_current_a` gespiegelt und bilden
die Quelle der bestehenden Direct-Entities.

Die bestehenden Keys und Unique IDs dürfen durch DATA-06 nicht verändert
werden.

### Bisherige Leistungsinterpretation

Die vorhandenen direkten Leistungs-, Spannungs- und Stromvergleiche zeigen,
dass `U * I` beziehungsweise `3 * U * I` eine Scheinleistungsabschätzung und
keinen Ersatz für die native Direct-Leistung ergibt. Insbesondere sind die
heutigen Spannungs- und Stromentitäten Maxima ihrer jeweiligen Arrays und
keine nachgewiesenen phasenweise ausgerichteten Paare.

Daher gilt weiterhin:

- keine Gesamtleistungsberechnung aus den Maximalwerten;
- keine Ableitung einer vermeintlich genaueren Wirkleistung aus Spannung und
  Strom;
- die native Direct-Leistung bleibt die maßgebliche Real-Power-Entity.

## Noch nicht ausreichend belegt

### Vollständiger Snapshot oder Delta

Die bisherige Analyse nahm als bevorzugtes Design an, dass jede neue
Direct-Meldung die komplette Spannungs- und Stromliste ersetzt. Dafür fehlt in
der eingecheckten Evidenz noch ein ausreichender Nachweis.

Vor der Implementierung muss deshalb in realen `2/33`-Frames geprüft werden:

- ist Feld `29` in jedem relevanten Heartbeat vorhanden;
- ist Feld `30` in jedem relevanten Heartbeat vorhanden;
- erscheinen beide immer gemeinsam;
- wie viele Werte enthalten sie jeweils;
- ändert sich dieses Verhalten zwischen `unplugged`, `plugged_in`,
  einphasigem Laden, dreiphasigem Laden, Start, Stop und Leistungsänderungen.

Erst danach wird festgelegt, ob ein neuer Heartbeat den gesamten
positionsbezogenen Messsatz ersetzt oder ob pro Messgröße beziehungsweise
Position eigene Freshness-Zeitpunkte benötigt werden.

### Positionsstabilität innerhalb eines Feldes

Dass ein wiederholtes Feld drei Werte enthält, beweist noch nicht, dass
Position `0`, `1` und `2` dauerhaft dieselbe elektrische Bedeutung behalten.

Es darf daher vorerst nicht:

- nach Wertgröße sortiert werden;
- aus einer Spannung oder einem Strom auf `L1/L2/L3` geschlossen werden;
- eine Position anhand des jeweils größten oder kleinsten Werts umbenannt
  werden.

### Paarung von Spannung und Strom

Zusätzlich zur Stabilität innerhalb der Felder muss getrennt nachgewiesen
werden, dass:

```text
field 29, position i
```

und

```text
field 30, position i
```

dieselbe physische Leiter-/Phasenposition beschreiben.

Ohne diesen Nachweis wäre selbst ein Entity-Paar wie
`phase_1_voltage`/`phase_1_current` semantisch zu stark, weil es bereits eine
gemeinsame Phase suggeriert.

Für eine spätere Benennung als `L1/L2/L3` ist darüber hinaus eine elektrische
Referenz oder ein kontrollierter Installationsvergleich erforderlich.

## Konkreter Parserfehler für eine zukünftige Positionsauswertung

Der aktuelle Parser verwirft nicht-finite Werte, bevor die Liste aufgebaut ist.
Für das heutige Maximum ist das korrekt. Für positionsbezogene Werte würde es
aber die Positionen verschieben.

Beispiel eines hypothetischen Rohwerts:

```text
[231.2, NaN, 230.8]
```

Der heutige Sammelmechanismus würde daraus effektiv:

```text
[231.2, 230.8]
```

machen. Eine spätere Zuordnung nach Listenindex würde den ursprünglichen dritten
Wert fälschlich als zweiten Wert behandeln.

Vor DATA-06 muss deshalb eine positionsstabile interne Repräsentation eingeführt
werden, beispielsweise:

```text
[231.2, None, 230.8]
```

oder ein gleichwertiges festes Positionsmodell. Für die bestehenden Maxima
kann anschließend weiterhin separat nur über valide Werte aggregiert werden.
Damit bleibt die bestehende Semantik unverändert.

## Robustheitsregeln für die Rohdaten

Vor einer Entity-Implementierung müssen folgende Fälle definiert und getestet
sein:

### Erwartete Kardinalität

- exakt drei Werte;
- ein oder zwei Werte;
- keine Werte;
- mehr als drei Werte;
- unterschiedliche Anzahl von Spannungs- und Stromwerten.

Mehr als drei Werte sollten nicht still auf drei Werte gekürzt werden. Ein
solcher Frame kann auf eine bisher falsch verstandene Struktur oder eine
Protokolländerung hindeuten und sollte diagnostisch als Anomalie behandelt
werden, bevor daraus Positions-Entities aktualisiert werden.

### Packed und unpacked

Der Parser muss die Reihenfolge erhalten bei:

- drei einzelnen `fixed32`-Feldern;
- einem gepackten Feld;
- mehreren gepackten Segmenten;
- einer Mischung aus packed und unpacked, sofern ein solcher realer Frame
  überhaupt beobachtet wird.

Eine gepackte Bytefolge, deren Länge kein Vielfaches von vier ist, darf nicht
teilweise als gültige Positionsliste verwendet werden.

### Nicht-finite Werte

`NaN`, `+Inf` und `-Inf` dürfen keinen Messwert erzeugen, ihre ursprüngliche
Position darf für eine positionsbezogene Auswertung aber nicht verloren gehen.

### Nullwerte

Ein vom Gerät ausdrücklich gelieferter `0.0 A`-Wert ist ein echter Messwert und
muss als `0 A` erhalten bleiben.

Eine nicht gelieferte Position darf dagegen nicht künstlich zu `0 A` werden.
Solange keine vollständige Snapshot-Semantik belegt ist, darf aus einem
fehlenden Element außerdem noch nicht automatisch geschlossen werden, dass die
betreffende Phase physisch nicht benutzt wird.

## Freshness, `unknown` und `unavailable`

Die bestehende Integration trennt bereits grundsätzlich zwischen einer
verfügbaren Datenquelle und dem Vorhandensein eines einzelnen Feldes:

- gesunde Quelle, Feld fehlt -> Entity-Wert `unknown`;
- erforderlicher Direct-Datenpfad nicht verfügbar/frisch -> Entity
  `unavailable`.

Dieses Modell soll für DATA-06 beibehalten werden.

Wie fehlende einzelne Positionen innerhalb eines ansonsten frischen Heartbeats
behandelt werden, hängt jedoch von der noch zu klärenden Snapshot-/Delta-Frage
ab. Deshalb wird die frühere Festlegung „jede neue Meldung setzt fehlende
Positionen sofort auf `unknown`“ vorerst zurückgenommen.

Mögliche Zielmodelle sind:

### Falls `2/33` vollständige Arrays liefert

Jeder Heartbeat ersetzt den gesamten Positionssatz. Eine in diesem Snapshot
nicht gelieferte beziehungsweise ungültige Position wird `unknown`.

### Falls Teil-/Delta-Updates vorkommen

Positionen beziehungsweise die beiden Arrays benötigen eigene
Beobachtungszeitpunkte und eine klar definierte Freshness-Regel. Ein älterer
Wert darf dann nicht still als aktuell erscheinen, muss aber auch nicht durch
ein unrelated Teilupdate sofort gelöscht werden.

## Empfohlenes Entity-Design nach Abschluss der Evidenzphase

### Bestehende Aggregate erhalten

Die bestehenden Entitäten bleiben mit unveränderten Keys und Unique IDs
bestehen:

- `phase_voltage_v` / `direct_phase_voltage_v`;
- `phase_current_a` / `direct_phase_current_a`.

Da es sich tatsächlich um Maximalwerte handelt, kann später geprüft werden, ob
nur die sichtbaren Übersetzungen präziser als „maximale Phasenspannung“ und
„maximaler Phasenstrom“ formuliert werden. Das wäre keine Änderung der Unique
IDs.

### Neue Positions-Entities erst nach Nachweis

Dauerhafte Entity-Keys sollten erst festgelegt werden, wenn Positionsstabilität
und Voltage/Current-Paarung belegt sind. Bis dahin ist eine interne oder
Diagnose-Darstellung mit neutralen Begriffen wie `voltage_position_1` und
`current_position_1` fachlich sauberer als `phase_1_*`.

Sind Paarung und stabile Reihenfolge bestätigt, können beispielsweise sechs
zusätzliche Sensoren entstehen:

| Messgröße | mögliche Schlüssel nach Bestätigung |
| --- | --- |
| Spannung | `direct_phase_1_voltage_v`, `direct_phase_2_voltage_v`, `direct_phase_3_voltage_v` |
| Strom | `direct_phase_1_current_a`, `direct_phase_2_current_a`, `direct_phase_3_current_a` |

Sie sollten zunächst:

- `EntityCategory.DIAGNOSTIC` verwenden;
- standardmäßig deaktiviert sein;
- Spannung mit `SensorDeviceClass.VOLTAGE` und `V` exponieren;
- Strom mit `SensorDeviceClass.CURRENT` und `A` exponieren;
- `SensorStateClass.MEASUREMENT` verwenden.

Eine normale Aktivierung oder Benennung als `L1/L2/L3` ist ein späterer Schritt
und benötigt zusätzliche Evidenz.

## Rundung und Recorder-Last

Die bestehenden Maximalwerte werden bereits vor der Veröffentlichung gerundet:

- Spannung auf eine Nachkommastelle;
- Strom auf zwei Nachkommastellen.

Die späteren Einzelwerte sollten dieselbe Normalisierung verwenden. Damit
werden rohe Float32-Artefakte nicht als unnötige Home-Assistant-Zustandswechsel
in den Recorder geschrieben.

Die Entscheidung für standardmäßig deaktivierte Diagnose-Entities reduziert
zusätzlich Recorder- und UI-Last für Benutzer, die diese Detailwerte nicht
benötigen.

## Erforderliche Evidenz vor Implementierung

Mindestens eine kontrollierte Aufzeichnung soll vollständige Feld-29- und
Feld-30-Rohwerte mit Zeitstempel für mehrere Betriebszustände dokumentieren:

1. unplugged;
2. Fahrzeug verbunden, aber nicht ladend;
3. aktives einphasiges Laden;
4. aktives dreiphasiges Laden;
5. mindestens eine deutliche Leistungsänderung;
6. Start und Stop beziehungsweise Session-Grenzen.

Dabei ist pro Heartbeat festzuhalten:

```text
Timestamp
charging state
phase setting/readback
field 29 raw ordered values
field 30 raw ordered values
charging power
```

Die Evidenzphase gilt erst als abgeschlossen, wenn daraus belastbar entschieden
werden kann:

- Snapshot oder Delta;
- erwartete Kardinalität;
- stabile Positionen;
- Paarung von Spannung und Strom derselben Position.

## Erforderliche Tests vor Entity-Implementierung

1. Packed- und unpacked-Floatwerte werden in Wire-Reihenfolge erhalten.
2. Nicht-finite Werte verschieben keine nachfolgenden Positionen.
3. Die bisherigen Maximalwert-Keys und ihre Werte bleiben unverändert.
4. Positionswerte werden niemals nach Größe sortiert.
5. Ein-, zwei-, drei- und mehr als dreielementige Listen werden explizit
   behandelt.
6. Unterschiedliche Kardinalität von Feld `29` und `30` wird sicher behandelt.
7. Ungültige packed-Längen werden nicht teilweise übernommen.
8. Tatsächlich gelieferte `0.0`-Werte bleiben echte Nullwerte.
9. Snapshot-/Delta-Verhalten folgt der zuvor dokumentierten Live-Evidenz.
10. Einzelwerte erhalten korrekte Einheiten, Device Classes und
    `MEASUREMENT`-State-Class.
11. Neue Entities sind standardmäßig deaktiviert und diagnostisch.
12. Bestehende Unique IDs bleiben unverändert.
13. Fehlende Feldwerte und fehlender Direct-Datenpfad werden korrekt als
    `unknown` beziehungsweise `unavailable` unterschieden.
14. Eine spätere `phase_1`-Paarung wird nur freigegeben, wenn `voltage[i]` und
    `current[i]` als dieselbe physische Position bestätigt sind.

## Empfehlung

DATA-06 sollte nicht mehr als „Analysis complete; implementation pending“
geführt werden, sondern als:

> **Analysis mostly complete; phase-array evidence validation pending**

Empfohlenes weiteres Vorgehen:

1. Parser so vorbereiten, dass Rohpositionen einschließlich ungültiger Slots
   positionsstabil untersucht werden können, ohne die bestehenden Aggregate zu
   verändern.
2. Kontrollierte reale `2/33`-Captures über die relevanten Betriebszustände
   sammeln und Snapshot-/Delta-Semantik, Kardinalität, Positionsstabilität und
   Voltage/Current-Paarung klären.
3. Erst danach dauerhafte sechs Einzel-Entities definieren und implementieren.
4. Nach zusätzlicher elektrischer Zuordnung separat über `L1/L2/L3`-Namen und
   normale Aktivierung entscheiden.

Unverändert gilt: DATA-06 rechtfertigt weder das Entfernen der bestehenden
Aggregatwerte noch die Berechnung einer neuen Gesamtleistung aus Spannungs- und
Strommaxima.

## Live-Evidenz: Solar-Ladevorgang (2026-09-02)

Ein privacy-safe Direct-Heartbeat `2/33` während aktiver Solar-Ladung enthielt
je drei geordnete Werte:

```text
field 29 voltage: [228.11, 229.12, 228.66] V
field 30 current: [  5.67,   0.01,   0.01] A
```

Im selben Zeitfenster meldeten die bestehenden Aggregate `229.1 V` und
`5.67 A`, also jeweils den Maximalwert der Liste, bei `1258.2 W` Ladeleistung.
Die Momentaufnahme ist mit einer einphasig wirksamen Last vereinbar, beweist
aber weder eine feste physische Position noch eine allgemeine Zuordnung zu
`L1/L2/L3`. Insbesondere bleiben Snapshot-vs-Delta, Positionsstabilität,
abweichende Kardinalitäten und Mehrphasen-/Grenzfallaufnahmen offen.

Zwei nachfolgende Heartbeats bestätigten die Kardinalität und das Muster erneut:

```text
field 29 voltage: [230.90, 231.63, 230.51] V -> [231.12, 231.46, 230.51] V
field 30 current: [  5.71,   0.01,   0.01] A -> [  5.71,   0.01,   0.01] A
```

Damit ist die geordnete Dreierstruktur für diesen Solar-Betriebszustand über
mehrere Frames wiederholt beobachtet. Sie ist weiterhin kein Beleg für eine
positionsstabile oder physisch benannte Phasen-Zuordnung.
