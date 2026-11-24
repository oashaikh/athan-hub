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

Once the camera is on the network it is found by its Wi-Fi MAC address, and if the
router gave it a new address, Home Assistant, go2rtc and the talk service are moved
to it, so a new router needs no manual changes.
"""
import getpass
import json
import re
import hashlib
import ipaddress
import secrets
import socket
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

CAMERA = "10.68.68.22"
IFACE = "wlan0"
ENV_FILE = Path("/etc/athan-hub/athan-hub.env")
HA = Path("/var/lib/homeassistant")
# Every place that names the camera's address; core.config_entries holds the camera entities.
CAMERA_FILES = [ENV_FILE, HA / "go2rtc.yaml", HA / "packages/athan_hub_camera.yaml", HA / ".storage/core.config_entries"]


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
            found = re.search(r'"qrwifimac":"([0-9A-Fa-f:]{17})"', response.read().decode(errors="replace"))
        # getPlatformID only binds the camera; setupWifiInfo is what stores the Wi-Fi and
        # makes it leave setup mode. It takes the name and password as hex (firmware 05.02.31.112).
        wifi = urllib.parse.urlencode({
            "userid": "admin", "userkey": hashlib.md5(b"admin123").hexdigest(),
            "ssid_hex": ssid.encode().hex().upper(), "key_hex": key.encode().hex().upper(),
        })
        try:
            with urllib.request.urlopen(f"http://{CAMERA}/goform/setupWifiInfo?{wifi}", timeout=15) as response:
                answer = re.sub(r"<[^>]+>", "", response.read(300).decode(errors="replace")).strip()
        except OSError:
            answer = "no reply; it has left setup mode to join the Wi-Fi"
    finally:
        subprocess.run(["nmcli", "con", "down", hotspots[0]], capture_output=True)
        subprocess.run(["nmcli", "con", "delete", hotspots[0]], capture_output=True)
    sent = f"Sent {ssid} to camera {hotspots[0]} (it answered: {answer})."
    ip = locate(found.group(1)) if found else None
    if not ip:
        return f"{sent} It has not appeared on the network after 3 minutes; check the Wi-Fi password and try again."
    return f"{sent} {move_to(ip)}"


def locate(mac: str, wait: int = 180) -> str | None:
    """The camera's address on the home network, found by its Wi-Fi MAC."""
    route = subprocess.run(["ip", "-4", "-o", "route", "show", "default"], capture_output=True, text=True).stdout.split()
    lan = subprocess.run(["ip", "-4", "-o", "addr", "show", route[route.index("dev") + 1]], capture_output=True, text=True).stdout.split()
    network = ipaddress.ip_interface(lan[lan.index("inet") + 1]).network
    deadline = time.monotonic() + wait
    while time.monotonic() < deadline:
        # One datagram to every address fills the ARP table; nothing needs to answer.
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            for host in network.hosts():
                probe.sendto(b"", (str(host), 9))
                time.sleep(0.02)  # a burst of ARP requests gets dropped by the router
        time.sleep(3)
        for line in subprocess.run(["ip", "neigh"], capture_output=True, text=True).stdout.splitlines():
            if mac.lower() in line.lower() and "FAILED" not in line:
                return line.split()[0]
        time.sleep(5)
    return None


def swap_ip(text: str, old: str, new: str) -> str:
    """Replace one address with another, leaving longer ones (.5 in .56) alone."""
    return re.sub(rf"(?<![\d.]){re.escape(old)}(?![\d])", new, text)


def move_to(ip: str) -> str:
    env = ENV_FILE.read_text()
    old = re.search(r"^ATHAN_HA_CAMERA_IP=(.*)$", env, re.M)
    # A reset always puts the admin and video password back to the factory one.
    ENV_FILE.write_text(re.sub(r"^ATHAN_HA_CAMERA_ADMIN_PW=.*$", "ATHAN_HA_CAMERA_ADMIN_PW=admin123", env, flags=re.M))
    if not old or old.group(1) == ip:
        subprocess.run(["systemctl", "try-restart", "cam720-talk.service"])
        return f"It is on the network at {ip}, the same address as before, so Home Assistant needs no changes."
    # Home Assistant rewrites core.config_entries while it runs, so it is stopped for the edit.
    subprocess.run(["docker", "stop", "homeassistant"], capture_output=True)
    try:
        for path in CAMERA_FILES:
            if path.exists():
                path.write_text(swap_ip(path.read_text(), old.group(1), ip))
    finally:
        subprocess.run(["docker", "start", "homeassistant"], capture_output=True)
    subprocess.run(["systemctl", "try-restart", "cam720-talk.service"])
    for _ in range(60):  # back up before the notification is sent to it
        try:
            urllib.request.urlopen("http://127.0.0.1:8123/manifest.json", timeout=3)
            break
        except OSError:
            time.sleep(3)
    return f"It moved from {old.group(1)} to {ip}; Home Assistant, the video streams and two-way talk now use the new address."


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
