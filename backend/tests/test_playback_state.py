import datetime as dt
from pathlib import Path

from athan_hub.core.playback_state import PlaybackStateStore


def test_runtime_state_lifecycle_and_stale_expiry(tmp_path):
    store = PlaybackStateStore(tmp_path / "athan-active.json")
    started = dt.datetime(2026, 8, 12, 17, 0, tzinfo=dt.timezone.utc)
    store.write_active("asr", 4, 2.0, started)

    active = store.read_active(started + dt.timedelta(seconds=1), grace_seconds=120)
    assert active["prayer"] == "asr"
    assert active["remaining_seconds"] == 1

    assert store.read_active(started + dt.timedelta(seconds=123), grace_seconds=120) is None
    assert not store.path.exists()


def test_clear_active_is_idempotent(tmp_path):
    store = PlaybackStateStore(tmp_path / "athan-active.json")
    store.clear_active()
    store.write_active("fajr", 1, 30.0, dt.datetime.now(dt.timezone.utc))
    store.clear_active()
    store.clear_active()
    assert not store.path.exists()
