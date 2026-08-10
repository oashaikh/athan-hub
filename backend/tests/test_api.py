from fastapi.testclient import TestClient

from athan_hub.main import app


def test_first_run_upload_workflow() -> None:
    with TestClient(app) as client:
        assert client.get("/api/health").status_code == 200
        settings = client.get("/api/settings").json()
        assert settings["echo_mac"] == ""
        assert settings["disconnect_after_play"] == "0"

        csv_data = b"date,fajr,shurooq,dhuhr,asr,maghrib,isha\n2026-08-10,03:46,05:41,13:20,17:21,20:53,21:58\n"
        response = client.post("/api/timetable/upload", files={"file": ("times.csv", csv_data, "text/csv")})
        assert response.status_code == 200
        assert response.json()["rows"] == 1
        assert client.post("/api/timetable/import").status_code == 200
        day = client.get("/api/timetable/day", params={"date": "2026-08-10"}).json()
        assert day["prayers"]["fajr"]["effective"] == "03:46"

        mp3 = b"ID3" + b"\x00" * 32
        response = client.post("/api/audio/upload", data={"name": "Test Athan"}, files={"file": ("athan.mp3", mp3, "audio/mpeg")})
        assert response.status_code == 200
        assert "file_path" not in response.json()
        profiles = client.get("/api/audio/profiles").json()
        assert profiles[0]["name"] == "Test Athan"
        assert "file_path" not in profiles[0]


def test_upload_validation_and_timezone_propagation() -> None:
    with TestClient(app) as client:
        invalid_csv = client.post("/api/timetable/upload", files={"file": ("times.txt", b"data", "text/plain")})
        assert invalid_csv.status_code == 400

        invalid_mp3 = client.post("/api/audio/upload", data={"name": "Bad"}, files={"file": ("bad.mp3", b"not mp3", "audio/mpeg")})
        assert invalid_mp3.status_code == 400

        too_large = client.post("/api/audio/upload", data={"name": "Large"}, files={"file": ("large.mp3", b"ID3" + b"0" * 1024, "audio/mpeg")})
        assert too_large.status_code == 413

        timezone = client.put("/api/settings", json={"timezone": "Etc/UTC"})
        assert timezone.status_code == 200
        assert client.get("/api/health").json()["time"].endswith("+00:00")

        unknown = client.put("/api/settings", json={"unexpected": "value"})
        assert unknown.status_code == 422
