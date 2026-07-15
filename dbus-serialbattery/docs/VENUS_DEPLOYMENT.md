# Venus-GX-Deployment

## Zweck

Diese Datei beschreibt die kontrollierte Übertragung der projektspezifischen ECS/BMV-Anpassungen aus dem Repository auf das Venus GX sowie Prüfung und Rollback.

Sie ist noch kein automatisches Installationsskript. Pfade und Befehle müssen vor der ersten produktiven Anwendung mit dem aktuellen Repository- und GX-Stand abgeglichen werden.

## Zielsystem

- Gerät: Victron Venus GX
- Venus OS: v3.71
- Hauptinstallation:
  `/opt/victronenergy/dbus-serialbattery/`
- Persistente Anpassungen:
  `/data/etc/dbus-serialbattery/`
- Serial-Starter-Konfiguration:
  `/data/conf/serial-starter.d/dbus-serialbattery.conf`
- Logs:
  `/data/log/dbus-serialbattery*/current`

## Wichtige Pfadabweichung

Historischer projektspezifischer Treiber:

`/data/etc/dbus-serialbattery/batteries/ecs_bmv.py`

Aktuelle Upstream-Struktur im Repository:

`dbus-serialbattery/bms/`

Vor dem Deployment muss daher geklärt werden:

1. Wo liegt `ecs_bmv.py` im Repository?
2. Welche Basisklasse verwendet der Treiber?
3. Welcher Loader läuft tatsächlich auf dem GX?
4. Wird der Treiber über expliziten Import und `supported_bms_types` registriert oder über einen anderen Mechanismus?
5. Ist das Verzeichnis `batteries` ein korrektes Python-Paket mit `__init__.py`?
6. Muss `/data/etc/dbus-serialbattery` oder ein Unterverzeichnis in `sys.path` aufgenommen werden?

Keine Pfadstruktur ohne vorherigen Abgleich ändern.

## Vorprüfung auf dem GX

```sh
cat /opt/victronenergy/version

ls -ld   /opt/victronenergy/dbus-serialbattery   /data/etc/dbus-serialbattery   /data/conf/serial-starter.d

find /data/etc/dbus-serialbattery -maxdepth 3 -type f -print
find /opt/victronenergy/dbus-serialbattery -maxdepth 2 -type f -name '*ecs*' -print

grep -R "class EcsBmvBattery" -n   /data/etc/dbus-serialbattery   /opt/victronenergy/dbus-serialbattery 2>/dev/null

grep -R "ecs_bmv" -n   /data/etc/dbus-serialbattery   /opt/victronenergy/dbus-serialbattery 2>/dev/null

cat /data/conf/serial-starter.d/dbus-serialbattery.conf

ls -l /dev/ttyUSB* /dev/serial/by-id/* 2>/dev/null
```

## Laufenden Stand sichern

Vor jeder Änderung ein Sicherungsverzeichnis anlegen:

```sh
TS="$(date +%Y%m%d-%H%M%S)"
BACKUP="/data/backup/dbus-serialbattery-$TS"
mkdir -p "$BACKUP"

cp -a /data/etc/dbus-serialbattery "$BACKUP/" 2>/dev/null || true
cp -a /data/conf/serial-starter.d/dbus-serialbattery.conf "$BACKUP/" 2>/dev/null || true
cp -a /opt/victronenergy/dbus-serialbattery/dbus-serialbattery.py "$BACKUP/" 2>/dev/null || true

echo "$BACKUP"
```

Zusätzlich Hashwerte erfassen:

```sh
find /data/etc/dbus-serialbattery   /opt/victronenergy/dbus-serialbattery/dbus-serialbattery.py   -type f -exec sha256sum {} \; 2>/dev/null
```

## Repository-Stand dokumentieren

Auf einem System mit Git-Arbeitskopie:

```sh
git status --short
git branch --show-current
git rev-parse HEAD
git log -1 --oneline
```

Der verwendete Commit muss in `docs/PROJECT_STATE.md` eingetragen werden.

## Empfohlene Deployment-Strategie

### Variante A: Persistente projektspezifische Dateien unter `/data`

Bevorzugt, wenn die aktuelle Loader-Struktur dies unterstützt.

Vorteile:

- Venus-OS-Updates überschreiben `/data` nicht.
- Projektspezifischer Code bleibt von der Upstream-Installation getrennt.

Voraussetzungen:

- korrekter Python-Paketpfad,
- sauberer Import,
- eindeutige Registrierung von `EcsBmvBattery`,
- keine Verwechslung mit `bms.ecs.Ecs`.

### Variante B: Integration in die lokale dbus-serialbattery-Installation

Nur verwenden, wenn die aktuelle Upstream-Version reguläre Treiber ausschließlich in `dbus-serialbattery/bms/` erwartet.

Nachteile:

- Änderungen unter `/opt/victronenergy` können durch Neuinstallation oder Update überschrieben werden.
- Ein Update muss anschließend erneut geprüft beziehungsweise eingespielt werden.

Vor einer Entscheidung zuerst den aktuellen Inhalt von `ecs_bmv.py` und die laufende Loader-Version vergleichen.

## Dateirechte

Nach dem Kopieren prüfen:

```sh
chown -R root:root /data/etc/dbus-serialbattery
find /data/etc/dbus-serialbattery -type d -exec chmod 755 {} \;
find /data/etc/dbus-serialbattery -type f -exec chmod 644 {} \;
```

Ausführbare Testskripte bei Bedarf:

```sh
chmod 755 /data/etc/dbus-serialbattery/test_ecs_modbus_raw.py
```

## Python-Syntax und Import prüfen

Syntax:

