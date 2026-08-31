# DIAG-01: Voranalyse der Diagnostik- und Capture-Architektur

Stand: 2026-08-31  
Bezug: [Backlog `DIAG-01`](backlog.md)

Geprüfter PowerPulse-Stand: `b116518d674916e8bdf83ed22d467ee069658e77`  
Vergleichsbasis `shuette42/ecoflow-energy-ha`: `79b24d1ac733559514473ff0e6c24efb0be3c900`

## Ergebnis in Kurzform

DIAG-01 sollte **nicht** als Port der Diagnostik aus
`shuette42/ecoflow-energy-ha` umgesetzt werden. PowerPulse 2 besitzt bereits
eine für dieses Projekt angepasste, deutlich sicherere Basis:

- begrenzte Recent-, Command-, GET- und Correlation-Views;
- eigene Buckets je Kanal/Command-Kombination;
- getrennte SET-/SET-reply-Erfassung;
- explizite `truncated`- und `payload_omitted`-Marker;
- Privacy-sichere Observer-Zusammenfassungen statt Raw-Payloads;
- eng allowlistete Command-Strukturanalyse;
- runtime-only HMAC-Fingerprints für opaque Bytes;
- Command-Korrelation über Source, Sequenz und Reply;
- maskierte Topic-Muster;
- getrennte Stream-/Readback-Diagnostik.

Die wesentlichen verbleibenden Lücken sind andere:

1. Die Samples je Bucket sind ein **Tail**, keine repräsentative Langzeitstichprobe.
2. Das Bucket-Limit ist LRU-artig; verdrängte Buckets und Frames verschwinden
   ohne `received/kept/dropped`-Nachweis.
3. Commands besitzen zwar eigene Listen, aber keinen garantierten
   **Bucket-Typ-Reservebereich** gegen viele unterschiedliche Telemetrie-Typen
   oder periodische App-Writes.
4. Ein leerer Capture erklärt noch nicht eindeutig, ob nichts gesendet wurde,
   ob die relevanten Topics wirklich beobachtet wurden oder ob der Buffer
   bereits Daten verwerfen musste.
5. Ein expliziter, aus der **tatsächlichen Subscription** abgeleiteter
   `app_writes_watched`-Status fehlt.
6. Connection-Status und tatsächliche Datenfrische sind vorhanden, aber über
   mehrere Diagnostikabschnitte verteilt und nicht als einheitliche
   Capture-Health-Sicht zusammengeführt.
7. Für nicht gemappte Protobuf-Felder gibt es noch keine begrenzte
   Feldinventur.
8. Es gibt noch keinen letzten, rekursiven Privacy-Guard über den komplett
   zusammengesetzten Diagnostics-Export.

Die Empfehlung lautet daher: **bestehende PowerPulse-Diagnostik erweitern,
nicht ersetzen**. Die Umsetzung kann ohne Fahrzeug erfolgen und darf weder
zusätzliches Hintergrund-Polling noch eine Runtime-Abhängigkeit von
`ecoflow-energy-ha` einführen.

## Home-Assistant-Anforderungen

Die aktuellen offiziellen Home-Assistant-Dokumente behandeln Diagnostik als
wichtige Troubleshooting-Funktion, verlangen aber ausdrücklich, dass keine
Passwörter, Tokens, Standortdaten oder persönlichen Informationen im Export
landen. Home Assistant stellt dafür unter anderem `async_redact_data` bereit.

Referenzen:

- <https://developers.home-assistant.io/docs/core/integration/diagnostics/>
- <https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/diagnostics/>

Für PowerPulse ist das besonders relevant, weil Protobuf-Frames und
PowerOcean-Relay-Payloads neben Messwerten auch Device-, Accessory-, Account-
oder Vehicle-Identifikatoren enthalten können.

## Aktueller PowerPulse-Stand

### Diagnostics-Export

`diagnostics.py` exportiert aktuell:

- redigierte Config-Entry-Daten;
- Geräte- und PowerOcean-Observer-Übersichten;
- MQTT-Connection- und Subscription-Informationen;
- `passive_settings_refresh`;
- getrennte Phase-Readback-Quellen;
- Recent Frames;
- Command Frames;
- GET Frames;
- Command Correlations;
- Frame Buckets.

