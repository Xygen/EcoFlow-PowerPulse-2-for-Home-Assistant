# PHASE-01: Analyse des Phasen-Readbacks

Stand: 2026-08-30  
Bezug: [Backlog `PHASE-01`](backlog.md)

## Ergebnis in Kurzform

Der Root-Cause ist eine Verfügbarkeitslücke im **Direct-Readback**, nicht eine
unklare Phasen-Zuordnung. Die Zuordnung ist durch gekoppelte Beobachtungen
bestätigt:

| Wert | Bedeutung |
| ---: | --- |
| `0` | Auto |
| `1` | einphasig |
| `2` | dreiphasig |

Der gültige Wert ist gelegentlich über den Direct-Stream `241/44` nicht frisch
verfügbar. Derselbe Wert wurde im PowerOcean-Elternzubehör beobachtet. Diese
Provider-Quelle wird diagnostisch erfasst, aber noch nicht zur Freigabe oder
Bestätigung der Phase-Control verwendet.

## Aktueller Datenfluss

### Direct-Quelle

Der Parser des C376-Settings-Reports `241/44` erzeugt sowohl
`phase_specified_raw` als auch das normalisierte `phase_mode`. Der Coordinator
merkt den Zeitpunkt des letzten Direct-Reports und verwendet eine feste
Frischegrenze.

`phase_control_available()` verlangt derzeit:

1. einen gültigen Schreibpfad über genau einen PowerOcean-Beobachter,
2. einen für den aktuellen Ladezustand zulässigen Control,
3. einen frischen Direct-Report,
4. einen gültigen normalisierten Wert (`auto`, `one_phase` oder `three_phase`).

Fehlt Bedingung 3, wird die Control `unavailable`, auch wenn ein gültiger
Provider-Wert vorliegt.

### Provider-Quellen

Provider-Snapshots werden getrennt nach `provider_parent_accessory` und
`provider_device_detail` erfasst. Die bisherigen Beobachtungen zeigen:

- der Elternzubehör-Pfad kann `phaseSpecified` liefern und wurde gegen
  Direct-Readback abgeglichen;
- der Geräte-Detail-Pfad liefert den Phasenwert für dieses Gerät nicht
  zuverlässig und darf daher nicht als gleichwertige Quelle gelten;
- die Diagnose bewahrt Quellen, Zeitpunkte und Wertvalidität getrennt auf.

Damit ist der Provider-Elternwert ein möglicher Fallback, der
Geräte-Detailwert aber kein geeigneter Ersatz.

## Root-Cause

Die aktuelle Implementierung koppelt die Freigabe der Phase-Control an die
Frische des Direct-Streams. Diese Kopplung ist für sichere Direct-Bestätigung
verständlich, bildet aber die vorhandene zweite Evidenzquelle noch nicht ab.

Der Fehler ist daher eine fehlende **Readback-Quellenstrategie**:

- Quelle A (Direct `241/44`) ist bevorzugt und zeitnah;
- Quelle B (PowerOcean-Elternzubehör) ist langsamer, aber fachlich bestätigt;
- die Entscheidung, wann B eine Control freigeben oder einen Write bestätigen
  darf, ist noch nicht implementiert.

Einfach die bestehende Direct-Frischegrenze zu verlängern wäre keine Lösung.
Das würde einen möglicherweise alten Direct-Wert als frisch behandeln und die
Sicherheitsbedeutung der Frischegrenze verwässern.

## Abgeleitete Zielregeln

### Für die Anzeige

Der Read-only-Phasenwert kann aus einer validen Quelle angezeigt werden. Dabei
sollten Quelle und Alter des Wertes nachvollziehbar bleiben. Ein fehlender
aktueller Snapshot darf nicht automatisch einen gesunden Datenpfad als
`unavailable` markieren.

### Für einen Write

Ein Provider-Fallback darf nur verwendet werden, wenn alle folgenden Regeln
erfüllt sind:

1. Es handelt sich ausschließlich um den bestätigten
   `provider_parent_accessory`-Pfad.
2. Der Wert ist numerisch gültig und liegt in `0..2`.
3. Der Snapshot besitzt einen erfassten Beobachtungszeitpunkt und liegt
   innerhalb einer ausdrücklich festgelegten Provider-Frischegrenze.
4. Es gibt keinen aktuelleren Direct-Wert mit abweichender Bedeutung.
5. Nach dem Write kommen wie bisher ein passendes `set_reply` und ein neuer,
   unabhängiger Readback zusammen.

Für eine besonders konservative erste Umsetzung sollte der Provider-Wert die
Control nur dann freigeben, wenn der Direct-Stream nicht frisch ist, aber der
Provider-Snapshot frisch und eindeutig ist. Bei widersprüchlichen Quellen
bleibt die Control gesperrt.

### Für die Quellenpriorität

Die empfohlene Priorität lautet:

1. frischer Direct-Readback;
2. frischer Provider-Elternzubehör-Readback;
3. kein bestätigbarer Wert.

Der Provider-Geräte-Detailwert darf nicht in diese Prioritätskette aufgenommen
werden, solange seine Semantik für dieses Gerät nicht bestätigt ist.

## Risiken und offene Entscheidungen

- Die Provider-Abfrage ist langsamer als der Direct-Stream. Die zulässige
  Provider-Frischegrenze muss deshalb fachlich festgelegt und getestet werden.
- Ein Provider-Snapshot kann einen älteren Zustand enthalten, der nach einer
  gerade erfolgten Änderung noch nicht nachgezogen wurde.
- Ein bloßer Wertvergleich ohne Zeitstempel genügt nicht als Write-Bestätigung.
- Bei Direct-/Provider-Konflikt muss fail-closed gelten; automatische Auswahl
  nach numerischer Nähe wäre falsch.
- Der allgemeine Coordinator-Merge bewahrt fehlende Felder aus älteren Werten.
  Für die Phase-Control muss daher zwischen dem sichtbaren letzten Wert und
  einem frisch bestätigbaren Readback unterschieden werden.

## Erforderliche Tests vor Implementierung

Die Testabdeckung sollte mindestens diese Fälle enthalten:

1. frischer Direct-Wert: Control verfügbar, Direct ist bevorzugte Quelle;
2. Direct veraltet, frischer gültiger Provider-Elternwert: Fallback zulässig;
3. beide Quellen veraltet: Control `unavailable`;
4. Provider-Geräte-Detailwert allein vorhanden: kein Fallback;
5. Providerwert außerhalb `0..2`, fehlend oder falsch typisiert: kein Fallback;
6. Direct und Provider widersprechen sich: kein automatisches Freigeben;
7. Provider-Readback nach einem Phase-Write bestätigt nur bei neuem Snapshot;
8. bestehende Direct- und Provider-Diagnose bleiben getrennt und redigiert;
9. ein Control-Service kann bei gesperrtem Fallback weiterhin nicht schreiben.

## Empfehlung

PHASE-01 ist ausreichend analysiert für einen kleinen, isolierten Folge-Change:

- eine eigene Readback-Qualifikation für Phase ergänzen,
- nur `provider_parent_accessory` als nachrangige Quelle zulassen,
- Quellenzeitpunkt und Frische explizit berücksichtigen,
- bestehende Write-Gates und die unabhängige Bestätigung unverändert lassen.

Die Analyse rechtfertigt keine generelle Lockerung der Controls und keinen
Fallback auf den Geräte-Detail-Provider.
