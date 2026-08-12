import uuid

from fastapi.testclient import TestClient

from athan_hub.db import models
from athan_hub.db.migrations import init_db
from athan_hub.db.session import SessionLocal
from athan_hub.main import app
from athan_hub.services.reward_service import award, profile_rewards


def make_profile(db):
    suffix = uuid.uuid4().hex[:8]
    profile = models.ChildProfile(
        name=f"Reward child {suffix}",
        slug=f"reward-child-{suffix}",
        theme="classic_mushaf",
        active=1,
        created_at="2026-08-12T10:00:00+01:00",
        updated_at="2026-08-12T10:00:00+01:00",
    )
    db.add(profile)
    db.commit()
    return profile


def test_memorised_reward_is_awarded_once():
    init_db()
    with SessionLocal() as db:
        profile = make_profile(db)
        key = f"memorised:{profile.id}:1:1"
        assert award(db, profile.id, key, "memorised", 25)
        assert not award(db, profile.id, key, "memorised", 25)
        assert profile_rewards(db, profile.id)["stars"] == 25


def test_session_completion_and_progress_rewards_are_idempotent():
    init_db()
    with TestClient(app) as client:
        profile = client.post("/api/admin/profiles", json={"name": f"Session {uuid.uuid4().hex[:6]}"}).json()
        created = client.post(
            f"/api/quran/profiles/{profile['id']}/sessions",
            json={"surah_id": 1, "start_ayah": 1, "end_ayah": 1, "recitation_id": 100005},
        )
        assert created.status_code == 201
        session_id = created.json()["id"]
        payload = {"repetitions": 2, "practice_seconds": 60, "completed": True}
        first = client.put(f"/api/quran/profiles/{profile['id']}/sessions/{session_id}", json=payload)
        second = client.put(f"/api/quran/profiles/{profile['id']}/sessions/{session_id}", json=payload)
        assert first.status_code == 200
        assert second.status_code == 200

        progress = client.put(
            f"/api/quran/profiles/{profile['id']}/progress/1:1",
            json={"state": "memorised", "completed_repetitions": 2},
        )
        retry = client.put(
            f"/api/quran/profiles/{profile['id']}/progress/1:1",
            json={"state": "memorised", "completed_repetitions": 2},
        )
        assert progress.status_code == retry.status_code == 200

        rewards = client.get(f"/api/quran/profiles/{profile['id']}/rewards").json()
        assert rewards["stars"] == 37  # 10 daily practice + 2 repeats + 25 memorised
        assert "first_session" in rewards["badges"]
        assert rewards["streak"] == 1


def test_leaderboard_disabled_returns_hidden():
    init_db()
    with TestClient(app) as client:
        assert client.get("/api/quran/leaderboard").json() == {"enabled": False, "entries": []}