Der Config-Entry wird über Home Assistants `async_redact_data` für E-Mail und
Passwort redigiert. Für die danach zusammengesetzten Runtime-Abschnitte gibt es
aber keinen abschließenden rekursiven Export-Guard.

### Frame-Capture

`DiagnosticFrameCapture` besitzt derzeit folgende Default-Limits:

| Bereich | Limit |
| --- | ---: |
| Recent frames | 40 |
| SET/SET-reply frames | 24 |
| GET frames | 24 |
| Buckets | 48 |
| Samples je Bucket | 16 |
| Command correlations | 48 |

Die Capture-Struktur ist vollständig im Speicher und begrenzt. Es werden keine
zusätzlichen Recorder-Entities erzeugt.

### Bereits vorhandene Privacy-Sicherungen

Die aktuelle Implementierung ist insbesondere auf dem PowerOcean-Observer
bereits konservativ:

- Observer-Raw-Payloads werden **nicht** exportiert;
- `observed_get`-Payloads werden ebenfalls nicht als Raw-Hex exportiert;
- bekannte Wallbox-/Observer-Seriennummern sowie die User-ID werden vor der
  Hex-Ausgabe längenerhaltend mit `X` überschrieben;
- Observer-SETs werden nur für explizit freigegebene Command-Paare strukturell
  untersucht;
- kleine numerische Werte können erhalten bleiben;
- opaque Bytefelder werden nur nach Länge beziehungsweise über einen
  runtime-only HMAC-Fingerprint repräsentiert;
- der Fingerprint-Key wird bei jedem Integration-Runtime neu erzeugt und nie
  exportiert.

Diese Schutzmaßnahmen sollen durch DIAG-01 **nicht gelockert** werden.
Insbesondere ist das vollständige Weglassen von Observer-Raw-Payloads eine
bewusste Sicherheitsgrenze und kein Defizit, das durch den Upstream-Capture
ersetzt werden sollte.

## Vergleich mit `shuette42/ecoflow-energy-ha`

Die Upstream-Integration besitzt eine deutlich reifere Langzeit-Capture-
Architektur. Die wichtigsten Muster wurden gegen den aktuellen Stand geprüft.

| Upstream-Muster | Für PowerPulse? | Bewertung |
| --- | --- | --- |
| Typed/per-message long-term sampling | **Ja, adaptiert** | löst das aktuelle Tail-Problem |
| reservierte SET-/SET-reply-Typ-Slots | **Ja, adaptiert** | seltene Writes müssen bei Typ-Sättigung überleben |
| `seen/kept/dropped` und per-key counts | **Ja** | Capture-Vollständigkeit muss beweisbar sein |
| benannte gedroppte Message-Typen | **Ja, begrenzt** | sonst ist unklar, ob genau der gesuchte Typ fehlte |
| explizite Truncation | **bereits vorhanden** | PowerPulse hat `truncated` schon heute |
| `app_writes_watched` | **Ja** | aus realem Subscription-Erfolg ableiten |
| Connection vs. Data Freshness | **Ja** | bestehende Timestamps bündeln, keine neuen Polls |
| Unknown-Protobuf-Fields | **Ja, aber anders** | PowerPulse hat keine durchgehend typisierte Proto-Schema-Grenze |
| finaler Export-Redaction-Pass | **Ja** | Defense in depth |
| längenerhaltende Sanitization unbekannter Identifier | **teilweise ja** | zusätzlich zu den bekannten Secrets, aber konservativ testen |
| Thread-Lock um Capture | **Nein, derzeit nicht nötig** | PowerPulse bridged Paho-Callbacks auf den HA-Event-Loop |
| 24-h Deep-Capture/Opt-in | **nicht für ersten Change nötig** | zunächst vorhandenes Memory-Budget besser nutzen |
| dynamischer Bundle-Byte-Budget | **später/evidenzbasiert** | kein aktueller PowerPulse-Nachweis, dass 2048 B die Forschung blockieren |
| Upstream-First-command-Bucket-Key | **nicht blind übernehmen** | Bundle-Komposition muss für PowerPulse separat geprüft werden |

## Lücke 1: Tail-Sampling verliert Langzeitverlauf

Ein Bucket behält aktuell maximal die letzten 16 Samples dieses Typs. Bei einem
Report, der jede Sekunde oder alle paar Sekunden eintrifft, beschreibt ein
mehrstündiger Capture damit nur die letzten Sekunden beziehungsweise Minuten.

