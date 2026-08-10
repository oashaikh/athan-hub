import logging
import threading
from pathlib import Path
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from ..core import bluetooth, playback
from ..db import models


DEFAULTS = {
    "pre_connect_seconds": 10,
    "connect_retry_seconds": 20,
    "grace_seconds": 120,
    "disconnect_after_play": 0,
    "sink_volume_percent": 140,
}

_playback_thread: Optional[threading.Thread] = None
_playback_lock = threading.Lock()


def _get_setting(db: Session, key: str, default: Optional[Any] = None) -> Any:
    row = db.get(models.Setting, key)
    return row.value if row else default


def _get_int(db: Session, key: str, default: int) -> int:
    try:
        value = _get_setting(db, key)
        return int(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _get_bool(db: Session, key: str, default: bool = False) -> bool:
    value = _get_setting(db, key)
    return default if value is None else str(value) in ["1", "true", "True", "yes", "on"]


def set_echo_mac(db: Session, mac: str) -> str:
    mac = bluetooth.normalise_mac(mac)
    db.merge(models.Setting(key="echo_mac", value=mac))
    db.commit()
    return mac


def get_echo_mac(db: Session) -> str:
    return str(_get_setting(db, "echo_mac", ""))


def status(db: Session) -> Dict[str, Any]:
    mac = get_echo_mac(db)
    if not mac:
        return {"connected": False, "sink": None, "sink_label": None, "mac": None, "error": "MAC not set"}
    value = bluetooth.status(mac)
    sink = value.get("sink")
    return {"connected": value.get("connected"), "sink": sink, "sink_label": "Echo speaker" if sink else None, "mac": mac}


def connect_device(db: Session) -> Dict[str, Any]:
    mac = get_echo_mac(db)
    if not mac:
        raise ValueError("MAC not set")
    return {"mac": mac, **bluetooth.connect(mac, retry_seconds=_get_int(db, "connect_retry_seconds", DEFAULTS["connect_retry_seconds"]))}


def discover_devices() -> list[Dict[str, str]]:
    return bluetooth.discover()


def pair_device(db: Session, mac: str) -> Dict[str, Any]:
    result = bluetooth.pair(mac)
    set_echo_mac(db, mac)
    return result


def disconnect_device(db: Session) -> Dict[str, Any]:
    mac = get_echo_mac(db)
    if not mac:
        raise ValueError("MAC not set")
    return bluetooth.disconnect(mac)


def test_play(db: Session, audio_file: Path) -> Dict[str, Any]:
    mac = get_echo_mac(db)
    if not mac:
        raise ValueError("MAC not set")
    args = {
        "pre_connect_seconds": _get_int(db, "pre_connect_seconds", DEFAULTS["pre_connect_seconds"]),
        "connect_retry_seconds": _get_int(db, "connect_retry_seconds", DEFAULTS["connect_retry_seconds"]),
        "disconnect_after_play": _get_bool(db, "disconnect_after_play", False),
        "sink_volume_percent": _get_int(db, "sink_volume_percent", 140),
    }

    def worker() -> None:
        try:
            playback.play_once(mac, audio_file, **args)
        except Exception:
            logging.exception("Async test play failed")

    global _playback_thread
    with _playback_lock:
        if _playback_thread and _playback_thread.is_alive():
            playback.stop_playback()
            _playback_thread.join(timeout=2)
        _playback_thread = threading.Thread(target=worker, daemon=True)
        _playback_thread.start()
    return {"status": "started"}


def stop_test() -> Dict[str, Any]:
    global _playback_thread
    result = playback.stop_playback()
    with _playback_lock:
        if _playback_thread and _playback_thread.is_alive():
            _playback_thread.join(timeout=2)
        _playback_thread = None
    return result
