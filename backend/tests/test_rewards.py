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
        assert award(db, profile.id, key, "memorisation_milestone", 25)
        assert not award(db, profile.id, key, "memorisation_milestone", 25)
        assert award(db, profile.id, f"legacy-ayah:{profile.id}", "memorised", 99)
        assert award(db, profile.id, f"legacy-repeat:{profile.id}", "repetition", 99)
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
        # 10 for the first completed practice session of the day, 1 for the memorised ayah.
        assert rewards["stars"] == 11
        assert "first_session" in rewards["badges"]
        assert rewards["streak"] == 1


def test_individual_ayahs_award_a_star_immediately():
    init_db()
    with TestClient(app) as client:
        profile = client.post("/api/admin/profiles", json={"name": f"Progress {uuid.uuid4().hex[:6]}"}).json()
        for ayah in range(1, 10):
            response = client.put(
                f"/api/quran/profiles/{profile['id']}/progress/2:{ayah}",
                json={"state": "memorised", "completed_repetitions": 10},
            )
            assert response.status_code == 200
            rewards = client.get(f"/api/quran/profiles/{profile['id']}/rewards").json()
            assert rewards["stars"] == ayah

        tenth = client.put(
            f"/api/quran/profiles/{profile['id']}/progress/2:10",
            json={"state": "memorised", "completed_repetitions": 10},
        )
        assert tenth.status_code == 200
        rewards = client.get(f"/api/quran/profiles/{profile['id']}/rewards").json()
        # 10 stars for the 10 memorised ayahs of surah 2, plus 25 for the 10-ayah milestone.
        assert rewards["stars"] == 35

        unmarked = client.put(
            f"/api/quran/profiles/{profile['id']}/progress/2:10",
            json={"state": "needs_practice", "completed_repetitions": 10},
        )
        assert unmarked.status_code == 200
        rewards = client.get(f"/api/quran/profiles/{profile['id']}/rewards").json()
        assert rewards["stars"] == 34


def test_completed_surah_awards_one_star_per_ayah():
    init_db()
    with TestClient(app) as client:
        profile = client.post("/api/admin/profiles", json={"name": f"Surah {uuid.uuid4().hex[:6]}"}).json()
        for ayah in range(1, 4):
            response = client.put(
                f"/api/quran/profiles/{profile['id']}/progress/108:{ayah}",
                json={"state": "memorised", "completed_repetitions": 1},
            )
            assert response.status_code == 200
        assert client.get(f"/api/quran/profiles/{profile['id']}/rewards").json()["stars"] == 3

        unmarked = client.put(
            f"/api/quran/profiles/{profile['id']}/progress/108:3",
            json={"state": "needs_practice", "completed_repetitions": 1},
        )
        assert unmarked.status_code == 200
        assert client.get(f"/api/quran/profiles/{profile['id']}/rewards").json()["stars"] == 2

        remarked = client.put(
            f"/api/quran/profiles/{profile['id']}/progress/108:3",
            json={"state": "memorised", "completed_repetitions": 1},
        )
        assert remarked.status_code == 200
        assert client.get(f"/api/quran/profiles/{profile['id']}/rewards").json()["stars"] == 3

        with SessionLocal() as db:
            assert db.query(models.RewardEvent).filter_by(
                profile_id=profile["id"],
                category="surah",
            ).count() == 1


def test_legacy_flat_surah_reward_is_corrected_to_ayah_count():
    init_db()
    with SessionLocal() as db:
        profile = make_profile(db)
        event = models.RewardEvent(
            profile_id=profile.id,
            event_key=f"surah:{profile.id}:114",
            category="surah",
            points=50,
            created_at="2026-08-12T10:00:00+01:00",
        )
        db.add(event)
        db.add_all(
            models.QuranProgress(
                profile_id=profile.id,
                verse_key=f"114:{ayah}",
                state="memorised",
            )
            for ayah in range(1, 7)
        )
        db.commit()

        assert profile_rewards(db, profile.id)["stars"] == 6
        db.refresh(event)
        assert event.points == 6


def test_first_surah_badge_is_revoked_when_surah_no_longer_complete():
    init_db()
    with TestClient(app) as client:
        profile = client.post("/api/admin/profiles", json={"name": f"Badge {uuid.uuid4().hex[:6]}"}).json()
        for ayah in range(1, 4):
            response = client.put(
                f"/api/quran/profiles/{profile['id']}/progress/108:{ayah}",
                json={"state": "memorised", "completed_repetitions": 1},
            )
            assert response.status_code == 200
        rewards = client.get(f"/api/quran/profiles/{profile['id']}/rewards").json()
        assert "first_surah" in rewards["badges"]

        unmarked = client.put(
            f"/api/quran/profiles/{profile['id']}/progress/108:3",
            json={"state": "needs_practice", "completed_repetitions": 1},
        )
        assert unmarked.status_code == 200
        rewards = client.get(f"/api/quran/profiles/{profile['id']}/rewards").json()
        assert "first_surah" not in rewards["badges"]

        remarked = client.put(
            f"/api/quran/profiles/{profile['id']}/progress/108:3",
            json={"state": "memorised", "completed_repetitions": 1},
        )
        assert remarked.status_code == 200
        rewards = client.get(f"/api/quran/profiles/{profile['id']}/rewards").json()
        assert "first_surah" in rewards["badges"]


def test_leaderboard_disabled_returns_hidden():
    init_db()
    with TestClient(app) as client:
        assert client.get("/api/quran/leaderboard").json() == {"enabled": False, "entries": []}