Das ist gerade für Reverse Engineering problematisch:

```text
Capture läuft mehrere Stunden
        |
seltenes Setting/Status-Ereignis in der Mitte
        |
frequenter gleicher Message-Typ läuft weiter
        |
letzte 16 Samples verdrängen das Ereignis
```

Die vorhandene Trennung je Message-Typ verhindert bereits, dass **ein anderer**
frequenter Typ den Bucket leert. Sie verhindert aber nicht, dass ein seltenes
Ereignis **innerhalb desselben Typs** verschwindet.

### Empfohlene Lösung

Pro Bucket eine zeitlich ausgedünnte Stichprobe über die gesamte
Runtime/Capture-Spanne behalten:

- erstes Sample erhalten;
- jüngstes Sample immer erhalten;
- dazwischen Samples in zeitlichen Slots verteilen;
- wenn das Budget voll wird, Slotbreite erhöhen und bestehende Historie
  gleichmäßig neu ausdünnen;
- optional wenige zusätzliche „novel change“-Samples für stabile Settings-
  Änderungen reservieren.

Damit wird das vorhandene per-Bucket-Limit besser genutzt, ohne die Anzahl der
gespeicherten Frames erhöhen zu müssen.

## Lücke 2: LRU-Bucket-Verdrängung ist diagnostisch unsichtbar

Die aktuellen Buckets werden beim Zugriff nach hinten verschoben. Ist das
48-Bucket-Limit erreicht, wird der älteste Bucket vollständig entfernt.

Dadurch kann ein seltener, aber wichtiger Message-Typ verschwinden, während
häufige aktive Typen ihre Position ständig erneuern. Zudem verliert der Export
mit dem Bucket auch dessen bisherigen `count`.

Ein späterer Diagnostics-Download kann dann nicht unterscheiden:

```text
Message-Typ wurde nie gesehen
```

von:

```text
Message-Typ wurde gesehen, aber wegen Bucket-Limit verworfen
```

### Empfohlene Lösung

Der Capture muss zusätzlich begrenzt zählen:

- `frames_seen`;
- `frames_kept`;
- `message_types_tracked`;
- `message_types_max`;
- `frames_dropped_type_budget`;
- `dropped_per_type` mit eigenem festen Limit;
- `dropped_types_untracked`, falls auch die Liste der verworfenen Typen voll
  ist;
- `per_type.seen` und `per_type.kept`.

Der Counter selbst ist sehr günstig und benötigt keine Raw-Frames.

## Lücke 3: SET/SET-reply brauchen eine Typ-Reserve

PowerPulse besitzt bereits eine eigene `commands`-Liste. Das schützt
beobachtete Writes vor dem allgemeinen Recent-Tail.

Das löst aber nicht vollständig das **Bucket-Typ-Limit**. Bei vielen
unterschiedlichen Message-Typen kann ein Write-Bucket verdrängt werden. Zudem
können periodische App-Writes selbst die reservierte Kapazität dominieren.

### Empfohlene Lösung

Eine kleine feste Typ-Reserve für:

```text
observed_set
set_reply
```

vorsehen. Telemetrie darf diese Slots nicht belegen und Writes dürfen nicht die
Telemetrie-Grundkapazität verbrauchen.

Die Reserve darf das heutige Worst-Case-Memory-Budget nicht einfach vergrößern.
Entweder wird die bisherige Bucket-Kapazität partitioniert oder die
per-Bucket-Sample-Tiefe entsprechend reduziert.

Zusätzlich kann ein nachweislich periodischer Write-Typ bei extremer Häufigkeit
zugunsten eines neuen seltenen Write-Typs weichen. Diese Optimierung sollte
aber nur mit klarer Schwelle und Tests übernommen werden; ein normaler
Benutzer-Write darf niemals als „periodisch“ klassifiziert werden.

## Lücke 4: Capture-Vollständigkeit und leere Captures

Ein leerer oder kurzer Frame-Bereich ist heute mehrdeutig. Er kann bedeuten:

- Gerät/Observer war still;
- MQTT war nicht verbunden;
- relevante Subscription wurde abgelehnt;
- die App hat keine Writes gesendet;
- der Capture hat einen Typ verworfen;
- Observer-Payload wurde absichtlich ausgelassen.

Ein Diagnostics-Export soll diese Fälle auseinanderhalten.

### Empfohlene Capture-Metadaten

