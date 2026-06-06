from unittest.mock import patch, call

import piframe.rtc as rtc_mod


def test_sync_from_rtc_calls_hwclock():
    with patch("subprocess.run") as mock_run:
        rtc_mod.sync_from_rtc()
    mock_run.assert_called_once()
    args = mock_run.call_args[0][0]
    assert "hwclock" in args
    assert "--hctosys" in args


def test_sync_from_rtc_tolerates_error():
    with patch("subprocess.run", side_effect=FileNotFoundError("not found")):
        rtc_mod.sync_from_rtc()  # must not raise


def test_set_daily_wake_no_rtc():
    with patch("piframe.rtc._rtc_available", return_value=False):
        result = rtc_mod.set_daily_wake()
    assert result is False


def test_set_daily_wake_calls_rtcwake():
    with patch("piframe.rtc._rtc_available", return_value=True), \
         patch("subprocess.run") as mock_run:
        result = rtc_mod.set_daily_wake(hour=8)
    assert result is True
    args = mock_run.call_args[0][0]
    assert "rtcwake" in args
    assert "-m" in args
    assert "mem" in args


def test_set_daily_wake_tolerates_missing_binary():
    with patch("piframe.rtc._rtc_available", return_value=True), \
         patch("subprocess.run", side_effect=FileNotFoundError("not found")):
        result = rtc_mod.set_daily_wake()
    assert result is False
