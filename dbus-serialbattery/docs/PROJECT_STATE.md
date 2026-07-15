# Projektstand: Victron BMV-712 + ECS LiPro als BMS

Stand: 2026-07-15

## Repository

- Repository: `RWollAurea/venus-os_dbus-serialbattery`
- Standardbranch: `master`
- Letzter von ChatGPT gelesener Commit auf `master`: `5842e4414a9c55a4ab311c54261f8e9c870fb36f`
- Upstream-Herkunft: Fork des Projekts `mr-manuel/venus-os_dbus-serialbattery`
- Projektspezifische Dateien `ecs_bmv.py` und `test_ecs_modbus_raw.py`: im Standardbranch durch den GitHub-Zugriff derzeit noch nicht auffindbar; Pfad und Commit müssen bestätigt werden.

## Zielsystem

- Gerät: Victron Venus GX
- Venus OS: v3.71
- dbus-serialbattery Hauptinstallation:
  `/opt/victronenergy/dbus-serialbattery/`
- Persistente eigene Anpassungen:
  `/data/etc/dbus-serialbattery/`
- Historischer eigener Treiber:
  `/data/etc/dbus-serialbattery/batteries/ecs_bmv.py`
- Treiberklasse:
  `EcsBmvBattery`
- BMV-712 per VE.Direct am GX
- ECS LiPro1-6 Active Version 1.0 per USB-RS485 am GX

## Architektur

Der kombinierte Battery-Service soll folgende Quellen verwenden:

| Zielwert/Funktion | Quelle |
|---|---|
| Gesamtspannung | BMV-712 `/Dc/0/Voltage` |
| Strom | BMV-712 `/Dc/0/Current` |
| SoC | BMV-712 `/Soc` |
| Zellspannungen | ECS Modbus |
| Temperatur | ECS Modbus |
| OVP | ECS Modbus |
| LVP | ECS Modbus |
| Schutz-/Fehlerstatus | ECS Modbus |
| Ladefreigabe | ECS maßgeblich |
| Entladefreigabe | ECS maßgeblich |

Der BMV ist kein vollständiges BMS. ECS bleibt für den Zellschutz maßgeblich.

## Bestätigte ECS-Informationen

- Protokoll: Modbus RTU
- Werkseinstellung laut ECS-Dokumentation: 19200 Baud
- Register 7: Zellspannung in mV
- Register 8: Temperaturrohwert; endgültige Umrechnung noch verifizieren
- Register 13: Betriebs-/Fehlerstatus
- Register 14: LVP
- Register 15: OVP
- Register 28: Slave-Adresse
- Register 30: EEPROM-Speicherbestätigung
- Frühere Adressen: 100, 200, 300, 400
- Hinweis: einzelne Module können gegebenenfalls auf Adresse 0 reagieren
- Minimaltest: zunächst ausschließlich Register 7 lesen

## Aktuell bekannte Hardware-/Busbesonderheiten

- USB-Ports können als `/dev/ttyUSB0` bis `/dev/ttyUSB3` erscheinen.
- Stabile Zuordnung soll über `/dev/serial/by-id/` erfolgen.
- Die galvanisch getrennte RS485-Schnittstelle benötigt eine passende Versorgung; ohne die benötigte Versorgung wurden in früheren Tests nur `0x00`-Antworten beobachtet.
- Bei Timeout prüfen:
  - falscher Port,
  - A/B vertauscht,
  - fehlender GND,
  - fehlende Versorgung,
  - falsche Slave-ID,
  - falsche Parität oder Baudrate,
  - Port durch anderen Prozess belegt.
- Modbus Exception 02 bedeutet: Kommunikation funktioniert grundsätzlich, Registeradresse oder Registeranzahl ist jedoch ungültig.

## Aktueller Softwarestand

Der Upstream-Startpunkt im Repository befindet sich unter:

`dbus-serialbattery/dbus-serialbattery.py`

Die aktuell gelesene Version:

- importiert den vorhandenen Upstream-Treiber `from bms.ecs import Ecs`,
- registriert diesen mit 19200 Baud in `supported_bms_types`,
- kennt in der gelesenen Fassung keinen Import von `ecs_bmv.py`,
- erwartet reguläre Treiber in der Paketstruktur `dbus-serialbattery/bms/`.