Ein eigener `mqtt_capture`-Abschnitt sollte immer vorhanden sein, auch wenn
kein Frame gespeichert ist:

```text
schema
limits
sampling/stats
sources
app_writes_watched
payload_policy
```

`payload_policy` soll ausdrücklich dokumentieren, dass PowerOcean-Observer und
GET Requests absichtlich keine Raw-Payload-Ausgabe besitzen.

## Lücke 5: `app_writes_watched`

Die MQTT-Clients abonnieren heute bereits die relevanten SET-/SET-reply-Pfade.
Ein neuer Subscribe oder Poll ist deshalb nicht erforderlich.

Der Status soll aus dem **realen Ergebnis der laufenden Subscriptions**
abgeleitet werden, nicht aus einer Konfigurationsabsicht.

Konzeptionell pro Source:

```text
app_writes_watched =
    MQTT connected
    AND erforderliche SET-Subscription(s) erfolgreich
    AND erforderliche SET-reply-Subscription(s) erfolgreich
```

Der Export sollte bei mehreren Quellen unterscheiden, ob:

- PowerPulse selbst Writes beobachtet;
- der PowerOcean-Observer Writes beobachtet;
- nur ein Teilpfad verfügbar ist.

Damit bedeutet „keine Write-Frames im Capture“ nicht mehr automatisch „die App
hat nichts geschrieben“.

## Lücke 6: Connection und Datenfrische zusammenführen

PowerPulse kennt bereits:

- MQTT connected;
- Reconnect attempts;
- Subscription results;
- letzte `241/44`-Zeit;
- letzte Heartbeat-Zeit;
- Settings-/Provider-Readback-Diagnostik;
- source-aware Setting Observations.

DIAG-01 soll diese Informationen **nicht erneut messen**. Stattdessen wird beim
Diagnostics-Download aus vorhandenen monotonic/UTC-Timestamps eine kompakte
Source-Health-Sicht erzeugt.

Wichtig ist die Trennung:

```text
transport_connected = true
```

beweist nicht:

```text
direct_settings_fresh = true
heartbeat_fresh = true
```

Gerade die Untersuchungen zu STREAM-02 und PHASE-01 zeigen, dass eine weiterhin
verbundene WSS-Session zeitweise keine frischen Direct-Reports liefern kann.

Die Diagnostik sollte deshalb Connection und Data Freshness nebeneinander
zeigen, ohne zusätzliche Health-Check-Entities oder Polls einzuführen.

## Lücke 7: „Unknown fields“ für PowerPulse anders modellieren

`ecoflow-energy-ha` kann bei typisierten Protobuf-Messages
`UnknownFieldSet` verwenden: Felder, die nicht in der generierten Schema-Klasse
stehen, sind technisch eindeutig „unknown“.

PowerPulse verwendet dagegen für viele Forschungs-/Direct-Pfade bewusst den
manuellen Wire-Parser `iter_protobuf_fields`. Es existiert dort keine
vollständige Schema-Klasse, gegen die ein Feld automatisch als „unknown“
klassifiziert werden könnte.

Eine 1:1-Übernahme wäre deshalb semantisch falsch.

### Empfohlene PowerPulse-Variante: bounded unmapped-field inventory

Für ausgewählte, bekannte Command-Familien soll intern eine explizite Liste der
bereits gemappten Feldnummern geführt werden. Die Diagnostik kann dann
zusammenfassen, welche **nicht gemappten** Felder tatsächlich gesehen wurden.

Privacy-Regeln:

- Feldnummer und Wire-Type dürfen gezeigt werden;
- Varints beziehungsweise feste Scalars nur konservativ und für als sicher
  eingestufte Command-Familien;
- length-delimited Felder grundsätzlich nur als Byte-Länge;
- keine Raw-Bytes;
- kein rekursives Durchlaufen unbekannter Nested Messages in der ersten
  Umsetzung;
- Commands und Feldnummern jeweils hart begrenzen;
- bei Überschreitung explizit `truncated`/`untracked` melden.

Der Begriff `unmapped_fields` ist für PowerPulse zunächst ehrlicher als
`unknown_proto_fields`.

## Lücke 8: finaler Privacy-Guard

Heute wird Privacy an mehreren Erzeugungsstellen korrekt berücksichtigt.
Dennoch kann ein später neu hinzugefügter Diagnostics-Abschnitt versehentlich
einen Identifier exportieren, wenn sein Autor die lokale Redaction vergisst.

