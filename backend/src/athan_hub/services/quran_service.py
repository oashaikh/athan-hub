from __future__ import annotations

import re
import unicodedata
from functools import lru_cache

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..api.schemas import AdminProfileCreate, AdminProfileUpdate, PracticeStateUpdate, ProgressUpdate
from ..core.config import get_settings
from ..core.quran_resources import QuranResources
from ..core.time_utils import now_local
from ..db import models


THEME_BY_GENDER = {"boy": "night_explorer", "girl": "garden_light", None: "classic_mushaf"}


@lru_cache(maxsize=1)
def resources() -> QuranResources:
    settings = get_settings()
    return QuranResources(settings.quran_resource_db, settings.quran_manifest_path)


def _timestamp() -> str:
    return now_local().isoformat()


def _profile(db: Session, profile_id: int, *, active_only: bool = True) -> models.ChildProfile:
    profile = db.get(models.ChildProfile, profile_id)
    if profile is None or (active_only and not profile.active):
        raise HTTPException(404, "Profile not found")
    return profile


def profile_summary(db: Session, profile: models.ChildProfile, *, include_progress: bool = False) -> dict:
    progress = db.query(models.QuranProgress).filter_by(profile_id=profile.id).order_by(models.QuranProgress.verse_key).all()
    result = {
        "id": profile.id,
        "name": profile.name,
        "slug": profile.slug,
        "gender": profile.gender,
        "theme": profile.theme,
        "preferred_recitation_id": profile.preferred_recitation_id,
        "last_surah_id": profile.last_surah_id,
        "start_ayah": profile.start_ayah,
        "end_ayah": profile.end_ayah,
        "repetitions": profile.repetitions,
        "playback_speed": profile.playback_speed,
        "show_arabic": bool(profile.show_arabic),
        "show_translation": bool(profile.show_translation),
        "show_transliteration": bool(profile.show_transliteration),
        "recall_mode": bool(profile.recall_mode),
        "active": bool(profile.active),
        "memorised_count": sum(1 for row in progress if row.state == "memorised"),
        "practised_count": len(progress),
    }
    if include_progress:
        result["progress"] = [
            {
                "verse_key": row.verse_key,
                "state": row.state,
                "completed_repetitions": row.completed_repetitions,
                "last_practised_at": row.last_practised_at,
                "first_memorised_at": row.first_memorised_at,
            }
            for row in progress
        ]
    return result


def list_public_profiles(db: Session) -> list[dict]:
    rows = db.query(models.ChildProfile).filter_by(active=1).order_by(models.ChildProfile.name).all()
    return [profile_summary(db, row) for row in rows]


def get_public_profile(db: Session, profile_id: int) -> dict:
    return profile_summary(db, _profile(db, profile_id), include_progress=True)


