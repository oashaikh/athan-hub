import json
import os
import random
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Optional
from xml.sax.saxutils import quoteattr

from .config import get_settings


class EchoUnavailable(RuntimeError):
    """Home Assistant reports the Echo as unavailable, so a notify call would play nothing."""


def enabled() -> bool:
    settings = get_settings()
    return bool(settings.ha_token and settings.ha_notify_service and settings.ha_audio_url)


def _echo_slug() -> str:
    return get_settings().ha_notify_service.removeprefix("alexa_media_")


def audio_url(prayer: Optional[str] = None) -> str:
    """The athan setting for this prayer: ATHAN_HA_AUDIO_URL_<PRAYER> if set, else ATHAN_HA_AUDIO_URL.

    The value is a comma-separated list of athans to choose from at random. An athan
    longer than Alexa's 240-second limit is split into parts joined with "+", which are
    played back to back.
    """
    if prayer:
        override = os.environ.get(f"ATHAN_HA_AUDIO_URL_{prayer.upper()}", "")
        if override:
            return override
    return get_settings().ha_audio_url


def choose_athan(prayer: Optional[str] = None) -> list[str]:
    """Pick one athan at random for this prayer and return its part URLs in order."""
    choices = [choice.strip() for choice in audio_url(prayer).split(",") if choice.strip()]
    return [part.strip() for part in random.choice(choices).split("+") if part.strip()]


def part_seconds(url: str, fallback: float) -> float:
    """Playing time of a hosted part, from its size: Alexa's format is constant 48 kbps (6000 bytes/s)."""
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=10) as response:
            size = int(response.headers.get("Content-Length") or 0)
        return size / 6000 if size else fallback
    except (urllib.error.URLError, OSError, ValueError):
        return fallback


def _call(method: str, path: str, payload: Optional[dict] = None, timeout_seconds: int = 20) -> Any:
    settings = get_settings()
    request = urllib.request.Request(
        f"{settings.ha_url.rstrip('/')}{path}",
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={"Authorization": f"Bearer {settings.ha_token}", "Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        body = response.read()
        return json.loads(body) if body else {}


def _state(entity_id: str) -> Optional[dict]:
    try:
        return _call("GET", f"/api/states/{entity_id}")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def _service(domain: str, service: str, data: dict) -> None:
    _call("POST", f"/api/services/{domain}/{service}", data)


def play(
    duration_seconds: float,
    prayer: Optional[str] = None,
    timeout_seconds: int = 20,
    retry_seconds: int = 90,
) -> Dict[str, Any]:
    """Play the hosted athan on the Echo through Home Assistant, then wait for it to finish.

    Amazon fetches the audio itself, so the URL must be public HTTPS in Alexa's MP3
    format (48 kbps, 24 kHz, at most 240 seconds). Do Not Disturb silences the Echo
    without any error, so it is switched off for the athan and restored afterwards, as
    is the volume when ATHAN_HA_VOLUME is set.
    """
    settings = get_settings()
    media_player = f"media_player.{_echo_slug()}"
    dnd_switch = f"switch.{_echo_slug()}_do_not_disturb"
    parts = choose_athan(prayer)

    # Home Assistant answers 400/5xx for a minute or so while it restarts, so keep trying.
    deadline = time.monotonic() + retry_seconds
    dnd_was_on = False
    previous_volume = None
    while True:
        try:
            echo = _state(media_player)
            if echo is not None and echo.get("state") == "unavailable":
                raise EchoUnavailable(f"{media_player} is unavailable in Home Assistant")
            dnd = _state(dnd_switch)
            dnd_on_now = bool(dnd and dnd.get("state") == "on")
            dnd_was_on = dnd_was_on or dnd_on_now
            if dnd_on_now:
                _service("switch", "turn_off", {"entity_id": dnd_switch})
            if previous_volume is None:
                previous_volume = (echo or {}).get("attributes", {}).get("volume_level")
            if settings.ha_volume and echo is not None:
                _service("media_player", "volume_set", {"entity_id": media_player, "volume_level": settings.ha_volume / 100})
            _service("notify", settings.ha_notify_service, {"message": f"<audio src={quoteattr(parts[0])}/>", "data": {"type": "tts"}})
            break
        except (urllib.error.URLError, OSError, EchoUnavailable):
            if time.monotonic() >= deadline:
                raise
            time.sleep(5)

    if len(parts) == 1:
        time.sleep(max(0.0, duration_seconds))
    else:
        # Each later part is sent as the previous one ends; Alexa queues nothing itself.
        for previous, part in zip(parts, parts[1:]):
            time.sleep(part_seconds(previous, duration_seconds / len(parts)))
            _service("notify", settings.ha_notify_service, {"message": f"<audio src={quoteattr(part)}/>", "data": {"type": "tts"}})
        time.sleep(part_seconds(parts[-1], 0))
    try:
        if settings.ha_volume and previous_volume is not None:
            _service("media_player", "volume_set", {"entity_id": media_player, "volume_level": previous_volume})
        if dnd_was_on:
            _service("switch", "turn_on", {"entity_id": dnd_switch})
    except (urllib.error.URLError, OSError):
        pass  # the athan has played; failing to restore volume or DND must not mark it failed
    return {
        "status": "played",
        "output": "home_assistant",
        "service": settings.ha_notify_service,
        "audio_url": "+".join(parts),
        "dnd_lifted": dnd_was_on,
        "volume": settings.ha_volume or None,
    }