Der Upstream-Ansatz eines **einzigen letzten Redaction-Passes über den komplett
zusammengesetzten Export** ist deshalb sinnvoll als Defense in depth.

### Anforderungen an den PowerPulse-Guard

1. Config-Credentials bleiben weiterhin explizit über `async_redact_data`
   geschützt.
2. Der finale Pass muss rekursiv Dict-Werte, Listen und **Dict-Keys** prüfen.
3. Bekannte vollständige Seriennummern/User-ID müssen ersetzt werden.
4. Zusätzlich können seriennummerähnliche, bisher unbekannte Identifier
   konservativ längenerhaltend maskiert werden.
5. Bereits vor-sanitized `redacted_hex` darf nicht erneut mit einem Regex über
   Hex-Zeichen behandelt werden; ein zweiter ungezielter Pass kann die
   Forschungsdaten beschädigen.
6. Runtime-HMAC-Fingerprints sind bereits nicht rückrechenbare,
   runtime-lokale Vergleichswerte und müssen nicht umgeschrieben werden.
7. Unterschiedliche Identifier in Dict-Keys müssen unterschiedliche stabile
   Aliase innerhalb **eines Exports** erhalten, damit durch Redaction keine
   Keys kollidieren und Daten verloren gehen.
8. Der finale Guard darf keine rohe Observer-Payload-Ausgabe legitimieren.

Der bestehende Upstream-Code ist MIT-lizenziert; das PowerPulse-Repository
führt `shuette42` bereits im MIT-Copyright-Hinweis. Trotzdem sollte die
PowerPulse-Implementierung nur die benötigten Konzepte beziehungsweise kleine
geeignete Hilfsfunktionen übernehmen und die vorhandene Projektarchitektur
beibehalten.

## Truncation und Payload-Omission nicht vermischen

`truncated` ist in PowerPulse bereits explizit vorhanden und ist daher **kein
neues DIAG-01-Feature**.

Es gibt aber zwei unterschiedliche Situationen:

```text
truncated = true
-> Raw-Payload durfte grundsätzlich gespeichert werden, wurde aber am
   Byte-Budget abgeschnitten

payload_omitted = true
-> Raw-Payload wird aus Privacy-/Policy-Gründen absichtlich überhaupt nicht
   exportiert
```

Diese Unterscheidung soll im neuen `mqtt_capture.payload_policy` erklärt und in
Tests festgehalten werden.

Ein dynamischer Bundle-Budget-Mechanismus wie im Upstream ist für den ersten
DIAG-01-Change nicht erforderlich. Er sollte erst übernommen werden, wenn reale
PowerPulse-Captures zeigen, dass relevante Multi-Command-Frames durch das
bestehende 2048-Byte-Limit systematisch unbrauchbar werden.

## Bucket-Key-Strategie nicht blind ändern

Der aktuelle PowerPulse-Bucket-Key enthält Kanal und alle im Frame gefundenen
Command-Paare. Das kann denselben Grundtyp auf mehrere Buckets verteilen, wenn
sich die Bundle-Zusammensetzung ändert.

Der Upstream verwendet für Protobuf dagegen den ersten Command als
Typ-Identität und hält die restlichen Commands nur als Metadaten.

Für PowerPulse ist noch nicht bewiesen, dass „first command“ dieselbe stabile
Semantik besitzt. Deshalb soll DIAG-01 den Bucket-Key **nicht gleichzeitig und
ungeprüft** ändern.

Erste Implementierung:

- bestehende Key-Semantik beibehalten;
- Seen/Kept/Dropped-Statistik ergänzen;
- über Tests beziehungsweise vorhandene Capture-Fixtures prüfen, ob variable
  Bundles unnötige Fragmentierung verursachen;
- erst danach eine eigene stabile Message-Type-Key-Regel einführen.

## Ressourcen- und Performance-Budget

DIAG-01 darf keine zusätzliche Netzwerkaktivität erzeugen.

Insbesondere:

- keine neuen regelmäßigen HTTP-Polls;
- keine neuen hochfrequenten MQTT-Requests;
- keine Recorder-Entities für Capture-Zähler;
- bestehende MQTT-Callbacks und vorhandene Timestamps verwenden;
- alle Listen, Maps und Drop-Statistiken hart begrenzen;
- keine Persistenz des Raw-Captures in HA-Storage/Recorder für die erste
  Umsetzung.

