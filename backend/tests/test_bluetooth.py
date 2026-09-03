from types import SimpleNamespace
import subprocess
import threading
import time

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


def test_connect_serializes_attempts_across_callers(monkeypatch, tmp_path) -> None:
    state_lock = threading.Lock()
    first_entered = threading.Event()
    release_first = threading.Event()
    active = 0
    maximum_active = 0

    monkeypatch.setattr(bluetooth, "_connection_lock_path", lambda: tmp_path / "bluetooth-connect.lock")

    def fake_connect_unlocked(_mac, _retry_seconds):
        nonlocal active, maximum_active
        with state_lock:
            active += 1
            maximum_active = max(maximum_active, active)
            if not first_entered.is_set():
                first_entered.set()
        release_first.wait(timeout=1)
        with state_lock:
            active -= 1
        return {"status": "connected", "stdout": "", "stderr": ""}

    monkeypatch.setattr(bluetooth, "_connect_unlocked", fake_connect_unlocked)
    results = []
    threads = [
        threading.Thread(target=lambda: results.append(bluetooth.connect("AA:BB:CC:DD:EE:FF", retry_seconds=2)))
        for _ in range(2)
    ]
    threads[0].start()
    assert first_entered.wait(timeout=1)
    threads[1].start()
    time.sleep(0.05)
    release_first.set()
    for thread in threads:
        thread.join(timeout=2)

    assert len(results) == 2
    assert maximum_active == 1


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


def test_prepare_output_claims_sink_without_playing_audio(monkeypatch) -> None:
    connections = []
    defaults = []
    volumes = []

    monkeypatch.setattr(bluetooth, "is_connected", lambda _mac: False)
    monkeypatch.setattr(
        bluetooth,
        "connect",
        lambda mac, retry_seconds: connections.append((mac, retry_seconds))
        or {"status": "connected", "stdout": "claimed", "stderr": ""},
    )
    monkeypatch.setattr(bluetooth, "detect_sink", lambda _mac: "bluez_output.test")
    monkeypatch.setattr(bluetooth, "set_default_sink", defaults.append)
    monkeypatch.setattr(bluetooth, "set_sink_volume", lambda sink, volume: volumes.append((sink, volume)))

    result = playback.prepare_output(
        "AA:BB:CC:DD:EE:FF",
        timeout_seconds=30,
        sink_volume_percent=120,
    )

    assert result["status"] == "ready"
    assert connections == [("AA:BB:CC:DD:EE:FF", 30)]
    assert defaults == ["bluez_output.test"]
    assert volumes == [("bluez_output.test", 1.2)]


def test_prepare_output_reconnects_half_connected_device_without_sink(monkeypatch) -> None:
    clock = [0.0]
    state = {"connected": True, "sink_ready": False}
    disconnects = []
    connections = []

    monkeypatch.setattr(playback.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(playback.time, "sleep", lambda seconds: clock.__setitem__(0, clock[0] + seconds))
    monkeypatch.setattr(bluetooth, "is_connected", lambda _mac: state["connected"])
    monkeypatch.setattr(
        bluetooth,
        "detect_sink",
        lambda _mac: "bluez_output.test" if state["sink_ready"] else None,
    )

    def disconnect(mac):
        disconnects.append(mac)
        state["connected"] = False
        return {"status": "disconnected", "stdout": "", "stderr": ""}

    def connect(mac, retry_seconds):
        connections.append((mac, retry_seconds))
        state["connected"] = True
        state["sink_ready"] = True
        return {"status": "connected", "stdout": "reconnected", "stderr": ""}

    monkeypatch.setattr(bluetooth, "disconnect", disconnect)
    monkeypatch.setattr(bluetooth, "connect", connect)
    monkeypatch.setattr(bluetooth, "set_default_sink", lambda _sink: None)
    monkeypatch.setattr(bluetooth, "set_sink_volume", lambda _sink, _volume: None)

    result = playback.prepare_output(
        "AA:BB:CC:DD:EE:FF",
        timeout_seconds=10,
        sink_volume_percent=100,
    )

    assert result == {
        "status": "ready",
        "sink": "bluez_output.test",
        "connect": "reconnected",
    }
    assert disconnects == ["AA:BB:CC:DD:EE:FF"]
    assert connections == [("AA:BB:CC:DD:EE:FF", 7)]
