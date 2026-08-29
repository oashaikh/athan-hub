import logging
import math
import subprocess
import time
from pathlib import Path
from typing import Any, Dict

from . import bluetooth


class PlaybackError(Exception):
    pass


def prepare_output(
    mac: str,
    timeout_seconds: int = 30,
    sink_volume_percent: int = 100,
    connect_retry_seconds: int | None = None,
) -> Dict[str, Any]:
    timeout_seconds = max(1, int(timeout_seconds))
    deadline = time.monotonic() + timeout_seconds
    if bluetooth.is_connected(mac):
        connect_result = {"status": "already connected", "stdout": "", "stderr": ""}
    else:
        remaining = max(1, math.ceil(deadline - time.monotonic()))
        retry_seconds = min(remaining, connect_retry_seconds or remaining)
        connect_result = bluetooth.connect(mac, retry_seconds=retry_seconds)

    sink_name = None
    while time.monotonic() < deadline:
        sink_name = bluetooth.detect_sink(mac)
        if sink_name:
            break
        time.sleep(min(1, max(0, deadline - time.monotonic())))
    if not sink_name:
        raise PlaybackError("Bluetooth sink not detected")

    bluetooth.set_default_sink(sink_name)
    try:
        bluetooth.set_sink_volume(sink_name, sink_volume_percent / 100.0)
    except Exception as exc:
        logging.getLogger(__name__).warning("Failed to set sink volume: %s", exc)
    return {
        "status": "ready",
        "sink": sink_name,
        "connect": connect_result.get("stdout", ""),
    }


def play_once(
    mac: str,
    audio_file: Path,
    pre_connect_seconds: int = 30,
    connect_retry_seconds: int = 20,
    disconnect_after_play: bool = False,
    sink_volume_percent: int = 100,
) -> Dict[str, Any]:
    if not audio_file.exists():
        raise PlaybackError(f"Audio file not found: {audio_file}")
    output = prepare_output(
        mac,
        timeout_seconds=connect_retry_seconds + pre_connect_seconds,
        sink_volume_percent=sink_volume_percent,
        connect_retry_seconds=connect_retry_seconds,
    )
    proc = subprocess.run(["mpg123", "-q", str(audio_file)])
    if proc.returncode != 0:
        raise PlaybackError("mpg123 playback failed")
    if disconnect_after_play:
        bluetooth.disconnect(mac)
    return {"status": "played", "sink": output["sink"], "connect": output["connect"]}


def stop_playback() -> Dict[str, Any]:
    kill = subprocess.run(["pkill", "-f", "mpg123"], capture_output=True, text=True)
    if kill.returncode == 0:
        return {"code": 0, "stdout": "stopped via pkill", "stderr": ""}
    ps = subprocess.run(["pgrep", "-f", "mpg123"], capture_output=True, text=True)
    pids = [pid for pid in ps.stdout.strip().splitlines() if pid] if ps.stdout else []
    for pid in pids:
        subprocess.run(["kill", "-9", pid])
    if pids:
        return {"code": 0, "stdout": f"killed {','.join(pids)}", "stderr": ""}
    return {"code": kill.returncode, "stdout": ps.stdout.strip(), "stderr": kill.stderr.strip()}