Historisch lag der projektspezifische Treiber dagegen unter:

`/data/etc/dbus-serialbattery/batteries/ecs_bmv.py`

Damit besteht eine noch zu klärende Abweichung zwischen:

- historischer eigener `batteries`-/`BasicBattery`-Struktur,
- aktueller Upstream-`bms`-/`Battery`-Struktur.

Vor einer weiteren Loader-Änderung muss der aktuelle Inhalt von `ecs_bmv.py` vollständig gelesen werden.

## Letztes bekanntes Problem

Der eigene Treiber wurde vom Python-Prozess nicht geladen beziehungsweise nicht getestet.

Beobachtung:

- Im Log erschien `Testing Ecs`.
- Eigene Logausgaben aus `ecs_bmv.py` erschienen nicht.
- `test_connection()` der eigenen Klasse wurde nicht erreicht.

Frühere Ursache:

- `/data/etc/dbus-serialbattery` lag nicht im `sys.path`.
- `BasicBattery.__subclasses__()` konnte nur bereits importierte Klassen sehen.
- Ein früherer Importversuch endete mit:
  `ModuleNotFoundError: No module named 'batteries'`

Wichtig: Der aktuell im Repository gelesene Upstream-Loader arbeitet nicht über `BasicBattery.__subclasses__()`, sondern über eine explizite Liste `supported_bms_types`. Der aktuelle projektspezifische Code muss deshalb vor dem nächsten Fix gegen die tatsächlich verwendete Version abgeglichen werden.

## Offene Punkte mit Priorität

1. Pfad und Commit von `ecs_bmv.py` im Repository bestätigen.
2. Pfad und Commit von `test_ecs_modbus_raw.py` im Repository bestätigen.
3. Aktuellen Inhalt beider Dateien vollständig prüfen.
4. Feststellen, ob `ecs_bmv.py` von `Battery`, `BasicBattery` oder einer anderen Basisklasse erbt.
5. Aktuell auf dem GX laufende `dbus-serialbattery.py` mit dem Repository vergleichen.
6. Serial-Starter-Konfiguration und tatsächlich übergebenen Port dokumentieren.
7. Modbus-Parameter Parität, Stopbits und Slave-ID am realen Gerät bestätigen.
8. BMV-D-Bus-Service eindeutig erfassen.
9. Erst danach das ESS-/DVCC-Mapping festlegen.

## Nächster minimaler Arbeitsschritt

Nicht erneut am Importmechanismus ändern, bevor folgende Daten vorliegen:

```sh
cd /opt/victronenergy/dbus-serialbattery
git rev-parse HEAD 2>/dev/null || true

find /data/etc/dbus-serialbattery -maxdepth 3 -type f -print
grep -R "class EcsBmvBattery" -n /data/etc/dbus-serialbattery /opt/victronenergy/dbus-serialbattery 2>/dev/null
grep -R "ecs_bmv" -n /data/etc/dbus-serialbattery /opt/victronenergy/dbus-serialbattery 2>/dev/null

cat /data/conf/serial-starter.d/dbus-serialbattery.conf
ls -l /dev/ttyUSB* /dev/serial/by-id/* 2>/dev/null
```

Danach Repository-Datei und GX-Datei inhaltlich vergleichen.

## Sicherheitsstatus

Noch nicht als produktionsreif einstufen.

Bis zur vollständigen Abbildung von ECS-Kommunikationsverlust, OVP, LVP und Temperaturfehlern darf der kombinierte Service nicht als alleinige Schutzinstanz betrachtet werden. Die physischen ECS-Sicherheitsschleifen bleiben maßgeblich.

## Rollback

Vor jeder Änderung auf dem GX:

```sh
cp -a DATEI DATEI.bak-$(date +%Y%m%d-%H%M%S)
```

Bei Repository-Änderungen den vorherigen Commit-SHA hier dokumentieren.

Aktueller dokumentierter Ausgangs-Commit:

`5842e4414a9c55a4ab311c54261f8e9c870fb36f`
