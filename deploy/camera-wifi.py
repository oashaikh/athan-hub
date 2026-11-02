#!/usr/bin/env python3
"""Put a CAM720 (Jooan) camera on Wi-Fi without the CAM720 app or its cloud.

After a reset the camera broadcasts an open "JA-..." hotspot and listens at
10.68.68.22. The CAM720 app joins that hotspot and sends the Wi-Fi details in one
HTTP request, signed with the factory login (admin / admin123). This script does
the same from this machine's own Wi-Fi adapter, so no phone is involved.

Run as root: sudo python3 /opt/athan-hub/deploy/camera-wifi.py "<Wi-Fi name>"  (asks for the password)
"""
import getpass
import hashlib
import secrets
import subprocess
import sys
import time
import urllib.parse
import urllib.request

CAMERA = "10.68.68.22"
IFACE = "wlan0"


def nmcli(*args: str) -> str:
    return subprocess.run(["nmcli", *args], capture_output=True, text=True, check=True).stdout


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__.strip().splitlines()[-1])
        return 2
    ssid, key = sys.argv[1], getpass.getpass(f"Password for {sys.argv[1]}: ")
    nmcli("dev", "wifi", "rescan", "ifname", IFACE)
    time.sleep(5)
    hotspots = [n for n in nmcli("-t", "-f", "SSID", "dev", "wifi", "list", "ifname", IFACE).splitlines() if n.startswith("JA")]
    if not hotspots:
        print("No JA-... hotspot found. Reset the camera (hold reset until it beeps) and keep it near this machine.")
        return 1
    print("Joining", hotspots[0])
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
            print("Camera answered:", response.read(300).decode(errors="replace"))
    finally:
        subprocess.run(["nmcli", "con", "down", hotspots[0]], capture_output=True)
        subprocess.run(["nmcli", "con", "delete", hotspots[0]], capture_output=True)
    print("The camera should now join", ssid, "within a minute. Find its new address in the router or Pi-hole.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
