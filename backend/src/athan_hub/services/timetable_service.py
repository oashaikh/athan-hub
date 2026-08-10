import datetime as dt
from typing import Any

from sqlalchemy.orm import Session

from ..core import csv_import
from ..core.config import get_settings
from ..core.time_utils import PRAYER_ORDER, combine_date_time, now_local
from ..db import models
from . import exclusions_service


settings = get_settings()
LAST_UPLOAD_FILE = settings.upload_dir / "latest.csv"


def save_csv_upload(content: bytes) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    LAST_UPLOAD_FILE.write_bytes(content)
    rows = csv_import.parse_csv(content)
    return rows[:7], rows


def import_csv(db: Session, content: bytes | None = None, replace_overrides: bool = False) -> dict[str, Any]:
    if content is None:
        if not LAST_UPLOAD_FILE.exists():
            raise ValueError("No timetable CSV has been uploaded")
        content = LAST_UPLOAD_FILE.read_bytes()
    rows = csv_import.parse_csv(content)
    updated_at = now_local().isoformat()
    for row in rows:
        db.merge(models.PrayerTime(**row, source="csv", updated_at=updated_at))
    if replace_overrides:
        dates = [row["date"] for row in rows]
        db.query(models.ManualOverride).filter(models.ManualOverride.date.in_(dates)).delete(synchronize_session=False)
    db.commit()
    return {"imported": len(rows), "preview": rows[:7]}


def get_day(db: Session, date_str: str) -> dict[str, Any]:
    base = db.get(models.PrayerTime, date_str)
    overrides = {row.prayer_name: row for row in db.query(models.ManualOverride).filter(models.ManualOverride.date == date_str).all()}
    prayers: dict[str, Any] = {}
    for prayer in ["fajr", "shurooq", "dhuhr", "asr", "maghrib", "isha"]:
        base_time = getattr(base, prayer) if base else None
        override = overrides.get(prayer)
        excluded = exclusions_service.is_excluded(db, date_str, prayer)
        effective = apply_override(base_time, override)
        source = "manual" if override else (base.source if base else "csv")
        prayers[prayer] = {
            "base": base_time,
            "override": override.time_hhmm if override else None,
            "enabled": True if override is None else bool(override.enabled),
            "effective": effective,
            "source": source,
            "excluded": excluded,
        }
    return {"date": date_str, "prayers": prayers}


def update_manual_overrides(db: Session, date_str: str, updates: dict[str, Any]) -> dict[str, Any]:
    now_iso = now_local().isoformat()
    for prayer, payload in updates.items():
        if prayer not in ["fajr", "shurooq", "dhuhr", "asr", "maghrib", "isha"]:
            continue
        existing = db.query(models.ManualOverride).filter(
            models.ManualOverride.date == date_str,
            models.ManualOverride.prayer_name == prayer,
        ).first()
        values = {
            "time_hhmm": payload.get("time"),
            "enabled": 1 if payload.get("enabled", True) else 0,
            "updated_at": now_iso,
        }
        if existing:
            for key, value in values.items():
                setattr(existing, key, value)
        else:
            db.add(models.ManualOverride(date=date_str, prayer_name=prayer, **values))
    db.commit()
    return get_day(db, date_str)


def apply_override(base_time: str | None, override: models.ManualOverride | None) -> str | None:
    if override is None:
        return base_time
    if override.enabled == 0:
        return None
    return override.time_hhmm or base_time


def effective_prayer_time(db: Session, date_str: str, prayer: str) -> str | None:
    base = db.get(models.PrayerTime, date_str)
    base_time = getattr(base, prayer) if base else None
    override = db.query(models.ManualOverride).filter(
        models.ManualOverride.date == date_str,
        models.ManualOverride.prayer_name == prayer,
    ).first()
    effective = apply_override(base_time, override)
    if not effective or exclusions_service.is_excluded(db, date_str, prayer):
        return None
    return effective


def build_schedule(db: Session, date_str: str, include_shurooq: bool = False) -> dict[str, str | None]:
    prayers = PRAYER_ORDER.copy()
    if include_shurooq:
        prayers.insert(1, "shurooq")
    return {prayer: effective_prayer_time(db, date_str, prayer) for prayer in prayers}


def record_playback(db: Session, date_str: str, prayer: str, hhmm: str, played_at: str | None = None) -> None:
    db.merge(models.PlaybackState(
        date=date_str,
        prayer_name=prayer,
        time_hhmm=hhmm,
        played_at=played_at or now_local().isoformat(),
    ))
    db.commit()


def has_played(db: Session, date_str: str, prayer: str, hhmm: str) -> bool:
    return db.query(models.PlaybackState).filter(
        models.PlaybackState.date == date_str,
        models.PlaybackState.prayer_name == prayer,
        models.PlaybackState.time_hhmm == hhmm,
    ).first() is not None


def upcoming_events(db: Session, include_shurooq: bool = False) -> list[tuple[str, str, dt.datetime]]:
    now = now_local()
    dates = [now.date().isoformat(), (now + dt.timedelta(days=1)).date().isoformat()]
    events = []
    for date_str in dates:
        for prayer, time_value in build_schedule(db, date_str, include_shurooq).items():
            value = combine_date_time(date_str, time_value)
            if value:
                events.append((date_str, prayer, value))
    events.sort(key=lambda item: item[2])
    return events