### Bestehender theoretischer Speicherrahmen

Die aktuelle Maximalbelegung der Buckets beträgt `48 * 16 = 768` Samples.
Ein nicht-Observer-Frame kann bis zu 2048 Raw-Bytes als Hex-String halten, also
4096 Zeichen. Im künstlichen Worst Case ergeben allein diese Hex-Zeichen etwa
3 MiB Inhalt, noch ohne Python-Objekt-Overhead.

Das ist **keine gemessene Runtime-RAM-Nutzung**, sondern nur eine obere
Größenordnung der gespeicherten Hex-Nutzdaten.

Die DIAG-01-Umsetzung soll diesen Worst-Case-Rahmen möglichst halten oder
reduzieren. Langzeitabdeckung soll durch bessere Auswahl der Samples entstehen,
nicht durch immer größere Buffers.

## Empfohlenes Zielmodell

Konzeptionell:

```text
MQTT frame
   |
existing privacy-safe frame inspection
   |
message-type classification
   |
Bounded Diagnostic Capture
   +-- recent tail
   +-- long-window per-type sample
   +-- reserved SET/SET-reply types
   +-- GET sample
   +-- command correlation
   +-- seen/kept/dropped stats
   +-- optional bounded novelty samples
   |
Diagnostics builder
   +-- source connection/subscription health
   +-- direct/provider freshness from existing timestamps
   +-- app_writes_watched
   +-- bounded unmapped-field inventory
   +-- capture limits/payload policy
   |
final recursive privacy guard
   |
Home Assistant diagnostics download
```

Die Capture-Daten bleiben rein diagnostisch. Sie dürfen keinen Entity-State und
keine Control-Freigabe beeinflussen.

## Vorgeschlagene Export-Struktur

Die genaue JSON-Struktur ist Implementierungsdetail. Als Zielbild genügt:

```text
mqtt_capture:
  schema
  policy:
    listen_only
    observer_payloads_omitted
    get_payloads_omitted
    max_frame_bytes
  statistics:
    frames_seen
    frames_kept
    frames_dropped_type_budget
    dropped_per_type
    dropped_types_untracked
    per_type
  sources:
    powerpulse:
      connected
      subscriptions
      app_writes_watched
      direct_settings_last_report
      heartbeat_last_report
    powerocean_observer:
      connected
      subscriptions
      app_writes_watched
  samples:
    recent
    per_type
    commands
    requests
    correlations
  unmapped_fields
```

Zeitabhängige `age_s`-Werte dürfen beim **einmaligen Diagnostics-Download**
berechnet werden. Sie erzeugen dort keinen Recorder-Churn. Es sollen dafür aber
keine laufend aktualisierten Entity-Attribute angelegt werden.

## Umsetzungsreihenfolge

### Phase A: Capture-Statistik und Langzeit-Sampling

1. `DiagnosticFrameCapture` um `seen/kept/dropped` erweitern.
2. Gedroppte Message-Typen begrenzt benennen.
3. Tail-Samples pro Bucket durch end-to-end-Sampling ersetzen.
4. SET/SET-reply-Typ-Reserve einführen.
5. Bestehende Recent-/Command-/Request-/Correlation-APIs kompatibel halten,
   soweit sinnvoll.

Kein Netzwerkcode muss dafür geändert werden.

### Phase B: Diagnostics-Truthfulness

1. `mqtt_capture`-Metadaten auch bei leerem Capture exportieren.
2. `app_writes_watched` aus realen Subscription-Ergebnissen ableiten.
3. Connection und Stream-/Readback-Freshness gebündelt darstellen.
4. `truncated` und `payload_omitted` als unterschiedliche Policies erklären.

### Phase C: Privacy Defense in Depth

1. längenerhaltende Sanitization unbekannter Identifier für exportierbare
   Direct-Raw-Payloads ergänzen;
2. finalen rekursiven Export-Guard hinzufügen;
3. pre-sanitized Hex explizit vom strukturellen Regex-Pass ausnehmen;
4. Dict-Key-Collisionen durch per-export Alias-Mapping verhindern.

### Phase D: bounded unmapped-field inventory

1. pro ausgewählter Command-Familie bekannte Feldnummern definieren;
2. nicht gemappte Feldnummern/Wire-Typen begrenzt sammeln;
3. Bytefelder nur über Länge darstellen;
4. keine Entity und kein Control aus dieser Diagnostik ableiten.

