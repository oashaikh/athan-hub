import datetime as dt
import hmac
import shutil
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from .schemas import BluetoothPairRequest, ManualUpdate, PinRequest, SettingsUpdate, TestPlayRequest
from ..core import pin_auth
from ..core.config import get_settings
from ..core.time_utils import now_local
from ..core import playback_state
from ..db import models
from ..db.session import get_db
from ..services import (
    audio_service,
    audit_service,
    bluetooth_service,
    exclusions_service,
    settings_service,
    timetable_service,
)


router = APIRouter(prefix="/api")
settings = get_settings()


async def _read_limited(file: UploadFile, limit: int, label: str) -> bytes:
    content = await file.read(limit + 1)
    if len(content) > limit:
        raise HTTPException(413, f"{label} exceeds the {limit // (1024 * 1024)} MB limit")
    if not content:
        raise HTTPException(400, f"{label} is empty")
    return content


def _looks_like_mp3(content: bytes) -> bool:
    return content.startswith(b"ID3") or (len(content) >= 2 and content[0] == 0xFF and content[1] & 0xE0 == 0xE0)


def _looks_like_image(content: bytes, suffix: str) -> bool:
    signatures = {
        ".png": lambda value: value.startswith(b"\x89PNG\r\n\x1a\n"),
        ".jpg": lambda value: value.startswith(b"\xff\xd8\xff"),
        ".jpeg": lambda value: value.startswith(b"\xff\xd8\xff"),
        ".webp": lambda value: len(value) >= 12 and value[:4] == b"RIFF" and value[8:12] == b"WEBP",
    }
    return signatures[suffix](content)


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "time": now_local().isoformat()}


@router.get("/public/config")
def public_config(db: Session = Depends(get_db)):
    values = settings_service.all_settings(db)
    return {
        "timezone": values.get("timezone", settings.timezone),
        "dashboard_background": values.get("dashboard_background", ""),
    }


@router.get("/settings")
def get_settings_api(db: Session = Depends(get_db)):
    return settings_service.all_settings(db)


@router.put("/settings")
def update_settings_api(payload: SettingsUpdate, db: Session = Depends(get_db)):
    values = payload.model_dump(exclude_none=True)
    try:
        settings_service.update_settings(db, values)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    audit_service.add_entry(db, "INFO", "Updated settings", values)
    return JSONResponse({"ok": True})


@router.post("/timetable/upload")
async def upload_timetable(file: UploadFile = File(...)):
    if not file.filename or Path(file.filename).suffix.lower() != ".csv":
        raise HTTPException(400, "Timetable must be a CSV file")
    content = await _read_limited(file, settings.timetable_upload_limit, "Timetable CSV")
    try:
        preview, rows = timetable_service.save_csv_upload(content)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"preview": preview, "rows": len(rows)}


@router.post("/timetable/import")
def import_timetable(replace_overrides: bool = False, db: Session = Depends(get_db)):
    try:
        result = timetable_service.import_csv(db, replace_overrides=replace_overrides)
        audit_service.add_entry(db, "INFO", "Imported timetable", result)
        return result
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/timetable/day")
def timetable_day(date: str, db: Session = Depends(get_db)):
    return timetable_service.get_day(db, date)


@router.put("/timetable/day")
def update_timetable_day(date: str, payload: ManualUpdate, db: Session = Depends(get_db)):
    return timetable_service.update_manual_overrides(db, date, payload.prayers)


@router.get("/timetable/next")
def next_prayer(db: Session = Depends(get_db)):
    now = now_local()
    events = [event for event in timetable_service.upcoming_events(db) if event[2] >= now]
    if not events:
        return {"next": None}
    date_str, prayer, when = events[0]
    return {"next": {"date": date_str, "prayer": prayer, "time": when.strftime("%H:%M"), "at": when.isoformat(), "countdown": int((when - now).total_seconds())}}


@router.get("/playback/status")
def playback_status(db: Session = Depends(get_db)):
    grace = bluetooth_service._get_int(db, "grace_seconds", 120)
    active = playback_state.read_active(grace_seconds=grace)
    return active or {"active": False, "remaining_seconds": 0}


@router.get("/bluetooth/status")
def bluetooth_status(db: Session = Depends(get_db)):
    return bluetooth_service.status(db)


@router.post("/bluetooth/connect")
def bluetooth_connect(db: Session = Depends(get_db)):
    try:
        result = bluetooth_service.connect_device(db)
        audit_service.add_entry(db, "INFO", "Connected Bluetooth", result)
        return result
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/bluetooth/scan")
def bluetooth_scan():
    try:
        return {"devices": bluetooth_service.discover_devices()}
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/bluetooth/pair")
def bluetooth_pair(payload: BluetoothPairRequest, db: Session = Depends(get_db)):
    try:
        result = bluetooth_service.pair_device(db, payload.mac)
        audit_service.add_entry(db, "INFO", "Paired Bluetooth device", {"mac": payload.mac})
        return result
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/bluetooth/disconnect")
def bluetooth_disconnect(db: Session = Depends(get_db)):
    try:
        return bluetooth_service.disconnect_device(db)
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc


def _test_audio(db: Session, prayer_name: str) -> Path:
    profile = audio_service.profile_for_prayer(db, prayer_name)
    if profile:
        return Path(profile.file_path)
    fallback = settings.audio_dir / "athan.mp3"
    if fallback.exists():
        return fallback
    raise HTTPException(400, "Upload and enable an MP3 audio profile first")


