# Projektstand: Victron BMV-712 + ECS LiPro als BMS

Stand: 2026-07-15

## Repository

- Repository: `RWollAurea/venus-os_dbus-serialbattery`
- Upstream-/Standardbranch: `master`
- Aktiver Entwicklungsbranch: `ecs-bmv-integration`
- Upstream-Basis: `5842e4414a9c55a4ab311c54261f8e9c870fb36f`
- Upstream-Herkunft: Fork von `mr-manuel/venus-os_dbus-serialbattery`
- Schreibzugriff über den ChatGPT Codex Connector ist bestätigt.

## Zielsystem

- Gerät: Victron Venus GX
- Venus OS: v3.71
- Hauptinstallation: `/opt/victronenergy/dbus-serialbattery/`
- Persistente Konfiguration: `/data/etc/dbus-serialbattery/`
- BMV-712 per VE.Direct am GX
- ECS LiPro1-6 Active Version 1.0 per USB-RS485 am GX
- FTDI-Adapter laut Projektkonfiguration:
  `/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_AG0KG1HS-if00-port0`

## Aktuelle projektspezifische Dateien

- `dbus-serialbattery/bms/ecs_bmv.py`
- `dbus-serialbattery/tools/test_ecs_modbus_raw.py`
- `dbus-serialbattery/dbus-serialbattery.py`
- `dbus-serialbattery/projekt-config/config.ini`
- `dbus-serialbattery/projekt-config/serial-starter.d/dbus-serialbattery.conf`
- `dbus-serialbattery/AGENTS.md`
- `dbus-serialbattery/docs/VENUS_DEPLOYMENT.md`
- `dbus-serialbattery/docs/ECS_MODBUS.md`
- `dbus-serialbattery/docs/DBUS_MAPPING.md`
- `dbus-serialbattery/docs/TEST_PLAN.md`
- `dbus-serialbattery/docs/SYSTEM_PROMPT.md`

## Aktuelle Treiberintegration

Treiber:

`dbus-serialbattery/bms/ecs_bmv.py`

Klasse:

`EcsBmv`

Der Entwicklungsbranch importiert den Treiber im Loader mit:

```python
from bms.ecs_bmv import EcsBmv
```

und registriert ihn mit 19200 Baud in `supported_bms_types`.

Damit sind Import und explizite Registrierung im Repository grundsätzlich vorhanden.

## Aktuelle Treiberfunktion

Der Treiber verwendet derzeit:

- Modbus RTU
- 19200 Baud
- 8 Datenbits, gerade Parität, 1 Stopbit
- Slave-IDs 1, 2, 3 und 4
- Registerblock 7 bis 15
- vollständigen Snapshot aller vier Slaves
- Fail-safe bei unvollständigem ECS-Snapshot:
  - CCL = 0
  - DCL = 0
  - `charge_fet = False`
  - `discharge_fet = False`

Registerauswertung:

- Register 7: Zellspannung in mV
- Register 8: Temperatur als `raw / 10 - 60` °C
- Register 13: Status
- Register 14: LVP
- Register 15: OVP

## Noch nicht erreichter Endstand

Die BMV-Abfrage ist in `refresh_data()` noch deaktiviert.

Aktuelle Platzhalter:

- Strom: `0.0 A`
- SoC: `50 %`

Die Gesamtspannung wird derzeit aus der Summe der ECS-Zellspannungen gebildet. Das entspricht noch nicht dem Projektziel, nach dem Gesamtspannung, Strom und SoC vom BMV-712 kommen sollen.

## Kritischer Loader-Hinweis

Die Datei `dbus-serialbattery/dbus-serialbattery.py` im Entwicklungsbranch unterscheidet sich stark von der aktuellen `master`-Version.

Beim letzten Vergleich wurden gegenüber `master` ungefähr 97 Zeilen hinzugefügt und 318 Zeilen entfernt.

Das deutet darauf hin, dass eine ältere oder vom GX übernommene Loader-Version in den Branch gelangt ist. Vor einem produktiven Deployment muss die ECS-BMV-Integration in die aktuelle `master`-Version übertragen werden. Zieländerungen am Loader sind nur:

```python
from bms.ecs_bmv import EcsBmv
```

und:

```python
{"bms": EcsBmv, "baud": 19200},
```

Weitere Loader-Abweichungen müssen separat begründet werden.

## Konfigurationsstand

Die Projektkonfiguration soll für den gezielten Test verwenden:

```ini
BMS_TYPE = EcsBmv
AUTO_DETECT_BMS = False
BLOCK_ON_DISCONNECT = True
```

Der verwendete By-ID-Port darf nicht gleichzeitig durch `EXCLUDED_DEVICES` ausgeschlossen werden.

## Offene technische Punkte

1. Loader auf aktuelle `master`-Basis bringen.
2. Slave-IDs am realen System bestätigen. Aktueller Code: 1 bis 4; historisch genannt: 100, 200, 300, 400.
3. Temperaturformel anhand realer Vergleichswerte bestätigen.
4. Statusregister 13 bitgenau dokumentieren.
5. Semantik der Werte in Register 14 und 15 bestätigen.
6. BMV-Service dynamisch und eindeutig erkennen.
7. Nicht blockierende Übernahme von BMV-Spannung, Strom und SoC implementieren.
8. Kommunikationsalter/Staleness für ECS und BMV definieren.
9. CVL, CCL und DCL fachlich für ESS/DVCC festlegen.
10. OVP-, LVP-, Temperatur- und Kommunikationsverlusttests durchführen.
11. Verhalten nach USB-Trennung, Wiederanstecken und GX-Neustart testen.

## Nächster minimaler Arbeitsschritt

1. Aktuelle Loader-Datei aus `master` als Grundlage verwenden.
2. Nur Import und Registrierung von `EcsBmv` übernehmen.
3. Projektkonfiguration mit `BMS_TYPE = EcsBmv` verwenden.
4. Roh-Modbus-Test auf Register 7 für jeden realen Slave ausführen.
5. Erst danach `EcsBmv.test_connection()` über den Service testen.

## Erwartete Logfolge

```text
Starting dbus-serialbattery
Testing EcsBmv
ECS_BMV: __init__
ECS_BMV: test_connection start
ECS_BMV: test_connection ok
Connection established to EcsBmv
```

`Testing Ecs` bezeichnet nur den getrennten Upstream-Treiber `bms.ecs.Ecs`.

## Sicherheitsstatus

Noch nicht produktionsreif.

Die physischen ECS-Sicherheitsschleifen bleiben maßgeblich. Der kombinierte D-Bus-Service darf erst nach erfolgreichem Test von Kommunikationsverlust, OVP, LVP, Temperaturfehlern und BMV-Ausfall für ESS/DVCC eingesetzt werden.

## Rollback

Vor jeder Änderung auf dem GX:

```sh
cp -a DATEI DATEI.bak-$(date +%Y%m%d-%H%M%S)
```

Vor jeder Repository-Änderung aktuellen Branch und Commit dokumentieren.
