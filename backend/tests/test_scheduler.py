import datetime as dt
from pathlib import Path
from types import SimpleNamespace

from athan_hub.core import scheduler


class _Session:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None


def _configure_tick(monkeypatch, now_values: list[dt.datetime], event_time: dt.datetime) -> None:
    values = iter(now_values)
    monkeypatch.setattr(scheduler, "SessionLocal", _Session)
    monkeypatch.setattr(scheduler, "now_local", lambda: next(values))
    monkeypatch.setattr(
        scheduler.timetable_service,
        "upcoming_events",
        lambda _db: [(event_time.date().isoformat(), "asr", event_time)],
    )
    monkeypatch.setattr(scheduler.timetable_service, "has_played", lambda *_args: False)
    monkeypatch.setattr(scheduler.timetable_service, "record_playback", lambda *_args: None)
    monkeypatch.setattr(
        scheduler.audio_service,
        "profile_for_prayer",
        lambda _db, _prayer: SimpleNamespace(
            id=7,
            file_path=str(Path("/tmp/athan.mp3")),
            duration_seconds=180,
        ),
    )
    monkeypatch.setattr(scheduler.bluetooth_service, "get_echo_mac", lambda _db: "AA:BB:CC:DD:EE:FF")
    monkeypatch.setattr(
        scheduler.bluetooth_service,
        "_get_int",
        lambda _db, key, default: {
            "pre_connect_seconds": 30,
            "connect_retry_seconds": 20,
            "grace_seconds": 120,
            "sink_volume_percent": 100,
        }.get(key, default),
    )
    monkeypatch.setattr(scheduler.bluetooth_service, "_get_bool", lambda *_args: False)
    monkeypatch.setattr(scheduler.audit_service, "add_entry", lambda *_args: None)
    monkeypatch.setattr(scheduler.playback_state, "write_active", lambda *_args: None)
    monkeypatch.setattr(scheduler.playback_state, "clear_active", lambda: None)
    scheduler._prepared_occurrences.clear()


def test_tick_does_not_prepare_before_takeover_window(monkeypatch) -> None:
    event_time = dt.datetime(2026, 8, 29, 18, 0, tzinfo=dt.timezone.utc)
    _configure_tick(monkeypatch, [event_time - dt.timedelta(seconds=31)] * 2, event_time)
    preparations: list[dict] = []
    plays: list[dict] = []
    monkeypatch.setattr(scheduler, "prepare_output", lambda *args, **kwargs: preparations.append(kwargs))
    monkeypatch.setattr(scheduler, "play_once", lambda *args, **kwargs: plays.append(kwargs))

    delay = scheduler.tick()

    assert preparations == []
    assert plays == []
    assert delay == 1


def test_tick_prepares_once_inside_window_without_playing(monkeypatch) -> None:
    event_time = dt.datetime(2026, 8, 29, 18, 0, tzinfo=dt.timezone.utc)
    now = event_time - dt.timedelta(seconds=30)
    _configure_tick(monkeypatch, [now] * 4, event_time)
    preparations: list[dict] = []
    plays: list[dict] = []
    monkeypatch.setattr(
        scheduler,
        "prepare_output",
        lambda *args, **kwargs: preparations.append(kwargs) or {"status": "ready", "sink": "bluez_output.test"},
    )
    monkeypatch.setattr(scheduler, "play_once", lambda *args, **kwargs: plays.append(kwargs))

    scheduler.tick()
    scheduler.tick()

    assert len(preparations) == 1
    assert preparations[0]["timeout_seconds"] == 30
    assert plays == []


def test_failed_takeover_still_plays_when_prayer_becomes_due(monkeypatch) -> None:
    event_time = dt.datetime(2026, 8, 29, 18, 0, tzinfo=dt.timezone.utc)
    _configure_tick(
        monkeypatch,
        [event_time - dt.timedelta(seconds=30), event_time, event_time],
        event_time,
    )
    plays: list[dict] = []

    def fail_preparation(*_args, **_kwargs):
        raise RuntimeError("speaker is still owned by another source")

    monkeypatch.setattr(scheduler, "prepare_output", fail_preparation)
    monkeypatch.setattr(
        scheduler,
        "play_once",
        lambda *args, **kwargs: plays.append(kwargs) or {"status": "played"},
    )

    scheduler.tick()

    assert len(plays) == 1
