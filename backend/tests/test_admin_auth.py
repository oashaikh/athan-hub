import pytest
from fastapi.testclient import TestClient

from athan_hub.core import pin_auth
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
