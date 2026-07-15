# AGENTS.md

## Start einer neuen Arbeitssitzung

Vor jeder Analyse oder Änderung in dieser Reihenfolge lesen:

1. `dbus-serialbattery/AGENTS.md`
2. `dbus-serialbattery/docs/PROJECT_STATE.md`
3. `dbus-serialbattery/docs/VENUS_DEPLOYMENT.md`
4. `dbus-serialbattery/docs/ECS_MODBUS.md`
5. `dbus-serialbattery/docs/DBUS_MAPPING.md`
6. `dbus-serialbattery/docs/TEST_PLAN.md`
7. anschließend die konkret betroffenen Quell- und Konfigurationsdateien

Repository: `RWollAurea/venus-os_dbus-serialbattery`  
Upstream-/Standardbranch: `master`  
Aktiver Entwicklungsbranch: `ecs-bmv-integration`

Entwicklungsänderungen gehören auf `ecs-bmv-integration`. `master` bleibt möglichst nahe am Upstream `mr-manuel/venus-os_dbus-serialbattery`.

## Projektziel

Integration von:

- ECS LiPro1-6 Active Version 1.0 über RS485/Modbus RTU
- Victron BMV-712 Smart über VE.Direct/D-Bus
- Victron Venus GX mit Venus OS
- dbus-serialbattery

Venus OS soll eine ESS-/DVCC-taugliche kombinierte Batterie sehen.

Datenquellen:

- ECS: Zellspannung, Temperatur, Status, OVP, LVP und Zellschutz
- BMV-712: Gesamtspannung, Strom und SoC

ECS bleibt für den Zellschutz maßgeblich. BMV-Werte dürfen ECS-Schutzentscheidungen niemals übersteuern.

## Aktuelle projektspezifische Dateien

- Treiber: `dbus-serialbattery/bms/ecs_bmv.py`
- Klasse: `EcsBmv`
- Loader: `dbus-serialbattery/dbus-serialbattery.py`
- Roh-Modbus-Test: `dbus-serialbattery/tools/test_ecs_modbus_raw.py`
- Projektkonfiguration: `dbus-serialbattery/projekt-config/config.ini`
- Serial-Starter-Beispiel: `dbus-serialbattery/projekt-config/serial-starter.d/dbus-serialbattery.conf`

Historische Bezeichnungen wie `EcsBmvBattery` und der Pfad `/data/etc/dbus-serialbattery/batteries/ecs_bmv.py` sind nicht mehr der aktuelle Repository-Stand.

Der vorhandene Upstream-Treiber `dbus-serialbattery/bms/ecs.py` ist eine andere ECS-/GreenView-Integration und darf nicht mit `ecs_bmv.py` verwechselt werden.

## Systempfade auf dem Venus GX

- Hauptinstallation: `/opt/victronenergy/dbus-serialbattery/`
- Persistente Konfiguration: `/data/etc/dbus-serialbattery/`
- Serial-Starter: `/data/conf/serial-starter.d/dbus-serialbattery.conf`
- Logs: `/data/log/dbus-serialbattery*/current`

## Verbindliche Arbeitsregeln

- Keine Architekturänderung, Neuinstallation oder größere Refaktorierung ohne ausdrücklichen Auftrag.
- Vor jeder Änderung Branch, Commit, betroffene Datei und den tatsächlich auf dem GX laufenden Stand prüfen.
- Repository-Datei und GX-Datei nie ungeprüft als identisch annehmen.
- Änderungen minimal und ursachenbezogen halten.
- Keine neuen Funktionen ergänzen, solange der aktuelle Fehler nicht sauber eingegrenzt ist.
- Bei mehreren Lösungswegen Varianten bewerten, eine Empfehlung geben und vor größeren Änderungen Freigabe abwarten.
- Vor Repository-Schreibvorgängen die Datei erneut lesen und die aktuelle Blob-SHA verwenden.
- Keine Secrets, Tokens, Schlüssel oder privaten Zugangsdaten einchecken.

## Quellenpriorität

Bei Widersprüchen gilt:

