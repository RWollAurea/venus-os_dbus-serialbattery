#!/usr/bin/env python3
import sys
import time
import serial

PORT = sys.argv[1] if len(sys.argv) > 1 else "/dev/ttyUSB0"
SLAVE = int(sys.argv[2]) if len(sys.argv) > 2 else 1
BAUD = int(sys.argv[3]) if len(sys.argv) > 3 else 19200
REGISTER = int(sys.argv[4]) if len(sys.argv) > 4 else 7
COUNT = int(sys.argv[5]) if len(sys.argv) > 5 else 1

# Grosszuegige Pausen fuer ECS/LiPro RS485-Bus
PRE_TX_DELAY = 0.30
POST_TX_DELAY = 0.10
POST_RX_DELAY = 0.50
TAIL_DRAIN_DELAY = 0.20

TIMEOUT = 1.50


def crc16_modbus(data: bytes) -> int:
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc & 0xFFFF


def build_request(slave: int, register: int, count: int) -> bytes:
    pdu = bytes([
        slave & 0xFF,
        0x03,
        (register >> 8) & 0xFF,
        register & 0xFF,
        (count >> 8) & 0xFF,
        count & 0xFF,
    ])
    crc = crc16_modbus(pdu)
    return pdu + bytes([crc & 0xFF, (crc >> 8) & 0xFF])


def check_crc(frame: bytes) -> bool:
    if len(frame) < 5:
        return False
    body = frame[:-2]
    got = frame[-2] | (frame[-1] << 8)
    return crc16_modbus(body) == got


def decode_registers(rx: bytes):
    byte_count = rx[2]
    data = rx[3:3 + byte_count]

    values = []
    for i in range(0, len(data), 2):
        values.append((data[i] << 8) | data[i + 1])

    return values


def main() -> int:
    print(f"Port={PORT}, Slave={SLAVE}, Baud={BAUD}, Register={REGISTER}, Count={COUNT}")

    req = build_request(SLAVE, REGISTER, COUNT)
    expected_len = 5 + 2 * COUNT

    print("TX:", req.hex(" "))

    try:
        with serial.Serial(
            port=PORT,
            baudrate=BAUD,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_EVEN,
            stopbits=serial.STOPBITS_ONE,
            timeout=TIMEOUT,
            write_timeout=TIMEOUT,
        ) as ser:
            # Alten Muell vom Bus entfernen
            ser.reset_input_buffer()
            ser.reset_output_buffer()
            time.sleep(PRE_TX_DELAY)

            ser.write(req)
            ser.flush()
            time.sleep(POST_TX_DELAY)

            # Nur exakt die erwartete Antwortlaenge lesen
            rx = ser.read(expected_len)

            # Danach evtl. Nachlauf separat lesen und ignorieren
            time.sleep(TAIL_DRAIN_DELAY)
            tail = ser.read(64)

            time.sleep(POST_RX_DELAY)

    except Exception as e:
        print(f"ERGEBNIS: Serial-Fehler: {e}")
        return 10

    print("RX:", rx.hex(" ") if rx else "<timeout>")
    if tail:
        print("RX_TAIL_IGNORED:", tail.hex(" "))

    if not rx:
        print("ERGEBNIS: Keine Antwort.")
        return 2

    # Exception-Antwort ist immer 5 Byte lang:
    # slave, function|0x80, exception, crc_lo, crc_hi
    if len(rx) >= 5 and rx[1] & 0x80:
        exc_frame = rx[:5]
        if check_crc(exc_frame):
            print(f"ERGEBNIS: Modbus Exception Code {exc_frame[2]}")
            return 4
        print("ERGEBNIS: Exception-Frame mit falscher CRC.")
        return 3

    if len(rx) != expected_len:
        print(f"ERGEBNIS: Unerwartete Laenge: {len(rx)} statt {expected_len}")
        return 6

    if not check_crc(rx):
        print("ERGEBNIS: CRC falsch.")
        return 3

    if rx[0] != (SLAVE & 0xFF):
        print(f"ERGEBNIS: Antwort von unerwartetem Slave {rx[0]}")
        return 7

    if rx[1] != 0x03:
        print(f"ERGEBNIS: Unerwartete Function {rx[1]}")
        return 5

    values = decode_registers(rx)
    print("Registerwerte:", values)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
