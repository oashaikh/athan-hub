from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from .schemas import AdminProfileCreate, AdminProfileUpdate, LeaderboardSettingsUpdate
from ..db import models
from ..db.session import get_db
from ..services import quran_service
from ..services import settings_service


router = APIRouter(prefix="/api/admin", tags=["admin"])


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


@router.get("/quran/rewards")
def reward_settings(db: Session = Depends(get_db)):
    values = settings_service.all_settings(db)
    return {
        "enabled": values["leaderboard_enabled"] == "1",
        "repetitions": values["leaderboard_repetitions"] == "1",
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
            "leaderboard_repetitions": payload.repetitions,
            "leaderboard_daily_practice": payload.daily_practice,
            "leaderboard_memorised": payload.memorised,
            "leaderboard_surahs": payload.surahs,
        },
    )
    return reward_settings(db)


@router.get("/quran/cache")
def quran_cache(db: Session = Depends(get_db)):
    from ..services.quran_cache_service import default_cache_service

    return default_cache_service(db).cache_summary(db)


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
