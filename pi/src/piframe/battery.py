"""
INA219 battery monitor on I2C address 0x40.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

INA219_ADDR = 0x40
I2C_BUS = 1

# LiPo voltage range for SoC estimation
_VMIN = 3.0
_VMAX = 4.2


def read_battery() -> dict:
    """
    Read voltage and current from INA219.
    Returns dict with keys: voltage_v, current_ma, soc_pct.
    Returns empty dict on error (no battery connected, no I2C, etc.).
    """
    try:
        import smbus2
        bus = smbus2.SMBus(I2C_BUS)
        voltage_v = _read_bus_voltage(bus)
        current_ma = _read_current(bus)
        bus.close()
    except Exception as exc:
        logger.debug("INA219 read failed: %s", exc)
        return {}

    soc = max(0.0, min(100.0, (voltage_v - _VMIN) / (_VMAX - _VMIN) * 100))
    return {
        "voltage_v": round(voltage_v, 3),
        "current_ma": round(current_ma, 1),
        "soc_pct": round(soc, 1),
    }


# INA219 register addresses
_REG_BUS_VOLTAGE = 0x02
_REG_CURRENT = 0x04
_REG_CALIBRATION = 0x05

# Calibration for 0.1 Ω shunt, 3.2A max
_CALIBRATION_VALUE = 4096
_CURRENT_LSB = 0.0001  # 0.1 mA/bit


def _read_bus_voltage(bus) -> float:
    raw = bus.read_word_data(INA219_ADDR, _REG_BUS_VOLTAGE)
    # INA219 returns big-endian; swap bytes
    raw = ((raw & 0xFF) << 8) | ((raw >> 8) & 0xFF)
    return ((raw >> 3) * 4) / 1000.0  # 4 mV/bit


def _read_current(bus) -> float:
    # Write calibration first
    cal = _CALIBRATION_VALUE
    cal_be = ((cal & 0xFF) << 8) | ((cal >> 8) & 0xFF)
    bus.write_word_data(INA219_ADDR, _REG_CALIBRATION, cal_be)

    raw = bus.read_word_data(INA219_ADDR, _REG_CURRENT)
    raw = ((raw & 0xFF) << 8) | ((raw >> 8) & 0xFF)
    if raw > 0x7FFF:
        raw -= 0x10000
    return raw * _CURRENT_LSB * 1000  # convert to mA
