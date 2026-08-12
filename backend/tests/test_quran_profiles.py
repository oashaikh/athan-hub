import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from athan_hub.db import models
from athan_hub.db.migrations import init_db
from athan_hub.db.session import SessionLocal


def test_quran_profile_tables_and_unique_progress():
    init_db()
    suffix = uuid.uuid4().hex[:8]
    with SessionLocal() as db:
        profile = models.ChildProfile(
            name=f"Yusuf {suffix}",
            slug=f"yusuf-{suffix}",
            theme="night_explorer",
            active=1,
            created_at="2026-08-12T10:00:00+01:00",
            updated_at="2026-08-12T10:00:00+01:00",
        )
        db.add(profile)
        db.commit()
        db.add(models.QuranProgress(profile_id=profile.id, verse_key="1:1", state="learning"))
        db.commit()
        db.add(models.QuranProgress(profile_id=profile.id, verse_key="1:1", state="memorised"))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()


def test_reward_events_use_unique_semantic_keys():
    init_db()
    suffix = uuid.uuid4().hex[:8]
    with SessionLocal() as db:
        profile = models.ChildProfile(
            name=f"Maryam {suffix}",
            slug=f"maryam-{suffix}",
            theme="garden_light",
            active=1,
            created_at="2026-08-12T10:00:00+01:00",
            updated_at="2026-08-12T10:00:00+01:00",
        )
        db.add(profile)
        db.commit()
        key = f"memorised:{profile.id}:1:1"
        db.add(models.RewardEvent(profile_id=profile.id, event_key=key, category="memorised", points=25, created_at="2026-08-12T10:00:00+01:00"))
        db.commit()
        db.add(models.RewardEvent(profile_id=profile.id, event_key=key, category="memorised", points=25, created_at="2026-08-12T10:01:00+01:00"))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()


def test_audio_profile_has_duration_column():
    init_db()
    assert hasattr(models.AudioProfile, "duration_seconds")
