from types import SimpleNamespace
import subprocess

import pytest

from athan_hub.core import bluetooth
from athan_hub.core import playback


def test_mac_validation() -> None:
    assert bluetooth.normalise_mac("aa:bb:cc:dd:ee:ff") == "AA:BB:CC:DD:EE:FF"
    with pytest.raises(bluetooth.BluetoothError, match="Invalid"):
        bluetooth.normalise_mac("not-a-mac")


def test_device_discovery(monkeypatch) -> None:
    def fake_run(args, **_kwargs):
        if args[-1] == "devices":
            return SimpleNamespace(returncode=0, stdout="Device AA:BB:CC:DD:EE:FF Living Room Speaker\n", stderr="")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(bluetooth.subprocess, "run", fake_run)
    assert bluetooth.discover(3) == [{"mac": "AA:BB:CC:DD:EE:FF", "name": "Living Room Speaker"}]


def test_bluetooth_command_uses_requested_timeout(monkeypatch) -> None:
    observed = {}

    def fake_run(args, **kwargs):
        observed["args"] = args
        observed["timeout"] = kwargs["timeout"]
        raise subprocess.TimeoutExpired(args, kwargs["timeout"])

    monkeypatch.setattr(bluetooth.subprocess, "run", fake_run)

    with pytest.raises(bluetooth.BluetoothError, match="timed out"):
        bluetooth._run(["bluetoothctl", "connect", "AA:BB:CC:DD:EE:FF"], timeout_seconds=4)

    assert observed == {
        "args": ["bluetoothctl", "connect", "AA:BB:CC:DD:EE:FF"],
        "timeout": 4,
    }


def test_connect_retries_after_one_command_timeout(monkeypatch) -> None:
    attempts = []

    monkeypatch.setattr(bluetooth, "is_connected", lambda _mac: False)
    monkeypatch.setattr(bluetooth, "detect_sink", lambda _mac: None)
    monkeypatch.setattr(bluetooth.time, "time", iter([0, 0, 1]).__next__)
    monkeypatch.setattr(bluetooth.time, "sleep", lambda _seconds: None)

    def fake_run(args, timeout_seconds=35):
        attempts.append(timeout_seconds)
        if len(attempts) == 1:
            raise bluetooth.BluetoothError("Bluetooth command timed out")
        return 0, "Connection successful", ""

    monkeypatch.setattr(bluetooth, "_run", fake_run)

    result = bluetooth.connect("AA:BB:CC:DD:EE:FF", retry_seconds=20)

    assert result["status"] == "connected"
    assert attempts == [8, 8]


def test_playback_keeps_speaker_connected_by_default(monkeypatch, tmp_path) -> None:
    audio_file = tmp_path / "athan.mp3"
    audio_file.write_bytes(b"ID3")
    disconnects = []

    monkeypatch.setattr(bluetooth, "is_connected", lambda _mac: True)
    monkeypatch.setattr(bluetooth, "detect_sink", lambda _mac: "bluez_output.test")
    monkeypatch.setattr(bluetooth, "set_default_sink", lambda _sink: None)
    monkeypatch.setattr(bluetooth, "set_sink_volume", lambda _sink, _volume: None)
    monkeypatch.setattr(bluetooth, "disconnect", lambda mac: disconnects.append(mac))
    monkeypatch.setattr(
        playback.subprocess,
        "run",
        lambda _args: SimpleNamespace(returncode=0),
    )

    result = playback.play_once("AA:BB:CC:DD:EE:FF", audio_file)

    assert result["status"] == "played"
    assert disconnects == []


def test_playback_waits_for_sink_without_reconnecting_connected_device(monkeypatch, tmp_path) -> None:
    audio_file = tmp_path / "athan.mp3"
    audio_file.write_bytes(b"ID3")
    sink_checks = iter([None, "bluez_output.test"])
    reconnects = []

    monkeypatch.setattr(bluetooth, "is_connected", lambda _mac: True)
    monkeypatch.setattr(bluetooth, "detect_sink", lambda _mac: next(sink_checks))
    monkeypatch.setattr(
        bluetooth,
        "connect",
        lambda mac, retry_seconds: reconnects.append((mac, retry_seconds))
        or {"status": "connected", "stdout": "", "stderr": ""},
    )
    monkeypatch.setattr(bluetooth, "set_default_sink", lambda _sink: None)
    monkeypatch.setattr(bluetooth, "set_sink_volume", lambda _sink, _volume: None)
    monkeypatch.setattr(playback.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(
        playback.subprocess,
        "run",
        lambda _args: SimpleNamespace(returncode=0),
    )

    result = playback.play_once(
        "AA:BB:CC:DD:EE:FF",
        audio_file,
        pre_connect_seconds=2,
    )

    assert result["status"] == "played"
    assert reconnects == []
