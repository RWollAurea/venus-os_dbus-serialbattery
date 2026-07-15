# D-Bus-Mapping ECS + BMV

## Zielbild

Der kombinierte Battery-Service verbindet BMV-Messwerte mit ECS-Zellschutz.

| Zielwert/Funktion | Quelle |
|---|---|
| Gesamtspannung | BMV `/Dc/0/Voltage` |
| Strom | BMV `/Dc/0/Current` |
| SoC | BMV `/Soc` |
| Zellspannungen | ECS Register 7 |
| Temperaturen | ECS Register 8 |
| Status | ECS Register 13 |
| LVP | ECS Register 14 |
| OVP | ECS Register 15 |
| Ladefreigabe | ECS maßgeblich |
| Entladefreigabe | ECS maßgeblich |

## Aktueller Entwicklungsstand

`bms/ecs_bmv.py` arbeitet derzeit ECS-only.

Vorläufig:

- Strom: `0.0 A`
- SoC: `50 %`
- Gesamtspannung: Summe der ECS-Zellspannungen

Diese Werte sind Entwicklungsplatzhalter und kein produktiver Endstand.

## BMV-Service-Erkennung

Vor einer festen Zuordnung alle `com.victronenergy.battery.*` Services erfassen.

Der BMV ist über mehrere Merkmale eindeutig zu bestimmen:

- Produktname
- Verbindung/Port
- DeviceInstance
- vorhandene Pfade `/Dc/0/Voltage`, `/Dc/0/Current`, `/Soc`

Eine fest kodierte Servicebezeichnung wie `com.victronenergy.battery.ttyO2` ist nur zulässig, wenn sie auf dem realen System dauerhaft bestätigt wurde.

## Fehlerverhalten

### ECS nicht erreichbar

- CCL = 0
- DCL = 0
- Laden gesperrt
- Entladen gesperrt
- Kommunikationsalarm
- alte Zellwerte als veraltet behandeln

### BMV nicht erreichbar

Noch endgültig festzulegen. Mindestanforderungen:

- ECS-Schutz bleibt aktiv
- keine erfundenen Strom-/SoC-Werte als gültig melden
- Staleness-/Kommunikationsalarm setzen
- ESS-/DVCC-Verhalten ausdrücklich testen

### OVP aktiv

- Laden sperren
- CCL auf 0 setzen
- Entladen nur sperren, wenn ein weiterer Schutzgrund vorliegt

### LVP aktiv

- Entladen sperren
- DCL auf 0 setzen
- Laden nur sperren, wenn ein weiterer Schutzgrund vorliegt

## Noch festzulegen

- CVL-Strategie
- normale CCL-/DCL-Grenzen
- Temperaturgrenzen
- Kommunikations-Timeouts
- Wiederanlauf und Hysterese
- Alarm-Mapping
- Umgang mit teilweise erreichbaren ECS-Modulen
- Verhalten bei BMV-Neustart und wechselndem D-Bus-Service
