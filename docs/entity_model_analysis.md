# ENTITY-03: Analyse des Entity-Modells

Stand: 2026-08-30  
Bezug: [Backlog `ENTITY-03`](backlog.md)

## Fragestellung

PowerPulse 2 stellt für mehrere Einstellungen sowohl eine Read-only-Entity als
auch eine schreibbare Control-Entity bereit. Beispiele sind maximaler Strom,
Solar-Mindeststrom, benutzerdefinierter Ladestrom, Phase, Smart-Ziel und
Bildschirm-/LED-Einstellungen.

Die zentrale Frage ist, ob diese Paare zusammengelegt werden können. Dabei ist
zu berücksichtigen, dass eine Control-Entity zeitweise nicht verfügbar sein
kann, obwohl der zuletzt bzw. aktuell beobachtete Einstellungswert weiterhin
für den Anwender lesbar sein sollte.

## Ist-Zustand

### Read-only-Beobachtung

Die Sensoren in `sensor.py` lesen Werte aus dem Coordinator-Datensatz. Ihre
Verfügbarkeit hängt vom Coordinator, dem erkannten Gerät und der benötigten
Datenquelle ab. Das Vorhandensein eines einzelnen Feldes ist bewusst kein
Verfügbarkeitskriterium; ein gesunder Datenpfad kann deshalb `unknown` liefern,
wenn ein Feld in einem Snapshot fehlt.

Relevante Einstellungsbeobachtungen sind unter anderem:

| Bedeutung | Read-only-Entity / Datenfeld |
| --- | --- |
| Maximaler Ausgangsstrom | `current_limit_raw` bzw. `output_current_max_raw` |
| Benutzerdefinierter Ladestrom | `user_current_set_a` |
| Solar-Mindeststrom | `solar_minimum_current_a` |
| Betriebsmodus | `work_mode` |
| Phase | `phase_mode` |
| Smart-Ziel und Zieltyp | `smart_charge_target_wh`, `smart_target_distance_km`, `smart_target_type` |
| Bildschirm/LED | `screen_enabled`, `screen_brightness_pct`, `indicator_enabled`, `indicator_brightness_pct` |

Diese Entities dienen der Beobachtung. Sie benötigen keine aktuell verfügbare
Schreibverbindung, sofern ihre jeweilige Read-only-Quelle noch verfügbar ist.

### Schreibbare Control-Entity

Numbers, Selects, Switches und DateTime-Entities prüfen zusätzlich, ob ein
Schreibpfad verwendbar ist. Dafür müssen unter anderem ein passender
PowerOcean-Beobachter, genau eine gültige Quelle, eine verbundene MQTT-/WSS-
Verbindung, ein zulässiger Betriebszustand und je nach Control ein frischer
Readback vorhanden sein.

Das ist sicherheitsrelevant: Eine Control-Entity soll `unavailable` werden,
wenn ein Schreibversuch nicht sicher durchgeführt oder bestätigt werden kann.
Das darf jedoch nicht automatisch bedeuten, dass der beobachtete Wert
unlesbar ist.

## Konkretes Problem bei Minimal-/Maximalstrom

Für den maximalen Ausgangsstrom und den Solar-Mindeststrom existieren bereits
Read-only-Werte sowie separate Numbers für Schreibzugriffe. Dadurch ist die
grundsätzliche Nutzeranforderung fachlich richtig abbildbar:

- der Number-Control darf bei fehlender Schreibfähigkeit `unavailable` sein;
- der Read-only-Sensor sollte den Einstellungswert weiterhin anzeigen;
- der Read-only-Sensor darf nicht wegen einer Control-Sperre verschwinden.

Die aktuelle Implementierung erfüllt die Trennung grundsätzlich. Es gibt aber
zwei offene Präzisionsprobleme:

1. `native_value` einer Control-Entity wird aus demselben Coordinator-Datensatz
   gelesen, auch wenn die Control selbst `unavailable` ist. Home Assistant
   macht diesen Wert in der Oberfläche dann nicht zuverlässig als lesbare
   Beobachtung zugänglich.
2. `merge_snapshot_after_read()` behält vorhandene Werte, wenn ein späterer
   Provider-Snapshot ein Feld nicht enthält. Das verhindert zwar, dass ein
   einzelner unvollständiger Snapshot Werte löscht, kann aber einen alten
   Einstellungswert zeitlich unbegrenzt wie einen aktuellen Wert erscheinen
   lassen. Für Einstellungen fehlt bislang eine einheitliche, pro Feld
   sichtbare Herkunfts- und Frischeinformation.

