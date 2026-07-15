# ECS Modbus RTU

## Geltungsbereich

ECS LiPro1-6 Active Version 1.x im Projekt BMV-712 + ECS-BMS.

## Aktueller Parameterstand

| Parameter | Wert | Status |
|---|---:|---|
| Protokoll | Modbus RTU | bestätigt |
| Baudrate | 19200 | dokumentiert und implementiert |
| Datenbits | 8 | implementiert |
| Parität | Even | implementiert, real weiter prüfen |
| Stopbits | 1 | implementiert, real weiter prüfen |
| Funktionscode | 0x03 | implementiert |
| Aktuelle Slave-IDs | 1, 2, 3, 4 | im Treiber, real bestätigen |

Historisch wurden 100, 200, 300 und 400 genannt. Diese Abweichung ist offen.

## Register

| Register | Bedeutung | Interpretation |
|---:|---|---|
| 7 | Zellspannung | mV |
| 8 | Temperaturrohwert | aktuell `raw / 10 - 60` °C |
| 13 | Betriebs-/Fehlerstatus | Bitbelegung offen |
| 14 | LVP | aktuell `0 = inaktiv`, ungleich `0 = aktiv` |
| 15 | OVP | aktuell `0 = inaktiv`, ungleich `0 = aktiv` |
| 28 | Slave-Adresse | Geräteadresse |
| 30 | EEPROM-Bestätigung | genaue Schreibsequenz offen |

## Implementierung

- Treiber: `bms/ecs_bmv.py`
- Roh-Test: `tools/test_ecs_modbus_raw.py`
- Produktiver Treiber liest Register 7 bis 15 als Block.
- Erster Kommunikationstest liest ausschließlich Register 7.

## Minimaltest

```sh
python3 tools/test_ecs_modbus_raw.py \
  /dev/serial/by-id/USB_RS485_ADAPTER \
  1 19200 7 1
```

Kein anderer Prozess darf dabei den Port geöffnet haben.

## Fehlerinterpretation

- Keine Antwort: Port, Versorgung, A/B, GND, Slave-ID, 8E1 und Portbelegung prüfen.
- Nur `0x00`: Versorgung der galvanisch getrennten RS485-Schnittstelle prüfen.
- Exception 02: Kommunikation funktioniert; Registeradresse oder Anzahl ist ungültig.
- CRC-Fehler: Busstörung, falsche Parameter, Echo/Nachlauf oder paralleler Portzugriff.

## Sicherheitsregel

Nur ein vollständiger, plausibler Snapshot aller konfigurierten Module darf übernommen werden. Bei unvollständiger Kommunikation müssen Lade- und Entladefreigabe sicher gesperrt werden.
