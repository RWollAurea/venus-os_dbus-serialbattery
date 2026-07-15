# Venus-GX-Deployment

## Ziel

Kontrollierte Übertragung der ECS/BMV-Integration aus dem Branch `ecs-bmv-integration` auf das Venus GX.

## Repository-Zuordnung

| Repository | Venus GX |
|---|---|
| `dbus-serialbattery/bms/ecs_bmv.py` | `/opt/victronenergy/dbus-serialbattery/bms/ecs_bmv.py` |
| `dbus-serialbattery/dbus-serialbattery.py` | `/opt/victronenergy/dbus-serialbattery/dbus-serialbattery.py` |
| `dbus-serialbattery/projekt-config/config.ini` | `/data/etc/dbus-serialbattery/config.ini` |
| `dbus-serialbattery/projekt-config/serial-starter.d/dbus-serialbattery.conf` | `/data/conf/serial-starter.d/dbus-serialbattery.conf` |
| `dbus-serialbattery/tools/test_ecs_modbus_raw.py` | `/data/etc/dbus-serialbattery/tools/test_ecs_modbus_raw.py` |

## Kritischer Vorbehalt

Die aktuelle Loader-Datei im Entwicklungsbranch weicht stark von `master` ab. Sie darf nicht ungeprüft auf das GX kopiert werden.

Vor dem Deployment die aktuelle `master`-Version des Loaders verwenden und nur ergänzen:

```python
from bms.ecs_bmv import EcsBmv
```

sowie in `supported_bms_types`:

```python
{"bms": EcsBmv, "baud": 19200},
```

## Vorprüfung

```sh
cat /opt/victronenergy/version
ls -ld /opt/victronenergy/dbus-serialbattery /data/etc/dbus-serialbattery /data/conf/serial-starter.d
ls -l /dev/ttyUSB* /dev/serial/by-id/* 2>/dev/null
cat /data/conf/serial-starter.d/dbus-serialbattery.conf
grep -n "EcsBmv" /opt/victronenergy/dbus-serialbattery/dbus-serialbattery.py
```

## Sicherung

```sh
TS="$(date +%Y%m%d-%H%M%S)"
BACKUP="/data/backup/dbus-serialbattery-$TS"
mkdir -p "$BACKUP"
cp -a /opt/victronenergy/dbus-serialbattery/dbus-serialbattery.py "$BACKUP/"
cp -a /opt/victronenergy/dbus-serialbattery/bms "$BACKUP/"
cp -a /data/etc/dbus-serialbattery "$BACKUP/" 2>/dev/null || true
cp -a /data/conf/serial-starter.d/dbus-serialbattery.conf "$BACKUP/" 2>/dev/null || true
echo "$BACKUP"
```

## Projektkonfiguration

Empfohlener Teststand:

```ini
[DEFAULT]
DEVICES = /dev/serial/by-id/usb-FTDI_FT232R_USB_UART_AG0KG1HS-if00-port0
BMS_TYPE = EcsBmv
AUTO_DETECT_BMS = False
BLOCK_ON_DISCONNECT = True
MAX_BATTERY_CHARGE_CURRENT = 65
MAX_BATTERY_DISCHARGE_CURRENT = 130
LOGGING = INFO
```

`EXCLUDED_DEVICES` darf den verwendeten Adapter nicht ausschließen.

## Installation

```sh
install -m 0644 ecs_bmv.py /opt/victronenergy/dbus-serialbattery/bms/ecs_bmv.py
mkdir -p /data/etc/dbus-serialbattery/tools
install -m 0755 test_ecs_modbus_raw.py /data/etc/dbus-serialbattery/tools/test_ecs_modbus_raw.py
```

Die Loader-Datei nur nach vorherigem Vergleich und ausdrücklicher Freigabe ersetzen.

## Syntax- und Importtest

```sh
cd /opt/victronenergy/dbus-serialbattery
python3 -m py_compile bms/ecs_bmv.py
python3 -m py_compile dbus-serialbattery.py
python3 -m py_compile /data/etc/dbus-serialbattery/tools/test_ecs_modbus_raw.py
python3 - <<'PY'
from bms.ecs_bmv import EcsBmv
print(EcsBmv)
PY
```

Erwartet:

```text
<class 'bms.ecs_bmv.EcsBmv'>
```

## Roh-Modbus-Test

Vorher sicherstellen, dass kein Dienst den Port geöffnet hält.

```sh
python3 /data/etc/dbus-serialbattery/tools/test_ecs_modbus_raw.py \
  /dev/serial/by-id/usb-FTDI_FT232R_USB_UART_AG0KG1HS-if00-port0 \
  1 19200 7 1
```

Für jeden bestätigten Slave wiederholen.

## Dienst neu starten

```sh
ls -ld /service/dbus-serialbattery*
svc -t /service/dbus-serialbattery*
```

## Logprüfung

```sh
tail -n 200 /data/log/dbus-serialbattery*/current
grep -iE 'ecs_bmv|ecsbmv|ecs|bmv|exception|traceback|error|testing' /data/log/dbus-serialbattery*/current
```

Erwartete Reihenfolge:

```text
Starting dbus-serialbattery
Testing EcsBmv
ECS_BMV: __init__
ECS_BMV: test_connection start
ECS_BMV: test_connection ok
Connection established to EcsBmv
```

## D-Bus-Prüfung

Alle Batterie-Services erfassen und den BMV eindeutig identifizieren. Benötigte Pfade:

- `/Dc/0/Voltage`
- `/Dc/0/Current`
- `/Soc`

Keine feste Servicebezeichnung verwenden, bevor sie auf dem realen System dauerhaft bestätigt wurde.

## ESS-/DVCC-Test

Erst nach stabiler ECS- und BMV-Kommunikation:

- CVL, CCL, DCL
- OVP und LVP
- Temperaturfehler
- ECS-Kommunikationsverlust
- BMV-Kommunikationsverlust
- USB-RS485 entfernen und wieder einstecken
- GX neu starten

Bei ECS-Kommunikationsverlust müssen Laden und Entladen sicher gesperrt werden.

## Rollback

```sh
BACKUP="/data/backup/dbus-serialbattery-YYYYMMDD-HHMMSS"
cp -a "$BACKUP/dbus-serialbattery.py" /opt/victronenergy/dbus-serialbattery/dbus-serialbattery.py
rm -rf /opt/victronenergy/dbus-serialbattery/bms
cp -a "$BACKUP/bms" /opt/victronenergy/dbus-serialbattery/
rm -rf /data/etc/dbus-serialbattery
cp -a "$BACKUP/dbus-serialbattery" /data/etc/ 2>/dev/null || true
cp -a "$BACKUP/dbus-serialbattery.conf" /data/conf/serial-starter.d/dbus-serialbattery.conf 2>/dev/null || true
svc -t /service/dbus-serialbattery*
```