## Bewertung einer Zusammenlegung

Eine Zusammenlegung von Read-only-Sensor und Control-Entity wird nicht
empfohlen. Die beiden Entities haben unterschiedliche Verträge:

| Aspekt | Read-only-Sensor | Control-Entity |
| --- | --- | --- |
| Zweck | letzten gültigen Gerätezustand anzeigen | neuen Wert schreiben |
| Verfügbarkeit | Datenquelle/Coordinator | zusätzlich Schreibpfad und Sicherheitsgates |
| Fehlersemantik | fehlendes Feld kann `unknown` sein | fehlende Bestätigung muss fehlschlagen |
| Risiko bei falschem Wert | irreführende Anzeige | unbeabsichtigter Geräteschreibvorgang |
| HA-Nutzererwartung | Wert lesen, auch bei Control-Sperre | Eingabe nur bei sicherem Schreibpfad |

Eine gemeinsame Entity würde diese Verfügbarkeitsregeln vermischen. Entweder
würde der Wert unnötig verschwinden, oder ein scheinbar verfügbares Control
würde einen Schreibversuch nahelegen, obwohl Transport, Modus oder Readback
nicht ausreichen.

## Empfohlene Lösung

### 1. Beobachtung und Schreiben getrennt lassen

Die bestehenden Entity-Paare bleiben getrennt. `ENTITY-03` sollte nicht als
pauschale Duplikatreduktion umgesetzt werden.

### 2. Read-only-Einstellungen als kanonische Anzeige definieren

Für jede Einstellung wird genau ein normal sichtbarer Read-only-Sensor als
kanonische Anzeige festgelegt. Rohsensoren bleiben Diagnose-Entities. Die
Control-Entity verwendet denselben fachlichen Wert, ist aber weiterhin
separat und standardmäßig deaktiviert.

### 3. Frische und Herkunft pro Einstellung ergänzen

Als nächster kleiner Code-Schritt sollte der Coordinator pro Einstellung
festhalten:

- Wert;
- Quelle (`direct`, `provider` oder gegebenenfalls `powerocean`);
- Zeitpunkt der letzten Beobachtung;
- ob der Wert nach einem aktuellen Snapshot bestätigt wurde.

Die Read-only-Entity kann dann einen bekannten Wert weiter anzeigen, aber mit
klarer Frische-/Quelleninformation. Ein Wert darf nicht stillschweigend als
aktuell gelten, nur weil er aus einem älteren Merge stammt.

### 4. Controls nur beim Schreiben sperren

Die bestehenden Control-Gates bleiben erhalten. Insbesondere darf eine
fehlende MQTT-Verbindung, ein laufender Ladevorgang oder fehlender Readback
nicht durch eine vermeintlich großzügigere Availability-Regel umgangen werden.
Die Backend-Schreibmethoden bleiben die letzte Sicherheitsbarriere.

### 5. Tests ergänzen

Vor einer Änderung sollten Tests die folgenden Fälle unterscheiden:

- Read-only-Wert vorhanden, Control-Schreibpfad verfügbar;
- Read-only-Wert vorhanden, Control wegen Transport oder Sicherheitsgate
  `unavailable`;
- Read-only-Feld im aktuellen Snapshot fehlend: `unknown` oder klar als letzter
  bekannter Wert gekennzeichnet;
- Coordinator oder Gerät tatsächlich nicht verfügbar: Entity `unavailable`;
- stale Provider-Wert darf keinen frischeren Direct-Wert überschreiben;
- ein Control-Service darf trotz sichtbarem Read-only-Wert nicht schreiben,
  wenn die Control-Gates nicht erfüllt sind.

## Ergebnis für ENTITY-03

Die ursprüngliche Annahme „Read-only- und Control-Entities sind unnötige
Duplikate“ ist zu grob. Die unterschiedlichen Verfügbarkeitsregeln machen die
Trennung sinnvoll und für die Nutzeranforderung notwendig.

Der sinnvolle Nachfolger von `ENTITY-03` ist daher keine unmittelbare
Entity-Entfernung, sondern eine kleine Readback-/Freshness-Erweiterung. Erst
wenn Herkunft, Alter und Semantik eindeutig sichtbar sind, kann geprüft
werden, ob einzelne rein technische Duplikate ohne Informationsverlust
entfallen können.
