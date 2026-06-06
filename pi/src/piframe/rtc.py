"""
DS3231 RTC utilities: sync system clock and schedule wake alarms.
"""
import logging
import subprocess
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

RTC_DEVICE = "/dev/rtc0"


def sync_from_rtc() -> None:
    """Sync system clock from hardware RTC (DS3231)."""
    try:
        subprocess.run(["hwclock", "--hctosys", "--utc", "--verbose"], check=True)
        logger.info("System clock synced from RTC")
    except subprocess.CalledProcessError as exc:
        logger.warning("hwclock --hctosys failed: %s", exc)
    except FileNotFoundError:
        logger.warning("hwclock not found; skipping RTC sync")


def set_daily_wake(hour: int = 8, minute: int = 0) -> bool:
    """
    Set DS3231 alarm to wake the Pi at the next occurrence of hour:minute.
    Suspends the system to RAM via rtcwake.
    Returns True if the command was invoked, False if rtc0 is not available.
    """
    if not _rtc_available():
        logger.info("No RTC device at %s; skipping rtcwake", RTC_DEVICE)
        return False

    now = datetime.now()
    wake = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if wake <= now:
        wake += timedelta(days=1)

    unix_ts = int(wake.timestamp())
    logger.info("Scheduling wake at %s (unix %d)", wake.isoformat(), unix_ts)

    try:
        subprocess.run(
            ["rtcwake", "-d", RTC_DEVICE, "-m", "mem", "-t", str(unix_ts)],
            check=True,
        )
        return True
    except subprocess.CalledProcessError as exc:
        logger.warning("rtcwake failed: %s", exc)
        return False
    except FileNotFoundError:
        logger.warning("rtcwake not found; Pi will not suspend")
        return False


def _rtc_available() -> bool:
    import os
    return os.path.exists(RTC_DEVICE)
