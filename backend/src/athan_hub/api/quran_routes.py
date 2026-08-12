from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .schemas import PracticeStateUpdate, ProgressUpdate, SessionCreate, SessionUpdate
from ..core.time_utils import now_local
from ..db import models
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


@router.post("/profiles/{profile_id}/sessions", status_code=201)
def create_session(profile_id: int, payload: SessionCreate, db: Session = Depends(get_db)):
    quran_service.get_public_profile(db, profile_id)
    quran_service._validate_range(payload.surah_id, payload.start_ayah, payload.end_ayah)
    if payload.recitation_id is not None and quran_service.resources().recitation(payload.recitation_id) is None:
        raise HTTPException(422, "Unknown QUL recitation")
    session = models.QuranSession(
        profile_id=profile_id,
        surah_id=payload.surah_id,
        start_ayah=payload.start_ayah,
        end_ayah=payload.end_ayah,
        recitation_id=payload.recitation_id,
        started_at=now_local().isoformat(),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return {"id": session.id, "started_at": session.started_at}


@router.put("/profiles/{profile_id}/sessions/{session_id}")
def update_session(profile_id: int, session_id: int, payload: SessionUpdate, db: Session = Depends(get_db)):
    quran_service.get_public_profile(db, profile_id)
    session = db.get(models.QuranSession, session_id)
    if session is None or session.profile_id != profile_id:
        raise HTTPException(404, "Session not found")
    from ..services import reward_service

    return reward_service.complete_session(db, session, payload)


@router.get("/profiles/{profile_id}/rewards")
def rewards(profile_id: int, db: Session = Depends(get_db)):
    quran_service.get_public_profile(db, profile_id)
    from ..services import reward_service

    return reward_service.profile_rewards(db, profile_id)


@router.get("/leaderboard")
def get_leaderboard(db: Session = Depends(get_db)):
    from ..services import reward_service

    return reward_service.leaderboard(db)
