from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .schemas import PracticeStateUpdate, ProgressUpdate
from ..db.session import get_db
from ..services import quran_service


router = APIRouter(prefix="/api/quran", tags=["quran"])


@router.get("/surahs")
def surahs(query: str | None = None):
    return quran_service.resources().list_surahs(query)


@router.get("/surahs/{surah_id}/verses")
def verses(surah_id: int):
    rows = quran_service.resources().verses(surah_id)
    if not rows:
        raise HTTPException(404, "Surah not found")
    return rows


@router.get("/recitations")
def recitations():
    return quran_service.resources().list_recitations()


@router.get("/profiles")
def profiles(db: Session = Depends(get_db)):
    return quran_service.list_public_profiles(db)


@router.get("/profiles/{profile_id}")
def profile(profile_id: int, db: Session = Depends(get_db)):
    return quran_service.get_public_profile(db, profile_id)


@router.put("/profiles/{profile_id}/state")
def profile_state(profile_id: int, payload: PracticeStateUpdate, db: Session = Depends(get_db)):
    return quran_service.update_practice_state(db, profile_id, payload)


@router.put("/profiles/{profile_id}/progress/{verse_key}")
def profile_progress(profile_id: int, verse_key: str, payload: ProgressUpdate, db: Session = Depends(get_db)):
    return quran_service.update_progress(db, profile_id, verse_key, payload)
