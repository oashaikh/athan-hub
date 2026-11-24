import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("camera_wifi", Path(__file__).parents[2] / "deploy/camera-wifi.py")
camera_wifi = importlib.util.module_from_spec(spec)
spec.loader.exec_module(camera_wifi)


def test_swap_ip_leaves_longer_addresses_alone():
    text = "rtsp://admin:x@192.168.1.5:554/a 192.168.1.56 http://192.168.1.5/ 10.192.168.1.5"
    assert camera_wifi.swap_ip(text, "192.168.1.5", "192.168.1.77") == (
        "rtsp://admin:x@192.168.1.77:554/a 192.168.1.56 http://192.168.1.77/ 10.192.168.1.5"
    )
