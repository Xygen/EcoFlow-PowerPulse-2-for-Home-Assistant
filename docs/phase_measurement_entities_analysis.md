# DATA-06: Analyse der Einzelwerte für Phasenspannung und Phasenstrom

Stand: 2026-08-30  
Bezug: [Backlog `DATA-06`](backlog.md)

## Ergebnis in Kurzform

Der Direct-Heartbeat `2/33` liefert für Protobuf-Feld `29` drei wiederholte
Floatwerte für Spannungen und für Feld `30` drei wiederholte Floatwerte für
Ströme. Die aktuelle Integration verwirft die Einzelwerte und veröffentlicht
jeweils nur den größten gültigen Wert als kompakte Zusammenfassung.

Das bestehende Aggregat soll aus Kompatibilitätsgründen erhalten bleiben. Die
sechs Einzelwerte können zusätzlich als getrennte, standardmäßig deaktivierte
Diagnose-Sensoren eingeführt werden. Vor einer produktiven Zuordnung zu
`L1/L2/L3` muss jedoch nachgewiesen werden, dass die Reihenfolge der
wiederholten Werte stabil und elektrisch eindeutig ist.

## Ist-Zustand

Der Parser akzeptiert sowohl einzelne Float-Felder als auch die gepackte
Protobuf-Form. Er sammelt die Werte in zwei Listen:

- Feld `29`: Phase voltage;
- Feld `30`: Phase current.

Danach setzt er aktuell:

- `phase_voltage_v = max(phase_voltages)`;
- `phase_current_a = max(phase_currents)`.

Diese beiden Werte werden außerdem als `direct_phase_voltage_v` und
`direct_phase_current_a` für die Direct-Entities gespiegelt. Die bestehenden
Entity-IDs und ihre Semantik als kompakte Maximalwerte dürfen durch die
Erweiterung nicht verändert werden.

Die vorhandenen Live-Vergleiche bestätigen, dass drei Werte vorhanden sind und
dass Spannung mal Strom nur eine scheinbare Leistung ergibt. Sie bestätigen
aber nicht, dass der erste, zweite und dritte Listenwert dauerhaft sicher
`L1`, `L2` und `L3` entsprechen.

## Nutzerproblem und Nutzen

Das Aggregat beantwortet die Frage „wie hoch ist der größte beobachtete
Phasenwert?“. Für Diagnose, Lastverteilung und die Erkennung einer einzelnen
auffälligen Phase reicht das nicht aus. Einzel-Entities würden zusätzlich
zeigen:

- ob nur eine oder drei Phasen belastet werden;
- ob eine Phase deutlich von den anderen abweicht;
- ob Spannung und Strom derselben Phase gemeinsam bewertet werden können.

Wichtig ist, dass dadurch kein neuer Gesamtleistungswert aus Maximalwerten
berechnet wird. Die bestehende Direct-Leistung bleibt die geeignete
Real-Power-Entity; Einzelspannung und Einzelstrom sind Messwerte, aber keine
automatische Ersatzberechnung für Leistung.

## Empfohlenes Entity-Design

### Bestehende Entities unverändert

Die aktuellen normalen, aber standardmäßig deaktivierten Direct-Entities
bleiben bestehen:

- `direct_phase_voltage` / `phase_voltage_v` als bisheriger Maximalwert;
- `direct_phase_current` / `phase_current_a` als bisheriger Maximalwert.

Damit bleiben bestehende Dashboards, Automationen und Entity-IDs kompatibel.

### Zusätzliche Einzel-Entities

Als erste sichere Modellierung werden sechs zusätzliche Sensoren vorgeschlagen:

| Messgröße | vorgeschlagene Schlüssel |
| --- | --- |
| Spannung | `direct_phase_1_voltage_v`, `direct_phase_2_voltage_v`, `direct_phase_3_voltage_v` |
| Strom | `direct_phase_1_current_a`, `direct_phase_2_current_a`, `direct_phase_3_current_a` |

Die Bezeichnung `phase_1` bis `phase_3` ist zunächst sicherer als `L1` bis
`L3`, solange die physische Zuordnung der Array-Positionen nicht nachgewiesen
ist. Die sechs Sensoren sollten standardmäßig deaktiviert und als Diagnose
klassifiziert werden, bis Reihenfolge, Verfügbarkeit und praktische
Interpretation durch weitere Daten bestätigt sind.

Nach einer bestätigten festen Zuordnung kann geprüft werden, ob nutzerseitig
sprechende Übersetzungen `L1`, `L2` und `L3` sinnvoll sind. Eine Umbenennung
der bestehenden Aggregat-Entities ist nicht vorgesehen.

