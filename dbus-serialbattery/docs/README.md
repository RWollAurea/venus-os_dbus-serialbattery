# Projektdokumentation ECS + BMV

Diese Dokumentation gehört zum Entwicklungsbranch `ecs-bmv-integration` des Repositories `RWollAurea/venus-os_dbus-serialbattery`.

## Lesereihenfolge für einen neuen Chat oder eine neue Arbeitssitzung

1. `../AGENTS.md`
2. `PROJECT_STATE.md`
3. `VENUS_DEPLOYMENT.md`
4. `ECS_MODBUS.md`
5. `DBUS_MAPPING.md`
6. `TEST_PLAN.md`
7. bei Bedarf `SYSTEM_PROMPT.md`

## Dateien

- `PROJECT_STATE.md` – aktueller technischer Stand, bekannte Risiken und nächster minimaler Schritt
- `VENUS_DEPLOYMENT.md` – kontrollierte Übertragung auf das Venus GX, Tests und Rollback
- `ECS_MODBUS.md` – bestätigte und noch offene Modbus-Parameter und Register
- `DBUS_MAPPING.md` – geplante Zuordnung von ECS- und BMV-Daten zum Battery-Service
- `TEST_PLAN.md` – verbindliche Testreihenfolge vom Import bis ESS/DVCC
- `SYSTEM_PROMPT.md` – vollständiger Projekt-Systemprompt für neue Chats

## Verbindliche Quellpfade im Branch

- Treiber: `../bms/ecs_bmv.py`
- Loader: `../dbus-serialbattery.py`
- Roh-Modbus-Test: `../tools/test_ecs_modbus_raw.py`
- Projektkonfiguration: `../projekt-config/config.ini`
- Serial-Starter-Beispiel: `../projekt-config/serial-starter.d/dbus-serialbattery.conf`

## Wichtiger Hinweis

Der Loader im Entwicklungsbranch weicht aktuell stark vom `master` ab. Vor einem produktiven Deployment muss die ECS-BMV-Registrierung auf Basis der aktuellen `master`-Version sauber integriert werden. Dieser Punkt ist in `PROJECT_STATE.md` als höchste Software-Priorität dokumentiert.