```sh
python3 -m py_compile /data/etc/dbus-serialbattery/batteries/ecs_bmv.py
python3 -m py_compile /data/etc/dbus-serialbattery/test_ecs_modbus_raw.py
```

Der konkrete Importtest hängt von der tatsächlich verwendeten Paketstruktur ab. Erst nach Prüfung von `ecs_bmv.py` festlegen.

Beispiel für die historische Struktur:

```sh
cd /opt/victronenergy/dbus-serialbattery
python3 - <<'PY'
import sys
sys.path.insert(0, "/data/etc/dbus-serialbattery")
from batteries.ecs_bmv import EcsBmvBattery
print(EcsBmvBattery)
PY
```

Dieser Test ist nur gültig, wenn:

- `/data/etc/dbus-serialbattery/batteries/__init__.py` vorhanden ist,
- `ecs_bmv.py` tatsächlich dort liegt,
- die Importe innerhalb des Treibers zur laufenden dbus-serialbattery-Version passen.

## Modbus-Minimaltest

Zuerst nur Register 7 lesen.

Beispiel:

```sh
python3 /data/etc/dbus-serialbattery/test_ecs_modbus_raw.py   /dev/serial/by-id/USB_RS485_ADAPTER   SLAVE_ID   19200   7   1
```

Die genaue Argumentfolge muss anhand des aktuellen Skripts bestätigt werden.

Erwartung:

- gültiger Modbus-RTU-Response,
- plausibler Wert im Bereich der aktuellen Zellspannung,
- keine große Registerblockabfrage,
- keine gleichzeitige Nutzung des Ports durch den dbus-serialbattery-Service.

Vor einem manuellen Porttest den betroffenen Service gegebenenfalls stoppen beziehungsweise sicherstellen, dass der Port nicht gleichzeitig geöffnet ist.

## Service neu starten

Vorher vorhandene Services ermitteln:

```sh
ls -ld /service/dbus-serialbattery*
```

Anschließend gezielt neu starten:

```sh
svc -t /service/dbus-serialbattery*
```

Keine pauschalen Änderungen an anderen Venus-Diensten.

## Logprüfung

```sh
tail -n 200 /data/log/dbus-serialbattery*/current
grep -iE 'ecs|bmv|exception|traceback|error|testing'   /data/log/dbus-serialbattery*/current
```

Erwartete Stufen:

1. Start von dbus-serialbattery
2. verwendeter serieller Port
3. Import beziehungsweise Registrierung von `EcsBmvBattery`
4. Aufruf von `test_connection()`
5. erfolgreicher Register-7-Test
6. eindeutige BMV-Service-Erkennung
7. Aufbau des Battery-D-Bus-Service

Eine Logmeldung `Testing Ecs` belegt nur den Test des Upstream-Treibers `bms.ecs.Ecs`, nicht den Aufruf des projektspezifischen Treibers.

## D-Bus-Prüfung

Vorhandene Batterie-Services erfassen:

```sh
dbus-send --system --print-reply   --dest=com.victronenergy.battery   /   org.freedesktop.DBus.Introspectable.Introspect
```

Je nach Venus-OS-Werkzeugen besser mit `dbus-spy`, `dbus-monitor` oder den vorhandenen Victron-D-Bus-Hilfswerkzeugen prüfen.

Zu bestätigen:

- BMV-Service und dessen `DeviceInstance`,
- `/Dc/0/Voltage`,
- `/Dc/0/Current`,
- `/Soc`,
- neuer kombinierter Battery-Service,
- keine D-Bus-Namenskollision,
- richtige Auswahl als Systembatterie.

## ESS-/DVCC-Prüfung

Erst nach stabiler ECS- und BMV-Kommunikation.

Zu prüfen:

- CVL,
- CCL,
- DCL,
- Ladefreigabe,
- Entladefreigabe,
- OVP-Reaktion,
- LVP-Reaktion,
- Temperaturfehler,
- ECS-Kommunikationsverlust,
- BMV-Kommunikationsverlust,
- Wiederanlauf nach Kommunikationsrückkehr.

Bei ECS-Ausfall muss ein sicherer Zustand verwendet werden. Alte Zellwerte dürfen nicht unbegrenzt weiterverwendet werden.

## Rollback

Service stoppen beziehungsweise neu starten, nachdem die gesicherten Dateien wiederhergestellt wurden.

Beispiel:

```sh
BACKUP="/data/backup/dbus-serialbattery-YYYYMMDD-HHMMSS"

rm -rf /data/etc/dbus-serialbattery
cp -a "$BACKUP/dbus-serialbattery" /data/etc/

cp -a "$BACKUP/dbus-serialbattery.conf"   /data/conf/serial-starter.d/dbus-serialbattery.conf

cp -a "$BACKUP/dbus-serialbattery.py"   /opt/victronenergy/dbus-serialbattery/dbus-serialbattery.py

svc -t /service/dbus-serialbattery*
```

Vor dem Ausführen Dateinamen und Sicherungsstruktur kontrollieren.

## Verhalten nach Venus-OS- oder dbus-serialbattery-Update

Nach jedem Update prüfen:

```sh
cat /opt/victronenergy/version
grep -n "from bms.ecs import Ecs"   /opt/victronenergy/dbus-serialbattery/dbus-serialbattery.py
grep -n "supported_bms_types"   /opt/victronenergy/dbus-serialbattery/dbus-serialbattery.py
```

Danach:

- Repository-Commit aktualisieren,
- laufende Loader-Struktur erneut bewerten,
- keine alte Patch-Datei blind auf eine neue Upstream-Version übertragen,
- vollständigen Import-, Modbus-, D-Bus- und Fail-safe-Test wiederholen.
