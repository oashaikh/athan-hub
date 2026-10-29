import json
from types import SimpleNamespace

import pytest

from athan_hub.core import home_assistant


class _Response:
    def __init__(self, body: dict | None = None):
        self._body = json.dumps(body or {}).encode()

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None


class _FakeHomeAssistant:
    """Answers the few REST calls play() makes and records the service calls."""

    def __init__(self, echo_state="idle", dnd="off", volume=0.8, failures=0):
        self.states = {
            "media_player.hallway_echo_pop": {"state": echo_state, "attributes": {"volume_level": volume}},
            "switch.hallway_echo_pop_do_not_disturb": {"state": dnd},
        }
        self.calls = []
        self.failures = failures

    def urlopen(self, req, timeout):
        if self.failures:
            self.failures -= 1
            raise home_assistant.urllib.error.HTTPError(req.full_url, 400, "Bad Request", None, None)
        path = req.full_url.split(":8123", 1)[1]
        if req.get_method() == "GET":
            return _Response(self.states[path.removeprefix("/api/states/")])
        self.calls.append((path, json.loads(req.data)))
        return _Response()


@pytest.fixture
def settings(monkeypatch):
    value = SimpleNamespace(
        ha_url="http://ha:8123/",
        ha_token="secret",
        ha_notify_service="alexa_media_hallway_echo_pop",
        ha_audio_url="https://example.com/a/athan.mp3",
        ha_volume=0,
        ha_playback="clip",
    )
    monkeypatch.setattr(home_assistant, "get_settings", lambda: value)
    monkeypatch.setattr(home_assistant.time, "sleep", lambda _s: None)
    return value


def _install(monkeypatch, fake):
    monkeypatch.setattr(home_assistant.urllib.request, "urlopen", fake.urlopen)
    return fake


def test_play_sends_ssml_audio_to_notify_service(monkeypatch, settings) -> None:
    fake = _install(monkeypatch, _FakeHomeAssistant())

    result = home_assistant.play(214)

    assert fake.calls == [(
        "/api/services/notify/alexa_media_hallway_echo_pop",
        {"message": '<audio src="https://example.com/a/athan.mp3"/>', "data": {"type": "tts"}},
    )]
    assert result["status"] == "played"
    assert home_assistant.enabled()


def test_play_lifts_do_not_disturb_and_restores_volume(monkeypatch, settings) -> None:
    settings.ha_volume = 60
    fake = _install(monkeypatch, _FakeHomeAssistant(dnd="on", volume=0.3))

    home_assistant.play(214)

    assert [path for path, _ in fake.calls] == [
        "/api/services/switch/turn_off",
        "/api/services/media_player/volume_set",
        "/api/services/notify/alexa_media_hallway_echo_pop",
        "/api/services/media_player/volume_set",
        "/api/services/switch/turn_on",
    ]
    assert fake.calls[1][1]["volume_level"] == 0.6
    assert fake.calls[3][1]["volume_level"] == 0.3


def test_play_uses_a_per_prayer_audio_url(monkeypatch, settings) -> None:
    monkeypatch.setenv("ATHAN_HA_AUDIO_URL_FAJR", "https://example.com/a/fajr.mp3")
    fake = _install(monkeypatch, _FakeHomeAssistant())

    home_assistant.play(0, prayer="fajr")
    home_assistant.play(0, prayer="isha")

    assert "fajr.mp3" in fake.calls[0][1]["message"]
    assert "athan.mp3" in fake.calls[1][1]["message"]


def test_play_retries_while_home_assistant_restarts(monkeypatch, settings) -> None:
    fake = _install(monkeypatch, _FakeHomeAssistant(failures=2))

    assert home_assistant.play(0)["status"] == "played"
    assert len(fake.calls) == 1


def test_play_raises_when_the_echo_stays_unavailable(monkeypatch, settings) -> None:
    _install(monkeypatch, _FakeHomeAssistant(echo_state="unavailable"))

    with pytest.raises(home_assistant.EchoUnavailable):
        home_assistant.play(0, retry_seconds=0)


def test_play_picks_a_random_athan_and_plays_its_parts_in_order(monkeypatch, settings) -> None:
    settings.ha_audio_url = "https://example.com/a/one.mp3"
    monkeypatch.setenv("ATHAN_HA_AUDIO_URL_FAJR", "https://example.com/a/fajr-a.mp3+https://example.com/a/fajr-b.mp3")
    monkeypatch.setattr(home_assistant, "part_seconds", lambda url, fallback: 1.0)
    fake = _install(monkeypatch, _FakeHomeAssistant())

    result = home_assistant.play(0, prayer="fajr")

    messages = [data["message"] for path, data in fake.calls if "notify" in path]
    assert messages == ['<audio src="https://example.com/a/fajr-a.mp3"/>', '<audio src="https://example.com/a/fajr-b.mp3"/>']
    assert result["audio_url"].endswith("fajr-b.mp3")


def test_choose_athan_picks_from_the_comma_separated_list(monkeypatch, settings) -> None:
    settings.ha_audio_url = "https://example.com/a/one.mp3, https://example.com/a/two.mp3"
    monkeypatch.setattr(home_assistant.random, "choice", lambda options: options[-1])

    assert home_assistant.choose_athan("isha") == ["https://example.com/a/two.mp3"]


def test_play_asks_the_alexa_skill_when_configured(monkeypatch, settings) -> None:
    settings.ha_playback = "skill"
    fake = _install(monkeypatch, _FakeHomeAssistant())

    home_assistant.play(0, prayer="fajr")

    assert fake.calls[-1] == ("/api/services/media_player/play_media", {
        "entity_id": "media_player.hallway_echo_pop",
        "media_content_id": "ask call to prayer to play the fajr athan",
        "media_content_type": "custom",
    })
