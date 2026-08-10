import shlex
import subprocess
import time
import re
from typing import Dict, Optional, Tuple


class BluetoothError(Exception):
    pass


def _run(args: list[str]) -> Tuple[int, str, str]:
    try:
        proc = subprocess.run(args, capture_output=True, text=True, timeout=35)
    except subprocess.TimeoutExpired as exc:
        raise BluetoothError(f"Bluetooth command timed out: {shlex.join(args)}") from exc
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def normalise_mac(mac: str) -> str:
    value = mac.strip().upper()
    if not re.fullmatch(r"(?:[0-9A-F]{2}:){5}[0-9A-F]{2}", value):
        raise BluetoothError("Invalid Bluetooth MAC address")
    return value


def sink_name_for_mac(mac: str) -> str:
    return normalise_mac(mac).replace(":", "_")


def discover(timeout_seconds: int = 8) -> list[Dict[str, str]]:
    _run(["bluetoothctl", "power", "on"])
    try:
        subprocess.run(
            ["bluetoothctl", "--timeout", str(max(3, min(timeout_seconds, 30))), "scan", "on"],
            capture_output=True,
            text=True,
            timeout=max(8, timeout_seconds + 5),
        )
    except subprocess.TimeoutExpired:
        pass
    code, out, err = _run(["bluetoothctl", "devices"])
    if code != 0:
        raise BluetoothError(f"Bluetooth scan failed: {err or out}")
    devices: list[Dict[str, str]] = []
    for line in out.splitlines():
        match = re.match(r"^Device\s+((?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2})(?:\s+(.*))?$", line.strip())
        if match:
            devices.append({"mac": match.group(1).upper(), "name": (match.group(2) or "Unknown device").strip()})
    return devices


def pair(mac: str) -> Dict[str, str]:
    mac = normalise_mac(mac)
    _run(["bluetoothctl", "power", "on"])
    if not is_paired(mac):
        code, out, err = _run(["bluetoothctl", "--agent", "NoInputNoOutput", "--timeout", "45", "pair", mac])
        if code != 0 and not is_paired(mac):
            raise BluetoothError(f"Pairing failed for {mac}: {err or out}")
    code, out, err = _run(["bluetoothctl", "trust", mac])
    if code != 0:
        raise BluetoothError(f"Could not trust {mac}: {err or out}")
    result = connect(mac, retry_seconds=25)
    return {"status": result["status"], "mac": mac, "stdout": result.get("stdout", ""), "stderr": result.get("stderr", "")}


def is_paired(mac: str) -> bool:
    code, out, _ = _run(["bluetoothctl", "info", normalise_mac(mac)])
    return code == 0 and "paired: yes" in out.lower()


def connect(mac: str, retry_seconds: int = 20) -> Dict[str, str]:
    mac = normalise_mac(mac)
    if is_connected(mac) and detect_sink(mac):
        return {"status": "connected", "stdout": "already connected", "stderr": ""}
    deadline = time.time() + retry_seconds
    last_error = ""
    while time.time() < deadline:
        code, out, err = _run(["bluetoothctl", "connect", mac])
        if code == 0 or "connection successful" in out.lower():
            return {"status": "connected", "stdout": out, "stderr": err}
        err_l = (err or "").lower()
        if "br-connection-busy" in err_l or "in progress" in err_l or "already connected" in out.lower():
            if is_connected(mac) or detect_sink(mac):
                return {"status": "connected", "stdout": out, "stderr": err}
        last_error = err or out
        time.sleep(2)
    if is_connected(mac) or detect_sink(mac):
        return {"status": "connected", "stdout": "connected after retries", "stderr": last_error}
    raise BluetoothError(f"Failed to connect to {mac}: {last_error}")


def disconnect(mac: str) -> Dict[str, str]:
    mac = normalise_mac(mac)
    code, out, err = _run(["bluetoothctl", "disconnect", mac])
    if code != 0 and "not connected" not in (out + err).lower():
        raise BluetoothError(f"Disconnect failed: {err or out}")
    return {"status": "disconnected", "stdout": out, "stderr": err}


def is_connected(mac: str) -> bool:
    code, out, _ = _run(["bluetoothctl", "info", normalise_mac(mac)])
    return code == 0 and "connected: yes" in out.lower()


def detect_sink(mac: str) -> Optional[str]:
    sink_prefix = f"bluez_output.{sink_name_for_mac(mac)}"
    code, out, _ = _run(["pactl", "list", "short", "sinks"])
    if code != 0:
        return None
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2 and parts[1].startswith(sink_prefix):
            return parts[1]
    return None


def set_default_sink(sink: str) -> None:
    code, out, err = _run(["pactl", "set-default-sink", sink])
    if code != 0:
        raise BluetoothError(f"Failed to set default sink: {err or out}")


def set_sink_volume(sink: str, volume: float = 1.0) -> None:
    percent = max(0, min(int(volume * 100), 150))
    code, out, err = _run(["pactl", "set-sink-volume", sink, f"{percent}%"])
    if code != 0:
        raise BluetoothError(f"Failed to set sink volume: {err or out}")


def status(mac: str) -> Dict[str, Optional[str] | bool]:
    sink = detect_sink(mac)
    return {"connected": is_connected(mac), "sink": sink}
