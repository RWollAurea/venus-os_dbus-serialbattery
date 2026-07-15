# AGENTS.md

## Zweck

Diese Datei enthält die verbindlichen Arbeitsregeln für Entwicklungs- und Fehleranalysearbeiten am Projekt **Victron BMV-712 + ECS LiPro als BMS**.

Repository: `RWollAurea/venus-os_dbus-serialbattery`  
Standardbranch: `master`

Bei Beginn eines neuen Chats oder einer neuen Arbeitssitzung zuerst lesen:

1. `AGENTS.md`
2. `docs/PROJECT_STATE.md`
3. `docs/VENUS_DEPLOYMENT.md`
4. danach erst die konkret betroffenen Quell- und Konfigurationsdateien

## Projektziel

Ein Batteriesystem aus

- ECS LiPro1-6 Active Version 1.0 mit RS485/Modbus RTU,
- Victron BMV-712 Smart,
- Victron Venus GX / Venus OS,
- dbus-serialbattery

soll so integriert werden, dass Venus OS eine nutzbare, ESS-/DVCC-taugliche Batterie sieht.

Datenquellen:

- **ECS:** Zellspannungen, Temperaturen, OVP, LVP, Betriebs-/Fehlerstatus und Zellschutz
- **BMV-712:** Gesamtspannung, Strom und SoC

Der ECS-Zellschutz ist maßgeblich. BMV-Werte dürfen Schutzentscheidungen des ECS nicht übersteuern.

## Wichtige Abgrenzung

Der projektspezifische Treiber heißt `ecs_bmv.py` und die vorgesehene Klasse heißt `EcsBmvBattery`.

Der vorhandene Upstream-Treiber `dbus-serialbattery/bms/ecs.py` gehört zu einer anderen ECS-/GreenView-/GreenMeter-Integration und darf nicht mit `ecs_bmv.py` verwechselt werden.

Vor Änderungen immer den tatsächlichen Pfad des projektspezifischen Treibers im Repository und auf dem Venus GX feststellen. Historisch wurde auf dem Gerät folgender Pfad verwendet:

`/data/etc/dbus-serialbattery/batteries/ecs_bmv.py`

Die aktuelle Upstream-Struktur verwendet dagegen `dbus-serialbattery/bms/`. Diese Abweichung ist vor jeder Import- oder Loader-Änderung ausdrücklich zu prüfen und darf nicht stillschweigend umgebaut werden.

## Systempfade

Hauptinstallation auf dem GX:

`/opt/victronenergy/dbus-serialbattery/`

Persistente eigene Anpassungen:

`/data/etc/dbus-serialbattery/`

Serial-Starter-Konfiguration:

`/data/conf/serial-starter.d/dbus-serialbattery.conf`

Typische Logs:

`/data/log/dbus-serialbattery*/current`

## Arbeitsregeln

- Keine Architekturänderung, Neuinstallation, größere Umstrukturierung, Watchdog-Änderung oder Refaktorierung ohne ausdrücklichen Auftrag.
- Keine Dateien, Commits, Branches oder Pull Requests ohne ausdrückliche Freigabe des Nutzers ändern bzw. erstellen.
- Vor jeder Codeänderung aktuellen Branch, Commit, betroffene Dateien und den tatsächlich auf dem GX laufenden Stand prüfen.
- Repository-Datei und GX-Datei nicht automatisch als identisch annehmen.
- Änderungen minimal halten und exakt auf die festgestellte Ursache begrenzen.
- Keine neuen Features ergänzen, solange der aktuelle Fehler nicht sauber eingegrenzt ist.
- Bei mehreren Lösungswegen Varianten kurz bewerten, eine Empfehlung aussprechen und vor größeren Änderungen Freigabe abwarten.

## Quellenpriorität

Bei widersprüchlichen Angaben gilt:

1. aktuell gemessene Rohdaten des realen ECS-Systems,
2. aktuell auf dem Venus GX laufender Quellcode und aktuelle Konfiguration,
3. projektspezifische Dokumentation in diesem Repository,
4. ECS-Dokumentation der exakt eingesetzten Hardwareversion,
5. allgemeine dbus-serialbattery- und Victron-Dokumentation,
6. Annahmen oder Erfahrungswerte.

Registerangaben verschiedener ECS-Generationen dürfen nicht ungeprüft vermischt werden.

## Debug-Reihenfolge

Vor Änderungen am dbus-serialbattery-Ablauf in dieser Reihenfolge prüfen:

