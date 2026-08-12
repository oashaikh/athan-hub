import hashlib
import re
import uuid
import os
import tempfile
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from ..core.config import get_settings
from ..core.audio_metadata import mp3_duration
from ..core.time_utils import now_local
from ..db import models


def safe_filename(value: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9_.-]+", "-", Path(value).name).strip("-.")
    return stem or "athan.mp3"


def save_profile(db: Session, name: str, filename: str, content: bytes) -> models.AudioProfile:
    settings = get_settings()
    clean_name = safe_filename(filename)
    target = settings.audio_dir / f"{uuid.uuid4().hex[:12]}-{clean_name}"
    with tempfile.NamedTemporaryFile(dir=settings.audio_dir, suffix=".mp3", delete=False) as temporary:
        temporary.write(content)
        temporary.flush()
        os.fsync(temporary.fileno())
        temporary_path = Path(temporary.name)
    try:
        duration = mp3_duration(temporary_path)
        os.replace(temporary_path, target)
    finally:
        temporary_path.unlink(missing_ok=True)
    profile = models.AudioProfile(
        name=name or target.stem,
        file_path=str(target),
        sha256=hashlib.sha256(content).hexdigest(),
        duration_seconds=duration,
        enabled=1,
        created_at=now_local().isoformat(),
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def profiles(db: Session) -> list[dict[str, Any]]:
    return [{"id": row.id, "name": row.name, "sha256": row.sha256, "duration_seconds": row.duration_seconds, "enabled": bool(row.enabled), "created_at": row.created_at} for row in db.query(models.AudioProfile).all()]


def mapping(db: Session) -> dict[str, int | None]:
    return {row.prayer_name: row.audio_profile_id for row in db.query(models.PrayerAudioMap).all()}


def set_mapping(db: Session, values: dict[str, int | None]) -> None:
    for prayer, profile_id in values.items():
        if prayer not in {"fajr", "dhuhr", "asr", "maghrib", "isha"}:
            continue
        current = db.get(models.PrayerAudioMap, prayer)
        if profile_id is None:
            if current:
                db.delete(current)
        elif db.get(models.AudioProfile, profile_id):
            db.merge(models.PrayerAudioMap(prayer_name=prayer, audio_profile_id=profile_id))
    db.commit()


def profile_for_prayer(db: Session, prayer: str) -> models.AudioProfile | None:
    row = db.get(models.PrayerAudioMap, prayer)
    if row and row.audio_profile_id:
        profile = db.get(models.AudioProfile, row.audio_profile_id)
        if profile and profile.enabled:
            return profile
    return db.query(models.AudioProfile).filter(models.AudioProfile.enabled == 1).first()