@router.post("/bluetooth/test-play")
def bluetooth_test(payload: TestPlayRequest, db: Session = Depends(get_db)):
    try:
        return bluetooth_service.test_play(db, _test_audio(db, payload.prayer_name))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/bluetooth/stop-test")
def bluetooth_stop():
    return bluetooth_service.stop_test()


@router.get("/audio/profiles")
def audio_profiles(db: Session = Depends(get_db)):
    return audio_service.profiles(db)


@router.post("/audio/upload")
async def audio_upload(name: str = Form("Athan"), file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename or Path(file.filename).suffix.lower() != ".mp3":
        raise HTTPException(400, "Only MP3 files are supported")
    content = await _read_limited(file, settings.audio_upload_limit, "MP3 audio")
    if not _looks_like_mp3(content):
        raise HTTPException(400, "Uploaded file does not appear to be a valid MP3")
    try:
        profile = audio_service.save_profile(db, name[:120], file.filename, content)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"id": profile.id, "name": profile.name, "enabled": bool(profile.enabled)}


@router.put("/audio/profiles/{profile_id}")
def audio_update(profile_id: int, payload: dict[str, Any], db: Session = Depends(get_db)):
    profile = db.get(models.AudioProfile, profile_id)
    if not profile:
        raise HTTPException(404, "Audio profile not found")
    if "enabled" in payload:
        profile.enabled = 1 if payload["enabled"] else 0
    if payload.get("name"):
        profile.name = str(payload["name"])
    db.commit()
    return {"ok": True}


@router.delete("/audio/profiles/{profile_id}")
def audio_delete(profile_id: int, db: Session = Depends(get_db)):
    profile = db.get(models.AudioProfile, profile_id)
    if not profile:
        raise HTTPException(404, "Audio profile not found")
    path = Path(profile.file_path)
    db.query(models.PrayerAudioMap).filter(models.PrayerAudioMap.audio_profile_id == profile_id).delete(synchronize_session=False)
    db.delete(profile)
    db.commit()
    audio_root = settings.audio_dir.resolve()
    resolved_path = path.resolve()
    if resolved_path.parent == audio_root:
        resolved_path.unlink(missing_ok=True)
    return {"ok": True}


@router.post("/audio/profiles/{profile_id}/test")
def audio_test(profile_id: int, db: Session = Depends(get_db)):
    profile = db.get(models.AudioProfile, profile_id)
    if not profile:
        raise HTTPException(404, "Audio profile not found")
    try:
        return bluetooth_service.test_play(db, Path(profile.file_path))
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/audio/mapping")
def audio_mapping(db: Session = Depends(get_db)):
    return audio_service.mapping(db)


@router.put("/audio/mapping")
def audio_mapping_update(payload: dict[str, int | None], db: Session = Depends(get_db)):
    audio_service.set_mapping(db, payload)
    return {"ok": True}


@router.get("/backgrounds")
def backgrounds():
    names = sorted(path.name for path in settings.background_dir.iterdir() if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"})
    return {"backgrounds": names}


@router.post("/backgrounds/upload")
async def background_upload(file: UploadFile = File(...)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg", ".webp"}:
        raise HTTPException(400, "Unsupported background image type")
    content = await _read_limited(file, settings.background_upload_limit, "Background image")
    if not _looks_like_image(content, suffix):
        raise HTTPException(400, "Uploaded file does not match its image extension")
    filename = audio_service.safe_filename(file.filename or f"background{suffix}")
    (settings.background_dir / filename).write_bytes(content)
    return {"filename": filename}


@router.get("/exclusions")
def exclusions(db: Session = Depends(get_db)):
    return exclusions_service.list_exclusions(db)


@router.post("/exclusions")
def exclusion_add(payload: dict[str, Any], db: Session = Depends(get_db)):
    row = models.Exclusion(
        kind=payload.get("kind") or "date",
        value=payload.get("value") or payload.get("date") or "",
        prayer_name=payload.get("prayer_name"),
        enabled=1 if payload.get("enabled", True) else 0,
        created_at=now_local().isoformat(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id}


@router.delete("/exclusions/{exclusion_id}")
def exclusion_delete(exclusion_id: int, db: Session = Depends(get_db)):
    row = db.get(models.Exclusion, exclusion_id)
    if not row:
        raise HTTPException(404, "Exclusion not found")
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.get("/logs")
def logs(limit: int = 100, db: Session = Depends(get_db)):
    return audit_service.list_entries(db, min(max(limit, 1), 500))


@router.get("/pin/status")
def pin_status(request: Request):
    return {"required": bool(settings.pin), "verified": not settings.pin or pin_auth.is_pin_valid(request, settings)}


@router.post("/pin/verify")
def pin_verify(payload: PinRequest, request: Request, response: Response):
    if not settings.pin or not hmac.compare_digest(payload.pin, settings.pin):
        raise HTTPException(401, "Invalid PIN")
    forwarded_proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    response.set_cookie(pin_auth.COOKIE_NAME, pin_auth.issue_token(settings), max_age=pin_auth.COOKIE_AGE, httponly=True, secure=forwarded_proto == "https", samesite="strict")
    return {"verified": True}
