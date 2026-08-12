import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from athan_hub.db import models
from athan_hub.db.migrations import init_db
from athan_hub.db.session import SessionLocal
from athan_hub.main import app
from fastapi.testclient import TestClient


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


def test_public_profile_state_is_strict_and_isolated():
    init_db()
    with TestClient(app) as client:
        # No PIN is configured in this test environment, so this setup request is
        # an authenticated-local equivalent; route classification is tested separately.
        created = client.post("/api/admin/profiles", json={"name": "Yusuf", "gender": "boy"})
        assert created.status_code == 201
        profile = created.json()
        assert profile["theme"] == "night_explorer"

        invalid = client.put(
            f"/api/quran/profiles/{profile['id']}/state",
            json={"name": "Changed"},
        )
        assert invalid.status_code == 422

        updated = client.put(
            f"/api/quran/profiles/{profile['id']}/state",
            json={
                "recitation_id": 100005,
                "surah_id": 1,
                "start_ayah": 1,
                "end_ayah": 7,
                "repetitions": 3,
                "playback_speed": 1.0,
                "show_arabic": True,
                "show_translation": True,
                "show_transliteration": False,
                "recall_mode": False,
            },
        )
        assert updated.status_code == 200
        assert updated.json()["last_surah_id"] == 1

        bad_range = client.put(
            f"/api/quran/profiles/{profile['id']}/state",
            json={
                "surah_id": 1,
                "start_ayah": 1,
                "end_ayah": 8,
                "repetitions": 3,
                "playback_speed": 1.0,
            },
        )
        assert bad_range.status_code == 422


def test_public_resources_and_progress_round_trip():
    init_db()
    with TestClient(app) as client:
        assert len(client.get("/api/quran/surahs").json()) == 114
        verses = client.get("/api/quran/surahs/1/verses").json()
        assert len(verses) == 7
        assert verses[0]["verse_key"] == "1:1"

        profile = client.post("/api/admin/profiles", json={"name": "Progress Child"}).json()
        response = client.put(
            f"/api/quran/profiles/{profile['id']}/progress/1:1",
            json={"state": "learning", "completed_repetitions": 2},
        )
        assert response.status_code == 200
        assert response.json()["completed_repetitions"] == 2
        detail = client.get(f"/api/quran/profiles/{profile['id']}").json()
        assert detail["progress"][0]["verse_key"] == "1:1"