### Phase E: optionale Novelty-Samples

Erst nach den Kernphasen prüfen, ob stabile Setting-Werte, die nach mehreren
gleichen Frames wechseln, zusätzlich gezielt als „novel“ Sample erhalten
werden sollen. Das ist für App-Vergleichstests nützlich, erhöht aber die
Capture-Komplexität und soll deshalb einen nachgewiesenen Nutzen haben.

## Erforderliche Tests

### Sampling und Bounds

1. ein seltener Message-Typ überlebt eine Flut eines häufigen Typs;
2. ein sechs- beziehungsweise 24-stündiger synthetischer Stream bleibt über
   die gesamte Zeitspanne repräsentiert;
3. erstes und jüngstes Sample eines Typs bleiben erhalten;
4. jeder Bucket bleibt innerhalb seines Sample-Limits;
5. Gesamtzahl der Typen bleibt begrenzt;
6. `frames_seen`, `frames_kept` und Dropped-Counter reconciliieren;
7. verworfene Typen werden bis zum eigenen Limit benannt;
8. Überschreitung der Dropped-Type-Liste wird explizit gezählt;
9. SET/SET-reply überleben Telemetrie-Typ-Sättigung;
10. periodische App-Writes können keinen neuen seltenen User-Write dauerhaft
    aus der Reserve verdrängen.

### Bestehende Funktionen dürfen nicht regressieren

11. Command-Correlation nach Source/Sequence funktioniert unverändert;
12. GET-View bleibt getrennt;
13. Observer-Raw-Payload bleibt ausgelassen;
14. `observed_get`-Raw-Payload bleibt ausgelassen;
15. `truncated` bleibt bei abgeschnittenen Direct-Frames korrekt;
16. Runtime-HMAC-Fingerprints bleiben nur innerhalb einer Runtime vergleichbar.

### Truthfulness

17. leeres Capture enthält trotzdem Limits, Source-Status und Subscription-
    Information;
18. `app_writes_watched=false` bei fehlender/abgelehnter relevanter
    Subscription;
19. `app_writes_watched=true` nur bei tatsächlich erfolgreicher Beobachtung der
    erforderlichen Pfade;
20. MQTT connected und stale Direct-Stream werden gleichzeitig korrekt
    dargestellt;
21. keine neuen Polls werden für Diagnostics gestartet.

### Privacy

22. E-Mail und Passwort bleiben redigiert;
23. bekannte Device-/Observer-Seriennummern erscheinen nirgendwo vollständig;
24. unbekannte serial-shaped Identifier in exportierbarem Direct-Raw-Payload
    werden längenerhaltend maskiert;
25. Identifier in Dict-Keys werden redigiert, ohne zwei unterschiedliche
    Geräte auf denselben Key zu kollabieren;
26. finale Redaction verändert vor-sanitized Hex nicht;
27. Fahrzeug-/Accessory-Identifier aus Observer-Payloads bleiben vollständig
    außerhalb des Exports;
28. Test-Fixtures beweisen, dass Sanitization Länge und relevante
    Protobuf-Struktur nicht beschädigt.

### Unmapped fields

29. gemappte Felder erscheinen nicht als unmapped;
30. unbekannte Varint-/Fixed-Felder werden nur gemäß Safe-Policy gezeigt;
31. unbekannte length-delimited Felder zeigen nur die Länge;
32. Command- und Field-Limits sind hart begrenzt und melden Truncation;
33. malformed Payloads können den Diagnostics-Download nicht abbrechen.

### Standalone-Betrieb

34. Tests importieren oder benötigen `ecoflow_energy` nicht;
35. PowerPulse-Diagnostik funktioniert unverändert, wenn die andere EcoFlow-
    Integration nicht installiert oder deaktiviert ist.

## Fahrzeugbedarf

Für die Implementierung und fast alle Tests von DIAG-01 ist **kein Fahrzeug**
erforderlich.

Die Architektur kann vollständig mit Unit-Tests und den bereits beobachtbaren
Idle-/MQTT-Pfaden umgesetzt werden. Eine spätere reale Validierung mit
App-Aktionen ist sinnvoll, um zu prüfen, ob die Langzeitstichprobe tatsächlich
die gewünschten seltenen Frames erhält. Ein Ladevorgang ist dafür nicht
zwingend notwendig.