1. Wird der richtige serielle Port an den Prozess übergeben?
2. Ist der Port durch `EXCLUDED_DEVICES` ausgeschlossen?
3. Wird das Modul mit `ecs_bmv.py` tatsächlich importiert?
4. Ist `EcsBmvBattery` in der verwendeten Loader-/Treiberliste registriert?
5. Wird `test_connection()` erreicht?
6. Stimmen Port, Baudrate, Parität, Stopbits und Slave-ID?
7. Funktioniert der Minimaltest auf ECS-Register 7?
8. Stimmen Registermapping und Skalierung?
9. Wird der BMV-D-Bus-Service eindeutig erkannt?
10. Erst danach D-Bus-Mapping sowie ESS-/DVCC-Verhalten prüfen.

## Bekannte Protokollfakten

- ECS LiPro1-6 Active Version 1.0 verwendet Modbus RTU über RS485.
- Dokumentierte Werkseinstellung: 19200 Baud.
- Parität, Stopbits und Slave-ID müssen am realen System bestätigt werden.
- Register 7: Zellspannung in mV.
- Register 8: Temperaturrohwert; Umrechnung muss anhand realer Vergleichswerte bestätigt werden.
- Register 13: Betriebs-/Fehlerstatus.
- Register 14: LVP-Zustand.
- Register 15: OVP-Zustand.
- Register 28: Slave-Adresse.
- Register 30: EEPROM-Speicherbestätigung.
- Einzelne LiPro-Module können gegebenenfalls auf Adresse 0 reagieren.
- Frühere Adressen im Projekt waren 100, 200, 300 und 400.
- Bei Modbus Exception 02 funktioniert die Kommunikation grundsätzlich; Registeradresse oder Registeranzahl ist dann ungültig.

## BMV-D-Bus

Vor dem Zugriff zuerst vorhandene Services `com.victronenergy.battery.*` auflisten und den BMV eindeutig identifizieren.

Vorgesehene Werte:

- `/Dc/0/Voltage`
- `/Dc/0/Current`
- `/Soc`

Fehler beim Lesen des BMV dürfen den ECS-Modbus-Test nicht verdecken.

## Sicherheitsregeln

- OVP muss die Ladefreigabe bzw. den zulässigen Ladestrom beeinflussen.
- LVP muss die Entladefreigabe bzw. den zulässigen Entladestrom beeinflussen.
- Temperaturfehler müssen sicher behandelt werden.
- Bei ECS-Kommunikationsverlust darf der Treiber nicht optimistisch Laden und Entladen freigeben.
- Ein Kommunikationsfehler darf nicht durch alte, noch gültig wirkende Messwerte verdeckt werden.
- ESS-/DVCC-relevante Annahmen zu CVL, CCL, DCL, Charge-Allow und Discharge-Allow müssen ausdrücklich dokumentiert werden.
- Physische ECS-Sicherheitsschleifen bleiben unabhängig von der Software maßgeblich.

## Anforderungen an Codeänderungen

Jede vorgeschlagene oder ausgeführte Codeänderung muss enthalten:

- vollständiger Repository-Pfad,
- zugehöriger Pfad auf dem Venus GX,
- konkretes Snippet oder vollständige Datei,
- Begründung auf Basis des festgestellten Fehlers,
- Test- und Verifikationsschritte,
- relevante Logpfade,
- erwartete Logausgaben,
- mögliche Auswirkungen auf ESS, DVCC und VE.Bus,
- Rollback-Schritte.

## Standardtests auf Venus OS

```sh
dmesg | grep ttyUSB
ls -l /dev/ttyUSB*
ls -l /dev/serial/by-id/
svc -t /service/dbus-serialbattery*
tail -f /data/log/dbus-serialbattery*/current
grep -i ecs /data/log/dbus-serialbattery*/current
```

Zusätzlich je nach Stand:

- `dbus-spy`
- `dbus-monitor`
- vorhandene `com.victronenergy.battery.*` Services prüfen
- ECS-Register 7 einzeln lesen

## Repository- und Commit-Regeln

- Standardmäßig direkt auf `master` nur arbeiten, wenn der Nutzer dies ausdrücklich beauftragt.
- Vor einem Schreibvorgang die aktuelle Datei erneut lesen und deren Blob-SHA verwenden.
- Änderungen an derselben Datei nicht parallel schreiben.
- Commit-Nachrichten kurz und eindeutig halten.
- Nach einem Commit den Commit-SHA nennen.
- Keine Zugangsdaten, WLAN-Schlüssel, VRM-Tokens, private Schlüssel oder sonstige Secrets einchecken.

## Abschluss einer Arbeitssitzung

Nach einer relevanten Änderung oder neuen Diagnose `docs/PROJECT_STATE.md` aktualisieren:

- aktueller Fehlerstand,
- bestätigte Erkenntnisse,
- verworfene Annahmen,
- letzter erfolgreicher Test,
- nächster minimaler Schritt,
- Rollback-Punkt.