def _slug_base(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().casefold()
    return re.sub(r"[^a-z0-9]+", "-", normalized).strip("-") or "profile"


def _unique_slug(db: Session, name: str, exclude_id: int | None = None) -> str:
    base = _slug_base(name)
    candidate = base
    suffix = 2
    while db.query(models.ChildProfile).filter(
        models.ChildProfile.slug == candidate,
        models.ChildProfile.id != exclude_id if exclude_id is not None else True,
    ).first():
        candidate = f"{base}-{suffix}"
        suffix += 1
    return candidate


def create_profile(db: Session, payload: AdminProfileCreate) -> dict:
    name = payload.name.strip()
    now = _timestamp()
    profile = models.ChildProfile(
        name=name,
        slug=_unique_slug(db, name),
        gender=payload.gender,
        theme=payload.theme or THEME_BY_GENDER[payload.gender],
        active=1,
        created_at=now,
        updated_at=now,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile_summary(db, profile)


def update_profile(db: Session, profile_id: int, payload: AdminProfileUpdate) -> dict:
    profile = _profile(db, profile_id, active_only=False)
    changes = payload.model_dump(exclude_unset=True)
    if "name" in changes:
        profile.name = changes["name"].strip()
        profile.slug = _unique_slug(db, profile.name, exclude_id=profile.id)
    if "gender" in changes:
        profile.gender = changes["gender"]
    if changes.get("theme") is not None:
        profile.theme = changes["theme"]
    profile.updated_at = _timestamp()
    db.commit()
    return profile_summary(db, profile)


def set_profile_active(db: Session, profile_id: int, active: bool) -> dict:
    profile = _profile(db, profile_id, active_only=False)
    profile.active = int(active)
    profile.updated_at = _timestamp()
    db.commit()
    return profile_summary(db, profile)


def delete_profile(db: Session, profile_id: int) -> None:
    profile = _profile(db, profile_id, active_only=False)
    for model in (models.QuranProgress, models.QuranSession, models.RewardEvent, models.ProfileBadge):
        db.query(model).filter_by(profile_id=profile_id).delete(synchronize_session=False)
    db.delete(profile)
    db.commit()


def _validate_range(surah_id: int, start_ayah: int, end_ayah: int) -> None:
    surahs = resources().list_surahs()
    surah = next((row for row in surahs if row["id"] == surah_id), None)
    if surah is None or start_ayah > end_ayah or end_ayah > surah["ayah_count"]:
        raise HTTPException(422, "Verse range is outside the selected surah")


def update_practice_state(db: Session, profile_id: int, payload: PracticeStateUpdate) -> dict:
    profile = _profile(db, profile_id)
    _validate_range(payload.surah_id, payload.start_ayah, payload.end_ayah)
    if payload.recitation_id is not None and resources().recitation(payload.recitation_id) is None:
        raise HTTPException(422, "Unknown QUL recitation")
    profile.preferred_recitation_id = payload.recitation_id
    profile.last_surah_id = payload.surah_id
    profile.start_ayah = payload.start_ayah
    profile.end_ayah = payload.end_ayah
    profile.repetitions = payload.repetitions
    profile.playback_speed = payload.playback_speed
    profile.show_arabic = int(payload.show_arabic)
    profile.show_translation = int(payload.show_translation)
    profile.show_transliteration = int(payload.show_transliteration)
    profile.recall_mode = int(payload.recall_mode)
    profile.updated_at = _timestamp()
    db.commit()
    return profile_summary(db, profile)


def update_progress(
    db: Session,
    profile_id: int,
    verse_key: str,
    payload: ProgressUpdate,
    *,
    allow_repetition_decrease: bool = False,
) -> dict:
    _profile(db, profile_id)
    try:
        surah_id, ayah_number = (int(value) for value in verse_key.split(":", 1))
    except (ValueError, TypeError):
        raise HTTPException(422, "Invalid verse key") from None
    _validate_range(surah_id, ayah_number, ayah_number)
    row = db.query(models.QuranProgress).filter_by(profile_id=profile_id, verse_key=verse_key).one_or_none()
    now = _timestamp()
    if row is None:
        row = models.QuranProgress(profile_id=profile_id, verse_key=verse_key, first_practised_at=now)
        db.add(row)
    row.state = payload.state
    row.completed_repetitions = (
        payload.completed_repetitions
        if allow_repetition_decrease
        else max(row.completed_repetitions or 0, payload.completed_repetitions)
    )
    row.last_practised_at = now
    if payload.state == "memorised" and not row.first_memorised_at:
        row.first_memorised_at = now
    db.commit()
    from . import reward_service

    memorised_count = db.query(models.QuranProgress).filter(
        models.QuranProgress.profile_id == profile_id,
        models.QuranProgress.verse_key.like(f"{surah_id}:%"),
        models.QuranProgress.state == "memorised",
    ).count()
    reward_service.reward_progress(db, profile_id, verse_key, memorised_count)
    return {
        "verse_key": row.verse_key,
        "state": row.state,
        "completed_repetitions": row.completed_repetitions,
        "last_practised_at": row.last_practised_at,
        "first_memorised_at": row.first_memorised_at,
    }
