import pytest
from fastapi.testclient import TestClient

from athan_hub.core import pin_auth
from athan_hub.api import admin_routes
from athan_hub.db import models
from athan_hub.db.session import SessionLocal
from athan_hub.main import app, settings


@pytest.fixture
def protected_client():
    old_pin, old_secret = settings.pin, settings.pin_secret
    settings.pin, settings.pin_secret = "246810", "test-secret"
    try:
        with TestClient(app) as client:
            yield client
    finally:
        settings.pin, settings.pin_secret = old_pin, old_secret


def authenticate(client: TestClient) -> None:
    assert client.post("/api/pin/verify", json={"pin": "246810"}).status_code == 200


def test_child_reads_remain_public_when_admin_pin_is_enabled(protected_client):
    assert protected_client.get("/api/public/config").status_code == 200
    assert protected_client.get("/api/timetable/next").status_code == 200


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("put", "/api/settings"),
        ("post", "/api/timetable/import"),
        ("post", "/api/bluetooth/connect"),
        ("get", "/api/logs"),
    ],
)
def test_system_api_requires_admin_pin(protected_client, method, path):
    response = protected_client.request(method, path, json={})
    assert response.status_code == 401
    assert response.json() == {"detail": "PIN_REQUIRED"}


def test_authenticated_admin_can_read_settings(protected_client):
    authenticate(protected_client)
    response = protected_client.get("/api/settings")
    assert response.status_code == 200
    assert "echo_mac" in response.json()


def test_route_classifier_keeps_quran_reads_and_practice_writes_public():
    assert not pin_auth.requires_admin("GET", "/api/quran/surahs")
    assert not pin_auth.requires_admin("PUT", "/api/quran/profiles/1/state")
    assert pin_auth.requires_admin("POST", "/api/admin/profiles")
    assert pin_auth.requires_admin("POST", "/api/audio/upload")


def test_only_admin_can_create_and_manage_profiles(protected_client):
    payload = {"name": "Maryam", "gender": "girl"}
    denied = protected_client.post("/api/admin/profiles", json=payload)
    assert denied.status_code == 401

    authenticate(protected_client)
    created = protected_client.post("/api/admin/profiles", json=payload)
    assert created.status_code == 201
    profile = created.json()
    assert profile["theme"] == "garden_light"

    assert protected_client.post(f"/api/admin/profiles/{profile['id']}/archive").status_code == 200
    assert all(row["id"] != profile["id"] for row in protected_client.get("/api/quran/profiles").json())
    assert protected_client.post(f"/api/admin/profiles/{profile['id']}/restore").status_code == 200
    corrected = protected_client.put(
        f"/api/admin/profiles/{profile['id']}/progress/1:1",
        json={"state": "needs_practice", "completed_repetitions": 4},
    )
    assert corrected.status_code == 200
    assert corrected.json()["state"] == "needs_practice"
    lowered = protected_client.put(
        f"/api/admin/profiles/{profile['id']}/progress/1:1",
        json={"state": "learning", "completed_repetitions": 1},
    )
    assert lowered.json()["completed_repetitions"] == 1


def test_admin_can_pin_cached_audio_and_start_download(protected_client, monkeypatch, tmp_path):
    authenticate(protected_client)
    path = tmp_path / "cached.mp3"
    path.write_bytes(b"ID3cached")
    with SessionLocal() as db:
        row = models.QuranAudioCache(recitation_id=99_999, content_key="1", local_path=str(path), source_url="https://example.test/1.mp3", byte_count=path.stat().st_size, sha256="x", pinned=0, created_at="2026-01-01T00:00:00+00:00", last_accessed_at="2026-01-01T00:00:00+00:00")
        db.add(row)
        db.commit()
        cache_id = row.id

    assert protected_client.put(f"/api/admin/quran/cache/{cache_id}", json={"pinned": True}).json()["pinned"] is True
    summary = protected_client.get("/api/admin/quran/cache").json()
    assert next(item for item in summary["items"] if item["id"] == cache_id)["pinned"] is True

    calls = []
    monkeypatch.setattr(admin_routes, "_prefetch_quran_audio", lambda recitation_id, surah_id: calls.append((recitation_id, surah_id)))
    recitation_id = protected_client.get("/api/quran/recitations").json()[0]["id"]
    response = protected_client.post("/api/admin/quran/cache/prefetch", json={"recitation_id": recitation_id, "surah_id": 1})
    assert response.status_code == 202
    assert calls == [(recitation_id, 1)]


def test_quran_settings_and_provenance_are_admin_only(protected_client):
    assert protected_client.get("/api/admin/quran/settings").status_code == 401
    assert protected_client.get("/api/admin/quran/sources").status_code == 401
    authenticate(protected_client)

    updated = protected_client.put(
        "/api/admin/quran/settings",
        json={"quran_cache_limit_bytes": 256 * 1024 * 1024},
    )
    assert updated.status_code == 200
    assert updated.json()["quran_cache_limit_bytes"] == 256 * 1024 * 1024
    sources = protected_client.get("/api/admin/quran/sources").json()
    assert sources["database"]["surahs"] == 114
    assert len(sources["commit"]) == 40
    assert sources["mirror"] == "https://github.com/oashaikh/quranic-universal-library"
    assert "Saheeh International" in sources["notice"]
