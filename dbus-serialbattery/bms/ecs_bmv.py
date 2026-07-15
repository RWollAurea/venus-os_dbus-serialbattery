#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import time

import serial

logger = logging.getLogger("ECS_BMV")

try:
    import dbus  # noqa: F401
except Exception:
    dbus = None

try:
    from battery import Battery as BasicBattery, Cell
except Exception:
    from basic_battery import BasicBattery, Cell


class EcsBmv(BasicBattery):
    """
    ECS LiPro1-6 Active V1.x + optional Victron BMV-712 composite driver.

    Current safe state:
      - ECS-only active
      - BMV reading disabled inside refresh_data()
      - Dummy current/SoC used until non-blocking BMV integration is added

    ECS protocol:
      RS485 Modbus RTU, 19200 baud, 8E1
      Slave addresses: 1..4
      Register 7  = cell voltage in mV
      Register 8  = temperature raw, degC = raw / 10 - 60
      Register 13 = status
      Register 14 = LVP state
      Register 15 = OVP state

    The driver reads registers 7..15 in one Modbus request per slave. The
    serial port is opened only once for a complete four-slave snapshot.
    """

    BATTERYTYPE = "ECS LiPro1-6 Active + BMV-712"

    ECS_BAUDRATE = 19200
    ECS_SLAVES = [1, 2, 3, 4]

    REG_CELL_VOLTAGE = 7
    REG_TEMP_RAW = 8
    REG_STATUS = 13
    REG_LVP = 14
    REG_OVP = 15

    REG_BLOCK_START = 7
    REG_BLOCK_COUNT = 9

    SERIAL_TIMEOUT = 1.0
    BUS_SETTLE_DELAY = 0.30
    POST_TX_DELAY = 0.10
    INTER_SLAVE_DELAY = 1.0

    MAX_FAILED_REFRESH_CYCLES = 3

    MIN_CELL_MV = 2000
    MAX_CELL_MV = 4500
    MIN_TEMPERATURE_C = -50.0
    MAX_TEMPERATURE_C = 120.0

    DEFAULT_CAPACITY_AH = 130
    DEFAULT_CHARGE_CURRENT_A = 65
    DEFAULT_DISCHARGE_CURRENT_A = 130

    BMV_SERVICE = "com.victronenergy.battery.ttyO2"

    def __init__(self, port, baud=ECS_BAUDRATE, address=None):
        logger.info(
            "ECS_BMV: __init__ port=%s baud=%s address=%s",
            port,
            baud,
            address,
        )

        try:
            super().__init__(port, baud, address)
        except TypeError:
            try:
                super().__init__(port, baud)
            except TypeError:
                super().__init__()

        self.port = port
        self.baud_rate = self.ECS_BAUDRATE
        self.address = address
        self.poll_interval = 5000

        self.type = self.BATTERYTYPE
        self.hardware_version = "ECS LiPro1-6 Active V1.x"
        self.version = "0.3-ecs-block-safe"

        self.capacity = self.DEFAULT_CAPACITY_AH
        self.max_battery_charge_current = self.DEFAULT_CHARGE_CURRENT_A
        self.max_battery_discharge_current = self.DEFAULT_DISCHARGE_CURRENT_A

        self.failed_refresh_cycles = 0
        self.ecs_last_ok = False

        self.ecs_cells_mv = {}
        self.ecs_temps_c = {}
        self.ecs_status = {}
        self.ecs_lvp = {}
        self.ecs_ovp = {}

        self.cell_count = len(self.ECS_SLAVES)
        self.cells = []

        self.capacity_remain = 65.0
        self.cycles = 0
        self.power = 0.0
        self.installed_capacity = self.DEFAULT_CAPACITY_AH
        self.total_ah_drawn = 0.0

        self.soc_calc = 50.0
        self.current_avg = 0.0
        self.time_to_soc_update = 0

        self.time_to_go = 0
        self.consumed_ah = 0.0

        for _ in self.ECS_SLAVES:
            try:
                cell = Cell(False)
            except TypeError:
                cell = Cell()
            cell.voltage = 3.3
            cell.balance = False
            self.cells.append(cell)

        # Mandatory values are initialised immediately so that the base class
        # never receives None during D-Bus setup or internal calculations.
        self.voltage = 13.3
        self.current = 0.0
        self.soc = 50.0

        self.temperature = 25.0
        self.temperature_1 = 25.0
        self.temperature_2 = 25.0
        self.temperature_3 = 25.0
        self.temperature_4 = 25.0
        self.temp1 = 25.0
        self.temp2 = 25.0

        self.cell_min_voltage = 3.3
        self.cell_max_voltage = 3.3
        self.cell_min_no = 0
        self.cell_max_no = 0

        self.charge_fet = True
        self.discharge_fet = True
        self.balance_fet = None

        self.unique_identifier_tmp = "ECSLiPro16ActiveV1x_130Ah"

    def get_settings(self):
        logger.info("ECS_BMV: get_settings")
        return True

    @staticmethod
    def crc16_modbus(data):
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 1:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        return crc & 0xFFFF

    @classmethod
    def build_request(cls, slave, register, count=1):
        frame = bytes(
            [
                slave & 0xFF,
                0x03,
                (register >> 8) & 0xFF,
                register & 0xFF,
                (count >> 8) & 0xFF,
                count & 0xFF,
            ]
        )
        crc = cls.crc16_modbus(frame)
        return frame + bytes([crc & 0xFF, (crc >> 8) & 0xFF])

    @classmethod
    def check_crc(cls, frame):
        if len(frame) < 5:
            return False
        body = frame[:-2]
        received_crc = frame[-2] | (frame[-1] << 8)
        return cls.crc16_modbus(body) == received_crc

    @staticmethod
    def _read_exact(ser, length):
        """Read up to length bytes, stopping when the serial timeout expires."""
        data = bytearray()

        while len(data) < length:
            chunk = ser.read(length - len(data))
            if not chunk:
                break
            data.extend(chunk)

        return bytes(data)

    def read_ecs_block_once(self, ser, slave):
        """
        Read registers 7 through 15 in one Modbus RTU request.

        Returned register indexes:
          0 = register 7  cell voltage
          1 = register 8  temperature
          6 = register 13 status
          7 = register 14 LVP
          8 = register 15 OVP
        """
        request = self.build_request(
            slave,
            self.REG_BLOCK_START,
            self.REG_BLOCK_COUNT,
        )

        ser.reset_input_buffer()
        ser.write(request)
        ser.flush()
        time.sleep(self.POST_TX_DELAY)

        header = self._read_exact(ser, 3)

        if len(header) != 3:
            raise IOError(
                "timeout/incomplete header slave=%s rx=%s"
                % (slave, header.hex(" "))
            )

        if header[0] != (slave & 0xFF):
            raise IOError(
                "unexpected slave %s expected %s" % (header[0], slave)
            )

        # Modbus exception response:
        # slave, function|0x80, exception code, CRC low, CRC high
        if header[1] & 0x80:
            crc_bytes = self._read_exact(ser, 2)
            frame = header + crc_bytes

            if len(frame) != 5:
                raise IOError(
                    "incomplete exception frame slave=%s rx=%s"
                    % (slave, frame.hex(" "))
                )

            if not self.check_crc(frame):
                raise IOError(
                    "modbus exception with bad crc rx=%s" % frame.hex(" ")
                )

            raise IOError("modbus exception code %s" % header[2])

        if header[1] != 0x03:
            raise IOError("unexpected function %s" % header[1])

        expected_byte_count = self.REG_BLOCK_COUNT * 2
        byte_count = header[2]

        if byte_count != expected_byte_count:
            raise IOError(
                "unexpected byte count %s expected %s"
                % (byte_count, expected_byte_count)
            )

        body_and_crc = self._read_exact(ser, byte_count + 2)
        frame = header + body_and_crc
        expected_length = 3 + byte_count + 2

        if len(frame) != expected_length:
            raise IOError(
                "unexpected length %s expected %s rx=%s"
                % (len(frame), expected_length, frame.hex(" "))
            )

        if not self.check_crc(frame):
            raise IOError("bad crc rx=%s" % frame.hex(" "))

        payload = frame[3 : 3 + byte_count]
        values = []
        for index in range(0, len(payload), 2):
            values.append((payload[index] << 8) | payload[index + 1])

        if len(values) != self.REG_BLOCK_COUNT:
            raise IOError(
                "decoded register count %s expected %s"
                % (len(values), self.REG_BLOCK_COUNT)
            )

        cell_mv = values[0]
        temperature_c = (values[1] / 10.0) - 60.0

        if not (self.MIN_CELL_MV <= cell_mv <= self.MAX_CELL_MV):
            raise IOError(
                "implausible cell voltage slave=%s mv=%s" % (slave, cell_mv)
            )

        if not (
            self.MIN_TEMPERATURE_C
            <= temperature_c
            <= self.MAX_TEMPERATURE_C
        ):
            raise IOError(
                "implausible temperature slave=%s temp=%s"
                % (slave, temperature_c)
            )

        logger.debug(
            "ECS_BMV: block read ok slave=%s values=%s",
            slave,
            values,
        )

        return {
            "cell_mv": cell_mv,
            "temperature_c": temperature_c,
            "status": values[6],
            "lvp": values[7],
            "ovp": values[8],
        }

    def read_all_ecs(self):
        """
        Read all four LiPro modules through one serial connection.

        Only a complete snapshot containing all configured slaves is committed.
        A partial snapshot is rejected so stale and fresh cell values cannot be
        mixed into one battery state.
        """
        new_cells_mv = {}
        new_temps_c = {}
        new_status = {}
        new_lvp = {}
        new_ovp = {}

        ok_count = 0

        try:
            with serial.Serial(
                port=self.port,
                baudrate=self.ECS_BAUDRATE,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_EVEN,
                stopbits=serial.STOPBITS_ONE,
                timeout=self.SERIAL_TIMEOUT,
                write_timeout=self.SERIAL_TIMEOUT,
            ) as ser:
                ser.reset_input_buffer()
                ser.reset_output_buffer()
                time.sleep(self.BUS_SETTLE_DELAY)

                for index, slave in enumerate(self.ECS_SLAVES):
                    try:
                        data = self.read_ecs_block_once(ser, slave)
                    except Exception as error:
                        logger.warning(
                            "ECS_BMV: block read failed slave=%s error=%s",
                            slave,
                            error,
                        )
                    else:
                        ok_count += 1
                        new_cells_mv[slave] = data["cell_mv"]
                        new_temps_c[slave] = data["temperature_c"]
                        new_status[slave] = data["status"]
                        new_lvp[slave] = data["lvp"]
                        new_ovp[slave] = data["ovp"]

                    if index < len(self.ECS_SLAVES) - 1:
                        time.sleep(self.INTER_SLAVE_DELAY)

        except Exception as error:
            logger.error(
                "ECS_BMV: cannot open or use serial port %s: %s",
                self.port,
                error,
            )

        expected_count = len(self.ECS_SLAVES)

        if ok_count == expected_count:
            self.ecs_cells_mv = new_cells_mv
            self.ecs_temps_c = new_temps_c
            self.ecs_status = new_status
            self.ecs_lvp = new_lvp
            self.ecs_ovp = new_ovp

            self.ecs_last_ok = True
            self.failed_refresh_cycles = 0

            logger.debug(
                "ECS_BMV: complete ECS snapshot cells=%s temps=%s lvp=%s ovp=%s",
                self.ecs_cells_mv,
                self.ecs_temps_c,
                self.ecs_lvp,
                self.ecs_ovp,
            )
        else:
            self.ecs_last_ok = False
            self.failed_refresh_cycles += 1

            logger.error(
                "ECS_BMV: incomplete ECS snapshot ok=%s/%s failed_cycles=%s",
                ok_count,
                expected_count,
                self.failed_refresh_cycles,
            )

        return ok_count

    def test_connection(self):
        logger.info("ECS_BMV: test_connection start port=%s", self.port)

        ok_count = self.read_all_ecs()

        if ok_count != len(self.ECS_SLAVES):
            logger.error(
                "ECS_BMV: test_connection failed, only %s/%s ECS slaves readable",
                ok_count,
                len(self.ECS_SLAVES),
            )
            return False

        self.update_values_from_ecs()

        logger.info(
            "ECS_BMV: test_connection ok slaves=%s voltage=%s cell_min=%s cell_max=%s",
            ok_count,
            self.voltage,
            self.cell_min_voltage,
            self.cell_max_voltage,
        )

        return True

    def update_values_from_ecs(self):
        if self.ecs_cells_mv:
            sorted_slaves = sorted(self.ecs_cells_mv.keys())
            pack_voltage = sum(self.ecs_cells_mv.values()) / 1000.0

            self.voltage = float(pack_voltage)

            for index in range(len(self.cells)):
                if index < len(sorted_slaves):
                    slave = sorted_slaves[index]
                    self.cells[index].voltage = (
                        self.ecs_cells_mv[slave] / 1000.0
                    )
                else:
                    self.cells[index].voltage = self.voltage / float(
                        self.cell_count
                    )

            min_slave = min(self.ecs_cells_mv, key=self.ecs_cells_mv.get)
            max_slave = max(self.ecs_cells_mv, key=self.ecs_cells_mv.get)

            min_mv = self.ecs_cells_mv[min_slave]
            max_mv = self.ecs_cells_mv[max_slave]

            self.cell_min_voltage = min_mv / 1000.0
            self.cell_max_voltage = max_mv / 1000.0

            try:
                self.cell_min_no = self.ECS_SLAVES.index(min_slave)
                self.cell_max_no = self.ECS_SLAVES.index(max_slave)
            except ValueError:
                self.cell_min_no = 0
                self.cell_max_no = 0

        for cell in self.cells:
            if getattr(cell, "voltage", None) is None:
                cell.voltage = self.voltage / float(self.cell_count)
            if getattr(cell, "balance", None) is None:
                cell.balance = False

        if self.ecs_temps_c:
            temperature = max(self.ecs_temps_c.values())
        else:
            temperature = 25.0

        self.temperature = float(temperature)
        self.temperature_1 = float(temperature)
        self.temperature_2 = float(temperature)
        self.temp1 = float(temperature)
        self.temp2 = float(temperature)

        if self.voltage is None:
            self.voltage = 13.3
        if self.current is None:
            self.current = 0.0
        if self.soc is None:
            self.soc = 50.0

        if getattr(self, "soc_calc", None) is None:
            self.soc_calc = self.soc

        if getattr(self, "current_avg", None) is None:
            self.current_avg = self.current

    def refresh_data(self):
        try:
            logger.debug("ECS_BMV: refresh_data start")

            ecs_ok_count = self.read_all_ecs()

            # BMV deliberately disabled here. Synchronous D-Bus reads inside
            # refresh_data previously blocked this battery service.
            bmv_ok = False

            self.update_values_from_ecs()

            # Stable placeholders until a non-blocking BMV cache is added.
            self.current = 0.0
            self.soc = 50.0
            self.soc_calc = self.soc
            self.current_avg = self.current

            self.capacity_remain = self.capacity * self.soc / 100.0
            self.power = self.voltage * self.current
            self.time_to_go = 0
            self.consumed_ah = self.capacity - self.capacity_remain

            lvp_active = any(value != 0 for value in self.ecs_lvp.values())
            ovp_active = any(value != 0 for value in self.ecs_ovp.values())
            communication_lost = not self.ecs_last_ok

            if communication_lost:
                logger.error(
                    "ECS_BMV: ECS communication incomplete, charge and discharge disabled"
                )
                self.max_battery_charge_current = 0
                self.max_battery_discharge_current = 0
                self.charge_fet = False
                self.discharge_fet = False
            else:
                self.charge_fet = not ovp_active
                self.discharge_fet = not lvp_active

                self.max_battery_charge_current = (
                    0 if ovp_active else self.DEFAULT_CHARGE_CURRENT_A
                )
                self.max_battery_discharge_current = (
                    0 if lvp_active else self.DEFAULT_DISCHARGE_CURRENT_A
                )

            logger.debug(
                "ECS_BMV: refresh_data done ecs_ok=%s bmv_ok=%s V=%s I=%s SoC=%s "
                "cell_min=%s cell_max=%s temp=%s ccl=%s dcl=%s",
                ecs_ok_count,
                bmv_ok,
                self.voltage,
                self.current,
                self.soc,
                self.cell_min_voltage,
                self.cell_max_voltage,
                self.temperature,
                self.max_battery_charge_current,
                self.max_battery_discharge_current,
            )

            return True

        except Exception as error:
            logger.exception("ECS_BMV: refresh_data exception: %s", error)

            # Fail-safe values: never let required attributes fall back to None.
            self.voltage = self.voltage if self.voltage is not None else 13.3
            self.current = self.current if self.current is not None else 0.0
            self.soc = self.soc if self.soc is not None else 50.0
            self.soc_calc = (
                self.soc_calc
                if getattr(self, "soc_calc", None) is not None
                else self.soc
            )
            self.current_avg = (
                self.current_avg
                if getattr(self, "current_avg", None) is not None
                else self.current
            )
            self.temperature = (
                self.temperature if self.temperature is not None else 25.0
            )
            self.temperature_1 = (
                self.temperature_1
                if self.temperature_1 is not None
                else 25.0
            )
            self.temperature_2 = (
                self.temperature_2
                if self.temperature_2 is not None
                else 25.0
            )
            self.temp1 = self.temp1 if self.temp1 is not None else 25.0
            self.temp2 = self.temp2 if self.temp2 is not None else 25.0
            self.cell_min_voltage = (
                self.cell_min_voltage
                if self.cell_min_voltage is not None
                else 3.3
            )
            self.cell_max_voltage = (
                self.cell_max_voltage
                if self.cell_max_voltage is not None
                else 3.3
            )
            self.cell_min_no = (
                self.cell_min_no if self.cell_min_no is not None else 0
            )
            self.cell_max_no = (
                self.cell_max_no if self.cell_max_no is not None else 0
            )

            self.ecs_last_ok = False
            self.max_battery_charge_current = 0
            self.max_battery_discharge_current = 0
            self.charge_fet = False
            self.discharge_fet = False

            return False