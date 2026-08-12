from __future__ import annotations

import datetime as dt

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..core.time_utils import now_local
from ..db import models


BADGES = {
    "first_session": ("sessions", 1),
    "streak_3": ("streak", 3),
    "streak_7": ("streak", 7),
    "streak_30": ("streak", 30),
    "ayahs_10": ("memorised", 10),
    "ayahs_50": ("memorised", 50),
    "ayahs_100": ("memorised", 100),
    "first_surah": ("surahs", 1),
    "hours_1": ("seconds", 3600),
    "hours_5": ("seconds", 5 * 3600),
    "hours_10": ("seconds", 10 * 3600),
}


def _now() -> str:
    return now_local().isoformat()


def award(db: Session, profile_id: int, key: str, category: str, points: int) -> bool:
    if db.query(models.RewardEvent.id).filter_by(event_key=key).first():
        return False
    try:
        with db.begin_nested():
            db.add(
                models.RewardEvent(
                    profile_id=profile_id,
                    event_key=key,
                    category=category,
                    points=points,
                    created_at=_now(),
                )
            )
            db.flush()
        db.commit()
        return True
    except IntegrityError:
        db.rollback()
        return False


def _completed_dates(db: Session, profile_id: int) -> list[dt.date]:
    rows = (
        db.query(models.QuranSession.ended_at)
        .filter_by(profile_id=profile_id, completed=1)
        .filter(models.QuranSession.ended_at.is_not(None))
        .all()
    )
    return sorted({dt.datetime.fromisoformat(row[0]).date() for row in rows})


def _streak(dates: list[dt.date]) -> int:
    if not dates:
        return 0
    streak = 1
    for current, previous in zip(reversed(dates[:-1]), reversed(dates[1:])):
        if previous - current != dt.timedelta(days=1):
            break
        streak += 1
    return streak


def _metrics(db: Session, profile_id: int) -> dict[str, int]:
    sessions = db.query(models.QuranSession).filter_by(profile_id=profile_id, completed=1)
    memorised = db.query(models.QuranProgress).filter_by(profile_id=profile_id, state="memorised").count()
    completed_surahs = (
        db.query(models.RewardEvent)
        .filter_by(profile_id=profile_id, category="surah")
        .count()
    )
    return {
        "sessions": sessions.count(),
        "streak": _streak(_completed_dates(db, profile_id)),
        "memorised": memorised,
        "surahs": completed_surahs,
        "seconds": int(sessions.with_entities(func.coalesce(func.sum(models.QuranSession.practice_seconds), 0)).scalar() or 0),
    }


def evaluate_badges(db: Session, profile_id: int) -> None:
    metrics = _metrics(db, profile_id)
    existing = {
        key for (key,) in db.query(models.ProfileBadge.badge_key).filter_by(profile_id=profile_id).all()
    }
    for badge_key, (metric, threshold) in BADGES.items():
        if badge_key not in existing and metrics[metric] >= threshold:
            db.add(models.ProfileBadge(profile_id=profile_id, badge_key=badge_key, awarded_at=_now()))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()


def profile_rewards(db: Session, profile_id: int) -> dict:
    stars = int(
        db.query(func.coalesce(func.sum(models.RewardEvent.points), 0))
        .filter_by(profile_id=profile_id)
        .scalar()
        or 0
    )
    badges = [
        key
        for (key,) in db.query(models.ProfileBadge.badge_key)
        .filter_by(profile_id=profile_id)
        .order_by(models.ProfileBadge.awarded_at, models.ProfileBadge.badge_key)
        .all()
    ]
    metrics = _metrics(db, profile_id)
    return {
        "stars": stars,
        "streak": metrics["streak"],
        "badges": badges,
        "memorised_count": metrics["memorised"],
        "practice_seconds": metrics["seconds"],
    }


def reward_progress(
    db: Session,
    profile_id: int,
    verse_key: str,
    previous_state: str | None,
    current_state: str,
    completed_repetitions: int,
    surah_complete: bool,
) -> None:
    day = now_local().date().isoformat()
    for repetition in range(1, min(completed_repetitions, 10) + 1):
        award(db, profile_id, f"repeat:{profile_id}:{verse_key}:{day}:{repetition}", "repetition", 1)
    if current_state == "memorised" and previous_state != "memorised":
        award(db, profile_id, f"memorised:{profile_id}:{verse_key}", "memorised", 25)
    if current_state == "memorised" and surah_complete:
        surah_id = verse_key.split(":", 1)[0]
        award(db, profile_id, f"surah:{profile_id}:{surah_id}", "surah", 50)
    evaluate_badges(db, profile_id)


def complete_session(db: Session, session: models.QuranSession, payload) -> dict:
    session.repetitions = max(session.repetitions, payload.repetitions)
    session.practice_seconds = max(session.practice_seconds, payload.practice_seconds)
    if payload.completed and not session.completed:
        session.completed = 1
        session.ended_at = _now()
    db.commit()
    if session.completed:
        day = dt.datetime.fromisoformat(session.ended_at).date().isoformat()
        award(db, session.profile_id, f"daily:{session.profile_id}:{day}", "daily_practice", 10)
        evaluate_badges(db, session.profile_id)
    return {
        "id": session.id,
        "profile_id": session.profile_id,
        "repetitions": session.repetitions,
        "practice_seconds": session.practice_seconds,
        "completed": bool(session.completed),
        "started_at": session.started_at,
        "ended_at": session.ended_at,
    }


def leaderboard(db: Session, week_start: dt.date | None = None) -> dict:
    enabled = (db.get(models.Setting, "leaderboard_enabled") or models.Setting(value="0", key="")).value == "1"
    if not enabled:
        return {"enabled": False, "entries": []}
    today = now_local().date()
    start = week_start or (today - dt.timedelta(days=today.weekday()))
    end = start + dt.timedelta(days=7)
    included = {
        "repetition": (db.get(models.Setting, "leaderboard_repetitions").value == "1"),
        "daily_practice": (db.get(models.Setting, "leaderboard_daily_practice").value == "1"),
        "memorised": (db.get(models.Setting, "leaderboard_memorised").value == "1"),
        "surah": (db.get(models.Setting, "leaderboard_surahs").value == "1"),
    }
    entries = []
    for profile in db.query(models.ChildProfile).filter_by(active=1).order_by(models.ChildProfile.name):
        points = 0
        for event in db.query(models.RewardEvent).filter_by(profile_id=profile.id):
            event_date = dt.datetime.fromisoformat(event.created_at).date()
            if start <= event_date < end and included.get(event.category, False):
                points += event.points
        entries.append({"profile_id": profile.id, "name": profile.name, "stars": points})
    entries.sort(key=lambda row: (-row["stars"], row["name"].casefold()))
    return {"enabled": True, "week_start": start.isoformat(), "entries": entries}
