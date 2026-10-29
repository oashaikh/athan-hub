import json
from types import SimpleNamespace

from athan_hub.core import home_assistant


class _Response:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None


def test_play_sends_ssml_audio_to_notify_service(monkeypatch) -> None:
    settings = SimpleNamespace(
        ha_url="http://ha:8123/",
        ha_token="secret",
        ha_notify_service="alexa_media_hallway_echo_pop",
        ha_audio_url="https://example.com/a/athan.mp3",
    )
    monkeypatch.setattr(home_assistant, "get_settings", lambda: settings)
    monkeypatch.setattr(home_assistant.time, "sleep", lambda _s: None)
    sent = []
    monkeypatch.setattr(home_assistant.urllib.request, "urlopen", lambda req, timeout: sent.append(req) or _Response())

    result = home_assistant.play(214)

    request = sent[0]
    assert request.full_url == "http://ha:8123/api/services/notify/alexa_media_hallway_echo_pop"
    assert request.get_header("Authorization") == "Bearer secret"
    assert json.loads(request.data) == {
        "message": '<audio src="https://example.com/a/athan.mp3"/>',
        "data": {"type": "tts"},
    }
    assert result["status"] == "played"
    assert home_assistant.enabled()
