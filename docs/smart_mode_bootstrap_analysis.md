# Issue #9: Smart-Modus nach Reload wieder bootstrapfähig machen

Stand: 2026-08-31
Bezug: [GitHub Issue #9](https://github.com/Xygen/EcoFlow-PowerPulse-2-for-Home-Assistant/issues/9)

## Ergebnis in Kurzform

Issue #9 ist ein reproduzierbarer Zustands- und UX-Fehler, keine allgemeine
Verbindungsstörung: Nach einem Integration-Reload ist die ausschließlich
flüchtige Smart-Konfiguration leer. Die notwendigen Smart-Controls sind dann
außerhalb des Smart-Modus nicht verfügbar, während gerade der Wechsel in den
Smart-Modus eine vollständige Konfiguration verlangt.

Die Lösung ist **nicht**, die bestehenden Geräteschreibvorgänge außerhalb des
Smart-Modus freizugeben. Stattdessen braucht die Integration eine persistierte,
seriennummerbezogene Staging-Konfiguration. Änderungen außerhalb von Smart
aktualisieren ausschließlich diese lokale Konfiguration. Erst der Wechsel in
den Smart-Modus darf daraus einen vollständigen Geräte-Payload erzeugen und
muss weiterhin SET-Reply und qualifizierten Readback verlangen.

## Bestätigter Ist-Zustand

- Der Coordinator initialisiert `_last_smart_settings` nur im Speicher.
- `async_set_work_mode(..., "smart")` baut einen vollständigen Smart-Payload
  aus diesem Cache.
- `_smart_settings_payload()` verlangt `ready_by_timestamp`, einen gültigen
  Zieltyp und den zu diesem Zieltyp passenden Zielwert. Fehlt etwas, entsteht
  der unspezifische Fehler `Stored Smart settings are unavailable`.
- Die Number-, Select- und DateTime-Controls für Smart verlangen derzeit
  `work_mode == "smart"`. Damit können sie die für den Moduswechsel nötigen
  Daten nicht vorbereiten.
- `smart_target_type_control_available()` verlangt zusätzlich positive
  Energie- **und** Distanzwerte. Das ist für einen energie- oder distanzbasierten
  Zieltyp jeweils zu streng.

Damit entsteht nach Reload in Solar, Fast oder Custom der Zirkel:

```text
kein persistierter Smart-Cache
-> Smart-Controls nicht verfügbar
-> keine Smart-Konfiguration vorbereitbar
-> Smart-Moduswechsel kann keinen vollständigen Payload bilden
-> Smart-Modus nicht aktivierbar
```

## Designgrenzen

### Staging ist keine aktuelle Gerätebeobachtung

Die aktuelle Read-only-Smart-Observation darf ausschließlich einen aktuell
qualifizierten Gerätewert zeigen. Fehlt ein solcher Report, bleibt sie
`unknown`; ein lokaler Entwurf darf diesen Zustand nicht ersetzen. Dies bewahrt
den mit ENTITY-03 festgelegten Unterschied zwischen Observation und Control.

### Außerhalb Smart niemals zum Gerät schreiben

Ein Smart-Control-Update bei Solar, Fast oder Custom darf weder den Modus
ändern noch einen Smart-SET senden. Es darf nur die lokale Staging-Konfiguration
ändern. Transport-, Ladezustands- und Readback-Gates für echte Geräteschreib-
vorgänge bleiben unverändert.

### Aktivierung bleibt fail-closed

Beim Wechsel nach Smart muss die komplette Staging-Konfiguration vor dem Senden
validiert werden. Danach gelten unverändert der korrelierte SET-Reply und ein
frischer qualifizierter Direct- oder zulässiger Provider-Readback. Ein lokaler
Entwurf ist niemals eine Write-Bestätigung.

## Empfohlenes Zielmodell

Pro Wallbox-Seriennummer wird eine versionierte, persistierte
`staged_smart_settings`-Struktur geführt. Sie enthält nur fachliche Smart-
Eingaben und keine Rohframes, Zugangsdaten oder Fahrzeugidentifikatoren:

```text
ready_by_timestamp
smart_target_type
smart_charge_target_wh
smart_target_distance_km
```

Bei einem energieorientierten Ziel sind Ready-by, `energy` und Energie nötig.
Bei einem Distanzziel sind Ready-by, `distance`, Distanz sowie die für den
Payload erforderliche, gültige Verbrauchsgrundlage nötig. Die jeweils andere
Zielgröße ist kein Pflichtfeld.

Die persistierte Staging-Struktur wird nur bei semantischen Änderungen und erst
nach einer erfolgreichen lokalen Validierung geschrieben. Bestätigte
Geräte-Reports und bestätigte Smart-Writes können sie aktualisieren, jedoch
nicht die Read-only-Observation durch einen Staging-Wert ersetzen.

### Verhalten der Controls

| Zustand | Control-Änderung | Gerätewirkung |
| --- | --- | --- |
| Solar/Fast/Custom | Staging aktualisieren | keine |
| Smart | vollständigen Payload schreiben | nur nach SET-Reply und Readback |
| Smart-Wechsel | Staging vollständig validieren, dann atomar senden | nur nach SET-Reply und Readback |

Die Controls sollen außerhalb Smart lokal bedienbar sein, solange Home Assistant
die Integration geladen hat. Für einen späteren Geräte-Write müssen sie nicht
vorab eine Direct- oder Provider-Verbindung vortäuschen. Ihre Darstellung muss
als Konfiguration/Entwurf klar von den aktuellen Smart-Observations
unterscheidbar bleiben.

## Validierungs- und Fehlermodell

Die Aktivierung soll konkrete Fehler liefern, etwa:

- `Smart mode requires a ready-by time`;
- `Smart mode requires an energy target`;
- `Smart mode requires a distance target`;
- `Smart distance target requires vehicle consumption`.

Ein Zieltyp darf ohne beide möglichen Zielwerte gewählt und gespeichert werden.
Erst der Smart-Moduswechsel prüft den für den gewählten Typ vollständigen
Bundle. Das verhindert eine unnötige Sperre der Konfiguration, ohne einen
unvollständigen Gerätebefehl zuzulassen.

## Umsetzungsvorschlag

1. Versionierten Home-Assistant-Store für `staged_smart_settings` einführen;
   beim Setup laden und pro Seriennummer validieren.
2. Staging-Zugriff von `_last_smart_settings` trennen. Letzteres bleibt
   gerätebeobachtete/temporäre Payload-Hilfe, ersetzt aber keinen Entwurf.
3. Smart-Control-Availability außerhalb Smart auf lokale Staging-Verfügbarkeit
   umstellen; die Setter außerhalb Smart ausschließlich lokal ausführen.
4. Beim Smart-Wechsel Staging mit dem notwendigen, frischen Geräte-Kontext
   zusammenführen, vollständig validieren und den vorhandenen atomaren
   Write-/Confirmation-Pfad nutzen.
5. Während aktivem Smart-Modus die Staging-Konfiguration nur zusammen mit
   erfolgreichem Geräte-Write fortschreiben; bei Fehler weder Gerät noch
   persistierten Entwurf als erfolgreich darstellen.
6. Übersetzungen und Entity-Darstellung auf eindeutige Unterscheidung zwischen
   Smart-Konfiguration und aktueller Smart-Observation prüfen.

## Tests ohne Fahrzeug

- frischer Start in Solar ohne Staging: alle Smart-Eingaben sind lokal setzbar,
  es wird kein MQTT-Publish ausgelöst;
- Energie- und Distanz-Bundle lassen sich unabhängig vorbereiten;
- Reload und Home-Assistant-Neustart stellen ein gültiges Staging wieder her;
- unvollständiges Bundle verhindert ausschließlich den Smart-Wechsel und nennt
  das fehlende Feld;
- Energie benötigt keine Distanz und umgekehrt;
- Staging-Werte werden nie als aktuelle Read-only-Smart-Observation gezeigt;
- aktiver Smart-Modus sendet weiterhin nur über den bestehenden bestätigten
  Write-Pfad;
- fehlender SET-Reply oder Readback aktualisiert weder Gerätedaten noch ein als
  bestätigt dargestelltes Staging;
- Serialisierungs-/Schemafehler im Store werden fail-closed behandelt und
  beeinträchtigen keine anderen Wallboxen.

## Live-Validierung in 0.1.1-beta.6

Am 2026-08-31 wurden in Solar Zieltyp `energy`, 30 kWh und der Folgetag um
12:00 Uhr lokal gestaged. Alle Werte blieben nach einem gezielten Reload des
Config Entry sichtbar; im PowerPulse-Kommandostrom entstand dabei kein
`241/102`. Die anschließende Smart-Aktivierung erzeugte genau einen
`241/102`-Request mit Sequenz 225, erhielt die passende SET_REPLY und wurde
durch den frischen Moduswert `smart` bestätigt. Das Fahrzeug war abgesteckt.

Ein zweiter Versuch mit Zieltyp `distance`, aber ohne Distanzwert, wurde mit
`Smart distance target must be 10 to 600 whole km` vor dem Publish abgewiesen;
es entstand kein weiterer `241/102`. Zieltyp und Betriebsmodus wurden danach
auf `energy` beziehungsweise den ursprünglichen Solar-Modus zurückgestellt.

## Implementierungsstand und kritische Abweichung

Die lokale Implementierung folgt dem Staging-Modell. Der Store ist sowohl an
den Config Entry als auch an die Wallbox-Seriennummer gebunden, wird vor dem
ersten Coordinator-Refresh geladen und speichert nur semantische Änderungen.
Fehlerhafte Geräte oder Einzelfelder im Store werden isoliert verworfen. Ein
fehlgeschlagener Store-Write setzt die lokale Änderung zurück, damit ein
Service-Aufruf Persistenz nicht fälschlich als erfolgreich meldet.

Abweichend vom ursprünglichen Issue-Vorschlag wird
`vehicle_consumption_raw` **nicht** persistiert. Dieser Wert ist keine
Benutzereingabe, kann vom angeschlossenen Fahrzeug abhängen und wäre nach einem
Fahrzeugwechsel potentiell gefährlich veraltet. Persistiert werden nur
Ready-by, Zieltyp, Zielenergie und Zielstrecke. Ein späterer App-Mitschnitt hat
die ursprüngliche Annahme zur Distanzenergie korrigiert: Die offizielle App
sendet für 100 km Feld 3 mit `0` und Feld 4 mit `100`; die Wallbox meldet danach
selbst 15000 Wh. Der Schreibpfad darf deshalb keinen Fahrzeugverbrauch
voraussetzen oder aus einem möglicherweise veralteten Profil erraten.

Die Control-Namen tragen nun den gemeinsamen Präfix
`Smart-Konfiguration`, während die bestehenden Read-only-Sensoren unverändert
Gerätebeobachtungen darstellen. Außerhalb Smart lösen Control-Änderungen keinen
MQTT-Publish aus. Im aktiven Smart-Modus wird der Entwurf erst nach einem
erfolgreich bestätigten Geräte-Write fortgeschrieben.
