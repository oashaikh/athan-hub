from types import SimpleNamespace

import pytest

from athan_hub.core import bluetooth


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
