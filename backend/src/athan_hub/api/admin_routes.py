from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from .schemas import AdminProfileCreate, AdminProfileUpdate
from ..db import models
from ..db.session import get_db
from ..services import quran_service


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
