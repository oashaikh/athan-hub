#!/usr/bin/env python3
"""Put a CAM720 (Jooan) camera on Wi-Fi without the CAM720 app or its cloud.

After a reset the camera broadcasts an open "JA-..." hotspot and listens at
10.68.68.22. The CAM720 app joins that hotspot and sends the Wi-Fi details in one
HTTP request, signed with the factory login (admin / admin123). This script does
the same from this machine's own Wi-Fi adapter, so no phone is involved.

Run as root: sudo camera-wifi "<Wi-Fi name>"  (asks for the password)
Home Assistant's "Camera Wi-Fi setup" script writes a request file instead, which
camera-wifi.path hands to `camera-wifi --request <file>`; the result is shown as a
Home Assistant notification.
"""
import getpass
import json
import hashlib
import secrets
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

CAMERA = "10.68.68.22"
IFACE = "wlan0"
ENV_FILE = Path("/etc/athan-hub/athan-hub.env")


def nmcli(*args: str) -> str:
    return subprocess.run(["nmcli", *args], capture_output=True, text=True, check=True).stdout


def notify(message: str) -> None:
    token = next((line.split("=", 1)[1] for line in ENV_FILE.read_text().splitlines() if line.startswith("ATHAN_HA_TOKEN=")), "")
    if token:
        urllib.request.urlopen(urllib.request.Request(
            "http://127.0.0.1:8123/api/services/persistent_notification/create", method="POST",
            data=json.dumps({"title": "Camera Wi-Fi setup", "message": message}).encode(),
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}), timeout=10)


def setup(ssid: str, key: str) -> str:
    nmcli("dev", "wifi", "rescan", "ifname", IFACE)
    time.sleep(5)
    hotspots = [n for n in nmcli("-t", "-f", "SSID", "dev", "wifi", "list", "ifname", IFACE).splitlines() if n.startswith("JA")]
    if not hotspots:
        return "No camera hotspot (JA-...) found. Reset the camera (hold reset until it beeps), wait a minute and try again."
    nmcli("dev", "wifi", "connect", hotspots[0], "ifname", IFACE)
    try:
        query = urllib.parse.urlencode({
            "id2_id": "", "tutkid": "",
            "ssid_hex": ssid.encode().hex(), "key_hex": key.encode().hex(),
            # The app sends cloud binding values here; the camera never reaches the cloud, so random ones do.
            "user_id": secrets.token_hex(16), "token": secrets.token_hex(16).upper(),
            "regionid": "0", "devdomin": "7", "key": key, "language": "en_US", "region": "US", "ssid": ssid,
            "userid": "admin", "userkey": hashlib.md5(b"admin123").hexdigest(),
        })
        with urllib.request.urlopen(f"http://{CAMERA}/goform/getPlatformID?{query}", timeout=15) as response:
            answer = response.read(300).decode(errors="replace")
    finally:
        subprocess.run(["nmcli", "con", "down", hotspots[0]], capture_output=True)
        subprocess.run(["nmcli", "con", "delete", hotspots[0]], capture_output=True)
    return f"Sent {ssid} to camera {hotspots[0]} (it answered: {answer}). It should join within a minute. Its password is back to the factory one, so update it in Home Assistant."


def main() -> int:
    if sys.argv[1:2] == ["--request"] and len(sys.argv) == 3:
        request = Path(sys.argv[2])
        if not request.exists():
            return 0
        ssid, key = request.read_text().split("\n")[:2]
        request.unlink()
        try:
            message = setup(ssid, key)
        except Exception as exc:  # report every failure on the dashboard
            message = f"Failed: {exc}"
        print(message)
        notify(message)
        return 0
    if len(sys.argv) != 2:
        print(__doc__.strip().splitlines()[-4])
        return 2
    print(setup(sys.argv[1], getpass.getpass(f"Password for {sys.argv[1]}: ")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
