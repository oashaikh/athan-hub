import json
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from .schemas import AdminProfileCreate, AdminProfileUpdate, LeaderboardSettingsUpdate, ProgressUpdate, QuranCacheUpdate, QuranPrefetchRequest, QuranSettingsUpdate
from ..core.config import get_settings
from ..db import models
from ..db.session import SessionLocal, get_db
from ..services import quran_service
from ..services import settings_service


router = APIRouter(prefix="/api/admin", tags=["admin"])
logger = logging.getLogger(__name__)


@router.get("/profiles")
def profiles(db: Session = Depends(get_db)):
    rows = db.query(models.ChildProfile).order_by(models.ChildProfile.name).all()
    return [quran_service.profile_summary(db, row) for row in rows]


@router.post("/profiles", status_code=status.HTTP_201_CREATED)
def create_profile(payload: AdminProfileCreate, db: Session = Depends(get_db)):
    return quran_service.create_profile(db, payload)


@router.put("/profiles/{profile_id}")
def update_profile(profile_id: int, payload: AdminProfileUpdate, db: Session = Depends(get_db)):
    return quran_service.update_profile(db, profile_id, payload)


@router.post("/profiles/{profile_id}/archive")
def archive_profile(profile_id: int, db: Session = Depends(get_db)):
    return quran_service.set_profile_active(db, profile_id, False)


@router.post("/profiles/{profile_id}/restore")
def restore_profile(profile_id: int, db: Session = Depends(get_db)):
    return quran_service.set_profile_active(db, profile_id, True)


@router.delete("/profiles/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_profile(profile_id: int, db: Session = Depends(get_db)):
    quran_service.delete_profile(db, profile_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/profiles/{profile_id}/progress/{verse_key}")
def correct_profile_progress(profile_id: int, verse_key: str, payload: ProgressUpdate, db: Session = Depends(get_db)):
    return quran_service.update_progress(
        db,
        profile_id,
        verse_key,
        payload,
        allow_repetition_decrease=True,
    )


@router.get("/quran/rewards")
def reward_settings(db: Session = Depends(get_db)):
    values = settings_service.all_settings(db)
    return {
        "enabled": values["leaderboard_enabled"] == "1",
        "repetitions": False,
        "daily_practice": values["leaderboard_daily_practice"] == "1",
        "memorised": values["leaderboard_memorised"] == "1",
        "surahs": values["leaderboard_surahs"] == "1",
    }


@router.put("/quran/rewards")
def update_reward_settings(payload: LeaderboardSettingsUpdate, db: Session = Depends(get_db)):
    settings_service.update_settings(
        db,
        {
            "leaderboard_enabled": payload.enabled,
            "leaderboard_repetitions": False,
            "leaderboard_daily_practice": payload.daily_practice,
            "leaderboard_memorised": payload.memorised,
            "leaderboard_surahs": payload.surahs,
        },
    )
    return reward_settings(db)


@router.get("/quran/settings")
def quran_settings(db: Session = Depends(get_db)):
    values = settings_service.all_settings(db)
    return {"quran_cache_limit_bytes": int(values["quran_cache_limit_bytes"])}


@router.put("/quran/settings")
def update_quran_settings(payload: QuranSettingsUpdate, db: Session = Depends(get_db)):
    settings_service.update_settings(db, payload.model_dump())
    return quran_settings(db)


@router.get("/quran/sources")
def quran_sources():
    settings = get_settings()
    manifest = json.loads(settings.quran_manifest_path.read_text(encoding="utf-8"))
    notice_path = settings.quran_manifest_path.with_name("NOTICE.md")
    return {
        "repository": manifest["qul_repository"],
        "mirror": manifest.get("qul_mirror"),
        "commit": manifest["qul_commit"],
        "snapshot_at": manifest["snapshot_at"],
        "schema_version": manifest["schema_version"],
        "database": manifest["database"],
        "datasets": manifest["datasets"],
        "notice": notice_path.read_text(encoding="utf-8"),
    }


@router.get("/quran/cache")
def quran_cache(db: Session = Depends(get_db)):
    from ..services.quran_cache_service import default_cache_service

    return default_cache_service(db).cache_summary(db)


@router.put("/quran/cache/{cache_id}")
def update_quran_cache(cache_id: int, payload: QuranCacheUpdate, db: Session = Depends(get_db)):
    from ..services.quran_cache_service import default_cache_service

    if not default_cache_service(db).set_pinned(db, cache_id, payload.pinned):
        raise HTTPException(404, "Cached recording not found")
    return {"id": cache_id, "pinned": payload.pinned}


def _prefetch_quran_audio(recitation_id: int, surah_id: int | None) -> None:
    from ..services.quran_cache_service import CacheQuotaError, CacheSourceError, resolve_audio

    recitation = quran_service.resources().recitation(recitation_id)
    if recitation is None:
        return
    surah_ids = [surah_id] if surah_id else range(1, 115)
    with SessionLocal() as db:
        for selected_surah in surah_ids:
            verses = quran_service.resources().verses(selected_surah)
            keys = [verse["verse_key"] for verse in verses] if recitation["source_kind"] == "ayah" else [None]
            for verse_key in keys:
                try:
                    resolve_audio(db, recitation_id, verse_key, selected_surah)
                except (CacheQuotaError, CacheSourceError, OSError, TimeoutError) as exc:
                    logger.warning("Quran pre-download skipped %s/%s: %s", recitation_id, verse_key or selected_surah, exc)


@router.post("/quran/cache/prefetch", status_code=status.HTTP_202_ACCEPTED)
def prefetch_quran_cache(payload: QuranPrefetchRequest, tasks: BackgroundTasks):
    if quran_service.resources().recitation(payload.recitation_id) is None:
        raise HTTPException(404, "Recitation not found")
    tasks.add_task(_prefetch_quran_audio, payload.recitation_id, payload.surah_id)
    return {"accepted": True}


@router.delete("/quran/cache/{cache_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_quran_cache(cache_id: int, db: Session = Depends(get_db)):
    from pathlib import Path

    row = db.get(models.QuranAudioCache, cache_id)
    if row is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    Path(row.local_path).unlink(missing_ok=True)
    db.delete(row)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
