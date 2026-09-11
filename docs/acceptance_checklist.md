# Abnahmeliste

Diese Liste bündelt alle offenen Abnahmeschritte an einer Stelle, damit nicht
für jedes Item einzeln getestet werden muss. Sie ist eine Arbeitsanleitung.
Maßgeblich für den Stand bleiben der [Backlog](backlog.md) und die
[Validierung](validation.md); Ergebnisse werden dorthin zurückgeschrieben.

**Prüfstand:** `1.0.5-beta.7`, Commit `9ae7051`,
[Release](https://github.com/Xygen/EcoFlow-PowerPulse-2-for-Home-Assistant/releases/tag/v1.0.5-beta.7).
Enthält Issue #14, #15, #16 und #19 zugleich, dazu die Korrekturen aus PR #36 an
der Zertifikatserneuerung. Am 2026-09-11 auf der Instanz installiert und nach
Neustart mit laufenden Streams bestätigt.

**Reihenfolge:** Der [Backlog](backlog.md) gibt vor, die Abnahme von Issue #16
zuerst abzuschließen und dafür kein weiteres Issue zu beginnen. Damit sind A4
und D1 die nächsten Schritte; A5 und A6 gehören zu Issue #15 und #19 und warten.

## Was als Nachweis zählt

Ein Schritt ist bestanden, wenn das beschriebene Ergebnis **beobachtet** wurde,
nicht wenn es plausibel erscheint. Grüne Tests und ein gemergter PR sind kein
Nachweis für Geräteverhalten.

Ein Schritt, dessen Bedingung sich nicht herstellen ließ, wird als *nicht
geprüft* vermerkt, nicht als bestanden. Eine fehlende Bedingung ist ein
offener Punkt, kein durch Unit-Tests ersetzbarer Nachweis.

Bei Bedarf vor jedem Block einen Diagnose-Export ziehen. Die Stream-Timeline
überlebt Reload und Neustart nicht — vor einem Neustart exportieren.

## A — Ohne Fahrzeug, jetzt durchführbar

Kein Ladevorgang, kein Passwortwechsel nötig. A1 bis A3 sind am 2026-09-11
bestanden und stehen unten in Block E; sie werden nicht wiederholt.

### A4 · Ausfallmeldung bei der Einrichtung

Einen **zweiten, testweisen** Integrationseintrag anlegen, während der Host
EcoFlow nicht erreicht — etwa mit kurz getrenntem Internet-Uplink. Danach den
Testeintrag wieder löschen.

*Bestanden:* Das Formular meldet ein Verbindungsproblem und fragt **nicht**,
ob das Passwort stimmt. Zusammen mit dem bereits bestätigten Gegenfall
(falsches Passwort meldet abgelehnte Zugangsdaten) ist damit die Aussage
„keine Falschmeldungen" belegt — erst beide Richtungen zusammen tragen sie.

### A5 · Einstellungspfad für Issue #15

Diese Schritte laufen über Anzeige-Einstellungen und brauchen kein Fahrzeug.
Der entsprechende Test für Issue #14 wurde auf `1.0.5-beta.1` so durchgeführt.

1. `Screen brightness` von 100 auf 75 setzen, dann zurück auf 100.
2. Währenddessen `LED indicator brightness` und beide Anzeige-Schalter
   unverändert lassen und danach prüfen.
3. Denselben Wert ein zweites Mal setzen, der bereits anliegt.

*Bestanden:* Jede Änderung wird erst als Erfolg gemeldet, nachdem ein
Readback sie bestätigt hat. Begleitwerte bleiben erhalten. Der
Wiederholungsschreibvorgang meldet keinen Scheinerfolg auf Basis eines
unvollständigen Provider-Berichts.

> Diese Schrittfolge ist aus den Abnahmekriterien von Issue #15 abgeleitet und
> nicht wörtlich in der Validierung vorgegeben. Sie deckt den Einstellungspfad
> ab, nicht den Ladepfad — der bleibt Block B.

### A6 · Stream-Timeline sichten

Diagnose-Export ziehen und die Timeline unter
`data.passive_settings_refresh.stream_timeline` ansehen.

*Bestanden:* Verbindungsübergänge, Recovery-Gründe, Berichtsalter und
Reconnect-Ergebnisse sind vorhanden und lesbar. Liefert die Evidenz, die
Issue #19 als nächsten Schritt braucht. Kein Bestehen/Fehlschlag, sondern eine
Beobachtung.

## B — Eine Fahrzeug-Session

Alles hier braucht ein verbundenes, ladendes Fahrzeug. Zusammen in **einem**
Durchlauf, sonst kostet jedes Item eine eigene Session.

### B1 · Abgelehnter Befehl nach Ladebeginn — Issue #14

Eine sensible Einstellung ändern, während sich der Ladezustand unmittelbar
davor ändert. Praktisch: Befehl absetzen, während das Fahrzeug gerade
anläuft.

*Bestanden:* Der wartende Befehl wird vor dem Senden abgelehnt, nicht
ausgeführt. Das ist der einzige Nachweis, der bei Issue #14 noch fehlt — die
lokalen Nebenläufigkeitstests ersetzen ihn ausdrücklich nicht.

### B2 · Feldgenaue Bestätigung unter Last — Issue #15

Während des Ladens eine Einstellung schreiben, deren Zielfeld im nächsten
Bericht **nicht** enthalten ist.

*Bestanden:* Ein Bericht ohne das Zielfeld bestätigt den alten Wert nicht. Ein
Provider, der bereits am Ziel steht, verhindert bei widersprechendem
Direct-Readback keinen notwendigen Schreibvorgang und meldet keinen
Scheinerfolg.

### B3 · Qualifizierte PowerOcean-Leistung — Issue #13

Rohe und qualifizierte Leistung während des Ladens beobachten, danach mit
**verbundenem Kabel, aber Direct im Idle**. Keine Ladereinstellung schreiben.

*Bestanden:* Während des Ladens folgt die qualifizierte Entität der schnellen
PowerOcean-Leistung. In einem frischen Direct-Idle-Fenster steht sie auf
`0 W`, auch wenn die rohe PowerOcean-Entität ungleich null meldet.

## C — Wartet auf eine echte Bedingung

Nicht erzwingbar. Falls die Bedingung eintritt, festhalten.

| Punkt | Bedingung | Erwartung |
| --- | --- | --- |
| `V2-AUTH-01` Erneuerung | EcoFlow lehnt den Token tatsächlich ab | Log meldet eine erneuerte Sitzung, Daten kommen im nächsten Zyklus zurück, **kein** Dialog |
| `V2-AUTH-01` Zertifikats-Refresh | Broker lehnt ein Zertifikat ab, oder es erreicht das Ersatzalter | Log meldet den Refresh, der Stream läuft weiter oder kommt zurück, ohne Reload und ohne Dialog |
| `ISSUE-12` | Verzögerter Start nahe der 30-Sekunden-Grenze | Erst dieser Fall rechtfertigt eine Änderung der Wartepolitik; bis dahin bleiben die Deadlines |
| `PHASE-01` | Reproduzierbarer stale-Direct-Zustand | Bis dahin bleibt die fail-closed Einschränkung als bekannt akzeptiert |

## D — Braucht ausdrücklich einen Eingriff

### D1 · Auslöser des Reparaturdialogs — Issue #16

Das EcoFlow-Kontopasswort ändern, sodass das gespeicherte abgelehnt wird.

*Bestanden:* Home Assistant bietet den Reparaturdialog an, statt weiter zu
wiederholen. Nach A1 und A2 ist das der **einzige** ungeprüfte Teil des
Reparaturpfads.

> Die Passwortänderung macht die EcoFlow-App und jede andere Integration mit
> diesen Zugangsdaten bis zur Neuanmeldung ungültig. Das Passwort setzt der
> Betreiber selbst.

## E — Bereits bestätigt, nicht erneut prüfen

| Punkt | Nachweis |
| --- | --- |
| `V2-AUTH-01` Anmeldung | Falsches Passwort meldet abgelehnte Zugangsdaten, `1.0.5-beta.3`, 2026-09-10 |
| `V2-AUTH-01` Kontoschutz (A1) | Abbruch vor jedem Anmeldeversuch; `modified_at` blieb gleich `created_at`, also kein Schreibvorgang. Beide Sprachen gesehen. `1.0.5-beta.6`, 2026-09-11 |
| `V2-AUTH-01` Eintragsaktualisierung (A2) | Smart-Entwürfe, Sprachassistent-Freigabe, Zählerstände und Betriebsmodus unverändert; Historie über den Reload unter derselben ID. `1.0.5-beta.6`, 2026-09-11 |
| `V2-AUTH-01` Broker-Adresse (A3) | Beide Clients auf `mqtt-e.ecoflow.com:8084`, Streams `on`, kein Fehler im Systemlog. `1.0.5-beta.6`, 2026-09-11 |
| `V2-SAFE-01` Anzeigepfad | Helligkeit 100 → 75 → 100 %, zweimal per Direct-Readback, `1.0.5-beta.1`, 2026-09-09 |
| Start/Stop | Stop-Persistenz und ein Start bei geschlossener App nach 22,8 s |
| Phasensteuerung | `auto → one_phase → auto` mit Readback, stale-Direct-Fallback als Einschränkung akzeptiert |

Der vollständige Bestand steht in der [Validierung](validation.md#confirmed-behavior).

## Ergebnisse festhalten

Nach jedem Block: Ergebnisse in die [Validierung](validation.md) eintragen,
mit Datum und Build. Erledigte Items im [Backlog](backlog.md) entfernen und
den gelieferten Stand im [Changelog](../CHANGELOG.md) vermerken.

Ein Item bleibt offen, bis seine Evidenz existiert — unabhängig davon, ob sein
Branch gemergt ist. Diese Trennung ist in den
[Merge- und Release-Gates](backlog.md#merge-and-release-gates) festgehalten.