## Daten- und Verfügbarkeitsregeln

### Anzahl der Werte

- Drei valide Werte: alle drei Einzel-Entities liefern Werte.
- Ein oder zwei valide Werte: nur die tatsächlich vorhandenen Positionen
  liefern Werte; fehlende Positionen werden `unknown`, nicht `0`.
- Keine validen Werte im aktuellen Direct-Report: Einzelwerte werden
  `unknown`; der gesunde Direct-Datenpfad bleibt nicht deshalb
  `unavailable`.
- Ungültige, nicht-finite oder falsch lange Bytefolgen werden verworfen.

### One-phase-Betrieb

Einphasiger Betrieb darf nicht durch künstliche Nullen für die nicht
verwendeten Phasen dargestellt werden. `0 A` wäre eine physische Aussage und
könnte mit einer echten Messung verwechselt werden. Nicht gelieferte Phasen
bleiben daher `unknown`, sofern der Report ihre Positionen nicht ausdrücklich
als Nullwert enthält.

### Freshness und Merge

Die Einzelwerte müssen an den Direct-Report und dessen Zeitstempel gebunden
bleiben. Das allgemeine Merge-Verhalten darf keine alte Einzelphase an eine
neue unvollständige Liste anhängen, ohne dies als letzten bekannten Wert zu
kennzeichnen. Für die Umsetzung ist deshalb zu entscheiden, ob Listen als
vollständiger Snapshot ersetzt werden oder ob pro Position eigene
Beobachtungszeitpunkte gespeichert werden.

Empfohlen wird zunächst ein vollständiger, positionsbezogener Snapshot: Jede
Direct-Meldung setzt die sechs Werte aus genau dieser Meldung. Nicht enthaltene
Positionen werden für diesen Snapshot `unknown`; ein separater letzter
bekannter Wert kann höchstens als Diagnoseinformation erhalten bleiben.

## Reihenfolge und Evidenzgrenze

Die vorhandenen Parser- und Live-Belege zeigen die Anzahl und physikalische
Art der Werte, aber keine ausreichende Dokumentation einer stabilen
Listenposition. Deshalb gelten folgende Grenzen:

- Keine automatische Umrechnung oder Sortierung nach Wertgröße.
- Keine Zuordnung zu `L1/L2/L3` allein anhand von Spannung oder Strom.
- Keine Paarbildung über zwei unabhängig eingetroffene Reports.
- Kein Summieren der Maximalwerte zur Gesamtleistung.

Für `phase_1` bis `phase_3` genügt ein kontrollierter Nachweis, dass mehrere
Reports dieselbe physische Reihenfolge beibehalten. Für die Namen `L1/L2/L3`
ist zusätzlich eine elektrische Referenz oder ein kontrollierter
Installationsvergleich erforderlich.

## Erforderliche Tests vor Implementierung

1. Unpacked- und packed-Floatwerte werden positionsgetreu in drei Werte je
   Messgröße übernommen.
2. Die bisherigen Maximalwert-Keys bleiben unverändert.
3. Reihenfolge und Werte werden nicht sortiert.
4. Ein-, zwei- und dreielementige Listen erzeugen keine künstlichen Nullen.
5. Nicht-finite Werte und ungültige Paketlängen werden sicher behandelt.
6. Ein neuer unvollständiger Report lässt keine alte Einzelposition als
   scheinbar aktuellen Messwert stehen.
7. Einzelwerte erhalten korrekte Einheiten, Device Classes und
   Measurement-State-Class.
8. Neue Entities sind standardmäßig deaktiviert; bestehende Entity-IDs und
   Übersetzungen bleiben unverändert.
9. Fehlende Einzelwerte führen zu `unknown`, ein tatsächlich fehlender
   Direct-Datenpfad zu `unavailable`.

## Empfehlung

DATA-06 ist als Designanalyse abgeschlossen. Empfohlen wird ein zweistufiges
Vorgehen:

1. Die sechs positionsbezogenen Direct-Diagnose-Sensoren mit vollständiger
   Snapshot-/Freshness-Semantik implementieren, ohne bestehende Aggregatwerte
   zu ändern.
2. Erst nach stabiler Positions-Evidenz über eine nutzerseitige
   `L1/L2/L3`-Benennung und eine eventuelle Aktivierung außerhalb der Diagnose
   entscheiden.

Die Analyse rechtfertigt weder das Entfernen der bestehenden Aggregatwerte
noch die Berechnung einer neuen Gesamtleistung aus den sechs Einzel-Entities.
