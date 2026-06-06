"""
Inject hardware stubs before any piframe module imports so tests
run on any platform without SPI/GPIO/I2C hardware.
"""
import sys
from unittest.mock import MagicMock

# Stub out hardware dependencies at the module level
_spidev = MagicMock()
_gpiozero = MagicMock()
_smbus2 = MagicMock()
_RPi = MagicMock()

sys.modules.setdefault("spidev", _spidev)
sys.modules.setdefault("gpiozero", _gpiozero)
sys.modules.setdefault("smbus2", _smbus2)
sys.modules.setdefault("RPi", _RPi)
sys.modules.setdefault("RPi.GPIO", _RPi.GPIO)

# epdconfig auto-detects the platform at import time via subprocess + /proc/cpuinfo.
# Patch it out so it doesn't try to open SPI devices.
import subprocess as _subprocess_real
_original_popen = _subprocess_real.Popen


def _mock_popen(cmd, *args, **kwargs):
    if "cpuinfo" in str(cmd):
        mock = MagicMock()
        mock.communicate.return_value = ("", "")
        return mock
    return _original_popen(cmd, *args, **kwargs)


import unittest.mock as _mock
_mock.patch("subprocess.Popen", side_effect=_mock_popen).start()
