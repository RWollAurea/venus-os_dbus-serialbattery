# Testplan ECS-BMV-Integration

## Reihenfolge

Spätere Tests setzen das Bestehen der vorherigen Stufe voraus.

## 1. Repository und Syntax

```sh
git status --short
git branch --show-current
git rev-parse HEAD
python3 -m py_compile bms/ecs_bmv.py
python3 -m py_compile dbus-serialbattery.py
python3 -m py_compile tools/test_ecs_modbus_raw.py
```

## 2. Import

```sh
python3 - <<'PY'
from bms.ecs_bmv import EcsBmv
print(EcsBmv)
PY
```

Erwartet:

```text
<class 'bms.ecs_bmv.EcsBmv'>
```

## 3. Loader-Registrierung

```sh
grep -n "from bms.ecs_bmv import EcsBmv" dbus-serialbattery.py
grep -n '"bms": EcsBmv' dbus-serialbattery.py
```

Genau ein Import und ein Eintrag in `supported_bms_types`.

## 4. Portzuordnung

```sh
dmesg | grep ttyUSB
ls -l /dev/ttyUSB*
ls -l /dev/serial/by-id/
```

Eindeutigen By-ID-Pfad dokumentieren.

## 5. Register 7 einzeln

Der Dienst darf den Port nicht geöffnet haben.

```sh
python3 tools/test_ecs_modbus_raw.py \
  /dev/serial/by-id/USB_RS485_ADAPTER \
  SLAVE 19200 7 1
```

Für jeden vorgesehenen Slave wiederholen.

Erwartet:

- Antwort vorhanden
- CRC korrekt
- plausible Zellspannung

## 6. Registerblock 7 bis 15

Erst nach erfolgreichem Einzelregistertest.

Erwartet je Slave:

- neun Register
- plausible Zellspannung
- plausible Temperatur
- Status, LVP und OVP lesbar
- keine Exception 02

## 7. `test_connection()`

Konfiguration:

```ini
BMS_TYPE = EcsBmv
AUTO_DETECT_BMS = False
LOGGING = INFO
```

Erwartete Logs:

```text
Testing EcsBmv
ECS_BMV: __init__
ECS_BMV: test_connection start
ECS_BMV: test_connection ok
Connection established to EcsBmv
```

## 8. ECS-Regelbetrieb

Prüfen:

- Zellspannungen
- Min./Max.-Zelle
- Temperaturen
- Polling-Laufzeit
- keine Portkollision
- keine ungewollte Polling-Intervallsteigerung

## 9. ECS-Kommunikationsverlust

Nacheinander testen:

- USB-RS485 abziehen
- einen Slave trennen
- A/B unterbrechen
- Schnittstellenversorgung unterbrechen

Erwartet:

- Teil-Snapshot wird verworfen
- CCL = 0
- DCL = 0
- Laden und Entladen gesperrt
- klare Logmeldung
- kein Dienstabsturz

## 10. BMV-Service-Erkennung

Alle Batterie-Services erfassen und den BMV eindeutig identifizieren.

Prüfen:

- `/Dc/0/Voltage`
- `/Dc/0/Current`
- `/Soc`

## 11. BMV-Integration

Nach Implementierung:

- Spannung vom BMV
- Strom vom BMV
- SoC vom BMV
- ECS-Schutz bleibt maßgeblich
- kein blockierender D-Bus-Zugriff in `refresh_data()`

## 12. Schutztests

- OVP
- LVP
- Übertemperatur
- Untertemperatur, sofern relevant
- ECS-Kommunikationsverlust
- BMV-Kommunikationsverlust

## 13. ESS/DVCC

Prüfen:

- CVL
- CCL
- DCL
- Ladefreigabe
- Entladefreigabe
- Reaktion des MultiPlus
- Wiederanlauf nach Fehlerende

## 14. Neustart und USB-Reihenfolge

- GX neu starten
- USB-Geräte in anderer Reihenfolge einstecken
- RS485 entfernen und wieder einstecken
- BMV neu starten

## Testprotokoll

Je Test dokumentieren:

- Datum
- Branch und Commit
- Venus-OS-Version
- Port und Slave-ID
- Befehl
- erwartetes Ergebnis
- tatsächliches Ergebnis
- Logauszug
- bestanden/nicht bestanden
