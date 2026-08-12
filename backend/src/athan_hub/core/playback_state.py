from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
import tempfile

from .config import get_settings


class PlaybackStateStore:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def write_active(
        self,
        prayer: str,
        profile_id: int,
        duration_seconds: float,
        started_at: dt.datetime,
    ) -> None:
        if started_at.tzinfo is None:
            raise ValueError("Playback start time must be timezone-aware")
        expected_finish = started_at + dt.timedelta(seconds=duration_seconds)
        payload = {
            "prayer": prayer,
            "audio_profile_id": profile_id,
            "started_at": started_at.isoformat(),
            "duration_seconds": duration_seconds,
            "expected_finish_at": expected_finish.isoformat(),
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", dir=self.path.parent, encoding="utf-8", delete=False) as temporary:
            json.dump(payload, temporary, separators=(",", ":"), sort_keys=True)
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_path = Path(temporary.name)
        try:
            os.replace(temporary_path, self.path)
        finally:
            temporary_path.unlink(missing_ok=True)

    def clear_active(self) -> None:
        self.path.unlink(missing_ok=True)

    def read_active(
        self,
        now: dt.datetime | None = None,
        grace_seconds: int = 120,
    ) -> dict | None:
        del grace_seconds  # Kept for API compatibility; playback ends at the measured media duration.
        if not self.path.is_file():
            return None
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            expected_finish = dt.datetime.fromisoformat(payload["expected_finish_at"])
        except (ValueError, KeyError, json.JSONDecodeError, OSError):
            self.clear_active()
            return None
        current = now or dt.datetime.now(expected_finish.tzinfo or dt.timezone.utc)
        if current >= expected_finish:
            self.clear_active()
            return None
        payload["active"] = True
        payload["remaining_seconds"] = max(0, int((expected_finish - current).total_seconds() + 0.999))
        return payload


def _store() -> PlaybackStateStore:
    return PlaybackStateStore(get_settings().playback_state_path)


def write_active(prayer: str, profile_id: int, duration_seconds: float, started_at: dt.datetime) -> None:
    _store().write_active(prayer, profile_id, duration_seconds, started_at)


def clear_active() -> None:
    _store().clear_active()


def read_active(now: dt.datetime | None = None, grace_seconds: int = 120) -> dict | None:
    return _store().read_active(now, grace_seconds)