## Abschlusskriterien

DIAG-01 kann nach Implementierung geschlossen werden, wenn:

- Langzeit-Sampling und Message-Type-Budgets hart begrenzt sind;
- seltene Typen und Writes nachweislich erhalten bleiben;
- Seen/Kept/Dropped-Statistiken einen Capture ehrlich beschreiben;
- ein leerer Capture nicht mehr mehrdeutig ist;
- `app_writes_watched` den realen Subscription-Zustand beschreibt;
- Connection und Data-Freshness getrennt sichtbar sind;
- eine begrenzte `unmapped_fields`-Sicht Forschungsfragen unterstützt;
- der vollständige Export einen letzten Privacy-Guard durchläuft;
- bestehende Observer-Payload-Omission und Command-Privacy erhalten bleiben;
- das Memory-Budget nicht unkontrolliert wächst;
- keine zusätzliche Polling-/Recorder-Last entsteht;
- keine Runtime-Abhängigkeit zu `shuette42/ecoflow-energy-ha` besteht.

## Empfehlung

Der Analyse-Stand ist ausreichend konkret für eine Umsetzung in kleinen,
getrennt testbaren Changes. Der Backlog-Status kann deshalb auf
**„Analysis complete; implementation pending“** gesetzt werden.

Die erste Implementierung sollte bewusst mit **Capture-Statistik,
Langzeit-Sampling und Write-Type-Reserve** beginnen. Diese Punkte liefern den
größten diagnostischen Nutzen bei geringem Risiko und ohne Änderung der
Netzwerk- oder Control-Pfade. Privacy-Guard und unmapped-field inventory folgen
als separate, leicht reviewbare Changes.

## Implementierungsstand 2026-08-31

Die Phasen A bis D sind lokal in Diagnose-Schema 12 umgesetzt. Pro Nachrichtentyp
bleiben erstes und jüngstes Sample sowie eine deterministische Stichprobe über
das gesamte Beobachtungsfenster erhalten. Das bisherige Gesamtlimit von 48
Typ-Buckets und 16 Samples je Typ wächst nicht; acht Typ-Slots sind innerhalb
dieses Budgets für `observed_set`/`set_reply` reserviert. Seltene neue Writes
können dadurch einen häufig wiederholten Write-Typ verdrängen, während ein
erneutes periodisches Auftreten den selteneren Typ nicht sofort wieder entfernt.

Der neue, stets vorhandene `mqtt_capture`-Block enthält Policy, Grenzen,
reconciliierte Zähler, Source-Status, Samples und die begrenzte
`unmapped_fields`-Inventur. `app_writes_watched` ist nur wahr, wenn MQTT verbunden
ist und sowohl `app_set` als auch `app_set_reply` tatsächlich mit Rückgabecode
null abonniert wurden. Direct- und Heartbeat-Status weisen `connected`,
`last_report`, einmalig berechnetes `age_s`, Freshness und Schwelle getrennt aus.

Für ausgewählte, bereits manuell geparste Command-Familien werden ausschließlich
noch nicht gemappte Feldnummer, Wire-Typ, Auftretenszahl und bei Bytefeldern die
Länge gesammelt. Werte und Byteinhalte werden nicht exportiert; Command- und
Feldzahl sind hart begrenzt und fehlerhafte Protobuf-Bodies erhöhen nur einen
Fehlerzähler. Ein finaler rekursiver Guard maskiert bekannte sowie seriennummern-
ähnliche Identifikatoren längenerhaltend, behandelt auch Dictionary-Keys mit
eindeutigen Aliasen und lässt bereits bereinigtes `redacted_hex` sowie
Runtime-Fingerprints unverändert. Die Direct-Byte-Redaction maskiert zusätzlich
unbekannte ASCII-Seriennummern vor der Hex-Kodierung, ohne Payload-Längen oder
Protobuf-Längenfelder zu verändern.

Die bestehenden Legacy-Schlüssel bleiben für kompatible Auswertungen erhalten.
Es wurden weder Subscription-, Publish-, Polling-, Entity- noch Persistenzpfade
ergänzt. 144 lokale Tests, Ruff und Python-Kompilierung sind erfolgreich; offen
ist nur die Prüfung eines realen, von Home Assistant erzeugten Schema-12-Exports
nach Installation des nächsten Builds.