1. aktuelle Rohmessung am realen ECS-System
2. tatsächlich auf dem Venus GX laufender Code und aktive Konfiguration
3. projektspezifische Dokumentation in diesem Branch
4. Dokumentation der exakt eingesetzten ECS-Hardwareversion
5. Upstream-/Victron-Dokumentation
6. Annahmen und Erfahrungswerte

Registerangaben unterschiedlicher ECS-Generationen dürfen nicht vermischt werden.

## Debug-Reihenfolge

1. richtiger serieller Port und stabile By-ID-Zuordnung
2. kein Ausschluss durch `EXCLUDED_DEVICES`
3. Import von `bms.ecs_bmv`
4. Registrierung von `EcsBmv` in `supported_bms_types`
5. Erreichen von `EcsBmv.test_connection()`
6. Baudrate, 8E1, Slave-ID und Verkabelung
7. Minimaltest Register 7
8. Registerblock und Skalierung
9. eindeutige BMV-Service-Erkennung
10. nicht blockierende Übernahme von BMV-Spannung, Strom und SoC
11. D-Bus-Mapping
12. ESS-/DVCC-Verhalten und Fail-safe-Tests

## Bestätigter bzw. aktueller Protokollstand

- Modbus RTU
- 19200 Baud
- aktuelle Implementierung: 8E1
- Register 7: Zellspannung in mV
- Register 8: Temperaturrohwert; aktuelle Formel `raw / 10 - 60` °C, real weiter verifizieren
- Register 13: Betriebs-/Fehlerstatus
- Register 14: LVP
- Register 15: OVP
- Register 28: Slave-Adresse
- Register 30: EEPROM-Speicherbestätigung
- aktueller Treiber: Slave-IDs 1, 2, 3, 4
- historisch genannt: 100, 200, 300, 400

Diese Adressabweichung ist offen und muss am realen System bestätigt werden.

## BMV-D-Bus

Vor einer festen Zuordnung alle `com.victronenergy.battery.*` Services erfassen und den BMV über Produktname, Verbindung, DeviceInstance und verfügbare Pfade eindeutig identifizieren.

Benötigte Werte:

- `/Dc/0/Voltage`
- `/Dc/0/Current`
- `/Soc`

Die BMV-Abfrage ist im aktuellen Treiber noch deaktiviert. Strom `0.0 A` und SoC `50 %` sind nur Entwicklungsplatzhalter und dürfen nicht als produktiver Endstand behandelt werden.

## Sicherheitsregeln

- OVP muss Laden sperren bzw. CCL sicher reduzieren.
- LVP muss Entladen sperren bzw. DCL sicher reduzieren.
- Temperaturfehler müssen sicher behandelt werden.
- ECS-Kommunikationsverlust darf nie zu optimistischer Lade-/Entladefreigabe führen.
- Alte Messwerte müssen als veraltet erkannt werden.
- Physische ECS-Sicherheitsschleifen bleiben unabhängig von der Software maßgeblich.
- ESS-/DVCC-Annahmen zu CVL, CCL, DCL und Freigaben müssen ausdrücklich dokumentiert und getestet werden.

## Anforderungen an jede Codeänderung

Immer angeben:

- Repository-Pfad
- Zielpfad auf dem GX
- vollständiges Snippet oder vollständige Datei
- Begründung
- Testschritte
- relevante Logpfade
- erwartete Logausgaben
- mögliche ESS-/DVCC-/VE.Bus-Auswirkungen
- Rollback

## Standardtests

```sh
dmesg | grep ttyUSB
ls -l /dev/ttyUSB*
ls -l /dev/serial/by-id/
svc -t /service/dbus-serialbattery*
tail -f /data/log/dbus-serialbattery*/current
grep -iE 'ecs|bmv|exception|traceback|error|testing' /data/log/dbus-serialbattery*/current
```

Zusätzlich nach Bedarf:

- `dbus-spy`
- `dbus-monitor`
- Batterie-Services auflisten
- Register 7 einzeln lesen

## Abschluss einer Sitzung

Nach jeder relevanten Diagnose oder Änderung `docs/PROJECT_STATE.md` aktualisieren:

- Branch und Commit
- aktueller Fehlerstand
- bestätigte Erkenntnisse
- verworfene Annahmen
- letzter erfolgreicher Test
- nächster minimaler Schritt
- Rollback-Punkt
